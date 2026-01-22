import { Metadata, ResolvingMetadata } from 'next';
import { redirect } from 'next/navigation';

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

    // Default to 3 days if timeframe is missing or unknown, to avoid 1-day ranges which look bugged
    // The user likely wants to see the coverage period.
    if (digest.timeframe === '24h') start.setDate(end.getDate() - 1);
    else if (digest.timeframe === '1week') start.setDate(end.getDate() - 7);
    else start.setDate(end.getDate() - 3); // Default and '3days' case

    const d1 = start.getDate();
    const m1 = start.getMonth() + 1;
    const y1 = start.getFullYear();

    const d2 = end.getDate();
    const m2 = end.getMonth() + 1;
    const y2 = end.getFullYear();

    let period = "";
    if (y1 === y2 && m1 === m2) {
        // Same month/year: "14-17.1.2026"
        period = `${d1}-${d2}.${m1}.${y1}`;
    } else if (y1 === y2) {
        // Same year: "30.1 - 2.2.2026"
        period = `${d1}.${m1} - ${d2}.${m2}.${y1}`;
    } else {
        // Diff year
        period = `${d1}.${m1}.${y1} - ${d2}.${m2}.${y2}`;
    }

    // --- Image Logic (Mirroring NewsCard) ---
    const CITY_IMAGES: Record<string, string> = {
        "Tbilisi": "https://images.unsplash.com/photo-1565008447742-97f6f38c985c?auto=format&fit=crop&w=800&q=80",
        "Kyiv": "https://images.unsplash.com/photo-1561542320-9a18cd340469?auto=format&fit=crop&w=800&q=80",
        "Kiev": "https://images.unsplash.com/photo-1561542320-9a18cd340469?auto=format&fit=crop&w=800&q=80",
        "London": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=800&q=80",
        "New York": "https://images.unsplash.com/photo-1496442226666-8d4a0e62e6e9?auto=format&fit=crop&w=800&q=80",
        "Paris": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=800&q=80",
        "Berlin": "https://images.unsplash.com/photo-1560969184-10fe8719e047?auto=format&fit=crop&w=800&q=80",
        "Tokyo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=800&q=80",
    };
    const DEFAULT_IMAGE = "/static/digest_images/placeholder.png";

    // Select Image
    let imageUrl = digest.image_url || CITY_IMAGES[digest.city || ""] || DEFAULT_IMAGE;

    // Resolve Relative Paths to Absolute Backend URL
    if (imageUrl && imageUrl.startsWith('/')) {
        const baseUrl = process.env.NODE_ENV === 'production'
            ? 'https://urbanous-production.up.railway.app'
            : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
        // Remove trailing slash from base if present
        const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
        imageUrl = `${cleanBase}${imageUrl}`;
    }

    return {
        title: digest.title || 'Urbanous News Digest',
        description: `${digest.city} | ${period} | ${digest.category || 'General'}`,
        openGraph: {
            title: digest.title || 'Urbanous News Digest',
            description: `${digest.city} | ${period} | ${digest.category || 'General'}`,
            type: 'article',
            images: [
                {
                    url: imageUrl,
                    width: 800,
                    height: 600,
                    alt: digest.title || "News Digest Illustration"
                }
            ]
        },
    };
}

export default async function Page({ params }: Props) {
    const { slug } = await params;
    // Redirect to main page with view_digest param
    redirect(`/?view_digest=${slug}`);
}
