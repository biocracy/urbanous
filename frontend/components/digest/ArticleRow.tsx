'use client';

import React, { useState } from 'react';
import { CheckCircle2, Wrench, Play, Loader2 } from 'lucide-react';
import { Article } from './types';

interface ArticleRowProps {
    article: Article;
    isTranslated: boolean;
    isSelected: boolean;
    onToggle: (url: string) => void;
    onAssess?: (article: Article) => Promise<any> | any;
    onDebug?: (article: Article) => void;
}

export function ArticleRow({ article, isTranslated, isSelected, onToggle, onAssess, onDebug }: ArticleRowProps) {
    const s = article.scores || { topic: 0, date: 0, is_fresh: false };
    const [isAssessing, setIsAssessing] = useState(false);
    const [assessmentResult, setAssessmentResult] = useState<any>(null);

    // Date Styling
    const isFresh = s.is_fresh || (article.relevance_score > 0 && s.date > 0);
    const dateColor = isFresh ? "text-green-400" : "text-red-400";

    // AI Check Logic
    const isAiTitlePass = article.ai_verdict === "VERIFIED";
    const aiTitleIcon = isAiTitlePass ? "✅" : "❌";

    // Title Logic
    const displayTitle = (isTranslated && article.translated_title)
        ? article.translated_title
        : article.title;

    const handleAssess = async () => {
        if (!onAssess) return;
        setIsAssessing(true);
        try {
            const result = await onAssess(article);
            if (result) setAssessmentResult(result);
        } catch (e) {
            console.error(e);
        } finally {
            setIsAssessing(false);
        }
    };

    return (
        <tr className={`hover:bg-slate-800/30 transition-colors group ${isSelected ? "bg-blue-900/10" : ""}`}>
            {/* 1. DATE */}
            <td className="px-4 py-3 text-center whitespace-nowrap">
                <div className={`flex items-center justify-center gap-2 font-medium ${dateColor}`}>
                    {article.date_str || "N/A"}
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (onDebug) onDebug(article);
                        }}
                        title={`Configure Extraction for ${article.source}`}
                        className="opacity-0 group-hover:opacity-50 hover:opacity-100 cursor-pointer text-slate-400 focus:outline-none"
                    >
                        <Wrench size={12} />
                    </button>
                </div>
            </td>

            {/* 2. TITLE */}
            <td className="px-4 py-3">
                <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block font-medium text-blue-400 hover:text-blue-300 transition-colors hover:underline decoration-blue-500/30 underline-offset-4"
                >
                    {displayTitle}
                </a>
                {(isTranslated && !article.translated_title) && (
                    <div className="mt-1 text-slate-500 text-xs italic">
                        (Translation unavailable)
                    </div>
                )}
            </td>

            {/* 3. AI TITLE CHECK */}
            <td className="px-4 py-3 text-center text-lg">
                <span title={`Status: ${article.ai_verdict || 'None'} (Hover to debug)`}>
                    {aiTitleIcon}
                </span>
            </td>

            {/* 4. AI CONTENT CHECK */}
            <td className="px-4 py-3 text-center">
                {assessmentResult ? (
                    <div
                        className={`relative group cursor-help flex justify-center font-bold ${assessmentResult.is_politics ? 'text-green-400' : 'text-red-400'}`}
                        title={`${assessmentResult.reasoning}`}
                    >
                        <span className="text-sm">
                            {assessmentResult.confidence}%
                        </span>
                    </div>
                ) : (
                    <button
                        onClick={handleAssess}
                        disabled={isAssessing}
                        className="p-1.5 rounded-full hover:bg-slate-700 text-slate-500 hover:text-blue-400 transition-colors disabled:opacity-50"
                        title="Assess Content with AI"
                    >
                        {isAssessing ? <Loader2 size={14} className="animate-spin text-blue-400" /> : <Play size={14} />}
                    </button>
                )}
            </td>

            {/* 5. SELECT CHECKBOX */}
            <td className="px-4 py-3 text-center">
                <button
                    onClick={() => onToggle(article.url)}
                    className={`w-5 h-5 mx-auto border rounded flex items-center justify-center transition-colors ${isSelected ? "bg-blue-600 border-blue-600 text-white" : "border-slate-600 text-transparent hover:border-slate-400"}`}
                >
                    <CheckCircle2 size={14} />
                </button>
            </td>
        </tr>
    );
}
