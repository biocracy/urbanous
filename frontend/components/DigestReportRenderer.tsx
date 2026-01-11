'use client';

import React, { useState, useMemo } from 'react';
import { Article, DigestReportRendererProps } from './digest/types';
import { OutletGroup } from './digest/OutletGroup';

export default function DigestReportRenderer({ articles, category, isTranslated = false, selectedUrls, onToggle, onAssess, onDebug }: DigestReportRendererProps) {
    const [displayCount, setDisplayCount] = useState(20);

    // Group Articles by Outlet
    const groupedArticles = useMemo(() => {
        const groups: { [key: string]: Article[] } = {};
        articles.forEach(art => {
            if (!groups[art.source]) groups[art.source] = [];
            groups[art.source].push(art);
        });

        // Convert to array and sort outlets by highest score (max relevance in group)
        return Object.entries(groups)
            .map(([source, arts]) => ({
                source,
                articles: arts.sort((a, b) => {
                    const d1 = a.date_str || "1970-01-01";
                    const d2 = b.date_str || "1970-01-01";
                    if (d1 !== d2) return d2.localeCompare(d1); // Newest date first
                    return b.relevance_score - a.relevance_score; // Tiebreaker
                }),
                maxScore: Math.max(...arts.map(a => a.relevance_score))
            }))
            .sort((a, b) => b.maxScore - a.maxScore);
    }, [articles]);

    const visibleGroups = groupedArticles.slice(0, displayCount);

    const handleLoadMore = () => {
        setDisplayCount(prev => prev + 10);
    };

    return (
        <div className="flex flex-col gap-8 pb-20">
            {visibleGroups.map(group => (
                <OutletGroup
                    key={group.source}
                    group={group}
                    isTranslated={isTranslated}
                    selectedUrls={selectedUrls}
                    onToggle={onToggle}
                    onAssess={onAssess}
                    onDebug={onDebug}
                />
            ))}

            {visibleGroups.length < groupedArticles.length && (
                <button
                    onClick={handleLoadMore}
                    className="mx-auto mt-8 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-full font-bold transition-all hover:scale-105 active:scale-95 shadow-lg shadow-blue-900/20"
                >
                    Load More Outlets ({groupedArticles.length - visibleGroups.length} remaining)
                </button>
            )}

            {visibleGroups.length === 0 && (
                <div className="text-center py-20 text-slate-500 italic">
                    No articles found for this category.
                </div>
            )}
        </div>
    );
}
