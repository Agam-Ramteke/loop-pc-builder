import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import { Component, ComponentCategory } from '@/data/mockData';
import path from 'path';

// Map frontend categories to actual MongoDB collection names (as per the scraper variables)
const CATEGORY_MAP: Record<string, string> = {
  'Video Card': 'GPUs',
  'CPU': 'Processors',
  'Memory': 'RAM',
  'Motherboard': 'Motherboards',
  'Power Supply': 'SMPS',
  'Storage': 'Storage',
  'Case': 'Cabinets',
  'CPU Cooler': 'CpuCoolers'
};

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

// Map DB keys to standard keys to normalize the output without touching the db
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
  return 0; // Default or could employ regex on title if needed
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const categoryQuery = searchParams.get('category');
    const searchQuery = searchParams.get('search');
    const sortBy = searchParams.get('sort');
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '20', 10);

    const client = await clientPromise;
    const db = client.db('PC_Parts');
    
    // Determine which collections to scan
    let collectionsToQuery = Object.values(CATEGORY_MAP);
    if (categoryQuery && categoryQuery !== 'All') {
      const dbCollectionName = CATEGORY_MAP[categoryQuery];
      if (dbCollectionName) {
         collectionsToQuery = [dbCollectionName];
      } else {
         return NextResponse.json({ error: "Invalid category" }, { status: 400 });
      }
    }

    let allResults: any[] = [];

    for (const collName of collectionsToQuery) {
        const collection = db.collection(collName);

        const filter: any = {};
        if (searchQuery) {
            filter.$or = [
                { name: { $regex: searchQuery, $options: 'i' } },
                { title: { $regex: searchQuery, $options: 'i' } },
                { "specs.Brand": { $regex: searchQuery, $options: 'i' } }
            ];
        }

        const docs = await collection.find(filter).limit(100).toArray();
        
        const normalizedDocs: Component[] = docs.map(doc => {
           // Base schema extraction
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
           
           // Generate local image URL or fallback
           let imageLocalUrl = "https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400";
           if (doc.image_path) {
              const filename = path.basename(doc.image_path);
              imageLocalUrl = `/api/images?file=${encodeURIComponent(filename)}`;
           }

           const name = doc.name || doc.title || 'Unknown Product';
           const brand = specs['Brand'] || (name ? name.split(' ')[0] : 'Unknown');

           return {
             id: doc._id.toString(),
             category: REVERSE_MAP[collName],
             name: name,
             brand: brand,
             price: isNaN(price) ? 0 : price,
             image: imageLocalUrl,
             inStock: !doc.out_of_stock,
             wattage: extractWattage(name, doc.specifications || doc.specs),
             specs: specs
           };
        });

        allResults = allResults.concat(normalizedDocs);
    }

    // Handle generic cross-collection sorting natively in code since we combine arrays
    if (sortBy === 'priceAsc') {
        allResults.sort((a, b) => a.price - b.price);
    } else if (sortBy === 'priceDesc') {
        allResults.sort((a, b) => b.price - a.price);
    }

    const startIndex = (page - 1) * limit;
    const paginatedResults = allResults.slice(startIndex, startIndex + limit);

    return NextResponse.json({
      data: paginatedResults,
      totalCount: allResults.length,
      page,
      totalPages: Math.ceil(allResults.length / limit)
    }, { status: 200 });

  } catch (error: any) {
     console.error("API /components error:", error);
     return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
