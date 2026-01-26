'use client';

import React, { useState } from 'react';
import { CheckCircle2, Wrench, Play, Loader2, Flag, Undo2 } from 'lucide-react';
import { Article } from './types';

interface ArticleRowProps {
    article: Article;
    isTranslated: boolean;
    isSelected: boolean;
    onToggle: (url: string) => void;
    onAssess?: (article: Article) => Promise<any> | any;
    onDebug?: (article: Article, type?: 'date' | 'title') => void;
    onReportSpam?: (article: Article) => void;
    isSpam?: boolean;
    showAdminControls?: boolean; // New prop to control visibility explicitly, or derive from onAssess
}

export function ArticleRowComponent({ article, isTranslated, isSelected, onToggle, onAssess, onDebug, onReportSpam, isSpam = false, showAdminControls }: ArticleRowProps) {
    // Derive admin visibility if not passed explicitly (fallback to existence of onAssess)
    const isAdmin = showAdminControls ?? !!onAssess;
    const s = article.scores || { topic: 0, date: 0, is_fresh: false };
    const [isAssessing, setIsAssessing] = useState(false);
    const [isReporting, setIsReporting] = useState(false);
    const [isReported, setIsReported] = useState(false);
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

    const handleReport = async () => {
        if (!onReportSpam) return;

        // Parent handles confirmation (Modal vs Direct)
        // We cast to any to check if a Promise is returned, supporting both sync (modal) and async (direct) flows
        const res = onReportSpam(article) as any;

        // Check if Promise-like
        if (res && typeof res.then === 'function') {
            setIsReporting(true);
            try {
                await res;
                setIsReported(true);
            } catch (e) { console.error(e); }
            finally { setIsReporting(false); }
        }
    };

    const rowClass = isSpam
        ? "opacity-50 grayscale hover:grayscale-0 transition-all bg-red-900/10 hover:bg-red-900/20"
        : `hover:bg-slate-800/30 transition-colors group ${isSelected ? "bg-blue-900/10" : ""}`;

    return (
        <tr className={rowClass}>
            {/* 1. DATE */}
            <td className="px-4 py-3 text-center whitespace-nowrap">
                <div className={`flex items-center justify-center gap-2 font-medium ${dateColor}`}>
                    {article.date_str || "N/A"}
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            e.stopPropagation();
                            if (onDebug) onDebug(article, 'date');
                        }}
                        title={`Configure Date Extraction for ${article.source}`}
                        className="opacity-0 group-hover:opacity-50 hover:opacity-100 cursor-pointer text-slate-400 focus:outline-none"
                    >
                        <Wrench size={12} />
                    </button>
                </div>
            </td>

            {/* 2. TITLE */}
            <td className="px-4 py-3">
                <div className="flex items-start gap-2 justify-between">
                    <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-blue-400 hover:text-blue-300 transition-colors hover:underline decoration-blue-500/30 underline-offset-4"
                    >
                        {displayTitle}
                    </a>
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (onDebug) onDebug(article, 'title');
                        }}
                        title={`Configure Title Extraction for ${article.source}`}
                        className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer text-slate-400 hover:text-blue-400 focus:outline-none mt-1"
                    >
                        <Wrench size={14} />
                    </button>
                </div>

                {(isTranslated && !article.translated_title) && (
                    <div className="mt-1 text-slate-500 text-xs italic">
                        (Translation unavailable)
                    </div>
                )}
            </td>

            {/* 3. AI TITLE CHECK - Only if Admin */}
            {isAdmin && (
                <td className="px-4 py-3 text-center text-lg">
                    <span title={`Status: ${article.ai_verdict || 'None'} (Hover to debug)`}>
                        {aiTitleIcon}
                    </span>
                </td>
            )}

            {/* 4. AI CONTENT CHECK - Only if Admin */}
            {isAdmin && (
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
                        <div className="flex gap-1 justify-center">
                            <button
                                onClick={handleAssess}
                                disabled={isAssessing}
                                className="p-1.5 rounded-full hover:bg-slate-700 text-slate-500 hover:text-blue-400 transition-colors disabled:opacity-50"
                                title="Assess Content with AI"
                            >
                                {isAssessing ? <Loader2 size={14} className="animate-spin text-blue-400" /> : <Play size={14} />}
                            </button>
                            <button
                                onClick={handleReport}
                                disabled={isReporting || (isReported && !isSpam)}
                                className={`p-1.5 rounded-full hover:bg-slate-700 transition-colors disabled:opacity-50 ${isReported || isSpam ? 'text-red-500' : 'text-slate-500 hover:text-red-400'}`}
                                title={isSpam ? "Undo (Un-flag)" : (isReported ? "Reported" : "Report as Spam")}
                            >
                                {isReporting ? <Loader2 size={14} className="animate-spin text-red-500" /> : (
                                    isSpam ? <Undo2 size={14} /> : <Flag size={14} />
                                )}
                            </button>
                        </div>
                    )}
                </td>
            )}

            {/* 5. SELECT CHECKBOX - Only if Admin */}
            {isAdmin && (
                <td className="px-4 py-3 text-center">
                    {!isSpam && (
                        <button
                            onClick={() => onToggle(article.url)}
                            className={`w-5 h-5 mx-auto border rounded flex items-center justify-center transition-colors ${isSelected ? "bg-blue-600 border-blue-600 text-white" : "border-slate-600 text-transparent hover:border-slate-400"}`}
                        >
                            <CheckCircle2 size={14} />
                        </button>
                    )}
                </td>
            )}
        </tr>
    );
}

export const ArticleRow = React.memo(ArticleRowComponent);
