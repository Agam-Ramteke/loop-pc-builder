'use client';

import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import { useParams, useRouter } from 'next/navigation';
import { getComponentById } from '@/services/api';
import { Component } from '@/data/mockData';
import { useBuild } from '@/context/BuildContext';
import { Plus, ArrowLeft, Activity } from 'lucide-react';

export default function ProductDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [component, setComponent] = useState<Component | null>(null);
  const [loading, setLoading] = useState(true);
  const { addComponent, build } = useBuild();

  useEffect(() => {
    if (typeof id === 'string') {
      getComponentById(id).then((data) => {
        setComponent(data || null);
        setLoading(false);
      });
    }
  }, [id]);

  if (loading) {
    return <div className="container mx-auto px-4 py-12 flex justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-neon-blue"></div></div>;
  }

  if (!component) {
    return (
      <div className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-3xl font-bold mb-4">Product Not Found</h1>
        <button onClick={() => router.back()} className="text-neon-blue hover:underline">Go Back</button>
      </div>
    );
  }

  const isSelected = build[component.category]?.id === component.id;

  return (
    <div className="container mx-auto px-4 py-8">
      <button 
        onClick={() => router.back()}
        className="flex items-center gap-2 text-gray-400 hover:text-neon-blue transition-colors mb-8"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      <div className="grid md:grid-cols-2 gap-12">
        {/* Images Component */}
        <div className="relative aspect-square rounded-[2rem] bg-white overflow-hidden md:sticky md:top-24 h-fit border border-border-gray shadow-2xl">
          <Image 
            src={component.image} 
            alt={component.name} 
            fill 
            className="object-contain p-12 mix-blend-multiply hover:scale-105 transition-transform duration-700"
          />
        </div>

        {/* Product Details Component */}
        <div className="flex flex-col">
          <div className="mb-2 text-neon-blue font-bold tracking-wide uppercase text-sm">
            {component.brand} • {component.category}
          </div>
          <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-4 text-foreground">
            {component.name}
          </h1>

          <div className="flex items-center gap-4 mb-8">
            <span className="text-4xl font-bold text-foreground">
              ₹{component.price.toFixed(2)}
            </span>
            {component.inStock ? (
              <span className="bg-neon-green/20 text-neon-green text-xs font-bold px-3 py-1.5 rounded-full border border-neon-green/30">
                IN STOCK
              </span>
            ) : (
               <span className="bg-red-500/20 text-red-500 text-xs font-bold px-3 py-1.5 rounded-full border border-red-500/30">
                OUT OF STOCK
              </span>
            )}
          </div>

          <button
            onClick={() => addComponent(component)}
            disabled={!component.inStock || isSelected}
            className={`flex items-center justify-center gap-2 h-14 rounded-lg font-bold text-lg transition-all w-full md:w-auto md:px-12 mb-12 ${
              isSelected 
                ? 'bg-neon-green/20 text-neon-green border border-neon-green/50 cursor-default'
                : component.inStock
                  ? 'bg-neon-blue text-black hover:bg-neon-blue/80 shadow-[0_0_15px_rgba(0,240,255,0.3)] hover:shadow-[0_0_25px_rgba(0,240,255,0.5)]'
                  : 'bg-dark-gray text-gray-500 cursor-not-allowed border border-border-gray'
            }`}
          >
            {isSelected ? "Added to Build" : "Add to Build"}
          </button>

          {/* Specifications Table */}
          <div className="bg-mid-gray/50 border border-border-gray rounded-lg overflow-hidden mb-8">
            <div className="px-6 py-4 bg-dark-gray border-b border-border-gray font-bold text-gray-300">
              Technical Specifications
            </div>
            <div className="divide-y divide-border-gray">
              {Object.entries(component.specs).map(([key, value]) => (
                <div key={key} className="flex px-6 py-3 hover:bg-white/5 transition-colors">
                  <div className="w-1/3 text-gray-400">{key}</div>
                  <div className="w-2/3 text-foreground font-medium">{value}</div>
                </div>
              ))}
              {component.wattage > 0 && (
                <div className="flex px-6 py-3 hover:bg-white/5 transition-colors">
                  <div className="w-1/3 text-gray-400">Estimated Wattage</div>
                  <div className="w-2/3 text-foreground font-medium">{component.wattage} W</div>
                </div>
              )}
            </div>
          </div>

          {/* Placeholder Price History */}
          <div className="p-6 rounded-lg border border-border-gray bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiIGZpbGw9Im5vbmUiIC8+CjxwYXRoIGQ9Ik0wIDM5aDQwTTAgMHY0MEgwem0zOSAwVjAiIHN0cm9rZT0icmdiYSgyMDAsMjAwLDIwMCwwLjAyKSIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiAvPgo8L3N2Zz4=')] relative overflow-hidden">
            <div className="flex items-center gap-2 mb-4 text-gray-400">
               <Activity className="w-5 h-5 text-neon-blue" />
               <h3 className="font-bold">Price History</h3>
            </div>
            <div className="h-32 flex items-end justify-between gap-2">
              {/* Dummy bars for aesthetic */}
              {[40, 60, 55, 45, 75, 50, 80, 70, 90, 85, 100, 95].map((h, i) => (
                <div key={i} className="w-full bg-neon-blue/40 rounded-t-sm hover:bg-neon-blue transition-colors cursor-crosshair" style={{ height: `${h}%` }}></div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
