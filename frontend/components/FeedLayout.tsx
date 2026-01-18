import React from 'react';
import { MOCK_NEWS, NewsItem } from '../data/mock-news';

export default function FeedLayout() {
    return (
        <div className="max-w-7xl mx-auto py-16 px-4 sm:px-6 lg:px-8">
            {/* Feed Header */}
            <div className="flex items-center gap-4 mb-8">
                <div className="h-1 w-12 bg-fuchsia-500 rounded-full shadow-[0_0_10px_#d946ef]"></div>
                <h2 className="text-3xl font-bold text-white tracking-tight">Today's Urban Pulse</h2>
                <span className="text-neutral-500 text-sm font-mono ml-auto">LIVE FEED / MOCK MODE</span>
            </div>

            {/* Masonry-ish Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {MOCK_NEWS.map((item) => (
                    <NewsCard key={item.id} item={item} />
                ))}
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
