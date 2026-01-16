'use client';

import React, { useState, useMemo } from 'react';
import { Article, DigestReportRendererProps } from './digest/types';
import { OutletGroup } from './digest/OutletGroup';

export default function DigestReportRenderer({ articles, category, isTranslated = false, selectedUrls, onToggle, onAssess, onDebug, onReportSpam, spamUrls, excludedArticles }: DigestReportRendererProps) {
    const [displayCount, setDisplayCount] = useState(20);

    // Group Articles by Outlet
    const groupedArticles = useMemo(() => {
        const groups: { [key: string]: { active: Article[], excluded: Article[], spam: Article[] } } = {};

        const processArticle = (art: Article, isExcludeList = false) => {
            if (!groups[art.source]) groups[art.source] = { active: [], excluded: [], spam: [] };

            if (selectedUrls && spamUrls && spamUrls.has(art.url)) {
                groups[art.source].spam.push(art);
            } else if (art.is_spam) {
                groups[art.source].spam.push(art);
            } else if (isExcludeList) {
                groups[art.source].excluded.push(art);
            } else {
                groups[art.source].active.push(art);
            }
        };

        articles.forEach(art => processArticle(art, false));

        if (excludedArticles) {
            excludedArticles.forEach(art => processArticle(art, true));
        }

        // Convert to array and sort outlets by highest score (max relevance in group)
        return Object.entries(groups)
            .map(([source, data]) => {
                const sortFn = (a: Article, b: Article) => {
                    const d1 = a.date_str || "1970-01-01";
                    const d2 = b.date_str || "1970-01-01";
                    if (d1 !== d2) return d2.localeCompare(d1); // Newest date first
                    return b.relevance_score - a.relevance_score; // Tiebreaker
                };

                const activeSorted = data.active.sort(sortFn);
                const excludedSorted = data.excluded.sort(sortFn);

                // Calculate max score for sorting the OUTLET order
                // We consider both active and excluded, so the outlet stays relevant even if items are unchecked.
                const maxActive = activeSorted.length > 0 ? Math.max(...activeSorted.map(a => a.relevance_score)) : 0;
                const maxExcluded = excludedSorted.length > 0 ? Math.max(...excludedSorted.map(a => a.relevance_score)) : 0;

                return {
                    source,
                    articles: activeSorted,
                    excludedArticles: excludedSorted,
                    spamArticles: data.spam.sort(sortFn),
                    maxScore: Math.max(maxActive, maxExcluded)
                };
            })
            .sort((a, b) => b.maxScore - a.maxScore);
    }, [articles, excludedArticles, spamUrls, selectedUrls]);

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
                    onReportSpam={onReportSpam}
                    excludedArticles={group.excludedArticles}
                    spamArticles={group.spamArticles}
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
