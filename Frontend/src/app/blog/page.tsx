import type { Metadata } from 'next';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowUpRight,
  BookOpen,
  Clock3,
  ExternalLink,
  Flame,
  Globe,
  MessageSquare,
  Newspaper,
  Sparkles,
} from 'lucide-react';
import { blogPosts } from '@/data/blogData';
import { redditPosts } from '@/data/communityData';

export const metadata: Metadata = {
  title: 'Blog | Loop PC Builder',
  description: 'Placeholder blog coverage and Reddit discussions for PC builders.',
};

const editorialSources = [
  { name: "Tom's Hardware", label: 'Benchmarks and buying advice' },
  { name: 'PC Gamer', label: 'Gaming-focused component picks' },
  { name: 'AnandTech', label: 'Architecture and performance analysis' },
  { name: 'TechPowerUp', label: 'GPU and PSU roundups' },
];

const featuredPost = {
  ...blogPosts[0],
  source: editorialSources[0].name,
  sourceLabel: editorialSources[0].label,
};

const curatedPosts = blogPosts.map((post, index) => ({
  ...post,
  source: editorialSources[index % editorialSources.length].name,
  sourceLabel: editorialSources[index % editorialSources.length].label,
}));

export default function BlogPage() {
  return (
    <section className="pb-20 pt-8">
      <div className="container mx-auto px-4">
        <div className="mb-8 rounded-[2rem] border border-border-gray bg-mid-gray/70 p-6 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur dark:bg-mid-gray/90 dark:shadow-[0_30px_80px_rgba(0,0,0,0.38)] md:p-8">
          <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-neon-blue/30 bg-neon-blue/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.32em] text-neon-blue">
                <BookOpen className="h-3.5 w-3.5" />
                LoopPC Blog
              </div>
              <h1 className="max-w-xl text-4xl font-heading font-bold tracking-tight text-foreground md:text-5xl">
                Build intel, editor picks, and Reddit signals in one place.
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-gray-500 dark:text-gray-400">
                A frontend placeholder blog hub for curated articles from across PC hardware sites, plus community posts worth watching while we wire in a real content backend later.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-border-gray bg-background/80 px-4 py-3 dark:bg-background/70">
                <div className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">Sources</div>
                <div className="mt-2 text-2xl font-bold text-foreground">4</div>
                <div className="text-sm text-gray-500">Editorial sites</div>
              </div>
              <div className="rounded-2xl border border-border-gray bg-background/80 px-4 py-3 dark:bg-background/70">
                <div className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">Threads</div>
                <div className="mt-2 text-2xl font-bold text-foreground">{redditPosts.length}</div>
                <div className="text-sm text-gray-500">Reddit posts</div>
              </div>
              <div className="rounded-2xl border border-border-gray bg-background/80 px-4 py-3 dark:bg-background/70">
                <div className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500">Mode</div>
                <div className="mt-2 text-2xl font-bold text-foreground">Static</div>
                <div className="text-sm text-gray-500">Frontend placeholder</div>
              </div>
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
            <article className="group overflow-hidden rounded-[1.75rem] border border-border-gray bg-background/85 dark:bg-background/90">
              <div className="relative h-72 overflow-hidden md:h-80">
                <Image
                  src={featuredPost.image}
                  alt={featuredPost.title}
                  fill
                  className="object-cover transition-transform duration-500 group-hover:scale-105"
                  priority
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
                <div className="absolute left-5 top-5 inline-flex items-center gap-2 rounded-full bg-black/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.28em] text-white">
                  <Globe className="h-3.5 w-3.5" />
                  {featuredPost.source}
                </div>
                <div className="absolute bottom-0 left-0 right-0 p-5 md:p-6">
                  <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-white/80">
                    <span>{featuredPost.category}</span>
                    <span className="h-1 w-1 rounded-full bg-white/60" />
                    <span>{featuredPost.date}</span>
                    <span className="h-1 w-1 rounded-full bg-white/60" />
                    <span>{featuredPost.readTime}</span>
                  </div>
                  <h2 className="max-w-2xl text-2xl font-heading font-bold text-white md:text-3xl">
                    {featuredPost.title}
                  </h2>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-white/78 md:text-base">
                    {featuredPost.excerpt}
                  </p>
                </div>
              </div>
            </article>

            <div className="grid gap-4">
              <div className="rounded-[1.75rem] border border-border-gray bg-background/80 p-5 dark:bg-background/90">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <Sparkles className="h-4 w-4 text-neon-blue" />
                  Why this page exists
                </div>
                <div className="space-y-3 text-sm leading-6 text-gray-500 dark:text-gray-400">
                  <p>Blog content now has a dedicated destination linked directly from the navbar.</p>
                  <p>Editorial cards are placeholders from multiple site styles so we can swap to live feeds later.</p>
                  <p>Reddit threads stay visible below to balance expert coverage with community sentiment.</p>
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-border-gray bg-background/80 p-5 dark:bg-background/90">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <Newspaper className="h-4 w-4 text-neon-green" />
                  Source mix
                </div>
                <div className="space-y-3">
                  {editorialSources.map((source) => (
                    <div
                      key={source.name}
                      className="flex items-center justify-between rounded-2xl border border-border-gray bg-mid-gray/70 px-4 py-3 dark:bg-mid-gray/60"
                    >
                      <div>
                        <div className="font-semibold text-foreground">{source.name}</div>
                        <div className="text-sm text-gray-500">{source.label}</div>
                      </div>
                      <ExternalLink className="h-4 w-4 text-gray-400" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-border-gray bg-mid-gray/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.26em] text-gray-500">
              <Globe className="h-3.5 w-3.5" />
              Around the web
            </div>
            <h2 className="text-2xl font-heading font-bold tracking-tight text-foreground md:text-3xl">
              Placeholder stories from different PC sites
            </h2>
          </div>
          <Link
            href="/builder"
            className="hidden items-center gap-2 rounded-full border border-border-gray bg-mid-gray/70 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:border-neon-blue hover:text-neon-blue md:inline-flex"
          >
            Open builder
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {curatedPosts.map((post) => (
            <article
              key={post.id}
              className="group overflow-hidden rounded-[1.6rem] border border-border-gray bg-mid-gray/60 transition-all duration-300 hover:-translate-y-1 hover:border-gray-300 dark:hover:border-gray-700"
            >
              <div className="relative h-44 overflow-hidden">
                <Image
                  src={post.image}
                  alt={post.title}
                  fill
                  className="object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />
                <div className="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-gray-900">
                  {post.source}
                </div>
              </div>

              <div className="space-y-4 p-5">
                <div className="flex items-center justify-between gap-3 text-xs font-semibold uppercase tracking-[0.24em] text-gray-500">
                  <span>{post.category}</span>
                  <span>{post.date}</span>
                </div>

                <div>
                  <h3 className="text-xl font-heading font-bold leading-tight text-foreground">
                    {post.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-gray-500 dark:text-gray-400">
                    {post.excerpt}
                  </p>
                </div>

                <div className="flex items-center justify-between gap-3 border-t border-border-gray pt-4">
                  <div>
                    <div className="text-sm font-semibold text-foreground">{post.source}</div>
                    <div className="text-sm text-gray-500">{post.sourceLabel}</div>
                  </div>
                  <div className="inline-flex items-center gap-2 text-sm font-medium text-neon-blue">
                    <Clock3 className="h-4 w-4" />
                    {post.readTime}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>

        <div className="mt-14">
          <div className="mb-8 flex items-end justify-between gap-4">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-border-gray bg-mid-gray/70 px-3 py-1 text-xs font-semibold uppercase tracking-[0.26em] text-gray-500">
                <MessageSquare className="h-3.5 w-3.5" />
                Reddit pulse
              </div>
              <h2 className="text-2xl font-heading font-bold tracking-tight text-foreground md:text-3xl">
                Community posts worth keeping an eye on
              </h2>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {redditPosts.map((post) => (
              <article
                key={post.id}
                className="rounded-[1.6rem] border border-border-gray bg-mid-gray/60 p-5 transition-all duration-300 hover:-translate-y-1 hover:border-neon-blue/40"
              >
                <div className="mb-4 flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.22em] text-gray-500">
                  <span className="rounded-full bg-neon-blue/10 px-3 py-1 text-neon-blue">{post.subreddit}</span>
                  <span>{post.flair}</span>
                  <span>{post.timestamp}</span>
                </div>

                <h3 className="text-xl font-heading font-bold leading-tight text-foreground">
                  {post.title}
                </h3>

                {post.preview ? (
                  <p className="mt-3 text-sm leading-6 text-gray-500 dark:text-gray-400">{post.preview}</p>
                ) : null}

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-border-gray pt-4">
                  <div className="text-sm font-medium text-foreground">{post.author}</div>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="inline-flex items-center gap-1.5">
                      <Flame className="h-4 w-4 text-orange-500" />
                      {post.upvotes.toLocaleString()}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <MessageSquare className="h-4 w-4 text-neon-blue" />
                      {post.comments}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
