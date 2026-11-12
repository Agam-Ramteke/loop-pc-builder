import { NextRequest, NextResponse } from 'next/server';
import path from 'path';
import { access, readFile } from 'fs/promises';

// All directories that may contain product images from different scrapers.
// The API will search each directory in order and serve the first match.
const IMAGE_DIRS = [
  path.resolve(process.cwd(), '../Backend/Data_Collection/Scrapers/MD_computers/product_images'),
  path.resolve(process.cwd(), '../Backend/Data_Collection/Scrapers/PrimeABGB/product_images'),
  path.resolve(process.cwd(), '../Backend/Data_Collection/Scrapers/Elite Hubs/product_images'),
];

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const filename = searchParams.get('file');

  if (!filename) {
    return new NextResponse('Filename is required', { status: 400 });
  }

  // Prevent directory traversal attacks
  const safeFilename = path.basename(filename);

  // Search through all image directories for the file
  for (const imageDir of IMAGE_DIRS) {
    const filePath = path.join(imageDir, safeFilename);

    try {
      await access(filePath);
      const fileBuffer = await readFile(filePath);

      let contentType = 'image/jpeg';
      if (filePath.endsWith('.png')) contentType = 'image/png';
      else if (filePath.endsWith('.gif')) contentType = 'image/gif';
      else if (filePath.endsWith('.webp')) contentType = 'image/webp';
      else if (filePath.endsWith('.svg')) contentType = 'image/svg+xml';

      return new NextResponse(fileBuffer, {
        status: 200,
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'public, max-age=86400',
        },
      });
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        console.error(`Error checking image in ${imageDir}:`, error);
      }
    }
  }

  // None of the directories had the file
  return new NextResponse('Image not found', { status: 404 });
}
