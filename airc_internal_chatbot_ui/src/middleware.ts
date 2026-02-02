import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    const token = request.cookies.get('access_token')?.value;
    const { pathname } = request.nextUrl;

    // Protected routes: /dashboard/*
    if (pathname.startsWith('/dashboard')) {
        if (!token) {
            const loginUrl = new URL('/auth/login', request.url);
            loginUrl.searchParams.set('redirect', pathname);
            return NextResponse.redirect(loginUrl);
        }
    }

    // Auth routes: /auth/*
    if (pathname.startsWith('/auth')) {
        if (token) {
            // If already logged in, redirect to dashboard
            // return NextResponse.redirect(new URL('/dashboard/chat', request.url));
            // Optional: Disable for now to allow accessing auth pages even if logged in (e.g. to logout or debug)
            // Or uncomment above to enforce.
        }
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/dashboard/:path*', '/auth/:path*'],
};
