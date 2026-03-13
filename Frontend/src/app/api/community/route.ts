import { NextResponse } from 'next/server';
import { unstable_cache } from 'next/cache';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

// ─── Types ─────────────────────────────────────────────────────────
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

// ─── YouTube Config ────────────────────────────────────────────────
const YT_API = 'https://www.googleapis.com/youtube/v3';
const YT_KEY = process.env.YOUTUBE_API_KEY || '';

const CURATED_CHANNELS = [
  { id: 'UCXuqSBlHAE6Xw-yeJA0Tunw', name: 'Linus Tech Tips' },
  { id: 'UCa4hiEkXbVY4VjGMO6mHQ',   name: 'Tech Burner' },
  { id: 'UCBS1NUWY7oC6FFHaXQy4zAA',  name: "Zack's Tech Turf" },
];

const SEARCH_QUERIES = [
  { q: 'PC build India 2026',    regionCode: 'IN' },
  { q: 'GPU review 2026',        regionCode: 'IN' },
  { q: 'budget gaming PC India', regionCode: 'IN' },
];

const ALLOWED_KEYWORDS = [
  'PC build', 'gaming PC', 'GPU', 'graphics card', 'CPU', 'RAM', 'motherboard',
  'SSD', 'storage', 'power supply', 'cooler', 'case', 'review', 'benchmark',
  'performance', 'FPS', 'gaming setup', 'PC upgrade', 'budget PC', 'budget build',
  'RTX', 'Ryzen', 'Intel', 'gaming laptop', 'monitor', 'keyboard', 'mouse',
  'PC gaming', 'thermal', 'overclocking', 'compatibility', 'PC specs',
  'gaming performance', 'PC configuration', 'PC troubleshooting'
];

const matchesKeywords = (title: string, description: string = '', titleOnly: boolean = false) => {
  const text = titleOnly ? title.toLowerCase() : (title + ' ' + description).toLowerCase();
  return ALLOWED_KEYWORDS.some(kw => {
    const regex = new RegExp(`\\b${kw.toLowerCase()}\\b`, 'i');
    return regex.test(text);
  });
};

// ─── YouTube: Curated (latest video from each channel) ─────────────
const fetchCuratedVideos = unstable_cache(async (): Promise<YTVideo[]> => {
  if (!YT_KEY) return [];
  try {
    const videos: YTVideo[] = [];

    for (const ch of CURATED_CHANNELS) {
      const uploadsPlaylistId = 'UU' + ch.id.slice(2);

      const plRes = await fetch(
        `${YT_API}/playlistItems?part=snippet&playlistId=${uploadsPlaylistId}&maxResults=10&key=${YT_KEY}`,
        { cache: 'no-store' }
      );
      if (!plRes.ok) continue;
      const plData = await plRes.json();
      
      for (const item of plData.items || []) {
        const videoId = item.snippet.resourceId.videoId;
        const title = item.snippet.title;

        // Strictly match title for YouTube to avoid irrelevant matches in description links
        if (!matchesKeywords(title, '', true)) continue;

        const statsRes = await fetch(
          `${YT_API}/videos?part=statistics&id=${videoId}&key=${YT_KEY}`,
          { cache: 'no-store' }
        );
        let viewCount = '0';
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          viewCount = statsData.items?.[0]?.statistics?.viewCount || '0';
        }

        videos.push({
          id: videoId,
          title,
          channel: ch.name,
          description: item.snippet.description || '',
          thumbnail: item.snippet.thumbnails?.medium?.url || item.snippet.thumbnails?.default?.url || '',
          publishedAt: item.snippet.publishedAt,
          viewCount,
          url: `https://www.youtube.com/watch?v=${videoId}`,
          source: 'curated',
        });
        break; 
      }
    }

    return videos;
  } catch (error) {
    console.error('Error fetching curated YouTube videos:', error);
    return [];
  }
}, ['youtube-curated-v5'], { revalidate: 300 });

// ─── YouTube: Search (trending videos per query) ───────────────────
const fetchSearchVideos = unstable_cache(async (): Promise<YTVideo[]> => {
  if (!YT_KEY) return [];
  try {
    const videos: YTVideo[] = [];

    for (const sq of SEARCH_QUERIES) {
      const searchRes = await fetch(
        `${YT_API}/search?part=snippet&type=video&maxResults=15&regionCode=${sq.regionCode}&q=${encodeURIComponent(sq.q)}&key=${YT_KEY}`,
        { cache: 'no-store' }
      );
      if (!searchRes.ok) continue;
      const searchData = await searchRes.json();

      for (const item of searchData.items || []) {
        const videoId = item.id.videoId;
        const title = item.snippet.title;

        if (!matchesKeywords(title, '', true)) continue;

        const descriptionSnippet = item.snippet.description || '';
        const truncatedDesc = descriptionSnippet.length > 120 
          ? descriptionSnippet.substring(0, 120) + '...' 
          : descriptionSnippet;

        videos.push({
          id: videoId,
          title,
          channel: item.snippet.channelTitle,
          description: truncatedDesc,
          thumbnail: item.snippet.thumbnails?.medium?.url || item.snippet.thumbnails?.default?.url || '',
          publishedAt: item.snippet.publishedAt,
          viewCount: '0', 
          url: `https://www.youtube.com/watch?v=${videoId}`,
          source: 'search',
        });
      }
    }

    return videos;
  } catch (error) {
    console.error('Error fetching search YouTube videos:', error);
    return [];
  }
}, ['youtube-search-v5'], { revalidate: 300 });

// ─── Reddit ────────────────────────────────────────────────────────
const REDDIT_URLS = [
  'https://www.reddit.com/r/buildapc/hot.json?limit=25',
  'https://www.reddit.com/r/IndianGaming/hot.json?limit=25',
];

const fetchRedditData = unstable_cache(async (): Promise<RedditPost[]> => {
  try {
    const results = await Promise.all(
      REDDIT_URLS.map(url =>
        fetch(url, { headers: { 'User-Agent': 'LoopPC/1.0' }, cache: 'no-store' })
          .then(res => { if (!res.ok) throw new Error(`Reddit ${res.status}`); return res.json(); })
      )
    );

    const posts = results.flatMap(r => r.data.children);

    const filtered = posts
      .filter((p: any) => !p.data.stickied)
      .filter((p: any) => matchesKeywords(p.data.title, p.data.selftext || '', false))
      .map((p: any) => ({
        id: p.data.id,
        subreddit: p.data.subreddit,
        title: p.data.title,
        score: p.data.score,
        numComments: p.data.num_comments,
        author: p.data.author,
        flair: p.data.link_flair_text || null,
        url: `https://reddit.com${p.data.permalink}`,
        createdUtc: p.data.created_utc,
        preview: p.data.selftext
          ? p.data.selftext.substring(0, 120) + (p.data.selftext.length > 120 ? '...' : '')
          : '',
      }));

    const buildapc = filtered.filter((p: any) => p.subreddit.toLowerCase() === 'buildapc').slice(0, 3);
    const indianGaming = filtered.filter((p: any) => p.subreddit.toLowerCase() === 'indiangaming').slice(0, 3);

    return [...buildapc, ...indianGaming];
  } catch (error) {
    console.error('Error fetching Reddit data:', error);
    return [];
  }
}, ['reddit-posts-v5'], { revalidate: 300 });

// ─── GET Handler ───────────────────────────────────────────────────
export async function GET() {
  const [curated, search, reddit] = await Promise.all([
    fetchCuratedVideos(),
    fetchSearchVideos(),
    fetchRedditData(),
  ]);

  const curatedChannelNames = new Set(CURATED_CHANNELS.map(c => c.name.toLowerCase()));
  const dedupedSearch = search.filter(v => !curatedChannelNames.has(v.channel.toLowerCase()));

  const interleaved: YTVideo[] = [];
  const maxLen = Math.max(curated.length, dedupedSearch.length);
  for (let i = 0; i < maxLen; i++) {
    if (i < curated.length) interleaved.push(curated[i]);
    if (i < dedupedSearch.length) interleaved.push(dedupedSearch[i]);
  }
  const cappedYoutube = interleaved.slice(0, 4);

  return NextResponse.json({
    debugVer: '4.1-fixed-cache',
    youtube: cappedYoutube,
    reddit,
  });
}
