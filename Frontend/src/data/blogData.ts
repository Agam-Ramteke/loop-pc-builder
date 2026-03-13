export interface BlogPost {
  id: string;
  title: string;
  excerpt: string;
  image: string;
  date: string;
  category: string;
  readTime: string;
  slug: string;
}

export const blogPosts: BlogPost[] = [
  {
    id: 'blog-1',
    title: 'Best Budget Gaming PCs You Can Build in 2026',
    excerpt: 'Building a capable gaming PC doesn\'t have to break the bank. We explore the best value components for a sub-₹50K build that handles 1080p gaming with ease.',
    image: 'https://images.unsplash.com/photo-1593640408182-31c70c8268f5?q=80&w=600&auto=format&fit=crop',
    date: 'Mar 10, 2026',
    category: 'Build Guide',
    readTime: '8 min read',
    slug: 'best-budget-gaming-pcs-2026',
  },
  {
    id: 'blog-2',
    title: 'RTX 5070 Ti vs RX 9070 XT: The Ultimate Mid-Range Showdown',
    excerpt: 'NVIDIA and AMD are going head-to-head in the mid-range GPU market. We compare performance, efficiency, and value to help you pick the right card.',
    image: 'https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=600&auto=format&fit=crop',
    date: 'Mar 8, 2026',
    category: 'Comparison',
    readTime: '12 min read',
    slug: 'rtx-5070ti-vs-rx-9070xt',
  },
  {
    id: 'blog-3',
    title: 'DDR5 RAM: Is It Finally Worth Upgrading?',
    excerpt: 'DDR5 prices have dropped significantly. We test whether the bandwidth improvements translate to real-world gaming and productivity gains over DDR4.',
    image: 'https://images.unsplash.com/photo-1563770660941-20978e870e26?q=80&w=600&auto=format&fit=crop',
    date: 'Mar 5, 2026',
    category: 'Analysis',
    readTime: '6 min read',
    slug: 'ddr5-ram-worth-upgrading',
  },
  {
    id: 'blog-4',
    title: 'How to Choose the Right Power Supply for Your Build',
    excerpt: 'Don\'t cheap out on your PSU. Learn about efficiency ratings, modular vs non-modular, and how to calculate the wattage you actually need.',
    image: 'https://images.unsplash.com/photo-1585800473926-24e543666f7f?q=80&w=600&auto=format&fit=crop',
    date: 'Mar 2, 2026',
    category: 'Guide',
    readTime: '10 min read',
    slug: 'choose-right-power-supply',
  },
];
