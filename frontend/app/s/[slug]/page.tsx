import { Metadata, ResolvingMetadata } from 'next';
import PublicDigestClient from './PublicDigestClient';

// Ensure fresh fetch every time (fixes caching of "Not Found" errors)
export const dynamic = 'force-dynamic';

type Props = {
    params: Promise<{ slug: string }>
};

// Fetch digest data for Metadata
async function getDigest(slug: string) {
    // Determine API Base URL
    // In production, server-side fetch cannot use localhost unless internal networking is set up.
    // Determined via User Input: Backend is hosted on Railway
    // HARDCODED to rule out bad ENV vars on Vercel
    const baseUrl = process.env.NODE_ENV === 'production'
        ? 'https://urbanous-production.up.railway.app'
        : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

    // console.log(`[Metadata] Fetching digest: ${slug} from ${baseUrl}`);
    try {
        const res = await fetch(`${baseUrl}/digests/public/${slug}`, {
            cache: 'no-store',
            headers: {
                'User-Agent': 'Urbanous-Metadata-Fetcher/1.0',
                'Accept': 'application/json'
            }
        });
        if (!res.ok) return null;
        return res.json();
    } catch (error) {
        console.error("Metadata fetch failed", error);
        return null;
    }
}

export async function generateMetadata(
    { params }: Props,
    parent: ResolvingMetadata
): Promise<Metadata> {
    // Next.js 15+: params is a Promise
    const { slug } = await params;
    const digest = await getDigest(slug);

    if (!digest) {
        return {
            title: 'Digest Not Found | Urbanous',
            description: 'The requested news digest could not be found.'
        };
    }

    // Format Period
    const end = new Date(digest.created_at);
    const start = new Date(end);
    if (digest.timeframe === '24h') start.setDate(end.getDate() - 1);
    else if (digest.timeframe === '3days') start.setDate(end.getDate() - 3);
    else if (digest.timeframe === '1week') start.setDate(end.getDate() - 7);

    const fmt = (d: Date) => `${d.getDate()}.${(d.getMonth() + 1)}.${d.getFullYear()}`;
    const period = `${fmt(start)} - ${fmt(end)}`;

    return {
        title: digest.title || 'Urbanous News Digest',
        description: `${digest.city} | ${period} | ${digest.category || 'General'}`,
        openGraph: {
            title: digest.title || 'Urbanous News Digest',
            description: `${digest.city} | ${period} | ${digest.category || 'General'}`,
            type: 'article',
        },
    };
}

export default async function Page({ params }: Props) {
    // We don't need params here for the client component, but we must respect the async signature
    await params;
    return <PublicDigestClient />;
}
