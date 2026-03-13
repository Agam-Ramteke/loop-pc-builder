import { NextRequest, NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import { ObjectId } from 'mongodb';
import path from 'path';

// Reusing same logic as list route, mapping needed locally
const CATEGORY_MAP = [
  'GPUs', 'Processors', 'RAM', 'Motherboards', 'SMPS', 'Storage', 'Cabinets', 'CpuCoolers'
];

const REVERSE_MAP: Record<string, any> = {
  'GPUs': 'Video Card',
  'Processors': 'CPU',
  'RAM': 'Memory',
  'Motherboards': 'Motherboard',
  'SMPS': 'Power Supply',
  'Storage': 'Storage',
  'Cabinets': 'Case',
  'CpuCoolers': 'CPU Cooler'
};

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    
    if (!ObjectId.isValid(id)) {
       return NextResponse.json({ error: "Invalid ID format" }, { status: 400 });
    }
    const objectId = new ObjectId(id);

    const client = await clientPromise;
    const db = client.db('PC_Parts');

    // Mongoose doesn't know which collection the ID belongs to, so we scan until found.
    // In a real optimized system, ID references might encode the collection, or we store all mixed.
    for (const collName of CATEGORY_MAP) {
      const collection = db.collection(collName);
      const doc = await collection.findOne({ _id: objectId });

      if (doc) {
           const specs: Record<string, string> = {};
           const specsData = doc.specifications || doc.specs;
           if (specsData) {
              for (const [key, val] of Object.entries(specsData)) {
                if (typeof val === 'string' && val.trim() !== '') {
                  specs[key] = val.trim();
                }
              }
           }

           let priceString = "0";
           if (typeof doc.price === 'object' && doc.price !== null) {
               priceString = doc.price.discounted || doc.price.original || "0";
           } else if (typeof doc.price === 'string') {
               priceString = doc.price;
           }
           
           const priceMatch = priceString.match(/[\d.]+/g);
           const priceClean = priceMatch ? priceMatch.join('') : "0";
           const price = parseFloat(priceClean);
           const name = doc.name || doc.title || 'Unknown Product';
           const brand = specs['Brand'] || (name ? name.split(' ')[0] : 'Unknown');

           let imageLocalUrl = "https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400";
           if (doc.image_path) {
              imageLocalUrl = `/api/images?file=${encodeURIComponent(path.basename(doc.image_path))}`;
           }

           const component = {
             id: doc._id.toString(),
             category: REVERSE_MAP[collName],
             name: name,
             brand: brand,
             price: isNaN(price) ? 0 : price,
             provider: doc.source || 'MD Computers',
             image: imageLocalUrl,
             inStock: !doc.out_of_stock,
             wattage: 0, // Simplified extraction
             specs: specs
           };

           return NextResponse.json(component, { status: 200 });
      }
    }

    return NextResponse.json({ error: "Component not found" }, { status: 404 });

  } catch (error) {
     console.error("API /components/[id] error:", error);
     return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
