'use client';
import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import dynamic from 'next/dynamic';

// Dynamic import for Globe (SSR issue prevention)
const NewsGlobe = dynamic(() => import('@/components/NewsGlobe'), {
    ssr: false,
    loading: () => <div className="h-screen w-full flex items-center justify-center bg-black text-white">Loading Globe...</div>
});

import { Settings } from 'lucide-react';
import SettingsModal from '@/components/SettingsModal';
import FeedLayout from '@/components/FeedLayout'; // NEW MOCK FEED

function HomeContent() {
    const { isAuthenticated, logout } = useAuthStore();
    const router = useRouter();
    const searchParams = useSearchParams();

    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    // SCROLL STATE: Track if we are at the top (Hero View)
    const [activeDigest, setActiveDigest] = useState<any>(null);
    const [isAtTop, setIsAtTop] = useState(true);
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        setIsMobile(/iPhone|iPad|iPod|Android/i.test(navigator.userAgent));
    }, []);

    // Handle URL Params for Digest View
    useEffect(() => {
        const viewDigestSlug = searchParams.get('view_digest');
        if (viewDigestSlug) {
            // Fetch the digest
            const fetchDigest = async () => {
                try {
                    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                    const res = await fetch(`${baseUrl}/digests/public/${viewDigestSlug}`);
                    if (res.ok) {
                        const data = await res.json();
                        setActiveDigest(data);

                        // Auto-scroll to feed section
                        setTimeout(() => {
                            const feedSection = document.getElementById('feed-section');
                            if (feedSection) {
                                feedSection.scrollIntoView({ behavior: 'smooth' });
                            }
                        }, 500);
                    }
                } catch (err) {
                    console.error("Failed to load digest from params", err);
                }
            };
            fetchDigest();
        } else {
            setActiveDigest(null);
        }
    }, [searchParams]);

    // Handle Main Container Scroll
    const handleScroll = (e: React.UIEvent<HTMLElement>) => {
        const scrollTop = e.currentTarget.scrollTop;
        // We are "At Top" if within the top 20px threshold
        const atTop = scrollTop < 20;
        if (atTop !== isAtTop) {
            setIsAtTop(atTop);
        }
    };

    const closeDigestView = () => {
        setActiveDigest(null);
        router.push('/', { scroll: false });
    };

    return (
        <main
            onScroll={handleScroll}
            className="relative h-screen w-full bg-black overflow-y-scroll overflow-x-hidden scroll-smooth"
        >
            {/* Header Overlay - Fixed to Viewport (viewport-relative) */}
            <div className="fixed top-0 left-0 w-full z-10 p-4 flex justify-between items-center pointer-events-none">
                <h1 className="text-2xl font-black tracking-tighter pointer-events-auto shadow-sm flex items-center cursor-default select-none">
                    {/* Logo with Gradient Mask */}
                    <div
                        className="h-8 w-6 -mt-1 bg-gradient-to-r from-fuchsia-400 to-indigo-400"
                        style={{
                            maskImage: 'url(/logo-mask-v5.png)',
                            maskSize: 'contain',
                            maskRepeat: 'no-repeat',
                            maskPosition: 'center',
                            WebkitMaskImage: 'url(/logo-mask-v5.png)',
                            WebkitMaskSize: 'contain',
                            WebkitMaskRepeat: 'no-repeat',
                            WebkitMaskPosition: 'center'
                        }}
                    />
                    <span className="bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-400 to-indigo-400">
                        RBANOUS.NET
                    </span>
                </h1>

                <div className="pointer-events-auto flex items-center gap-2">
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        className="p-2 bg-slate-800/80 hover:bg-slate-700 text-white rounded-full backdrop-blur-md transition-all shadow-lg border border-slate-700"
                        title="Settings"
                    >
                        <Settings className="w-5 h-5" />
                    </button>
                </div>
            </div>

            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

            {/* SECTION 1: HERO GLOBE (100vh) */}
            <div className="h-screen w-full relative z-0 shrink-0">
                <NewsGlobe disableScrollZoom={true} isAtTop={isAtTop} />

                {/* Scroll Hint */}
                <div className={`absolute bottom-8 left-1/2 -translate-x-1/2 text-white/50 text-sm animate-bounce pointer-events-none transition-opacity duration-300 ${isAtTop ? 'opacity-100' : 'opacity-0'}`}>
                    {isMobile ? "Two Fingers to Scroll ▼" : "Cmd + Scroll for News ▼"}
                </div>
            </div>

            {/* SNAP SPACER: Invisible anchor to snap top of viewport to 66vh */}
            {/* This makes the Globe 33% visible at the top */}
            <div className="absolute top-[60vh] w-full h-[1px] pointer-events-none" />

            {/* SECTION 2: CONTENT BELOW FOLD */}
            <div
                id="feed-section"
                className="min-h-screen w-full bg-neutral-950 border-t border-neutral-800 relative z-20 shadow-[0_-20px_40px_rgba(0,0,0,0.8)]"
            >
                <FeedLayout
                    activeDigest={activeDigest}
                    onCloseDigest={closeDigestView}
                />
            </div>
        </main>
    );
}

export default function HomeClient() {
    return (
        <Suspense fallback={<div className="h-screen w-full flex items-center justify-center bg-black text-white">Loading...</div>}>
            <HomeContent />
        </Suspense>
    );
}
