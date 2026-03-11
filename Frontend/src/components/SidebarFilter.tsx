'use client';

import React from 'react';

interface SidebarFilterProps {
  categories: string[];
  selectedCategory: string | 'All';
  onSelectCategory: (category: string | 'All') => void;
  onPriceChange: (min: number, max: number) => void;
}

export default function SidebarFilter({ categories, selectedCategory, onSelectCategory }: SidebarFilterProps) {
  return (
    <aside className="w-full lg:w-64 flex-shrink-0 space-y-8">
      <div>
        <h3 className="text-lg font-bold mb-4 text-neon-blue border-b border-border-gray pb-2">Categories</h3>
        <ul className="space-y-2">
          <li>
            <button
              onClick={() => onSelectCategory('All')}
              className={`text-sm transition-colors ${selectedCategory === 'All' ? 'text-neon-green font-bold' : 'text-gray-400 hover:text-foreground'}`}
            >
              All Components
            </button>
          </li>
          {categories.map((cat) => (
            <li key={cat}>
              <button
                onClick={() => onSelectCategory(cat)}
                className={`text-sm transition-colors ${selectedCategory === cat ? 'text-neon-green font-bold' : 'text-gray-400 hover:text-foreground'}`}
              >
                {cat}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-lg font-bold mb-4 text-neon-blue border-b border-border-gray pb-2">Price Range</h3>
        <div className="flex items-center gap-2">
          <input type="number" placeholder="Min" className="w-full bg-dark-gray border border-border-gray rounded px-2 py-1 text-sm text-foreground focus:outline-none focus:border-neon-blue" />
          <span className="text-gray-500">-</span>
          <input type="number" placeholder="Max" className="w-full bg-dark-gray border border-border-gray rounded px-2 py-1 text-sm text-foreground focus:outline-none focus:border-neon-blue" />
        </div>
      </div>
      
      <div>
        <h3 className="text-lg font-bold mb-4 text-neon-blue border-b border-border-gray pb-2">Availability</h3>
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input type="checkbox" className="rounded bg-dark-gray border-border-gray text-neon-blue focus:ring-neon-blue" defaultChecked />
          In Stock Only
        </label>
      </div>
    </aside>
  );
}
