import { createHash } from 'crypto';
import Redis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379/0';

declare global {
  var __redis: Redis | undefined;
}

function createClient(): Redis {
  return new Redis(REDIS_URL, {
    maxRetriesPerRequest: 1,
    lazyConnect: true,
    enableOfflineQueue: false,
  });
}

const redis = global.__redis ?? createClient();

redis.removeAllListeners('error');
redis.on('error', (error) => {
  if (process.env.NODE_ENV !== 'production' && (!error.message || error.message.includes('ECONNREFUSED'))) {
    return;
  }
  console.warn('Redis error:', error.message || error);
});

if (process.env.NODE_ENV === 'development') {
  global.__redis = redis;
}

export default redis;

export function buildCacheKey(namespace: string, payload: unknown): string {
  const hash = createHash('sha1').update(JSON.stringify(payload)).digest('hex');
  return `${namespace}:${hash}`;
}

export async function cacheGet<T>(key: string): Promise<T | null> {
  try {
    const value = await redis.get(key);
    return value ? (JSON.parse(value) as T) : null;
  } catch {
    return null;
  }
}

export async function cacheSet(key: string, value: unknown, ttlSeconds: number): Promise<void> {
  try {
    await redis.setex(key, ttlSeconds, JSON.stringify(value));
  } catch {
    // Cache writes are best-effort only.
  }
}

export async function cacheInvalidate(pattern: string): Promise<void> {
  try {
    const keys: string[] = [];
    const stream = redis.scanStream({ match: pattern });
    for await (const resultKeys of stream) {
      keys.push(...(resultKeys as string[]));
    }

    if (keys.length > 0) {
      await redis.del(...keys);
    }
  } catch {
    // Cache invalidation should never block the request path.
  }
}
