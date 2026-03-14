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

// Safety cap: never fetch more than this many docs per collection.
// Raise this if your collections grow beyond it.
const MAX_DOCS_PER_COLLECTION = 2000;

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
  return 0;
}

function parsePositiveInt(value: string | null, fallback: number, max?: number): number {
  const parsed = Number.parseInt(value ?? '', 10);
  if (!Number.isFinite(parsed) || parsed < 1) return fallback;
  if (max !== undefined) return Math.min(parsed, max);
  return parsed;
}

function parseOptionalNumber(value: string | null): number | null {
  if (value === null) return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const categoryQuery = searchParams.get('category');
    const searchQuery = searchParams.get('search');
    const sortBy = searchParams.get('sort');
    const page = parsePositiveInt(searchParams.get('page'), 1);
    const limit = parsePositiveInt(searchParams.get('limit'), 20, 100); // cap page size at 100

    // FIX 3 — Read price range from query params so filtering happens server-side
    const minPrice = parseOptionalNumber(searchParams.get('minPrice'));
    const maxPrice = parseOptionalNumber(searchParams.get('maxPrice'));
    const inStockOnly = searchParams.get('inStock') === 'true';

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

    // FIX 1 — Query all collections in parallel (no per-collection limit cap)
    const collectionResults = await Promise.all(
      collectionsToQuery.map(async (collName) => {
        const collection = db.collection(collName);

        const filter: any = {};
        if (searchQuery) {
          filter.$or = [
            { name: { $regex: searchQuery, $options: 'i' } },
            { title: { $regex: searchQuery, $options: 'i' } },
            { "specs.Brand": { $regex: searchQuery, $options: 'i' } }
          ];
        }

        // FIX 1 — Removed hard .limit(100); replaced with safety cap MAX_DOCS_PER_COLLECTION
        const docs = await collection.find(filter).limit(MAX_DOCS_PER_COLLECTION).toArray();

        const normalizedDocs: Component[] = docs.map(doc => {
          const specs = normalizeSpecs(doc.specifications || doc.specs);

          let discountedStr = '0';
          let originalStr = '0';
          let discountStr = '0';

          if (doc.price && typeof doc.price === 'object') {
            discountedStr = doc.price.discounted || '0';
            originalStr = doc.price.original || '0';
            discountStr = doc.price.discount || '0';
          } else if (doc.price && typeof doc.price === 'string') {
            discountedStr = doc.price;
          }

          let salePrice = 0;
          let originalPrice = 0;
          let discountPercent = 0;

          if (typeof discountedStr === 'string' || typeof originalStr === 'string') {
            const saleMatch = discountedStr.match?.(/[\d,.]+/g);
            salePrice = saleMatch ? parseFloat(saleMatch.join('').replace(/,/g, '')) : 0;

            const origMatch = originalStr.match?.(/[\d,.]+/g);
            const origNum = origMatch ? parseFloat(origMatch.join('').replace(/,/g, '')) : 0;

            if (!salePrice && origNum) salePrice = origNum;

            if (origNum && salePrice && origNum > salePrice) {
              originalPrice = origNum;
            }

            const discMatch = discountStr.match?.(/[\d.]+/);
            if (discMatch) {
              discountPercent = Math.round(parseFloat(discMatch[0]));
            } else if (origNum && salePrice && origNum > salePrice) {
              discountPercent = Math.round((1 - salePrice / origNum) * 100);
            }
          }


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
            price: isNaN(salePrice) ? 0 : salePrice,
            originalPrice: originalPrice,
            discountPercent: discountPercent,
            image: imageLocalUrl,
            inStock: !doc.out_of_stock && salePrice > 0,
            provider: doc.source || 'MD Computers',
            wattage: extractWattage(name, doc.specifications || doc.specs),
            specs: specs
          };
        });

        return normalizedDocs;
      })
    );

    let allResults: Component[] = collectionResults.flat();

    // ── SERVER-SIDE FILTERING ──
    if (minPrice !== null || maxPrice !== null || inStockOnly) {
      allResults = allResults.filter(comp => {
        const meetsMin = minPrice === null || comp.price >= minPrice;
        const meetsMax = maxPrice === null || comp.price <= maxPrice;
        const meetsStock = !inStockOnly || comp.inStock;
        return meetsMin && meetsMax && meetsStock;
      });
    }

    // FIX 2 — Added missing 'name' sort (A-Z). localeCompare handles accents/case correctly.
    if (sortBy === 'priceAsc') {
      allResults.sort((a, b) => a.price - b.price);
    } else if (sortBy === 'priceDesc') {
      allResults.sort((a, b) => b.price - a.price);
    } else {
      // Default: sort by name A-Z (covers the 'name' case and undefined sortBy)
      allResults.sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })
      );
    }

    const totalCount = allResults.length;
    const startIndex = (page - 1) * limit;
    const paginatedResults = allResults.slice(startIndex, startIndex + limit);

    return NextResponse.json({
      data: paginatedResults,
      totalCount,
      page,
      totalPages: Math.ceil(totalCount / limit)
    }, { status: 200 });

  } catch (error: any) {
    console.error("API /components error:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
