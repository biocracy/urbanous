import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Footer from './Footer';
import UnifiedDigestViewer from './UnifiedDigestViewer';
import { ArrowLeft, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';

// --- DATA TYPES ---
interface DigestFeedItem {
    id: number;
    slug: string;
    title: string;
    category: string;
    city: string;
    timeframe?: string;
    created_at: string;
    image_url?: string;
    user_name: string;
    summary?: string;
}

// --- STATIC IMAGES ---
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

const formatDateRange = (createdDateStr: string, timeframeStr: string = "24h") => {
    const createdDate = new Date(createdDateStr);
    const msToSubtract = timeframeStr === '24h' ? 24 * 60 * 60 * 1000 :
        timeframeStr === '3days' ? 3 * 24 * 60 * 60 * 1000 :
            (timeframeStr === 'week' || timeframeStr === '1week') ? 7 * 24 * 60 * 60 * 1000 : 0;
    const startDate = new Date(createdDate.getTime() - msToSubtract);

    // Format: DD.MM - DD.MM.YYYY
    const d1 = startDate.getDate().toString().padStart(2, '0');
    const m1 = (startDate.getMonth() + 1).toString().padStart(2, '0');
    const d2 = createdDate.getDate().toString().padStart(2, '0');
    const m2 = (createdDate.getMonth() + 1).toString().padStart(2, '0');
    const y = createdDate.getFullYear();

    // Compact format if months match: DD - DD.MM.YYYY
    if (m1 === m2) {
        if (d1 === d2) {
            return `${d2}.${m2}.${y}`;
        }
        return `${d1}-${d2}.${m2}.${y}`;
    }
    return `${d1}.${m1}-${d2}.${m2}.${y}`;
};


interface FeedLayoutProps {
    activeDigest?: any;
    onCloseDigest?: () => void;
}

export default function FeedLayout({ activeDigest, onCloseDigest }: FeedLayoutProps) {
    const [showAbout, setShowAbout] = useState(false);
    const [feedItems, setFeedItems] = useState<DigestFeedItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [page, setPage] = useState(0); // 0-indexed
    const [localDigest, setLocalDigest] = useState<any>(null); // NEW: Local mutable state for viewer
    const ITEMS_PER_PAGE = 6;
    const router = useRouter();

    // Sync activeDigest prop to local state
    useEffect(() => {
        setLocalDigest((prev: any) => {
            // Only overwrite if it's a DIFFERENT digest (or we had nothing)
            // This prevents background re-renders/fetches from wiping out local edit state (like the loader)
            // DEBUG LOG:
            if (activeDigest) {
                // console.log(`[FeedLayout] Syncing. ActiveID: ${activeDigest.id} (${typeof activeDigest.id}), PrevID: ${prev?.id} (${typeof prev?.id})`);
            }

            if (!prev || prev.id !== activeDigest?.id) {
                return activeDigest;
            }
            return prev;
        });
    }, [activeDigest]);

    // Fetch Feed Function
    const fetchFeed = async () => {
        setIsLoading(true);
        try {
            // Add timestamp to prevent caching
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/digests/public?limit=${ITEMS_PER_PAGE}&offset=${page * ITEMS_PER_PAGE}&_t=${Date.now()}`);
            if (res.ok) {
                const data = await res.json();
                setFeedItems(data);
            } else {
                console.error("Failed to fetch feed");
            }
        } catch (err) {
            console.error("Error fetching feed:", err);
        } finally {
            setIsLoading(false);
        }
    };

    // Initial Fetch & Page Change
    useEffect(() => {
        fetchFeed();
    }, [page]);

    // Re-fetch when closing digest (returning to list) to ensure updates
    useEffect(() => {
        if (!activeDigest) {
            fetchFeed();
        }
    }, [activeDigest]);

    // Handle Card Click
    const handleCardClick = (slug: string) => {
        router.push(`/?view_digest=${slug}`);
    };

    // If Viewing a Digest, override the main content
    if (activeDigest) {
        // Use local state if synced, else fallback to prop
        const digestToRender = localDigest || activeDigest;

        return (
            <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8 flex flex-col min-h-full">
                {/* Header with Back Button */}
                <div className="flex items-center gap-4 mb-4">
                    <button
                        onClick={onCloseDigest}
                        className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors flex items-center gap-2 group"
                    >
                        <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
                        <span className="font-mono text-sm uppercase">Back to Live Stream</span>
                    </button>
                    <div className="h-1 w-12 bg-blue-500 rounded-full shadow-[0_0_10px_#3b82f6] ml-auto"></div>
                    <span className="text-neutral-500 text-sm font-mono">ARCHIVED REPORT MODE</span>
                </div>

                {/* Unified Viewer Container */}
                <div className="w-full bg-neutral-900/30 border border-neutral-800 rounded-2xl overflow-hidden shadow-2xl min-h-[800px]">
                    <UnifiedDigestViewer
                        digestData={digestToRender}
                        isReadOnly={true} // Disable Interactions in Feed Mode
                        initialTab="digest"
                        setDigestSummary={(summary) => {
                            setLocalDigest((prev: any) => ({
                                ...prev,
                                digest: summary,
                                summary_markdown: summary
                            }));
                        }}
                        onShare={() => {
                            if (digestToRender.public_slug) {
                                const link = `${window.location.origin}/s/${digestToRender.public_slug}`;
                                navigator.clipboard.writeText(link);
                                alert("Link copied to clipboard!");
                            }
                        }}
                    />
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto py-16 px-4 sm:px-6 lg:px-8 flex flex-col min-h-full">
            {/* Feed Header */}
            <div className="flex items-center gap-4 mb-8">
                <div className="h-1 w-12 bg-fuchsia-500 rounded-full shadow-[0_0_10px_#d946ef]"></div>
                <h2 className="text-3xl font-bold text-white tracking-tight">Today's Urban Pulse</h2>
                <span className="text-neutral-500 text-sm font-mono ml-auto">LIVE FEED / REAL MODE</span>
            </div>

            {/* Content Area */}
            {isLoading ? (
                <div className="flex-grow flex items-center justify-center min-h-[400px]">
                    <Loader2 className="w-8 h-8 text-fuchsia-500 animate-spin" />
                </div>
            ) : (
                <>
                    {/* Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 flex-grow mb-12">
                        {feedItems.length > 0 ? (
                            feedItems.map((item) => (
                                <NewsCard key={item.id} item={item} onClick={() => handleCardClick(item.slug)} />
                            ))
                        ) : (
                            <div className="col-span-full text-center py-20 text-neutral-500">
                                No public digests found.
                            </div>
                        )}
                    </div>

                    {/* Pagination */}
                    <div className="flex justify-center items-center gap-4 pb-8">
                        <button
                            onClick={() => setPage(p => Math.max(0, p - 1))}
                            disabled={page === 0}
                            className="bg-neutral-900 border border-neutral-800 text-white p-3 rounded-full hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                            <ChevronLeft className="w-5 h-5" />
                        </button>
                        <span className="text-neutral-500 font-mono text-sm">Page {page + 1}</span>
                        <button
                            onClick={() => setPage(p => p + 1)}
                            disabled={feedItems.length < ITEMS_PER_PAGE} // Simple logic, assumes if < limit then last page
                            className="bg-neutral-900 border border-neutral-800 text-white p-3 rounded-full hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </div>
                </>
            )}

            {/* FOOTER 1: The "Top" Footer */}
            <Footer
                onAboutClick={() => setShowAbout(!showAbout)}
                isAboutActive={showAbout}
            />

            {/* EXPANDING ABOUT SECTION */}
            <div className={`overflow-hidden transition-all duration-700 ease-in-out ${showAbout ? 'max-h-[1600px] opacity-100' : 'max-h-0 opacity-0'}`}>
                <div className="py-16 border-y border-neutral-800/50 bg-neutral-900/30">
                    <div className="max-w-6xl mx-auto px-6 space-y-24">

                        {/* SECTION 1: HERO / INTRO */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                            <div className="space-y-6">
                                <h3 className="text-3xl font-black text-white tracking-tight">Understanding Urbanous</h3>
                                <p className="text-neutral-300 text-lg leading-relaxed">
                                    This is an app specifically created to allow you to seamlessly navigate global news in an effortless fashion.
                                </p>
                                <p className="text-neutral-400 text-lg leading-relaxed">
                                    Rather than relying on what others say about events in foreign places, you can now read local sources from places of interest without having to know their language or news outlet sites. Get a direct overview of what the locals say is happening in their localities.
                                </p>
                            </div>
                            {/* Hero Image */}
                            <div className="relative group rounded-2xl overflow-hidden border border-neutral-800 shadow-2xl shadow-black/50">
                                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent z-10" />
                                <img
                                    src="/about/hero.png"
                                    alt="Urbanous Globe Interface"
                                    className="w-full h-auto transform transition-transform duration-700 group-hover:scale-105"
                                />
                            </div>
                        </div>

                        {/* SECTION 2: MAP LEGEND */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                            {/* Legend Image */}
                            <div className="order-2 lg:order-1 relative rounded-2xl overflow-hidden border border-neutral-800 bg-neutral-900/50 shadow-2xl shadow-black/50">
                                <img
                                    src="/about/clusters-legend.png?v=129"
                                    alt="Map Clusters and Icons"
                                    className="w-full h-auto"
                                />
                            </div>

                            <div className="order-1 lg:order-2 space-y-6">
                                <h3 className="text-2xl font-bold text-white">Navigating the Map</h3>
                                <p className="text-neutral-400 leading-relaxed text-sm">
                                    The globe is populated with all cities across the world with a population of at least 100k inhabitants. The city icons come in three flavors:
                                </p>
                                <ul className="space-y-3 mt-4 text-sm text-neutral-300">
                                    <li className="flex items-center gap-3">
                                        <div className="shrink-0 w-8 h-8 rounded-full bg-[#3b82f6] border-2 border-white flex items-center justify-center text-white font-bold font-mono text-sm shadow-lg shadow-blue-900/50">S</div>
                                        <span>represents a <strong className="text-white">City</strong>.</span>
                                    </li>
                                    <li className="flex items-center gap-3">
                                        <div className="shrink-0 w-8 h-8 rounded-full bg-[#06b6d4] border-2 border-white flex items-center justify-center text-white font-bold font-mono text-sm shadow-lg shadow-cyan-900/50">T</div>
                                        <span>
                                            In order to keep the map clutter free, a clustering mechanism has been implemented.
                                            <strong className="text-white ml-1">City Clusters</strong> represent nearby cities.
                                        </span>
                                    </li>
                                    <li className="flex items-center gap-3">
                                        <div className="shrink-0 w-8 h-8 rounded-full bg-[#e11d48] border-2 border-white flex items-center justify-center text-white font-bold font-mono text-sm shadow-lg shadow-rose-900/50">B</div>
                                        <span>represent <strong className="text-white">Capitals</strong>.</span>
                                    </li>
                                </ul>
                            </div>
                        </div>

                    </div>
                </div>

                {/* FOOTER 2: The "Cloned" Footer - Now runs away with the content */}
                <Footer
                    onAboutClick={() => setShowAbout(false)}
                    isAboutActive={showAbout}
                />
            </div>
        </div>
    );
}

// Sub-Component for individual cards
function NewsCard({ item, onClick }: { item: DigestFeedItem, onClick: () => void }) {
    // Determine Image: flag_url OR city map OR default
    let imageUrl = item.image_url // Coat of Arms
        || CITY_IMAGES[item.city || ""]
        || DEFAULT_IMAGE;

    // Fix relative paths from backend (e.g. /static/...)
    // Fix relative paths from backend (e.g. /static/...)
    if (imageUrl && imageUrl.startsWith('/') && !imageUrl.startsWith('http')) {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        // Remove trailing slash from API URL if present to avoid double slash
        const cleanApiUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
        imageUrl = `${cleanApiUrl}${imageUrl}`;
    }

    console.log(`[DEBUG] Image for ${item.slug}:`, { original: item.image_url, final: imageUrl, apiUrl: process.env.NEXT_PUBLIC_API_URL });

    // Determine Source Text (user name? or generic?)
    // User requested "freshest first".
    const dateStr = new Date(item.created_at).toLocaleDateString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });

    return (
        <div
            onClick={onClick}
            className={`group relative bg-neutral-900/50 border border-neutral-800 rounded-xl overflow-hidden hover:border-neutral-600 transition-all duration-500 hover:shadow-2xl hover:shadow-fuchsia-900/20 flex flex-col cursor-pointer active:scale-95`}
        >

            {/* Label Badge */}
            <div className="absolute top-4 left-4 z-10">
                <span className="px-2 py-1 text-xs font-bold uppercase tracking-wider text-black bg-white/90 backdrop-blur rounded-sm">
                    {item.category}
                </span>
            </div>

            <div className="h-48 overflow-hidden relative">
                {/* Image Hover Zoom Effect */}
                <div
                    className="absolute inset-0 bg-cover bg-center group-hover:scale-105 transition-transform duration-700 ease-out"
                    style={{ backgroundImage: `url(${imageUrl})` }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-neutral-900 via-transparent to-transparent opacity-80" />
            </div>

            <div className="p-6 flex flex-col flex-grow">
                <div className="flex items-center gap-2 text-xs text-fuchsia-400 mb-2 font-mono uppercase tracking-widest">
                    <span>{item.city || 'Global'}</span>
                    <span className="w-1 h-1 bg-neutral-600 rounded-full" />
                    <span className="text-neutral-500">{formatDateRange(item.created_at, item.timeframe)}</span>
                </div>

                <h3 className="text-xl font-bold text-white mb-3 leading-tight group-hover:text-fuchsia-300 transition-colors line-clamp-2">
                    {item.title}
                </h3>

                <p className="text-neutral-400 text-sm leading-relaxed mb-6 line-clamp-3">
                    {item.summary
                        ? item.summary.replace(/[#*`\[\]]/g, '').replace(/\(citation:\d+\)/g, '').split(' ').slice(0, 30).join(' ') + '...'
                        : "Reading report summary..."}
                </p>

                <div className="mt-auto flex items-center justify-between border-t border-neutral-800 pt-4">
                    <span className="text-xs text-neutral-600">{dateStr}</span>
                    <button className="text-xs font-bold text-white group-hover:underline decoration-fuchsia-500 underline-offset-4">
                        READ DIGEST →
                    </button>
                </div>
            </div>
        </div>
    );
}
