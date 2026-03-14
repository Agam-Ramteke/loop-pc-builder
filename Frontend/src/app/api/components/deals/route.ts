import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';
import {
  CATEGORY_COLLECTIONS,
  REVERSE_CATEGORY_MAP,
  createPriceNumberExpression,
  createResolvedNameExpression,
  resolveImageUrl,
} from '@/lib/componentData';

export interface DealItem {
  id: string;
  name: string;
  category: string;
  originalPrice: number;
  salePrice: number;
  discountPercent: number;
  image: string;
}

export async function GET() {
  try {
    const client = await clientPromise;
    const db = client.db('PC_Parts');

    const dealGroups = await Promise.all(
      CATEGORY_COLLECTIONS.map(async (collectionName) => {
        const docs = await db
          .collection(collectionName)
          .aggregate<Record<string, unknown>>([
            {
              $match: {
                image_path: { $exists: true, $ne: null },
                out_of_stock: { $ne: true },
              },
            },
            {
              $addFields: {
                resolvedName: createResolvedNameExpression(),
                numericOriginalPrice: createPriceNumberExpression('$price.original'),
                numericSalePrice: createPriceNumberExpression({
                  $ifNull: ['$price.discounted', '$price.original'],
                }),
              },
            },
            {
              $addFields: {
                numericDiscountPercent: {
                  $cond: [
                    {
                      $and: [
                        { $gt: ['$numericOriginalPrice', 0] },
                        { $gt: ['$numericSalePrice', 0] },
                        { $gt: ['$numericOriginalPrice', '$numericSalePrice'] },
                      ],
                    },
                    {
                      $multiply: [
                        {
                          $divide: [
                            { $subtract: ['$numericOriginalPrice', '$numericSalePrice'] },
                            '$numericOriginalPrice',
                          ],
                        },
                        100,
                      ],
                    },
                    0,
                  ],
                },
              },
            },
            {
              $match: {
                numericOriginalPrice: { $gt: 0 },
                numericSalePrice: { $gt: 0 },
                numericDiscountPercent: { $gt: 0 },
              },
            },
            {
              $sort: {
                numericDiscountPercent: -1,
                numericSalePrice: 1,
              },
            },
            { $limit: 5 },
            {
              $project: {
                _id: 1,
                resolvedName: 1,
                image_path: 1,
                numericOriginalPrice: 1,
                numericSalePrice: 1,
                numericDiscountPercent: 1,
              },
            },
          ])
          .toArray();

        return docs.map((doc) => ({
          id: String(doc._id),
          name: String(doc.resolvedName || 'Unknown Product'),
          category: REVERSE_CATEGORY_MAP[collectionName] || collectionName,
          originalPrice: Math.round(Number(doc.numericOriginalPrice) || 0),
          salePrice: Math.round(Number(doc.numericSalePrice) || 0),
          discountPercent: Math.round(Number(doc.numericDiscountPercent) || 0),
          image: resolveImageUrl(doc.image_path),
        }));
      }),
    );

    const topDeals = dealGroups
      .flat()
      .sort((a, b) => b.discountPercent - a.discountPercent || a.salePrice - b.salePrice)
      .slice(0, 8);

    return NextResponse.json(topDeals, { status: 200 });
  } catch (error) {
    console.error('API /components/deals error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
