import { Metadata } from 'next';
import HomeClient from '@/components/HomeClient';

// Force dynamic rendering since we depend on searchParams
export const dynamic = 'force-dynamic';

export async function generateMetadata({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }): Promise<Metadata> {
  const params = await searchParams;
  const viewDigestSlug = params.view_digest;

  // Default Metadata
  const defaultMeta = {
    title: "Urbanous.net | Global News Intelligence",
    description: "Real-time AI News Discovery & Analysis. Navigate global news through local sources.",
    openGraph: {
      title: "Urbanous.net | Global News Intelligence",
      description: "Real-time AI News Discovery & Analysis. Navigate global news through local sources.",
      images: ['/about/hero.png'], // Default Hero
    }
  };

  if (!viewDigestSlug || typeof viewDigestSlug !== 'string') {
    return defaultMeta;
  }

  // Fetch Digest Metadata
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const res = await fetch(`${baseUrl}/digests/public/${viewDigestSlug}`);

    if (!res.ok) return defaultMeta;

    const data = await res.json();

    // Format Title & Description
    const title = data.title || `${data.city} Headlines`;
    const description = `${data.category || 'News'} Digest • ${data.timeframe || 'Recent'} • Read local insights from ${data.city}.`;

    // --- Image Logic (Mirroring NewsCard & Share Page) ---
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
    const DEFAULT_IMAGE = "https://www.urbanous.net/about/hero.png";

    // Select Image
    let imageUrl = data.image_url || CITY_IMAGES[data.city || ""] || DEFAULT_IMAGE;

    // Resolve Relative Paths to Absolute Backend URL (CRITICAL for Social Cards)
    if (imageUrl && imageUrl.startsWith('/')) {
      // Use Production Backend URL for cards to ensure images are reachable
      // Even if running local frontend, the card needs a public URL.
      const baseUrl = process.env.NODE_ENV === 'production'
        ? 'https://urbanous-production.up.railway.app'
        // If local, we can't really share localhost images 
        // but we'll fallback to dev behavior
        : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');

      const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
      imageUrl = `${cleanBase}${imageUrl}`;
    }

    // fallback to hero if everything failed? No, imageUrl should be set.

    return {
      title: `${title} | Urbanous`,
      description: description,
      openGraph: {
        title: title,
        description: description,
        url: `https://urbanous-production.up.railway.app/?view_digest=${viewDigestSlug}`,
        images: [
          {
            url: imageUrl,
            width: 1200,
            height: 630,
            alt: title
          }
        ],
        type: 'article'
      },
      twitter: {
        card: 'summary_large_image',
        title: title,
        description: description,
        images: [imageUrl],
      }
    };

  } catch (error) {
    console.error("Failed to fetch metadata for digest:", error);
    return defaultMeta;
  }
}

export default function Home() {
  return <HomeClient />;
}
