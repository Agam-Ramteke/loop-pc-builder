import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import {
  CATEGORY_COLLECTIONS,
  mapMongoDocToComponent,
} from '@/lib/componentData';

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db('PC_Parts');

    const selectedCategories = [...CATEGORY_COLLECTIONS]
      .sort(() => Math.random() - 0.5)
      .slice(0, 4);

    const sampledDocs = await Promise.all(
      selectedCategories.map(async (collectionName) => {
        const [doc] = await db
          .collection(collectionName)
          .aggregate<Record<string, unknown>>([
            {
              $match: {
                image_path: { $exists: true, $ne: null },
                out_of_stock: { $ne: true },
              },
            },
            { $sample: { size: 1 } },
            {
              $addFields: {
                collName: collectionName,
              },
            },
          ])
          .toArray();

        return doc ?? null;
      }),
    );

    const data = sampledDocs
      .filter((doc): doc is Record<string, unknown> => doc !== null)
      .map((doc) => mapMongoDocToComponent(doc, String(doc.collName)));

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('API /components/trending error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
