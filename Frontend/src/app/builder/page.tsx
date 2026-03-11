'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useBuild } from '@/context/BuildContext';
import { ComponentCategory } from '@/data/mockData';
import BuildSlot from '@/components/BuildSlot';
import CompatibilityBanner from '@/components/CompatibilityBanner';

const BUILD_CATEGORIES: ComponentCategory[] = [
  'CPU', 'CPU Cooler', 'Motherboard', 'Memory', 'Storage', 'Video Card', 'Case', 'Power Supply'
];

export default function BuilderPage() {
  const router = useRouter();
  const { build, totalPrice, totalWattage, clearBuild } = useBuild();

  const handleChoose = (category: ComponentCategory) => {
    // In our quick prototype, choosing a component navigates to browse pre-filtered
    // In a final app, this could open a modal over the same page
    // Using localStorage or state preservation, the context provider handles it across pages
    router.push(`/browse?category=${encodeURIComponent(category)}`);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">PC Builder</h1>
          <p className="text-gray-400">Select components below to draft your ultimate setup.</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={clearBuild}
            className="px-4 py-2 border border-red-500/50 text-red-500 hover:bg-red-500/10 rounded-md transition-colors font-medium text-sm"
          >
            Clear Build
          </button>
        </div>
      </div>

      {/* Compatibility Checker */}
      <div className="mb-8">
        <CompatibilityBanner />
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        
        {/* Builder Slots */}
        <div className="flex-grow flex flex-col gap-4">
          <div className="bg-dark-gray border-b border-border-gray px-4 py-3 rounded-t-lg hidden sm:flex text-sm font-bold text-gray-500">
            <div className="w-48">Component</div>
            <div className="flex-grow">Selection</div>
          </div>
          
          <div className="bg-background rounded-b-lg flex flex-col gap-2">
            {BUILD_CATEGORIES.map(category => (
              <BuildSlot 
                key={category}
                category={category}
                component={build[category]}
                onChoose={handleChoose}
              />
            ))}
          </div>
        </div>

        {/* Build Summary Sidebar */}
        <aside className="w-full lg:w-80 flex-shrink-0">
          <div className="bg-mid-gray/50 border border-border-gray rounded-lg p-6 sticky top-24">
            <h3 className="text-xl font-bold mb-6 border-b border-border-gray pb-4">Build Summary</h3>
            
            <div className="space-y-4 mb-6">
              <div className="flex justify-between items-center text-gray-300">
                <span>Base Total</span>
                <span className="font-mono">₹{totalPrice.toFixed(2)}</span>
              </div>
              <div className="flex justify-between items-center text-gray-300">
                <span>Estimated Wattage</span>
                <span className="font-mono text-neon-blue">{totalWattage}W</span>
              </div>
            </div>

            <div className="border-t border-border-gray pt-4 mb-8">
              <div className="flex justify-between items-center">
                <span className="font-bold text-lg text-foreground">Total Cost</span>
                <span className="font-bold text-2xl text-neon-green font-mono">₹{totalPrice.toFixed(2)}</span>
              </div>
            </div>

            <button className="w-full bg-foreground text-background font-bold py-3 rounded-md hover:bg-gray-300 transition-colors shadow-lg">
              Buy Components 
            </button>
            <p className="text-xs text-center text-gray-500 mt-4">
              Links will direct you to optimal retailers based on current pricing.
            </p>
          </div>
        </aside>

      </div>
    </div>
  );
}
