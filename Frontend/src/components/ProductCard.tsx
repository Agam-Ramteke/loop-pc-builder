'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Component } from '@/data/mockData';
import { useBuild } from '@/context/BuildContext';
import { Plus, Check } from 'lucide-react';

interface ProductCardProps {
  component: Component;
}

export default function ProductCard({ component }: ProductCardProps) {
  const { build, addComponent } = useBuild();
  const isSelected = build[component.category]?.id === component.id;

  return (
    <div className="bg-mid-gray border border-border-gray rounded-lg overflow-hidden hover:border-neon-blue transition-colors group flex flex-col h-full">
      <Link 
        href={`/product/${component.id}`} 
        className="block relative h-48 bg-white shrink-0" 
        style={{ maskImage: 'linear-gradient(to bottom, black 75%, transparent 100%)', WebkitMaskImage: 'linear-gradient(to bottom, black 75%, transparent 100%)' }}
      >
        <Image 
          src={component.image} 
          alt={component.name}
          fill
          className="object-contain p-6 group-hover:scale-[1.1] transition-transform duration-500 ease-out mix-blend-multiply"
        />
        {component.inStock ? (
          <span className="absolute top-2 right-2 bg-neon-green/20 text-neon-green text-[10px] font-bold px-1.5 py-0.5 rounded">
            IN STOCK
          </span>
        ) : (
          <span className="absolute top-2 right-2 bg-red-500/20 text-red-500 text-[10px] font-bold px-1.5 py-0.5 rounded">
            OUT OF STOCK
          </span>
        )}
      </Link>
      
      <div className="p-4 flex flex-col flex-grow">
        <div className="flex justify-between items-start mb-1">
          <div className="text-[10px] text-gray-400 font-medium">{component.brand}</div>
          <div className="text-[9px] font-bold text-neon-blue uppercase tracking-tighter opacity-70">
            {component.provider}
          </div>
        </div>
        <Link href={`/product/${component.id}`} className="text-sm font-bold text-foreground mb-3 hover:text-neon-blue transition-colors line-clamp-2 h-10 leading-tight">
          {component.name}
        </Link>
        
        <div className="text-[11px] text-gray-400 flex-grow mb-4 overflow-hidden">
          <ul className="space-y-1.5">
            {Object.entries(component.specs).slice(0, 3).map(([key, value]) => (
              <li key={key} className="line-clamp-1">
                <span className="text-gray-500">{key}:</span> {value}
              </li>
            ))}
          </ul>
        </div>
        
        <div className="flex items-center justify-between mt-auto">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xl font-bold text-foreground">₹{component.price.toLocaleString('en-IN')}</span>
            {component.originalPrice && component.originalPrice > component.price && (
              <>
                <span className="text-sm text-gray-400 line-through">₹{component.originalPrice.toLocaleString('en-IN')}</span>
                {component.discountPercent && (
                  <span className="text-xs font-bold text-neon-green bg-neon-green/10 px-1.5 py-0.5 rounded">
                    -{component.discountPercent}%
                  </span>
                )}
              </>
            )}
          </div>
          <button
            onClick={() => addComponent(component)}
            disabled={isSelected}
            className={`flex items-center justify-center w-10 h-10 rounded transition-colors ${
              isSelected 
                ? 'bg-neon-green/20 text-neon-green border border-neon-green/50 cursor-default'
                : component.inStock
                  ? 'bg-neon-blue text-black hover:bg-neon-blue/80'
                  : 'bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500/30'
            }`}
            title={isSelected ? "Already in build" : (component.inStock ? "Add to build" : "Add out-of-stock item")}
          >
            {isSelected ? <Check className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
