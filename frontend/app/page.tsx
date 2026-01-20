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

    return {
      title: `${title} | Urbanous`,
      description: description,
      openGraph: {
        title: title,
        description: description,
        // If the digest has a specific image (e.g. flag or city), use it? 
        // Currently data might not have a public image URL easily accessible, 
        // but we can fallback to the default or a specific implementation later.
        images: ['/about/hero.png'],
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
