import React, { useState } from 'react';
import { MOCK_NEWS, NewsItem } from '../data/mock-news';
import Footer from './Footer';

export default function FeedLayout() {
    const [showAbout, setShowAbout] = useState(false);

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
            <div className={`overflow-hidden transition-all duration-700 ease-in-out ${showAbout ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'}`}>
                <div className="py-12 border-y border-neutral-800/50 bg-neutral-900/30">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
                        <div className="space-y-6">
                            <h3 className="text-2xl font-bold text-white">Understanding Urbanous</h3>
                            <p className="text-neutral-400 leading-relaxed">
                                Urbanous connects global city data with local news narratives.
                                Our 3D Globe visualizes real-world clusters of activity, allowing you to
                                navigate the planet by "Heat" rather than borders.
                            </p>
                            <ul className="space-y-4 text-sm text-neutral-300">
                                <li className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-slate-800 flex items-center justify-center text-blue-400 font-mono font-bold">1</div>
                                    <span><strong>Scroll</strong> to explore the News Feed.</span>
                                </li>
                                <li className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-slate-800 flex items-center justify-center text-fuchsia-400 font-mono font-bold">2</div>
                                    <span><strong>Cmd + Scroll</strong> (or Ctrl) to Zoom/Pan the map.</span>
                                </li>
                                <li className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded bg-slate-800 flex items-center justify-center text-green-400 font-mono font-bold">3</div>
                                    <span><strong>Click Clusters</strong> to read aggregated digests.</span>
                                </li>
                            </ul>
                        </div>
                        {/* Visual Placeholder for Guide Image */}
                        <div className="aspect-video bg-neutral-800 rounded-xl border border-neutral-700 flex items-center justify-center relative overflow-hidden group">
                            <div className="absolute inset-0 bg-gradient-to-tr from-fuchsia-500/10 to-blue-500/10" />
                            <span className="text-neutral-500 font-mono text-xs z-10">[ INTERFACE DIAGRAM PLACEHOLDER ]</span>
                            {/* Simulated Interface Elements */}
                            <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 border border-dashed border-neutral-600 rounded opacity-50" />
                            <div className="absolute bottom-4 right-4 w-8 h-8 rounded-full bg-fuchsia-500/20 animate-pulse" />
                        </div>
                    </div>
                </div>

                {/* FOOTER 2: The "Cloned" Footer */}
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
