export interface Tweet {
  id: string;
  avatar: string;
  displayName: string;
  handle: string;
  content: string;
  likes: number;
  retweets: number;
  timestamp: string;
}

export interface RedditPost {
  id: string;
  title: string;
  author: string;
  upvotes: number;
  comments: number;
  subreddit: string;
  flair: string;
  timestamp: string;
  preview?: string;
}

export const tweets: Tweet[] = [
  {
    id: 'tweet-1',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=techguru',
    displayName: 'TechGuru',
    handle: '@techguru_builds',
    content: 'Just finished my new Ryzen 9 9950X build and the temps are insane with the Kraken Elite 🥶 Highly recommend the AM5 platform for anyone building fresh in 2026.',
    likes: 342,
    retweets: 87,
    timestamp: '2h',
  },
  {
    id: 'tweet-2',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=pcmaster',
    displayName: 'PC Master Race',
    handle: '@pcmasterrace',
    content: 'The RTX 5070 Ti is hitting amazing price points in India right now. If you\'ve been waiting to upgrade from a 3060, NOW is the time 🔥',
    likes: 1203,
    retweets: 456,
    timestamp: '5h',
  },
  {
    id: 'tweet-3',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=budgetbuilder',
    displayName: 'Budget Builder',
    handle: '@budget_builds_in',
    content: 'Built my little brother a gaming PC under ₹40K. i5-13400F + RX 7600 combo is unbeatable for 1080p. Check my thread for the full parts list! 🧵',
    likes: 891,
    retweets: 234,
    timestamp: '8h',
  },
  {
    id: 'tweet-4',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=overclockking',
    displayName: 'Overclock King',
    handle: '@oc_king_india',
    content: 'PSA: The Deepcool AK620 is ₹2,499 on PrimeABGB right now. Best air cooler deal I\'ve seen all year. Grab it before it\'s gone.',
    likes: 567,
    retweets: 189,
    timestamp: '12h',
  },
];

export const redditPosts: RedditPost[] = [
  {
    id: 'reddit-1',
    title: 'Finally completed my first build! Ryzen 7 7800X3D + RTX 4070 Super',
    author: 'u/first_time_builder',
    upvotes: 2847,
    comments: 342,
    subreddit: 'r/buildapc',
    flair: 'Build Complete',
    timestamp: '6h ago',
    preview: 'After months of research and saving, I finally pulled the trigger. Total cost came to about ₹1.2L. Couldn\'t be happier with the performance!',
  },
  {
    id: 'reddit-2',
    title: 'Is it worth waiting for AM6 or should I buy AM5 now?',
    author: 'u/upgrade_dilemma',
    upvotes: 1523,
    comments: 487,
    subreddit: 'r/buildapc',
    flair: 'Discussion',
    timestamp: '12h ago',
    preview: 'AM5 has matured nicely with DDR5 prices dropping. But AM6 is rumored for late 2026...',
  },
  {
    id: 'reddit-3',
    title: '[India] Best places to buy PC parts online? PrimeABGB vs Amazon vs Vedant',
    author: 'u/indian_pcbuilder',
    upvotes: 934,
    comments: 256,
    subreddit: 'r/IndianGaming',
    flair: 'Buying Advice',
    timestamp: '1d ago',
    preview: 'Comparing prices across major Indian retailers. Spreadsheet in comments.',
  },
  {
    id: 'reddit-4',
    title: 'The 7800X3D is STILL the best gaming CPU in 2026 — here\'s why',
    author: 'u/gaming_benchmarks',
    upvotes: 3201,
    comments: 891,
    subreddit: 'r/buildapc',
    flair: 'Discussion',
    timestamp: '2d ago',
    preview: 'Despite newer releases, the 3D V-Cache advantage is holding strong in modern titles.',
  },
];
