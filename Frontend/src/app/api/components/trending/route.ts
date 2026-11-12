import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import {
  CATEGORY_COLLECTIONS,
  mapMongoDocToComponent,
} from '@/lib/componentData';
import { cacheGet, cacheSet } from '@/lib/redis';

const CACHE_KEY = 'components:trending:v1';
const CACHE_TTL_SECONDS = 600;

export async function GET() {
  try {
    const cached = await cacheGet<ReturnType<typeof mapMongoDocToComponent>[]>(CACHE_KEY);
    if (cached) {
      return NextResponse.json(cached, { status: 200 });
    }

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

    void cacheSet(CACHE_KEY, data, CACHE_TTL_SECONDS);

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('API /components/trending error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
