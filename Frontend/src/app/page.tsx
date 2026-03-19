'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import {
  ArrowRight, Zap, Target, Cpu, HardDrive, MemoryStick, Monitor,
  Fan, Box, BatteryCharging, ChevronRight, TrendingDown,
  MessageCircle, ArrowUpRight, ThumbsUp, BookOpen, Sparkles,
  Activity, CircuitBoard, Database, PlugZap, Layout,
} from 'lucide-react';
import { Component } from '@/data/mockData';
import { blogPosts, BlogPost } from '@/data/blogData';
import { buildGuides, BuildGuide } from '@/data/buildGuides';
import ProductCard from '@/components/ProductCard';
import AnimatedSection from '@/components/AnimatedSection';

// ─── Category Icons Map ────────────────────────────────────────────
const CATEGORIES = [
  { name: 'CPU', label: 'Processors', icon: Cpu, color: '#4285F4' },
  { name: 'Video Card', label: 'Graphics Cards', icon: Layout, color: '#EA4335' },
  { name: 'Motherboard', label: 'Motherboards', icon: CircuitBoard, color: '#34A853' },
  { name: 'Memory', label: 'RAM', icon: MemoryStick, color: '#FBBC04' },
  { name: 'Storage', label: 'Storage', icon: Database, color: '#4285F4' },
  { name: 'Case', label: 'Cases', icon: Box, color: '#EA4335' },
  { name: 'Power Supply', label: 'Power Supplies', icon: PlugZap, color: '#34A853' },
  { name: 'CPU Cooler', label: 'CPU Coolers', icon: Fan, color: '#FBBC04' },
];

// ─── Deal Type ─────────────────────────────────────────────────────
interface DealItem {
  id: string;
  name: string;
  category: string;
  originalPrice: number;
  salePrice: number;
  discountPercent: number;
  image: string;
}

// ═══════════════════════════════════════════════════════════════════
//  1. HERO SECTION  (Compact ~45vh)
// ═══════════════════════════════════════════════════════════════════
function HeroSection() {
  return (
    <section className="relative w-full min-h-[40vh] flex flex-col items-center justify-center border-b border-border-gray overflow-hidden bg-dark-gray pt-12 pb-10 md:pt-16 md:pb-12">
      {/* Subtle gradient blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[30%] -right-[10%] w-[60%] h-[120%] bg-neon-blue/[0.04] rounded-full blur-[100px]" />
        <div className="absolute -bottom-[30%] -left-[10%] w-[50%] h-[100%] bg-neon-green/[0.04] rounded-full blur-[80px]" />
      </div>

      <div className="container mx-auto px-4 relative z-10 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border-gray bg-background/50 text-neon-blue text-xs mb-6 backdrop-blur-md">
          <Sparkles className="w-3.5 h-3.5" />
          <span className="font-medium tracking-wide">India&apos;s Smartest PC Builder</span>
        </div>

        <motion.h1 
          initial={{ opacity: 0, y: 24, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ 
            duration: 1.2, 
            ease: [0.22, 1, 0.36, 1],
          }}
          className="text-4xl md:text-6xl lg:text-7xl font-heading font-extrabold tracking-tighter mb-5 leading-[1.1]"
        >
          <motion.span
            initial={{ opacity: 0.5, color: 'var(--color-gray-500)' }}
            animate={{ opacity: 1, color: 'var(--color-foreground)' }}
            transition={{ duration: 1.5, delay: 0.2 }}
          >
            Build Your{' '}
          </motion.span>
          <motion.span 
            className="text-transparent bg-clip-text bg-gradient-to-r from-neon-blue via-cyan-400 to-neon-blue font-black tracking-tighter"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.5 }}
          >
            Dream PC
          </motion.span>
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="max-w-[540px] text-gray-500 text-base md:text-lg mb-8 font-light leading-relaxed"
        >
          Real-time pricing from top Indian retailers. Smart compatibility checks. Zero guesswork.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1 }}
          className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto"
        >
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Link
              href="/builder"
              className="group flex items-center justify-center gap-2 h-12 px-8 rounded-xl bg-foreground text-background font-heading font-bold text-sm transition-all duration-200 shadow-[0_0_20px_rgba(255,255,255,0.05)] w-full"
            >
              Start Building
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </motion.div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Link
              href="/browse"
              className="flex items-center justify-center h-12 px-8 rounded-xl bg-transparent text-foreground font-heading font-bold text-sm border border-border-gray hover:bg-foreground/5 dark:hover:bg-white/5 transition-all duration-200 w-full"
            >
              Browse Components
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  2. QUICK CATEGORY NAVIGATION
// ═══════════════════════════════════════════════════════════════════
function CategoryNavSection() {
  return (
    <section className="py-10 bg-background border-b border-border-gray">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="text-center mb-10">
            <h2 className="text-2xl md:text-3xl font-heading font-bold tracking-tight mb-2">Browse by Category</h2>
            <p className="text-gray-500 text-sm">Find exactly what you need for your build</p>
          </div>
        </AnimatedSection>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {CATEGORIES.map((cat, i) => (
            <AnimatedSection key={cat.name} delay={i * 0.04}>
                <Link
                  href={`/browse?category=${encodeURIComponent(cat.name)}`}
                  className="group relative flex flex-col items-center justify-center gap-3 p-4 aspect-square rounded-[2rem] border border-border-gray bg-mid-gray/20 backdrop-blur-md transition-all duration-500 hover:scale-[1.05] hover:border-opacity-100 border-opacity-40 overflow-hidden active:scale-95"
                  style={{ 
                    boxShadow: `inset 0 0 20px ${cat.color}05`,
                    borderColor: `${cat.color}20`
                  }}
                >
                  {/* Subtle Background Glow on Hover */}
                  <div className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500" style={{ backgroundColor: cat.color }} />
                  
                  {/* Bottom Accent Glow */}
                  <div 
                    className="absolute bottom-0 left-0 right-0 h-[2px] scale-x-0 group-hover:scale-x-50 transition-transform duration-500 origin-center blur-[1px]" 
                    style={{ backgroundColor: cat.color, boxShadow: `0 0 15px ${cat.color}` }} 
                  />
                  
                  <cat.icon 
                    className="w-10 h-10 transition-all duration-500 group-hover:scale-110 group-hover:drop-shadow-[0_0_15px_rgba(255,255,255,0.3)]" 
                    style={{ color: cat.color }} 
                  />
                  
                  <span className="text-[10px] font-bold text-gray-500 group-hover:text-foreground transition-colors text-center uppercase tracking-[0.2em] leading-none">
                    {cat.label}
                  </span>
                </Link>
            </AnimatedSection>
          ))}
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  3. PC BUILDER CTA
// ═══════════════════════════════════════════════════════════════════
function BuilderCTASection() {
  return (
    <section className="py-10 bg-background">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="relative overflow-hidden rounded-2xl border border-border-gray bg-gradient-to-r from-neon-blue/[0.08] via-transparent to-neon-green/[0.08] p-8 md:p-12 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-2xl bg-neon-blue/10 flex items-center justify-center shrink-0">
                <Target className="w-7 h-7 text-neon-blue" />
              </div>
              <div>
                <h3 className="text-xl md:text-2xl font-heading font-bold mb-1">Build Your PC Now</h3>
                <p className="text-gray-500 text-sm md:text-base">
                  Select parts, check compatibility, and compare prices — all in one tool.
                </p>
              </div>
            </div>
            <Link
              href="/builder"
              className="group flex items-center gap-2 h-11 px-6 rounded-xl bg-neon-blue text-white font-bold text-sm hover:bg-neon-blue/90 transition-all shrink-0"
            >
              Open Builder
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </AnimatedSection>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  4. TRENDING COMPONENTS
// ═══════════════════════════════════════════════════════════════════
function TrendingSection({ parts }: { parts: Component[] }) {
  if (parts.length === 0) return null;

  return (
    <section className="py-12 bg-dark-gray border-t border-b border-border-gray">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="flex justify-between items-end mb-10">
            <div>
              <h2 className="text-2xl md:text-3xl font-heading font-bold mb-2">Trending Components</h2>
              <p className="text-gray-500 text-sm">Popular picks this week</p>
            </div>
            <Link
              href="/browse"
              className="text-neon-blue hover:text-neon-blue/80 text-sm font-medium flex items-center gap-1 group"
            >
              View all <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </AnimatedSection>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {parts.map((part, i) => (
            <AnimatedSection key={part.id} delay={i * 0.08}>
              <ProductCard component={part} />
            </AnimatedSection>
          ))}
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  5. PRICE DROPS / DEALS
// ═══════════════════════════════════════════════════════════════════
function DealsSection({ deals }: { deals: DealItem[] }) {
  if (deals.length === 0) return null;

  return (
    <section id="deals" className="py-12 bg-background border-b border-border-gray">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="flex justify-between items-end mb-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-neon-red/10 flex items-center justify-center">
                <TrendingDown className="w-5 h-5 text-neon-red" />
              </div>
              <div>
                <h2 className="text-2xl md:text-3xl font-heading font-bold mb-1">Price Drops</h2>
                <p className="text-gray-500 text-sm">Best deals from Indian retailers right now</p>
              </div>
            </div>
          </div>
        </AnimatedSection>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {deals.map((deal, i) => (
            <AnimatedSection key={deal.id} delay={i * 0.06}>
              <Link
                href={`/product/${deal.id}`}
                className="group block rounded-xl border border-border-gray bg-mid-gray/30 hover:border-neon-red/30 transition-all duration-300 overflow-hidden"
              >
                <div className="relative h-36 bg-white">
                  <Image
                    src={deal.image}
                    alt={deal.name}
                    fill
                    className="object-contain p-4 group-hover:scale-105 transition-transform duration-500"
                  />
                  <span className="absolute top-2 left-2 bg-neon-red text-white text-xs font-bold px-2 py-0.5 rounded-md">
                    -{deal.discountPercent}%
                  </span>
                </div>
                <div className="p-4">
                  <div className="text-xs text-gray-400 mb-1">{deal.category}</div>
                  <h4 className="text-sm font-medium text-foreground mb-3 line-clamp-2 leading-tight">
                    {deal.name}
                  </h4>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-neon-green">₹{deal.salePrice.toLocaleString('en-IN')}</span>
                    <span className="text-xs text-gray-400 line-through">₹{deal.originalPrice.toLocaleString('en-IN')}</span>
                  </div>
                </div>
              </Link>
            </AnimatedSection>
          ))}
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  6. BUILD GUIDES
// ═══════════════════════════════════════════════════════════════════
function BuildGuidesSection() {
  return (
    <section id="build-guides" className="py-12 bg-dark-gray border-b border-border-gray">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-heading font-bold tracking-tight mb-2">Build Guides</h2>
            <p className="text-gray-500 text-sm max-w-lg mx-auto">
              Curated configurations for every budget. Pick a starting point and customize it in our builder.
            </p>
          </div>
        </AnimatedSection>

        <div className="grid md:grid-cols-3 gap-5">
          {buildGuides.map((guide, i) => (
            <AnimatedSection key={guide.id} delay={i * 0.1}>
              <div className="group rounded-2xl border border-border-gray bg-background hover:border-gray-400 dark:hover:border-gray-600 transition-all duration-300 overflow-hidden">
                {/* Header */}
                <div className="p-6 pb-4" style={{ borderBottom: `1px solid ${guide.color}20` }}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-2xl">{guide.icon}</span>
                    <span
                      className="text-xs font-bold px-2.5 py-1 rounded-full"
                      style={{ backgroundColor: `${guide.color}15`, color: guide.color }}
                    >
                      {guide.tier.toUpperCase()}
                    </span>
                  </div>
                  <h3 className="text-xl font-heading font-bold mb-1">{guide.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{guide.description}</p>
                </div>

                {/* Component List */}
                <div className="px-6 py-4">
                  <ul className="space-y-2.5">
                    {guide.components.map((comp) => (
                      <li key={comp.category} className="flex justify-between items-center text-sm">
                        <span className="text-gray-400">{comp.category}</span>
                        <span className="text-foreground font-medium text-right max-w-[65%] truncate">{comp.name}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-border-gray flex items-center justify-between">
                  <div>
                    <span className="text-xs text-gray-400">Total Estimated</span>
                    <div className="text-xl font-bold font-heading" style={{ color: guide.color }}>
                      ₹{guide.totalPrice.toLocaleString('en-IN')}
                    </div>
                  </div>
                  <Link
                    href="/builder"
                    className="flex items-center gap-1 text-sm font-medium px-4 py-2 rounded-lg border border-border-gray hover:bg-foreground/5 transition-colors"
                  >
                    Customize <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </AnimatedSection>
          ))}
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  7. BLOG SECTION
// ═══════════════════════════════════════════════════════════════════
function BlogSection() {
  return (
    <section id="blog" className="py-12 bg-background border-b border-border-gray">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="flex justify-between items-end mb-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-neon-blue/10 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-neon-blue" />
              </div>
              <div>
                <h2 className="text-2xl md:text-3xl font-heading font-bold mb-1">From the Blog</h2>
                <p className="text-gray-500 text-sm">Guides, reviews, and build inspiration</p>
              </div>
            </div>
            <Link href="/blog" className="text-neon-blue hover:text-neon-blue/80 text-sm font-medium flex items-center gap-1 group">
              All posts <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </AnimatedSection>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {blogPosts.map((post, i) => (
            <AnimatedSection key={post.id} delay={i * 0.08}>
              <article className="group rounded-xl border border-border-gray bg-mid-gray/30 hover:border-gray-400 dark:hover:border-gray-600 transition-all duration-300 overflow-hidden flex flex-col h-full">
                <div className="relative h-40 overflow-hidden">
                  <Image
                    src={post.image}
                    alt={post.title}
                    fill
                    className="object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <span className="absolute top-2 left-2 bg-neon-blue/90 text-white text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide">
                    {post.category}
                  </span>
                </div>
                <div className="p-4 flex flex-col flex-grow">
                  <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                    <span>{post.date}</span>
                    <span>·</span>
                    <span>{post.readTime}</span>
                  </div>
                  <h4 className="text-sm font-bold text-foreground mb-2 line-clamp-2 leading-snug group-hover:text-neon-blue transition-colors">
                    {post.title}
                  </h4>
                  <p className="text-xs text-gray-500 line-clamp-2 flex-grow">{post.excerpt}</p>
                </div>
              </article>
            </AnimatedSection>
          ))}
        </div>
      </div>
    </section>
  );
}

function timeAgo(input: string | number): string {
  const ts = typeof input === 'number' ? input * 1000 : new Date(input).getTime();
  const d = Math.floor((Date.now() - ts) / 1000);
  if (d < 3600)  return `${Math.floor(d / 60)}m ago`;
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`;
  return `${Math.floor(d / 86400)}d ago`;
}

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K views`;
  return `${n} views`;
}

function formatScore(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

// ═══════════════════════════════════════════════════════════════════
//  8. COMMUNITY OPINIONS (YouTube + Reddit)
// ═══════════════════════════════════════════════════════════════════
function CommunitySection() {
  const [youtube, setYoutube] = useState<any[]>([]);
  const [reddit, setReddit] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetch('/api/community')
      .then(r => r.json())
      .then(d => {
        if (!mounted) return;
        setYoutube(d.youtube ?? []);
        setReddit(d.reddit ?? []);
        setLoading(false);
      })
      .catch(() => {
        if (mounted) { setError(true); setLoading(false); }
      });
    return () => { mounted = false; };
  }, []);

  return (
    <section id="community" className="py-12 bg-dark-gray border-b border-border-gray">
      <div className="container mx-auto px-4">
        <AnimatedSection>
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-heading font-bold tracking-tight mb-2">Community Opinions</h2>
            <p className="text-gray-500 text-sm">What builders are watching and discussing</p>
          </div>
        </AnimatedSection>

        <div className="grid lg:grid-cols-2 gap-8 items-stretch">
          {/* YouTube Feed */}
          <AnimatedSection delay={0} direction="left" className="h-full">
            <div className="flex flex-col h-full">
              <div className="flex items-center gap-2 mb-5 shrink-0">
                <svg className="w-5 h-5 text-red-500" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.75 15.5v-7l6.5 3.5-6.5 3.5z"/>
                </svg>
                <h3 className="text-lg font-heading font-bold">Popular on YouTube</h3>
              </div>
              <div className="flex-1 flex flex-col justify-between space-y-3">
                {loading && (
                  <>
                    {[1, 2, 3, 4].map((n) => (
                      <div key={`yt-skel-${n}`} className="p-4 rounded-xl border border-border-gray bg-background h-[120px] animate-pulse" />
                    ))}
                  </>
                )}
                {!loading && (error || youtube.length === 0) && (
                  <div className="p-4 rounded-xl border border-border-gray bg-background text-gray-500 text-sm text-center">
                    Could not load videos. Check YOUTUBE_API_KEY in .env.local.
                  </div>
                )}
                {!loading && !error && youtube.length > 0 && youtube.map((video: any) => (
                  <a
                    key={video.id}
                    href={video.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-4 rounded-xl border border-border-gray bg-background hover:border-gray-400 dark:hover:border-gray-600 transition-all duration-300 flex items-start gap-5 flex-1 mb-3 last:mb-0 group"
                  >
                    <div className="relative w-56 h-32 shrink-0 overflow-hidden rounded-lg">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img 
                        src={video.thumbnail} 
                        alt={video.title} 
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" 
                      />
                    </div>
                    <div className="flex flex-col gap-1 min-w-0 py-1">
                      <p className="text-base font-bold text-foreground leading-tight line-clamp-2 group-hover:text-neon-blue transition-colors duration-200">{video.title}</p>
                      <p className="text-xs text-gray-400 font-medium">
                        {video.channel} · {formatViews(parseInt(video.viewCount, 10) || 0)} · {timeAgo(video.publishedAt)}
                      </p>
                      {video.description && (
                        <p className="text-[13px] text-gray-500 line-clamp-2 mt-1 leading-relaxed">{video.description}</p>
                      )}
                      {video.source === 'search' && (
                        <div className="mt-auto pt-2">
                          <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-neon-blue uppercase tracking-wider">
                            <Sparkles className="w-3 h-3" /> Trending
                          </span>
                        </div>
                      )}
                    </div>
                  </a>
                ))}
              </div>
            </div>
          </AnimatedSection>

          {/* Reddit Feed */}
          <AnimatedSection delay={0.1} direction="right" className="h-full">
            <div className="flex flex-col h-full">
              <div className="flex items-center gap-2 mb-5 shrink-0">
                <svg className="w-5 h-5 text-orange-500" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z" />
                </svg>
                <h3 className="text-lg font-heading font-bold">Popular on Reddit</h3>
              </div>
              <div className="flex-1 flex flex-col justify-between space-y-3">
                {loading && (
                  <>
                    {[1, 2, 3, 4, 5, 6].map((n) => (
                      <div key={`reddit-skel-${n}`} className="p-4 rounded-xl border border-border-gray bg-background h-[120px] animate-pulse" />
                    ))}
                  </>
                )}
                {!loading && (error || reddit.length === 0) && (
                  <div className="p-4 rounded-xl border border-border-gray bg-background text-gray-500 text-sm text-center">
                    Could not load posts.
                  </div>
                )}
                {!loading && !error && reddit.length > 0 && reddit.map((post: any) => (
                  <div
                    key={post.id}
                    className="p-4 rounded-xl border border-border-gray bg-background hover:border-gray-400 dark:hover:border-gray-600 transition-all duration-300 cursor-pointer flex-1 mb-3 last:mb-0"
                    onClick={() => window.open(post.url, '_blank')}
                  >
                    <div className="flex items-start gap-3 h-full">
                      <div className="flex flex-col items-center gap-0.5 text-gray-400 shrink-0 mt-0.5">
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span className="text-xs font-bold text-foreground">{formatScore(post.score)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-[10px] font-bold text-orange-500">r/{post.subreddit}</span>
                          {post.flair && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-500/10 text-gray-400 whitespace-nowrap">
                              {post.flair}
                            </span>
                          )}
                          <span className="text-xs text-gray-500 ml-auto">{timeAgo(post.createdUtc)}</span>
                        </div>
                        <h4 className="text-sm font-medium text-foreground mb-1 leading-snug line-clamp-2">{post.title}</h4>
                        {post.preview && (
                          <p className="text-xs text-gray-500 line-clamp-1 mb-2">{post.preview}</p>
                        )}
                        <div className="flex items-center gap-3 text-xs text-gray-500 mt-auto">
                          <span className="flex items-center gap-1">
                            <MessageCircle className="w-3 h-3" /> {formatScore(post.numComments)}
                          </span>
                          <span>u/{post.author}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </AnimatedSection>
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════
//  MAIN HOME PAGE
// ═══════════════════════════════════════════════════════════════════
export default function Home() {
  const [trendingParts, setTrendingParts] = useState<Component[]>([]);
  const [deals, setDeals] = useState<DealItem[]>([]);

  useEffect(() => {
    let mounted = true;

    // Fetch trending components
    fetch('/api/components/trending')
      .then(res => res.json())
      .then(parts => { if (mounted) setTrendingParts(parts); })
      .catch(console.error);

    // Fetch deals
    fetch('/api/components/deals')
      .then(res => res.json())
      .then(data => { if (mounted && Array.isArray(data)) setDeals(data); })
      .catch(console.error);

    return () => { mounted = false; };
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <HeroSection />
      <CategoryNavSection />
      <BuilderCTASection />
      <TrendingSection parts={trendingParts} />
      <DealsSection deals={deals} />
      <BuildGuidesSection />
      <BlogSection />
      <CommunitySection />
    </div>
  );
}
