import { NextRequest, NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';

// Look at the backend scraper directory that holds the downloaded product images
const IMAGE_DIR = path.resolve(process.cwd(), '../Backend/Data_Collection/Scrapers/MD_computers/product_images');

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const filename = searchParams.get('file');

  if (!filename) {
    return new NextResponse('Filename is required', { status: 400 });
  }

  // Prevent directory traversal attacks
  const safeFilename = path.basename(filename);
  const filePath = path.join(IMAGE_DIR, safeFilename);

  try {
    if (!fs.existsSync(filePath)) {
      return new NextResponse('Image not found', { status: 404 });
    }

    const fileBuffer = fs.readFileSync(filePath);

    // Determine content type
    let contentType = 'image/jpeg';
    if (filePath.endsWith('.png')) contentType = 'image/png';
    else if (filePath.endsWith('.gif')) contentType = 'image/gif';
    else if (filePath.endsWith('.webp')) contentType = 'image/webp';
    else if (filePath.endsWith('.svg')) contentType = 'image/svg+xml';

    return new NextResponse(fileBuffer, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=86400', // Cache for 1 day
      },
    });
  } catch (error) {
    console.error('Error serving image:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
