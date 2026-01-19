import React, { useState } from 'react';
import { MOCK_NEWS, NewsItem } from '../data/mock-news';
import Footer from './Footer';
import UnifiedDigestViewer from './UnifiedDigestViewer';
import { ArrowLeft } from 'lucide-react';

interface FeedLayoutProps {
    activeDigest?: any;
    onCloseDigest?: () => void;
}

export default function FeedLayout({ activeDigest, onCloseDigest }: FeedLayoutProps) {
    const [showAbout, setShowAbout] = useState(false);

    // If Viewing a Digest, override the main content
    if (activeDigest) {
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
                        digestData={activeDigest}
                        isReadOnly={true}
                        onShare={() => {
                            if (activeDigest.public_slug) {
                                const link = `${window.location.origin}/s/${activeDigest.public_slug}`;
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
                <span className="text-neutral-500 text-sm font-mono ml-auto">LIVE FEED / MOCK MODE</span>
            </div>

            {/* Masonry-ish Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 flex-grow">
                {MOCK_NEWS.map((item) => (
                    <NewsCard key={item.id} item={item} />
                ))}
            </div>

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
function NewsCard({ item }: { item: NewsItem }) {
    return (
        <div className={`group relative bg-neutral-900/50 border border-neutral-800 rounded-xl overflow-hidden hover:border-neutral-600 transition-all duration-300 hover:shadow-2xl hover:shadow-fuchsia-900/10 flex flex-col ${!item.imageUrl ? 'bg-gradient-to-br from-neutral-900 to-neutral-800' : ''}`}>

            {/* Label Badge */}
            <div className="absolute top-4 left-4 z-10">
                <span className="px-2 py-1 text-xs font-bold uppercase tracking-wider text-black bg-white/90 backdrop-blur rounded-sm">
                    {item.category}
                </span>
            </div>

            {item.imageUrl ? (
                <div className="h-48 overflow-hidden relative">
                    {/* Image Hover Zoom Effect */}
                    <div
                        className="absolute inset-0 bg-cover bg-center group-hover:scale-105 transition-transform duration-700 ease-out"
                        style={{ backgroundImage: `url(${item.imageUrl})` }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-neutral-900 via-transparent to-transparent opacity-80" />
                </div>
            ) : (
                // Text-Only Card Spacer
                <div className="h-6 w-full" />
            )}

            <div className="p-6 flex flex-col flex-grow">
                <div className="flex items-center gap-2 text-xs text-fuchsia-400 mb-2 font-mono uppercase tracking-widest">
                    <span>{item.location}</span>
                    <span className="w-1 h-1 bg-neutral-600 rounded-full" />
                    <span className="text-neutral-500">{item.source}</span>
                </div>

                <h3 className="text-xl font-bold text-white mb-3 leading-tight group-hover:text-fuchsia-300 transition-colors">
                    {item.title}
                </h3>

                <p className="text-neutral-400 text-sm leading-relaxed mb-6 line-clamp-3">
                    {item.summary}
                </p>

                <div className="mt-auto flex items-center justify-between border-t border-neutral-800 pt-4">
                    <span className="text-xs text-neutral-600">{item.date}</span>
                    <button className="text-xs font-bold text-white group-hover:underline decoration-fuchsia-500 underline-offset-4">
                        READ MORE →
                    </button>
                </div>
            </div>
        </div>
    );
}
