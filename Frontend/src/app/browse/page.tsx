'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ArrowLeft, ArrowRight } from 'lucide-react';
import { getComponents } from '@/services/api';
import { Component, ComponentCategory } from '@/data/mockData';
import SidebarFilter from '@/components/SidebarFilter';
import ProductCard from '@/components/ProductCard';

const CATEGORIES = ['CPU', 'CPU Cooler', 'Motherboard', 'Memory', 'Storage', 'Video Card', 'Case', 'Power Supply'];

function BrowsePageContent() {
  const searchParams = useSearchParams();
  const [components, setComponents] = useState<Component[]>([]);
  const [loading, setLoading] = useState(true);

  // Read initial values from URL query params
  const urlCategory = searchParams.get('category') || 'All';
  const urlSearch = searchParams.get('search') || '';
  const urlPage = Number.parseInt(searchParams.get('page') || '1', 10);
  const urlLimit = Number.parseInt(searchParams.get('limit') || '21', 10);

  // Filter states — initialized from URL
  const [selectedCategory, setSelectedCategory] = useState<string | 'All'>(urlCategory);
  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [priceRange, setPriceRange] = useState<[number, number]>([1000, 400000]);
  const [sortBy, setSortBy] = useState<'priceAsc' | 'priceDesc' | 'name'>('name');
  const [inStockOnly, setInStockOnly] = useState(true);

  // Pagination states
  const [page, setPage] = useState(Number.isFinite(urlPage) ? Math.max(urlPage, 1) : 1);
  const [limit, setLimit] = useState(Number.isFinite(urlLimit) ? Math.min(Math.max(urlLimit, 1), 100) : 21);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Sync state when URL params change (e.g. navbar search)
  useEffect(() => {
    const newCat = searchParams.get('category') || 'All';
    const newSearch = searchParams.get('search') || '';
    const newPage = Number.parseInt(searchParams.get('page') || '1', 10);
    const newLimit = Number.parseInt(searchParams.get('limit') || '21', 10);

    setSelectedCategory(newCat);
    setSearchQuery(newSearch);
    setPage(Number.isFinite(newPage) ? Math.max(newPage, 1) : 1);
    setLimit(Number.isFinite(newLimit) ? Math.min(Math.max(newLimit, 1), 100) : 21);
  }, [searchParams]);

  // Reset to page 1 whenever any filter/sort changes
  useEffect(() => {
    setPage(1);
  }, [selectedCategory, sortBy, priceRange, inStockOnly]);

  const [isSortOpen, setIsSortOpen] = useState(false);
  const SORT_OPTIONS = [
    { id: 'name', label: 'Name (A-Z)' },
    { id: 'priceAsc', label: 'Price (Low to High)' },
    { id: 'priceDesc', label: 'Price (High to Low)' },
  ] as const;

  useEffect(() => {
    const fetchComponents = async () => {
      setLoading(true);
      try {
        const result = await getComponents(
          selectedCategory as ComponentCategory | 'All',
          searchQuery || undefined,
          sortBy,
          page,
          21,
          priceRange[0],  // minPrice
          priceRange[1],  // maxPrice
          inStockOnly     // inStock
        );

        setComponents(result.data);
        setTotalPages(result.totalPages);
        setTotalCount(result.totalCount);
      } catch (error) {
        console.error("Failed to fetch components:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchComponents();
  }, [selectedCategory, searchQuery, sortBy, page, priceRange, inStockOnly]);

  return (
    <div className="container mx-auto px-4 py-8 flex flex-col lg:flex-row gap-8">
      {/* Sidebar Filter */}
      <div className="w-full lg:w-64 flex-shrink-0 lg:sticky lg:top-24 h-fit">
        <SidebarFilter
          categories={CATEGORIES}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          onPriceChange={(min, max) => setPriceRange([min, max])}
          inStockOnly={inStockOnly}
          onInStockOnlyChange={setInStockOnly}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-grow">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-10 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Browse Components</h1>
            {totalCount > 0 && !loading && (
              <p className="text-sm text-gray-400 mt-1 uppercase tracking-wider font-bold text-[10px]">Showing {components.length} of {totalCount} items</p>
            )}
          </div>

          <div className="relative z-30">
            <button
              onClick={() => setIsSortOpen(!isSortOpen)}
              className="group flex items-center gap-3 px-5 py-3 rounded-2xl bg-mid-gray/40 backdrop-blur-md border border-border-gray hover:border-neon-blue/50 hover:bg-mid-gray transition-all duration-300 shadow-xl"
            >
              <div className="flex flex-col items-start">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none mb-1">Sort by</span>
                <span className="text-sm font-bold text-foreground leading-none">
                  {SORT_OPTIONS.find(opt => opt.id === sortBy)?.label}
                </span>
              </div>
              <ChevronDown className={`w-4 h-4 text-neon-blue transition-transform duration-500 ${isSortOpen ? 'rotate-180' : ''}`} />
            </button>
            
            <AnimatePresence>
              {isSortOpen && (
                <>
                  {/* Backdrop to close on click outside */}
                  <div className="fixed inset-0 z-[-1]" onClick={() => setIsSortOpen(false)} />
                  
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                    className="absolute right-0 mt-3 w-56 rounded-2xl bg-black/90 backdrop-blur-xl border border-border-gray shadow-2xl overflow-hidden p-1.5"
                  >
                    {SORT_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        onClick={() => {
                          setSortBy(option.id);
                          setIsSortOpen(false);
                        }}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-bold transition-all duration-200 group/item ${
                          sortBy === option.id 
                            ? 'bg-neon-blue/10 text-neon-blue' 
                            : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                      >
                        {option.label}
                        {sortBy === option.id && <div className="w-1.5 h-1.5 rounded-full bg-neon-blue shadow-[0_0_8px_#4285F4]" />}
                      </button>
                    ))}
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-96 rounded-lg bg-mid-gray animate-pulse" />
            ))}
          </div>
        ) : components.length > 0 ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
              {components.map((component) => (
                <ProductCard key={component.id} component={component} />
              ))}
            </div>

            {!loading && totalPages > 1 && (
              <div className="flex items-center justify-center mt-16 gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => {
                    setPage(p => Math.max(1, p - 1));
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="group flex items-center gap-2 px-4 py-2.5 rounded-xl bg-mid-gray/40 backdrop-blur-md border border-border-gray hover:border-neon-blue/50 transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-mid-gray active:scale-95"
                >
                  <ArrowLeft className="w-3.5 h-3.5 text-neon-blue transition-transform group-hover:-translate-x-1" />
                  <span className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-400 group-hover:text-foreground">Prev</span>
                </button>

                <div className="flex flex-col items-center px-6 border-x border-border-gray/30">
                   <span className="text-[9px] font-black uppercase tracking-[0.3em] text-neon-blue/80 leading-none mb-1">Page</span>
                   <span className="text-lg font-heading font-bold text-foreground leading-none">
                     {page} <span className="text-gray-600 font-medium">/ {totalPages}</span>
                   </span>
                </div>

                <button
                  disabled={page === totalPages}
                  onClick={() => {
                    setPage(p => Math.min(totalPages, p + 1));
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="group flex items-center gap-2 px-4 py-2.5 rounded-xl bg-mid-gray/40 backdrop-blur-md border border-border-gray hover:border-neon-blue/50 transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-mid-gray active:scale-95"
                >
                  <span className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-400 group-hover:text-foreground">Next</span>
                  <ArrowRight className="w-3.5 h-3.5 text-neon-blue transition-transform group-hover:translate-x-1" />
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 bg-mid-gray/30 rounded-lg border border-dashed border-border-gray">
            <div className="text-gray-400 mb-2">No components found</div>
            <button
              onClick={() => setSelectedCategory('All')}
              className="text-neon-blue hover:text-neon-blue/80 transition-colors"
            >
              Clear filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function BrowsePage() {
  return (
    <Suspense fallback={
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map(i => <div key={i} className="h-96 rounded-lg bg-mid-gray animate-pulse" />)}
        </div>
      </div>
    }>
      <BrowsePageContent />
    </Suspense>
  );
}