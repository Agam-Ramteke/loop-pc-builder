import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import path from 'path';

const CATEGORY_MAP = [
  'GPUs', 'Processors', 'RAM', 'Motherboards', 'SMPS', 'Storage', 'Cabinets', 'CpuCoolers'
];

const REVERSE_CATEGORY: Record<string, string> = {
  'GPUs': 'Video Card',
  'Processors': 'CPU',
  'RAM': 'Memory',
  'Motherboards': 'Motherboard',
  'SMPS': 'Power Supply',
  'Storage': 'Storage',
  'Cabinets': 'Case',
  'CpuCoolers': 'CPU Cooler'
};

export interface DealItem {
  id: string;
  name: string;
  category: string;
  originalPrice: number;
  salePrice: number;
  discountPercent: number;
  image: string;
}

export async function GET(request: NextRequest) {
  try {
    const client = await clientPromise;
    const db = client.db('PC_Parts');

    const deals: DealItem[] = [];

    for (const collName of CATEGORY_MAP) {
      const collection = db.collection(collName);

      // Find products where the price object has a discount field
      const docs = await collection.find({
        'price.discount': { $exists: true, $nin: [null, ''] },
        image_path: { $exists: true, $ne: null },
      }).limit(5).toArray();

      for (const doc of docs) {
        if (!doc.price || typeof doc.price !== 'object') continue;

        const originalStr = doc.price.original || '';
        const discountedStr = doc.price.discounted || '';
        const discountStr = doc.price.discount || '';

        // Parse original price
        const origMatch = originalStr.match?.(/[\d,.]+/g);
        const originalPrice = origMatch ? parseFloat(origMatch.join('').replace(/,/g, '')) : 0;

        // Parse discounted price (may be null)
        let salePrice = 0;
        if (discountedStr) {
          const saleMatch = discountedStr.match?.(/[\d,.]+/g);
          salePrice = saleMatch ? parseFloat(saleMatch.join('').replace(/,/g, '')) : 0;
        }

        // Parse discount percent
        const discMatch = discountStr.match?.(/[\d.]+/);
        let discountPercent = discMatch ? parseFloat(discMatch[0]) : 0;

        // Calculate sale price if it was null but we have discount
        if (!salePrice && originalPrice && discountPercent) {
          salePrice = originalPrice * (1 - discountPercent / 100);
        }
        // Calculate discount percent if we have both prices but no explicit discount
        if (!discountPercent && originalPrice && salePrice && originalPrice > salePrice) {
          discountPercent = Math.round((1 - salePrice / originalPrice) * 100);
        }

        if (!originalPrice || !salePrice || discountPercent <= 0 || originalPrice <= salePrice) continue;

        let imageUrl = 'https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400';
        if (doc.image_path) {
          const filename = path.basename(doc.image_path);
          imageUrl = `/api/images?file=${encodeURIComponent(filename)}`;
        }

        deals.push({
          id: doc._id.toString(),
          name: doc.name || doc.title || 'Unknown Product',
          category: REVERSE_CATEGORY[collName] || collName,
          originalPrice: Math.round(originalPrice),
          salePrice: Math.round(salePrice),
          discountPercent: Math.round(discountPercent),
          image: imageUrl,
        });
      }
    }

    // Sort by highest discount first, take top 8
    deals.sort((a, b) => b.discountPercent - a.discountPercent);
    const topDeals = deals.slice(0, 8);

    return NextResponse.json(topDeals, { status: 200 });

  } catch (error: any) {
    console.error('API /components/deals error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
