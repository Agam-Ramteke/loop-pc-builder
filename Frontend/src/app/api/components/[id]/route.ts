import { NextRequest, NextResponse } from 'next/server';
import { ObjectId } from 'mongodb';
import clientPromise from '@/lib/mongodb';
import { CATEGORY_COLLECTIONS, mapMongoDocToComponent } from '@/lib/componentData';
import { cacheGet, cacheSet } from '@/lib/redis';

const CACHE_TTL_SECONDS = 1800;

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;

    if (!ObjectId.isValid(id)) {
      return NextResponse.json({ error: 'Invalid ID format' }, { status: 400 });
    }

    const cacheKey = `components:item:v1:${id}`;
    const cached = await cacheGet<ReturnType<typeof mapMongoDocToComponent>>(cacheKey);
    if (cached) {
      return NextResponse.json(cached, { status: 200 });
    }

    const objectId = new ObjectId(id);
    const client = await clientPromise;
    const db = client.db('PC_Parts');

    const results = await Promise.all(
      CATEGORY_COLLECTIONS.map(async (collectionName) => {
        const doc = await db.collection(collectionName).findOne({ _id: objectId });
        return doc ? { doc, collectionName } : null;
      }),
    );

    const found = results.find((result) => result !== null);
    if (!found) {
      return NextResponse.json({ error: 'Component not found' }, { status: 404 });
    }

    const payload = mapMongoDocToComponent(found.doc, found.collectionName);
    void cacheSet(cacheKey, payload, CACHE_TTL_SECONDS);

    return NextResponse.json(payload, { status: 200 });
  } catch (error) {
    console.error('API /components/[id] error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
