import { NextRequest, NextResponse } from 'next/server';

// /api/extracted-data/* -> {baseUrl}/*
async function handler(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const baseUrl = process.env.NEXT_PUBLIC_EXTRACTED_DATA_BASE_URL;
  
  if (!baseUrl) {
    return NextResponse.json(
      { error: 'NEXT_PUBLIC_EXTRACTED_DATA_BASE_URL environment variable is not configured' },
      { status: 500 }
    );
  }

  // Reconstruct the path from the catch-all route
  const forwardPath = path.join('/');
  const targetUrl = `${baseUrl}/${forwardPath}`;
  
  // Forward query parameters
  const url = new URL(targetUrl);
  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.append(key, value);
  });

  try {
    // Create headers to forward (excluding hop-by-hop headers)
    const headers = new Headers();
    req.headers.forEach((value, key) => {
      // Skip hop-by-hop headers and host header
      if (!['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 
            'te', 'trailers', 'transfer-encoding', 'upgrade', 'host'].includes(key.toLowerCase())) {
        headers.set(key, value);
      }
    });

    // Forward the request
    const response = await fetch(url.toString(), {
      method: req.method,
      headers,
      body: req.method !== 'GET' && req.method !== 'HEAD' ? await req.arrayBuffer() : undefined,
    });

    // Create response headers (excluding hop-by-hop headers)
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (!['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 
            'te', 'trailers', 'transfer-encoding', 'upgrade'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    // Return the proxied response
    return new NextResponse(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request' },
      { status: 500 }
    );
  }
}

// Export handlers for different HTTP methods
export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
export const HEAD = handler;
export const OPTIONS = handler; 