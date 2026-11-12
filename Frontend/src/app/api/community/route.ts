import { NextResponse } from 'next/server';
import { cacheGet, cacheSet } from '@/lib/redis';
import { XMLParser } from 'fast-xml-parser';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export interface YTVideo {
  id: string;
  title: string;
  channel: string;
  description: string;
  thumbnail: string;
  publishedAt: string;
  viewCount: string;
  url: string;
  source: 'curated' | 'search';
}

export interface RedditPost {
  id: string;
  subreddit: string;
  title: string;
  score: number;
  numComments: number;
  author: string;
  flair: string | null;
  url: string;
  createdUtc: number;
  preview: string;
}

interface CommunityPayload {
  youtube: YTVideo[];
  reddit: RedditPost[];
}

// YouTube Data API interfaces removed in favor of RSS parsing

interface RedditListingChild {
  data: {
    id: string;
    subreddit: string;
    title: string;
    score: number;
    num_comments: number;
    author: string;
    link_flair_text?: string | null;
    permalink: string;
    created_utc: number;
    selftext?: string;
    stickied?: boolean;
  };
}

interface RedditListingResponse {
  data?: {
    children?: RedditListingChild[];
  };
}

const CACHE_KEY = 'community:feed:v5';
const CACHE_TTL_SECONDS = 300;

const CURATED_CHANNELS = [
  { id: 'UCXuqSBlHAE6Xw-yeJA0Tunw', name: 'Linus Tech Tips' },
  { id: 'UCBS1NUWY7oC6FFHaXQy4zAA', name: "Zack's Tech Turf" },
];

const REDDIT_URLS = [
  'https://www.reddit.com/r/buildapc/hot.json?limit=25',
  'https://www.reddit.com/r/IndianGaming/hot.json?limit=25',
];

const ALLOWED_KEYWORDS = [
  'PC',
  'PC build',
  'gaming PC',
  'GPU',
  'graphics card',
  'CPU',
  'RAM',
  'motherboard',
  'SSD',
  'storage',
  'power supply',
  'cooler',
  'case',
  'review',
  'benchmark',
  'performance',
  'FPS',
  'gaming setup',
  'PC upgrade',
  'budget PC',
  'budget build',
  'RTX',
  'Ryzen',
  'Intel',
  'gaming laptop',
  'monitor',
  'keyboard',
  'mouse',
  'PC gaming',
  'thermal',
  'overclocking',
  'compatibility',
  'PC specs',
  'gaming performance',
  'PC configuration',
  'PC troubleshooting',
];

const REJECT_KEYWORDS = [
  'reaction',
  'reacts to',
  'drama',
  'this changes everything',
  "you won't believe",
  'mind blowing',
];

const matchesKeywords = (title: string, description = '', titleOnly = false) => {
  const text = titleOnly ? title.toLowerCase() : `${title} ${description}`.toLowerCase();
  
  const hasReject = REJECT_KEYWORDS.some((keyword) => {
    const regex = new RegExp(`\\b${keyword.toLowerCase()}\\b`, 'i');
    return regex.test(text);
  });

  if (hasReject) return false;

  return ALLOWED_KEYWORDS.some((keyword) => {
    const regex = new RegExp(`\\b${keyword.toLowerCase()}\\b`, 'i');
    return regex.test(text);
  });
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T | null> {
  try {
    const response = await fetch(url, init);
    if (!response.ok) {
      console.error(`Fetch failed for ${url.split('?')[0]}: ${response.status} ${response.statusText}`);
      try {
        const errBody = await response.json();
        console.error('Error body:', JSON.stringify(errBody));
      } catch {
        // ignore
      }
      return null;
    }
    return (await response.json()) as T;
  } catch (err) {
    console.error(`Fetch error for ${url.split('?')[0]}:`, err);
    return null;
  }
}

async function getYoutubeVideosFromRSS(channelId: string, channelName: string): Promise<YTVideo[]> {
  try {
    const url = `https://www.youtube.com/feeds/videos.xml?channel_id=${channelId}`;
    const response = await fetch(url, { 
      headers: { 'User-Agent': 'LoopPC/1.0' },
      cache: 'no-store' 
    });
    if (!response.ok) {
      console.error(`RSS fetch failed for channel ${channelName}: ${response.status} ${response.statusText}`);
      try {
        const errText = await response.text();
        console.error(`RSS fetch error body for ${channelName}:`, errText.substring(0, 500));
      } catch (e) {
        // ignore
      }
      return [];
    }
    
    const xmlData = await response.text();
    const parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: '@_',
    });
    
    const parsed = parser.parse(xmlData);
    const entries = parsed?.feed?.entry;
    if (!entries) return [];

    const videos: YTVideo[] = [];
    // Ensure entries is an array
    const entryArray = Array.isArray(entries) ? entries : [entries];

    for (const entry of entryArray) {
      const title = entry.title || '';
      const description = entry['media:group']?.['media:description'] || '';

      if (!matchesKeywords(title, description, true)) {
        // console.log(`[FILTERED] ${channelName}: ${title}`);
        continue;
      }

      console.log(`[MATCHED] ${channelName}: ${title}`);

      const videoId = entry['yt:videoId'];
      const thumbnailObj = entry['media:group']?.['media:thumbnail'];
      let thumbnailUrl = '';
      if (thumbnailObj && thumbnailObj['@_url']) {
        thumbnailUrl = thumbnailObj['@_url'];
      }

      videos.push({
        id: videoId || '',
        title,
        channel: channelName,
        description: description.length > 120 ? `${description.substring(0, 120)}...` : description,
        thumbnail: thumbnailUrl,
        publishedAt: entry.published || new Date().toISOString(),
        viewCount: entry['media:group']?.['media:community']?.['media:statistics']?.['@_views'] || '0',
        url: `https://www.youtube.com/watch?v=${videoId}`,
        source: 'curated',
      });
      
      if (videos.length >= 10) break;
    }

    return videos;
  } catch (err) {
    console.error(`Error parsing RSS for channel ${channelName}:`, err);
    return [];
  }
}

async function fetchRedditData(): Promise<RedditPost[]> {
  try {
    const responses = await Promise.all(
      REDDIT_URLS.map((url) =>
        fetchJson<RedditListingResponse>(url, {
          headers: { 'User-Agent': 'LoopPC/1.0' },
          cache: 'no-store',
        }),
      ),
    );

    const posts = responses.flatMap((response) => response?.data?.children || []);

    const filtered = posts
      .filter((post) => !post.data.stickied)
      .filter((post) => matchesKeywords(post.data.title, post.data.selftext || '', false))
      .map((post) => ({
        id: post.data.id,
        subreddit: post.data.subreddit,
        title: post.data.title,
        score: post.data.score,
        numComments: post.data.num_comments,
        author: post.data.author,
        flair: post.data.link_flair_text || null,
        url: `https://reddit.com${post.data.permalink}`,
        createdUtc: post.data.created_utc,
        preview: post.data.selftext
          ? `${post.data.selftext.substring(0, 120)}${post.data.selftext.length > 120 ? '...' : ''}`
          : '',
      }));

    const buildapc = filtered.filter((post) => post.subreddit.toLowerCase() === 'buildapc').slice(0, 3);
    const indianGaming = filtered.filter((post) => post.subreddit.toLowerCase() === 'indiangaming').slice(0, 3);

    return [...buildapc, ...indianGaming];
  } catch (error) {
    console.error('Error fetching Reddit data:', error);
    return [];
  }
}

export async function GET() {
  const cached = await cacheGet<CommunityPayload>(CACHE_KEY);
  if (cached) {
    return NextResponse.json({ ...cached, fromCache: true });
  }

  const rssPromises = CURATED_CHANNELS.map(channel => getYoutubeVideosFromRSS(channel.id, channel.name));
  const rssResults = await Promise.all(rssPromises);
  
  // Interleave results from different channels
  const interleaved: YTVideo[] = [];
  const maxPerChannel = Math.max(...rssResults.map(r => r.length));
  for (let i = 0; i < maxPerChannel; i++) {
    for (const channelResults of rssResults) {
      if (channelResults[i]) {
        interleaved.push(channelResults[i]);
      }
    }
  }

  const [reddit] = await Promise.all([
    fetchRedditData(),
  ]);

  const payload: CommunityPayload = {
    youtube: interleaved.slice(0, 4),
    reddit,
  };

  void cacheSet(CACHE_KEY, payload, CACHE_TTL_SECONDS);

  return NextResponse.json({
    ...payload,
    fromCache: false,
  });
}
