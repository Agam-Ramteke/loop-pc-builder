'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Plus, X } from 'lucide-react';
import { Component, ComponentCategory } from '@/data/mockData';
import { useBuild } from '@/context/BuildContext';

interface BuildSlotProps {
  category: ComponentCategory;
  component: Component | null;
  onChoose: (category: ComponentCategory) => void;
}

export default function BuildSlot({ category, component, onChoose }: BuildSlotProps) {
  const { removeComponent } = useBuild();

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-4 border border-border-gray rounded-lg bg-mid-gray/50 hover:bg-mid-gray transition-colors">
      <div className="w-full sm:w-48 font-bold text-gray-300">
        {category}
      </div>
      
      <div className="flex-grow flex items-center gap-4 w-full">
        {component ? (
          <>
            <div className="relative w-16 h-16 bg-white/5 rounded overflow-hidden flex-shrink-0">
              <Image src={component.image} alt={component.name} fill className="object-contain p-1" />
            </div>
            <div className="flex-grow">
              <Link href={`/product/${component.id}`} className="font-bold hover:text-neon-blue transition-colors line-clamp-1">
                {component.name}
              </Link>
              <div className="text-sm text-neon-green font-mono mt-1">₹{component.price.toFixed(2)}</div>
            </div>
            <button 
              onClick={() => removeComponent(category)}
              className="p-2 text-gray-500 hover:text-red-500 transition-colors"
              title="Remove component"
            >
              <X className="w-5 h-5" />
            </button>
          </>
        ) : (
          <button 
            onClick={() => onChoose(category)}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 border border-dashed border-gray-600 rounded-md text-gray-400 hover:text-neon-blue hover:border-neon-blue transition-colors bg-dark-gray"
          >
            <Plus className="w-4 h-4" />
            <span>Choose {category}</span>
          </button>
        )}
      </div>
    </div>
  );
}
