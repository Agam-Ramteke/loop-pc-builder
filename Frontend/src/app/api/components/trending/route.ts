import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import { Component, ComponentCategory } from '@/data/mockData';
import path from 'path';

const CATEGORY_MAP = [
  'GPUs', 'Processors', 'RAM', 'Motherboards', 'SMPS', 'Storage', 'Cabinets', 'CpuCoolers'
];

const REVERSE_MAP: Record<string, ComponentCategory> = {
  'GPUs': 'Video Card',
  'Processors': 'CPU',
  'RAM': 'Memory',
  'Motherboards': 'Motherboard',
  'SMPS': 'Power Supply',
  'Storage': 'Storage',
  'Cabinets': 'Case',
  'CpuCoolers': 'CPU Cooler'
};

function normalizeSpecs(docSpecs: any): Record<string, string> {
  const specs: Record<string, string> = {};
  if (!docSpecs) return specs;
  for (const [key, val] of Object.entries(docSpecs)) {
    if (typeof val === 'string' && val.trim() !== '') {
      specs[key] = val.trim();
    }
  }
  return specs;
}

function extractWattage(title: string, specs: any): number {
  if (specs && specs["Wattage"]) {
     const w = parseInt(specs["Wattage"].replace(/\D/g, ''), 10);
     if (!isNaN(w)) return w;
  }
  return 0;
}

export async function GET(request: NextRequest) {
  try {
    const client = await clientPromise;
    const db = client.db('PC_Parts');

    // Pick 4 random distinct categories
    const shuffledCategories = [...CATEGORY_MAP].sort(() => 0.5 - Math.random());
    const selectedCategories = shuffledCategories.slice(0, 4);

    const trendingResults: Component[] = [];

    for (const collName of selectedCategories) {
        const collection = db.collection(collName);
        
        // Grab a few and pick one, or just grab the first one (skip a random amount)
        // For performance, just grab the first one with an image
        const doc = await collection.findOne({ image_path: { $exists: true, $ne: null } });
        
        if (doc) {
           const specs = normalizeSpecs(doc.specifications || doc.specs);
           let priceString = "0";
           if (typeof doc.price === 'object' && doc.price !== null) {
               priceString = doc.price.discounted || doc.price.original || "0";
           } else if (typeof doc.price === 'string') {
               priceString = doc.price;
           }
           const priceMatch = priceString.match(/[\d.]+/g);
           const priceClean = priceMatch ? priceMatch.join('') : "0";
           const price = parseFloat(priceClean);
           
           let imageLocalUrl = "https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400";
           if (doc.image_path) {
              const filename = path.basename(doc.image_path);
              imageLocalUrl = `/api/images?file=${encodeURIComponent(filename)}`;
           }

           const name = doc.name || doc.title || 'Unknown Product';
           const brand = specs['Brand'] || (name ? name.split(' ')[0] : 'Unknown');

           trendingResults.push({
             id: doc._id.toString(),
             category: REVERSE_MAP[collName],
             name: name,
             brand: brand,
             price: isNaN(price) ? 0 : price,
             image: imageLocalUrl,
             inStock: !doc.out_of_stock,
             wattage: extractWattage(name, doc.specifications || doc.specs),
             specs: specs
           });
        }
    }

    return NextResponse.json(trendingResults, { status: 200 });

  } catch (error: any) {
     console.error("API /components/trending error:", error);
     return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
