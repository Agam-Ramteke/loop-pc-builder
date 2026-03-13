'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Search, ShoppingCart, Infinity as InfinityIcon } from 'lucide-react';
import { useBuild } from '@/context/BuildContext';
import { useState, useCallback } from 'react';

export default function Navbar() {
  const { totalPrice } = useBuild();
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (q) {
      router.push(`/browse?search=${encodeURIComponent(q)}`);
      setSearchQuery('');
    }
  }, [searchQuery, router]);

  return (
    <header className="sticky top-0 z-50 w-full bg-gradient-to-b from-background via-background/90 to-transparent pb-4 pt-2">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        
        {/* Logo & Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 group">
            <InfinityIcon className="h-8 w-8 text-neon-blue drop-shadow-[0_0_12px_#4285F4] group-hover:drop-shadow-[0_0_20px_#4285F4] transition-all" />
            <span className="font-heading font-bold text-xl tracking-tight">Loop<span className="text-neon-blue drop-shadow-[0_0_8px_#4285F4]">PC</span></span>
          </Link>
          
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-gray-700 dark:text-gray-300">
            <Link href="/browse" className="hover:text-neon-blue transition-colors">Browse Components</Link>
            <Link href="/builder" className="hover:text-neon-green transition-colors">PC Builder</Link>
            <Link href="/#blog" className="hover:text-neon-blue transition-colors">Blog</Link>
            <Link href="#" className="hover:text-neon-blue transition-colors">Saved Builds</Link>
          </nav>
        </div>

        {/* Search & Cart */}
        <div className="flex items-center gap-4">
          <form onSubmit={handleSearch} className="relative hidden sm:block">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search RTX 4090, Ryzen..."
              className="h-9 w-64 rounded-md border border-border-gray bg-mid-gray px-9 py-2 text-sm text-foreground focus:border-neon-blue focus:outline-none focus:ring-1 focus:ring-neon-blue transition-all"
            />
          </form>
          
          <Link href="/builder" className="flex items-center gap-2 bg-mid-gray hover:bg-border-gray border border-border-gray px-4 py-2 rounded-md transition-colors">
            <ShoppingCart className="h-4 w-4 text-neon-green" />
            <span className="text-sm font-bold text-neon-green">₹{totalPrice.toLocaleString('en-IN')}</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
