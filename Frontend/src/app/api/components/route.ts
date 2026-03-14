import { NextRequest, NextResponse } from 'next/server';
import type { Db, Document } from 'mongodb';
import clientPromise from '@/lib/mongodb';
import {
  CATEGORY_COLLECTIONS,
  CATEGORY_MAP,
  buildSearchFilter,
  createPriceNumberExpression,
  createResolvedNameExpression,
  createResolvedOriginalPriceSourceExpression,
  createResolvedSalePriceSourceExpression,
  createResolvedSpecsExpression,
  mapMongoDocToComponent,
} from '@/lib/componentData';
import { buildCacheKey, cacheGet, cacheSet } from '@/lib/redis';

type ComponentSort = 'priceAsc' | 'priceDesc' | 'name';
const CACHE_TTL_SECONDS = 120;

function buildBasePipeline(options: {
  collectionName: string;
  searchQuery?: string | null;
  inStockOnly: boolean;
  minPrice: number | null;
  maxPrice: number | null;
}): Document[] {
  const pipeline: Document[] = [];
  const searchFilter = buildSearchFilter(options.searchQuery ?? undefined, options.inStockOnly);

  if (Object.keys(searchFilter).length > 0) {
    pipeline.push({ $match: searchFilter });
  }

  pipeline.push({
    $addFields: {
      resolvedName: createResolvedNameExpression(),
      normalizedSpecs: createResolvedSpecsExpression(),
      numericPrice: createPriceNumberExpression(createResolvedSalePriceSourceExpression()),
      numericOriginalPrice: createPriceNumberExpression(createResolvedOriginalPriceSourceExpression()),
    },
  });

  const priceMatch: Record<string, number> = {};
  if (options.minPrice !== null) {
    priceMatch.$gte = options.minPrice;
  }
  if (options.maxPrice !== null) {
    priceMatch.$lte = options.maxPrice;
  }

  if (Object.keys(priceMatch).length > 0) {
    pipeline.push({ $match: { numericPrice: priceMatch } });
  }

  pipeline.push({
    $addFields: {
      numericDiscountPercent: {
        $cond: [
          {
            $and: [
              { $gt: ['$numericOriginalPrice', 0] },
              { $gt: ['$numericPrice', 0] },
              { $gt: ['$numericOriginalPrice', '$numericPrice'] },
            ],
          },
          {
            $multiply: [
              {
                $divide: [
                  { $subtract: ['$numericOriginalPrice', '$numericPrice'] },
                  '$numericOriginalPrice',
                ],
              },
              100,
            ],
          },
          0,
        ],
      },
      collName: { $literal: options.collectionName },
    },
  });

  pipeline.push({
    $project: {
      _id: 1,
      name: 1,
      title: 1,
      price: 1,
      source: 1,
      out_of_stock: 1,
      image_path: 1,
      normalizedSpecs: 1,
      numericPrice: 1,
      numericOriginalPrice: 1,
      numericDiscountPercent: 1,
      resolvedName: 1,
      collName: 1,
    },
  });

  return pipeline;
}

function buildUnionPipeline(collectionsToQuery: string[], options: Omit<Parameters<typeof buildBasePipeline>[0], 'collectionName'>): {
  collectionName: string;
  pipeline: Document[];
} {
  const [firstCollection, ...restCollections] = collectionsToQuery;
  const pipeline = buildBasePipeline({
    collectionName: firstCollection,
    ...options,
  });

  for (const collectionName of restCollections) {
    pipeline.push({
      $unionWith: {
        coll: collectionName,
        pipeline: buildBasePipeline({
          collectionName,
          ...options,
        }),
      },
    });
  }

  return {
    collectionName: firstCollection,
    pipeline,
  };
}

function buildSortStage(sortBy: string | null): Record<string, 1 | -1> {
  const safeSort = sortBy as ComponentSort | null;

  if (safeSort === 'priceAsc') {
    return {
      numericPrice: 1,
      resolvedName: 1,
    };
  }

  if (safeSort === 'priceDesc') {
    return {
      numericPrice: -1,
      resolvedName: 1,
    };
  }

  return {
    resolvedName: 1,
  };
}

async function countMatchingComponents(
  db: Db,
  collectionsToQuery: string[],
  options: Omit<Parameters<typeof buildBasePipeline>[0], 'collectionName'>,
): Promise<number> {
  const countResults = await Promise.all(
    collectionsToQuery.map(async (collectionName) => {
      const [countResult] = await db
        .collection(collectionName)
        .aggregate<{ totalCount: number }>([
          ...buildBasePipeline({
            collectionName,
            ...options,
          }),
          { $count: 'totalCount' },
        ])
        .toArray();

      return countResult?.totalCount ?? 0;
    }),
  );

  return countResults.reduce((sum, count) => sum + count, 0);
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const categoryQuery = searchParams.get('category');
    const searchQuery = searchParams.get('search');
    const sortBy = searchParams.get('sort');
    const parsedPage = Number.parseInt(searchParams.get('page') || '1', 10);
    const parsedLimit = Number.parseInt(searchParams.get('limit') || '21', 10);
    const page = Number.isFinite(parsedPage) ? Math.max(parsedPage, 1) : 1;
    const limit = Number.isFinite(parsedLimit) ? Math.min(Math.max(parsedLimit, 1), 100) : 21;
    const skip = (page - 1) * limit;
    const minPrice = searchParams.has('minPrice') ? Number.parseFloat(searchParams.get('minPrice') || '') : null;
    const maxPrice = searchParams.has('maxPrice') ? Number.parseFloat(searchParams.get('maxPrice') || '') : null;
    const inStockOnly = searchParams.get('inStock') === 'true';
    const safeMinPrice = Number.isFinite(minPrice) ? minPrice : null;
    const safeMaxPrice = Number.isFinite(maxPrice) ? maxPrice : null;

    const cacheKey = buildCacheKey('components:browse:v1', {
      category: categoryQuery || 'All',
      search: searchQuery || '',
      sort: sortBy || 'name',
      page,
      limit,
      minPrice: safeMinPrice,
      maxPrice: safeMaxPrice,
      inStockOnly,
    });

    const cached = await cacheGet<{
      data: ReturnType<typeof mapMongoDocToComponent>[];
      totalCount: number;
      page: number;
      totalPages: number;
    }>(cacheKey);
    if (cached) {
      return NextResponse.json(cached, { status: 200 });
    }

    let collectionsToQuery = CATEGORY_COLLECTIONS;
    if (categoryQuery && categoryQuery !== 'All') {
      const mappedCollection = CATEGORY_MAP[categoryQuery];
      if (!mappedCollection) {
        return NextResponse.json({ error: 'Invalid category' }, { status: 400 });
      }
      collectionsToQuery = [mappedCollection];
    }

    const client = await clientPromise;
    const db = client.db('PC_Parts');

    const queryOptions = {
      searchQuery,
      inStockOnly,
      minPrice: safeMinPrice,
      maxPrice: safeMaxPrice,
    };
    const { collectionName, pipeline } = buildUnionPipeline(collectionsToQuery, queryOptions);

    const sortStage = buildSortStage(sortBy);

    const [docs, totalCount] = await Promise.all([
      db
        .collection(collectionName)
        .aggregate<Record<string, unknown>>([
          ...pipeline,
          { $sort: sortStage },
          { $skip: skip },
          { $limit: limit },
        ])
        .toArray(),
      countMatchingComponents(db, collectionsToQuery, queryOptions),
    ]);

    const data = docs.map((doc) => mapMongoDocToComponent(doc, String(doc.collName)));

    const payload = {
      data,
      totalCount,
      page,
      totalPages: totalCount > 0 ? Math.ceil(totalCount / limit) : 1,
    };

    void cacheSet(cacheKey, payload, CACHE_TTL_SECONDS);

    return NextResponse.json(payload, { status: 200 });
  } catch (error) {
    console.error('API /components error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
