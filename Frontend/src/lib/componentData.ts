import path from 'path';
import type { Document, Filter } from 'mongodb';
import type { Component, ComponentCategory } from '@/data/mockData';

export const CATEGORY_MAP: Record<string, string> = {
  'Video Card': 'GPUs',
  'CPU': 'Processors',
  'Memory': 'RAM',
  'Motherboard': 'Motherboards',
  'Power Supply': 'SMPS',
  'Storage': 'Storage',
  'Case': 'Cabinets',
  'CPU Cooler': 'CpuCoolers',
};

export const CATEGORY_COLLECTIONS = Object.values(CATEGORY_MAP);

export const REVERSE_CATEGORY_MAP: Record<string, ComponentCategory> = {
  GPUs: 'Video Card',
  Processors: 'CPU',
  RAM: 'Memory',
  Motherboards: 'Motherboard',
  SMPS: 'Power Supply',
  Storage: 'Storage',
  Cabinets: 'Case',
  CpuCoolers: 'CPU Cooler',
};

const DEFAULT_IMAGE_URL = 'https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400';

export function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function parseINRPrice(value: unknown): number {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }

  if (typeof value !== 'string') {
    return 0;
  }

  const match = value.replace(/,/g, '').match(/[\d.]+/);
  return match ? Number.parseFloat(match[0]) || 0 : 0;
}

export function parseDiscountPercent(value: unknown): number {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0;
  }

  if (typeof value !== 'string') {
    return 0;
  }

  const match = value.match(/[\d.]+/);
  return match ? Number.parseFloat(match[0]) || 0 : 0;
}

export function normalizeSpecs(docSpecs: unknown): Record<string, string> {
  if (!docSpecs || typeof docSpecs !== 'object' || Array.isArray(docSpecs)) {
    return {};
  }

  const specs: Record<string, string> = {};

  for (const [key, value] of Object.entries(docSpecs)) {
    if (typeof value === 'string' && value.trim() !== '') {
      specs[key] = value.trim();
    }
  }

  return specs;
}

export function extractWattage(name: string, specs: Record<string, string>): number {
  const wattage = specs.Wattage;
  if (wattage) {
    const parsed = Number.parseInt(wattage.replace(/\D/g, ''), 10);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }

  const fromName = name.match(/(\d{2,4})\s*W\b/i);
  if (fromName) {
    const parsed = Number.parseInt(fromName[1], 10);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }

  return 0;
}

export function resolveImageUrl(imagePath: unknown): string {
  if (typeof imagePath !== 'string' || imagePath.trim() === '') {
    return DEFAULT_IMAGE_URL;
  }

  return `/api/images?file=${encodeURIComponent(path.basename(imagePath))}`;
}

export function getResolvedName(doc: Record<string, unknown>): string {
  if (typeof doc.name === 'string' && doc.name.trim() !== '') {
    return doc.name;
  }

  if (typeof doc.title === 'string' && doc.title.trim() !== '') {
    return doc.title;
  }

  return 'Unknown Product';
}

export function getComponentPriceFields(doc: Record<string, unknown>) {
  const priceValue = doc.price;

  let discounted = 0;
  let original = 0;
  let discountPercent = 0;

  if (typeof doc.numericPrice === 'number' && Number.isFinite(doc.numericPrice)) {
    discounted = doc.numericPrice;
  }

  if (typeof doc.numericOriginalPrice === 'number' && Number.isFinite(doc.numericOriginalPrice)) {
    original = doc.numericOriginalPrice;
  }

  if (typeof doc.numericDiscountPercent === 'number' && Number.isFinite(doc.numericDiscountPercent)) {
    discountPercent = Math.round(doc.numericDiscountPercent);
  }

  if (!discounted) {
    if (priceValue && typeof priceValue === 'object' && !Array.isArray(priceValue)) {
      const priceObject = priceValue as Record<string, unknown>;
      discounted = parseINRPrice(priceObject.discounted ?? priceObject.original);
      original = original || parseINRPrice(priceObject.original ?? priceObject.discounted);
      discountPercent = discountPercent || Math.round(parseDiscountPercent(priceObject.discount));
    } else {
      discounted = parseINRPrice(priceValue);
      original = original || discounted;
    }
  }

  if (!original && discounted) {
    original = discounted;
  }

  if (!discountPercent && original > discounted && discounted > 0) {
    discountPercent = Math.round(((original - discounted) / original) * 100);
  }

  if (original <= discounted) {
    original = 0;
  }

  return {
    price: discounted,
    originalPrice: original,
    discountPercent,
  };
}

export function mapMongoDocToComponent(doc: Record<string, unknown>, collectionName: string): Component {
  const specs = normalizeSpecs(doc.specifications ?? doc.specs ?? doc.normalizedSpecs);
  const name = getResolvedName(doc);
  const brand = specs.Brand || name.split(' ')[0] || 'Unknown';
  const { price, originalPrice, discountPercent } = getComponentPriceFields(doc);

  return {
    id: String(doc._id),
    category: REVERSE_CATEGORY_MAP[collectionName],
    name,
    brand,
    price: Number.isFinite(price) ? price : 0,
    originalPrice,
    discountPercent,
    image: resolveImageUrl(doc.image_path),
    inStock: doc.out_of_stock !== true && price > 0,
    provider: typeof doc.source === 'string' && doc.source.trim() !== '' ? doc.source : 'MD Computers',
    wattage: extractWattage(name, specs),
    specs,
  };
}

export function buildSearchFilter(searchQuery?: string, inStockOnly?: boolean): Filter<Document> {
  const filter: Filter<Document> = {};

  if (searchQuery?.trim()) {
    const regex = new RegExp(escapeRegex(searchQuery.trim()), 'i');
    filter.$or = [
      { name: regex },
      { title: regex },
      { 'specifications.Brand': regex },
      { 'specs.Brand': regex },
    ];
  }

  if (inStockOnly) {
    filter.out_of_stock = { $ne: true };
  }

  return filter;
}

export function createResolvedNameExpression(): Document {
  return {
    $ifNull: ['$name', { $ifNull: ['$title', 'Unknown Product'] }],
  };
}

export function createResolvedSpecsExpression(): Document {
  return {
    $ifNull: ['$specifications', { $ifNull: ['$specs', {}] }],
  };
}

export function createResolvedSalePriceSourceExpression(): Document {
  return {
    $ifNull: ['$price.discounted', { $ifNull: ['$price.original', { $ifNull: ['$price', '0'] }] }],
  };
}

export function createResolvedOriginalPriceSourceExpression(): Document {
  return {
    $ifNull: ['$price.original', { $ifNull: ['$price.discounted', { $ifNull: ['$price', '0'] }] }],
  };
}

export function createPriceNumberExpression(source: unknown): Document {
  if (source === '$price.original') {
    return { $ifNull: ['$numericOriginalPrice', 0] };
  }
  if (source === '$price.discounted' || source === '$price') {
    return { $ifNull: ['$numericPrice', 0] };
  }

  // Fallback to parsing the string natively in MongoDB 4.4+
  let cleaned: Document = { 
    $convert: { input: source, to: 'string', onError: '0', onNull: '0' }
  };
  const removals = ['₹', 'Rs.', 'Rs', ',', ' '];
  for (const r of removals) {
    cleaned = {
      $replaceAll: {
        input: cleaned,
        find: r,
        replacement: ''
      }
    };
  }

  return {
    $convert: {
      input: { $trim: { input: cleaned } },
      to: 'double',
      onError: 0,
      onNull: 0
    }
  };
}
