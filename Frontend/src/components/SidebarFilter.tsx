'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';

interface SidebarFilterProps {
  categories: string[];
  selectedCategory: string | 'All';
  onSelectCategory: (category: string | 'All') => void;
  onPriceChange: (min: number, max: number) => void;
  inStockOnly: boolean;
  onInStockOnlyChange: (enabled: boolean) => void;
}

const PRICE_MIN = 1000;
const PRICE_MAX = 400000;

function formatPrice(val: number): string {
  return '₹' + val.toLocaleString('en-IN');
}

/**
 * Custom dual-thumb range slider built with pure CSS + two native range inputs
 * overlaid on each other. Applies filter on pointerUp (drag end).
 */
function DualRangeSlider({
  min,
  max,
  valueMin,
  valueMax,
  onChange,
  onDragEnd,
}: {
  min: number;
  max: number;
  valueMin: number;
  valueMax: number;
  onChange: (low: number, high: number) => void;
  onDragEnd: () => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);

  // Convert value to percentage position
  const toPercent = (val: number) => ((val - min) / (max - min)) * 100;

  const leftPct = toPercent(valueMin);
  const rightPct = toPercent(valueMax);

  return (
    <div className="relative w-full h-8 flex items-center" ref={trackRef}>
      {/* Background track */}
      <div className="absolute left-0 right-0 h-1 rounded-full bg-border-gray" />
      {/* Active range highlight */}
      <div
        className="absolute h-1 rounded-full bg-neon-blue"
        style={{ left: `${leftPct}%`, right: `${100 - rightPct}%` }}
      />

      {/* Min thumb */}
      <input
        type="range"
        min={min}
        max={max}
        step={500}
        value={valueMin}
        onChange={(e) => {
          const v = Math.min(Number(e.target.value), valueMax - 500);
          onChange(v, valueMax);
        }}
        onPointerUp={onDragEnd}
        onTouchEnd={onDragEnd}
        className="slider-thumb absolute w-full pointer-events-none appearance-none bg-transparent z-10"
        style={{ height: '8px' }}
      />

      {/* Max thumb */}
      <input
        type="range"
        min={min}
        max={max}
        step={500}
        value={valueMax}
        onChange={(e) => {
          const v = Math.max(Number(e.target.value), valueMin + 500);
          onChange(valueMin, v);
        }}
        onPointerUp={onDragEnd}
        onTouchEnd={onDragEnd}
        className="slider-thumb absolute w-full pointer-events-none appearance-none bg-transparent z-20"
        style={{ height: '8px' }}
      />
    </div>
  );
}

export default function SidebarFilter({
  categories,
  selectedCategory,
  onSelectCategory,
  onPriceChange,
  inStockOnly,
  onInStockOnlyChange,
}: SidebarFilterProps) {
  const [priceMin, setPriceMin] = useState(PRICE_MIN);
  const [priceMax, setPriceMax] = useState(PRICE_MAX);

  const handleChange = useCallback((low: number, high: number) => {
    setPriceMin(low);
    setPriceMax(high);
  }, []);

  const handleDragEnd = useCallback(() => {
    onPriceChange(priceMin, priceMax);
  }, [priceMin, priceMax, onPriceChange]);

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
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>{formatPrice(priceMin)}</span>
          <span>{formatPrice(priceMax)}</span>
        </div>
        <DualRangeSlider
          min={PRICE_MIN}
          max={PRICE_MAX}
          valueMin={priceMin}
          valueMax={priceMax}
          onChange={handleChange}
          onDragEnd={handleDragEnd}
        />
        <div className="flex justify-between text-[10px] text-gray-500 mt-1">
          <span>{formatPrice(PRICE_MIN)}</span>
          <span>{formatPrice(PRICE_MAX)}</span>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold mb-4 text-neon-blue border-b border-border-gray pb-2">Availability</h3>
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input 
            type="checkbox" 
            className="rounded bg-dark-gray border-border-gray text-neon-blue focus:ring-neon-blue" 
            checked={inStockOnly}
            onChange={(e) => onInStockOnlyChange(e.target.checked)}
          />
          In Stock Only
        </label>
      </div>
    </aside>
  );
}
