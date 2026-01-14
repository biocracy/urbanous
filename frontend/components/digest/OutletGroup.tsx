'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Article } from './types';
import { ArticleRow } from './ArticleRow';

interface OutletGroupProps {
    group: {
        source: string;
        articles: Article[];
    };
    isTranslated: boolean;
    selectedUrls: Set<string>;
    onToggle: (url: string) => void;
    onAssess?: (article: Article) => void;
    onDebug?: (article: Article) => void;
    onReportSpam?: (article: Article) => void;
    excludedArticles?: Article[];
    spamArticles?: Article[];
}

export function OutletGroup({ group, isTranslated, selectedUrls, onToggle, onAssess, onDebug, onReportSpam, excludedArticles = [], spamArticles = [] }: OutletGroupProps) {
    const [isOpen, setIsOpen] = useState(true);
    const [isExcludedOpen, setIsExcludedOpen] = useState(false);
    const [isSpamOpen, setIsSpamOpen] = useState(false);

    return (
        <div className="animate-in fade-in duration-500 slide-in-from-bottom-2">
            {/* Collapsible Header */}
            <div
                onClick={() => setIsOpen(!isOpen)}
                className="border-b border-slate-700 pb-2 mb-4 cursor-pointer hover:bg-slate-800/30 p-2 rounded transition-colors flex items-center justify-between group"
            >
                <h3 className="text-xl font-bold text-slate-200 flex items-center gap-2">
                    {group.source}
                    <span className="text-sm font-normal text-slate-500">
                        ({group.articles.length} articles)
                    </span>
                </h3>
                <div className="text-slate-500 group-hover:text-slate-300">
                    {isOpen ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                </div>
            </div>

            {/* Articles Table */}
            {isOpen && (
                <div className="overflow-hidden bg-slate-900/30 rounded-lg border border-slate-700/50">
                    <table className="w-full text-left text-sm text-slate-400">
                        <thead className="bg-slate-800/50 text-slate-200 uppercase tracking-wider text-xs font-semibold">
                            <tr>
                                <th className="px-4 py-3 w-32 text-center">Date</th>
                                <th className="px-4 py-3">Title</th>
                                <th className="px-4 py-3 w-24 text-center">AI Title</th>
                                <th className="px-4 py-3 w-24 text-center">AI Content</th>
                                <th className="px-4 py-3 w-16 text-center">Select</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {group.articles.map((art, idx) => (
                                <ArticleRow
                                    key={'active-' + art.url}
                                    article={art}
                                    isTranslated={isTranslated}
                                    isSelected={selectedUrls.has(art.url)}
                                    onToggle={onToggle}
                                    onAssess={onAssess}
                                    onDebug={onDebug}
                                    onReportSpam={onReportSpam}
                                />
                            ))}

                            {/* Excluded Section */}
                            {excludedArticles.length > 0 && (
                                <>
                                    <tr className="bg-slate-800/20 border-t border-slate-700/50">
                                        <td colSpan={5} className="p-0">
                                            <button
                                                onClick={() => setIsExcludedOpen(!isExcludedOpen)}
                                                className="w-full py-2 text-xs font-bold text-slate-500 hover:text-blue-400 hover:bg-slate-800/50 uppercase tracking-wider flex items-center justify-center gap-2 transition-colors"
                                            >
                                                {isExcludedOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                                {isExcludedOpen ? 'Hide' : 'Expand'} {excludedArticles.length} Skipped Articles
                                            </button>
                                        </td>
                                    </tr>
                                    {isExcludedOpen && excludedArticles.map((art, idx) => (
                                        <ArticleRow
                                            key={'excluded-' + art.url}
                                            article={art}
                                            isTranslated={isTranslated}
                                            isSelected={selectedUrls.has(art.url)}
                                            onToggle={onToggle}
                                            onAssess={onAssess}
                                            onDebug={onDebug}
                                            onReportSpam={onReportSpam}
                                        />
                                    ))}
                                </>
                            )}
                        </tbody>
                        {/* Junk/Spam Section */}
                        {spamArticles.length > 0 && (
                            <tbody className="divide-y divide-red-900/30 border-t border-slate-700/50">
                                <tr className="bg-red-950/20">
                                    <td colSpan={5} className="p-0">
                                        <button
                                            onClick={() => setIsSpamOpen(!isSpamOpen)}
                                            className="w-full py-2 text-xs font-bold text-red-400 hover:text-red-300 hover:bg-red-900/20 uppercase tracking-wider flex items-center justify-center gap-2 transition-colors"
                                        >
                                            {isSpamOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                            {isSpamOpen ? 'Hide' : 'Show'} {spamArticles.length} Flagged as Spam
                                        </button>
                                    </td>
                                </tr>
                                {isSpamOpen && spamArticles.map((art, idx) => (
                                    <ArticleRow
                                        key={'spam-' + art.url}
                                        article={art}
                                        isTranslated={isTranslated}
                                        isSelected={false}
                                        onToggle={() => { }} // Disabled for spam
                                        onAssess={onAssess}
                                        onDebug={onDebug}
                                        onReportSpam={onReportSpam}
                                        isSpam={true}
                                    />
                                ))}
                            </tbody>
                        )}
                    </table>
                </div>
            )}
        </div>
    );
}
