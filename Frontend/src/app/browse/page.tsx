'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
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

  // Filter states — initialized from URL
  const [selectedCategory, setSelectedCategory] = useState<string | 'All'>(urlCategory);
  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 10000]);
  const [sortBy, setSortBy] = useState<'priceAsc' | 'priceDesc' | 'name'>('name');
  const [inStockOnly, setInStockOnly] = useState(true);

  // Pagination states
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Sync state when URL params change (e.g. navbar search)
  useEffect(() => {
    const newCat = searchParams.get('category') || 'All';
    const newSearch = searchParams.get('search') || '';
    setSelectedCategory(newCat);
    setSearchQuery(newSearch);
    setPage(1);
  }, [searchParams]);

  // Reset to page 1 whenever any filter/sort changes
  useEffect(() => {
    setPage(1);
  }, [selectedCategory, sortBy, priceRange, inStockOnly]);

  useEffect(() => {
    const fetchComponents = async () => {
      setLoading(true);
      try {
        // FIX 3 — Pass price range to the API so the server filters and counts correctly.
        // No client-side filtering needed; totalCount and totalPages are now always accurate.
        const result = await getComponents(
          selectedCategory as ComponentCategory | 'All',
          searchQuery || undefined,
          sortBy,
          page,
          20,
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
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Browse Components</h1>
            {totalCount > 0 && !loading && (
              <p className="text-sm text-gray-400 mt-1">Showing {components.length} of {totalCount} items</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-dark-gray border border-border-gray text-sm rounded-md px-3 py-1.5 focus:outline-none focus:border-neon-blue"
            >
              <option value="name">Name (A-Z)</option>
              <option value="priceAsc">Price (Low to High)</option>
              <option value="priceDesc">Price (High to Low)</option>
            </select>
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
              <div className="flex justify-center mt-12 gap-4">
                <button
                  disabled={page === 1}
                  onClick={() => {
                    setPage(p => Math.max(1, p - 1));
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="px-4 py-2 bg-dark-gray border border-border-gray rounded text-sm hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <span className="flex items-center text-sm text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  disabled={page === totalPages}
                  onClick={() => {
                    setPage(p => Math.min(totalPages, p + 1));
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="px-4 py-2 bg-dark-gray border border-border-gray rounded text-sm hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
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