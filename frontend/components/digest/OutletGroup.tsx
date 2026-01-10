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
    onAssess?: (article: Article) => void;
    onDebug?: (article: Article) => void;
}

export function OutletGroup({ group, isTranslated, onAssess, onDebug }: OutletGroupProps) {
    const [isOpen, setIsOpen] = useState(true);

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
                                <ArticleRow key={idx} article={art} isTranslated={isTranslated} onAssess={onAssess} onDebug={onDebug} />
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
