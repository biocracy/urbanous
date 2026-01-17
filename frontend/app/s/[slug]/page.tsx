import { Metadata, ResolvingMetadata } from 'next';
import PublicDigestClient from './PublicDigestClient';

type Props = {
    params: { slug: string }
};

// Fetch digest data for Metadata
async function getDigest(slug: string) {
    // Determine API Base URL
    // In production, server-side fetch cannot use localhost unless internal networking is set up.
    // Determined via User Input: Backend is hosted on Railway
    const isProd = process.env.NODE_ENV === 'production';
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || (isProd ? 'https://urbanous-production.up.railway.app' : 'http://localhost:8000');

    console.log(`[Metadata] Fetching digest: ${slug} from ${baseUrl}`);
    try {
        const res = await fetch(`${baseUrl}/digests/public/${slug}`, { next: { revalidate: 60 } });
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
    const slug = params.slug;
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

    // Requested Format: 
    // Title: Digest Title
    // Description: City Name | Period | Category

    return {
        title: digest.title || 'Urbanous News Digest',
        description: `${digest.city} | ${period} | ${digest.category || 'General'}`,
        openGraph: {
            title: digest.title || 'Urbanous News Digest',
            description: `${digest.city} | ${period} | ${digest.category || 'General'}`,
            type: 'article',
            images: ['/og-image-digest.png'], // Optional: Add a custom OG image if available
        },
    };
}

export default function Page({ params }: Props) {
    return <PublicDigestClient />;
}
