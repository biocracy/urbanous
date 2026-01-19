import React, { useState, useEffect } from 'react';
import {
    LayoutGrid, FileText, Sparkles, Check, Share2, Download, Copy,
    RotateCcw, Trash2, Languages, Cloud, Columns
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import DigestReportRenderer from './DigestReportRenderer';

interface UnifiedDigestViewerProps {
    digestData: any;
    // Actions - some might be disabled in Read-Only mode
    onSave?: () => void;
    onShare?: () => void;
    onDownload?: () => void;
    onDelete?: () => void;
    onRegenerateSummary?: () => void;
    onRegenerateAnalytics?: () => void;

    // State Setters (for editable mode)
    setDigestSummary?: (summary: string) => void;
    setAnalyticsViewMode?: (mode: 'cloud' | 'columns') => void;

    // Selection/Interaction
    selectedArticleUrls?: Set<string>;
    onToggleSelection?: (url: string) => void;

    // Context
    analyticsKeywords?: any[];
    analyticsViewMode?: 'cloud' | 'columns';

    // Flags
    isReadOnly?: boolean;
    isSaving?: boolean;
    isSharing?: boolean;
    isSummarizing?: boolean;
    isAnalyzing?: boolean;
    tickerText?: string;

    // Report Renderer Props
    spamUrls?: Set<string>;
    onReportSpam?: (article: any) => void;
    onAssessArticle?: (article: any) => void;
    onDebugArticle?: (article: any) => void;
}

export default function UnifiedDigestViewer({
    digestData,
    onSave,
    onShare,
    onDownload,
    onDelete,
    onRegenerateSummary,
    onRegenerateAnalytics,
    setDigestSummary,
    setAnalyticsViewMode,
    selectedArticleUrls = new Set(),
    onToggleSelection,
    analyticsKeywords = [],
    analyticsViewMode, // Removed default to allow local state fallback
    isReadOnly = false,
    isSaving = false,
    isSharing = false,
    isSummarizing = false,
    isAnalyzing = false,
    tickerText = '',
    spamUrls = new Set(),
    onReportSpam,
    onAssessArticle,
    onDebugArticle
}: UnifiedDigestViewerProps) {

    const [activeTab, setActiveTab] = useState<'articles' | 'digest' | 'analytics'>('digest');
    const [copiedSlug, setCopiedSlug] = useState<string | null>(null);
    const [isAnalyticsTranslated, setIsAnalyticsTranslated] = useState(false);
    const [internalAnalyticsViewMode, setInternalAnalyticsViewMode] = useState<'cloud' | 'columns'>('cloud');
    const [selectedKeyword, setSelectedKeyword] = useState<any | null>(null);

    // Use prop if available (controlled), else local state
    const viewMode = analyticsViewMode || internalAnalyticsViewMode;
    const handleSetViewMode = (mode: 'cloud' | 'columns') => {
        if (setAnalyticsViewMode) setAnalyticsViewMode(mode);
        else setInternalAnalyticsViewMode(mode);
    };

    // If initial view is empty but we have data, verify tabs
    // Default to 'digest' if summary exists, else 'articles'
    useEffect(() => {
        if (!digestData?.digest && digestData?.articles?.length > 0) {
            setActiveTab('articles');
        } else if (digestData?.digest) {
            setActiveTab('digest');
        }
    }, [digestData?.id]); // Only on new digest load

    const handleCopyLink = () => {
        if (!digestData?.public_slug) return;
        const link = `${window.location.origin}/s/${digestData.public_slug}`;
        navigator.clipboard.writeText(link);
        setCopiedSlug(digestData.public_slug);
        setTimeout(() => setCopiedSlug(null), 3000);
    };

    const isEditorActive = !isReadOnly && !!setDigestSummary;
    const effectiveKeywords = analyticsKeywords.length > 0 ? analyticsKeywords : (digestData?.analysis_source || []);

    // Date Range Helper
    const formatDateRange = (createdDateStr: string, timeframeStr: string = "24h") => {
        const createdDate = new Date(createdDateStr || Date.now());

        // "Inclusive" subtraction: If 3 days, we want Today + (Today-1) + (Today-2). 
        // So we subtract 2 days from the valid range "start".

        let daysToSubtract = 0;
        const normalizedTime = (timeframeStr || "").toLowerCase().replace(/\s/g, '');

        if (normalizedTime.includes("3day")) daysToSubtract = 3;
        else if (normalizedTime.includes("1week") || normalizedTime.includes("7day")) daysToSubtract = 7;
        else if (normalizedTime.includes("1month") || normalizedTime.includes("30day")) daysToSubtract = 30;
        else if (normalizedTime.includes("24h") || normalizedTime.includes("1day")) daysToSubtract = 1; // Explicitly handle 24h as 1 day range

        // Default to 1 day if 0, so we always show a range if desired? 
        // User asked for "time-intervals... do not show feed mode (single date)".
        // If we want interval for 24h (e.g. 16.1-17.1), we need daysToSubtract >= 1.
        if (daysToSubtract === 0) daysToSubtract = 1;

        const msToSubtract = daysToSubtract * 24 * 60 * 60 * 1000;
        const startDate = new Date(createdDate.getTime() - msToSubtract);

        const pad = (n: number) => n.toString().padStart(2, '0');
        const format = (d: Date) => `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
        const formatShort = (d: Date) => `${pad(d.getDate())}.${pad(d.getMonth() + 1)}`;

        // Same Year?
        if (startDate.getFullYear() === createdDate.getFullYear()) {
            // Same Month?
            if (startDate.getMonth() === createdDate.getMonth()) {
                // Same Day? (Unlikely but possible)
                if (startDate.getDate() === createdDate.getDate()) return format(createdDate);
                // DD-DD.MM.YYYY
                return `${startDate.getDate()}-${format(createdDate)}`;
            }
            // DD.MM-DD.MM.YYYY
            return `${formatShort(startDate)}-${format(createdDate)}`;
        }
        // Different Year
        return `${format(startDate)}-${format(createdDate)}`;
    };

    return (
        <div className="flex flex-col h-full bg-[#0a0a0a] text-white">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 border-b border-neutral-800 bg-black/40 backdrop-blur-md sticky top-0 z-20">
                <div className="flex items-center gap-4">
                    {/* Tabs */}
                    <div className="flex bg-neutral-900 rounded-lg p-1 border border-neutral-800">
                        <button
                            onClick={() => setActiveTab('articles')}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'articles' ? 'bg-neutral-800 text-white shadow-sm' : 'text-neutral-400 hover:text-white'}`}
                        >
                            <LayoutGrid className="w-4 h-4" />
                            Headlines
                            <span className="bg-neutral-950 px-1.5 py-0.5 rounded text-[10px] text-neutral-500 border border-neutral-800">
                                {digestData?.articles?.length || 0}
                            </span>
                        </button>
                        <button
                            onClick={() => setActiveTab('digest')}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'digest' ? 'bg-blue-900/30 text-blue-400 shadow-sm border border-blue-900/50' : 'text-neutral-400 hover:text-white'}`}
                        >
                            <FileText className="w-4 h-4" />
                            Report
                        </button>
                        {(effectiveKeywords.length > 0 || !isReadOnly) && (
                            <button
                                onClick={() => setActiveTab('analytics')}
                                className={`px-4 py-2 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'analytics' ? 'bg-fuchsia-900/30 text-fuchsia-400 shadow-sm border border-fuchsia-900/50' : 'text-neutral-400 hover:text-white'}`}
                            >
                                <Sparkles className="w-4 h-4" />
                                Intelligence
                            </button>
                        )}
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                    {/* Ticker */}
                    {tickerText && (
                        <div className=" text-xs font-mono text-fuchsia-400 animate-pulse mr-4 hidden md:block">
                            {tickerText}
                        </div>
                    )}

                    {!isReadOnly && onSave && (
                        <button
                            onClick={onSave}
                            disabled={isSaving}
                            className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-green-400 transition-colors"
                            title="Save to Library"
                        >
                            <Check className={`w-5 h-5 ${isSaving ? 'animate-pulse' : ''}`} />
                        </button>
                    )}

                    {onShare && (
                        <button
                            onClick={onShare}
                            disabled={isSharing}
                            className={`p-2 hover:bg-neutral-800 rounded-full transition-colors ${digestData?.is_public ? 'text-blue-400' : 'text-neutral-400 hover:text-blue-400'}`}
                            title="Share Public Link"
                        >
                            <Share2 className="w-5 h-5" />
                        </button>
                    )}

                    {digestData?.is_public && (
                        <div className="flex items-center">
                            <button
                                onClick={handleCopyLink}
                                className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors"
                                title="Copy Public Link"
                            >
                                {copiedSlug === digestData.public_slug ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                            </button>
                        </div>
                    )}

                    {onDownload && (
                        <button
                            onClick={onDownload}
                            className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors"
                            title="Download HTML Report"
                        >
                            <Download className="w-5 h-5" />
                        </button>
                    )}

                    {!isReadOnly && onDelete && digestData?.id && (
                        <button
                            onClick={onDelete}
                            className="p-2 hover:bg-red-900/30 rounded-full text-neutral-400 hover:text-red-400 transition-colors ml-2"
                            title="Delete Digest"
                        >
                            <Trash2 className="w-5 h-5" />
                        </button>
                    )}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-grow overflow-y-auto custom-scrollbar relative bg-neutral-900/30">

                {/* TAB 1: ARTICLES (DigestReportRenderer) */}
                <div className={`p-6 max-w-5xl mx-auto w-full transition-opacity duration-300 ${activeTab === 'articles' ? 'opacity-100 flex' : 'hidden opacity-0'}`}>
                    <div className="w-full">
                        <DigestReportRenderer
                            articles={digestData?.articles || []}
                            category={digestData?.category}
                            selectedUrls={selectedArticleUrls}
                            onToggle={onToggleSelection || (() => { })}
                            onReportSpam={!isReadOnly ? onReportSpam : undefined}
                            onAssess={!isReadOnly ? onAssessArticle : undefined}
                            onDebug={!isReadOnly ? onDebugArticle : undefined}
                            spamUrls={spamUrls}
                            excludedArticles={digestData?.excluded_articles || []}
                            isLoading={false} // Assuming loaded if enabled
                        />
                    </div>
                </div>

                {/* TAB 2: DIGEST (MarkDown / Editor) */}
                <div className={`h-full flex flex-col transition-opacity duration-300 ${activeTab === 'digest' ? 'opacity-100 flex' : 'hidden opacity-0'}`}>
                    <div className="flex-grow p-6 md:p-12 max-w-4xl mx-auto w-full">
                        {/* Header in Report View */}
                        <div className="mb-12 text-center border-b border-neutral-800 pb-8">
                            <h1 className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 mb-4 tracking-tight">
                                {digestData?.title || `${digestData?.category || 'News'} Report`}
                            </h1>
                            <div className="text-neutral-500 font-mono text-sm uppercase tracking-widest flex items-center justify-center gap-4">
                                {digestData?.category && (
                                    <>
                                        <span className="text-blue-400 font-bold">{digestData.category}</span>
                                        <span>•</span>
                                    </>
                                )}
                                <span>{digestData?.city || 'Global'}</span>
                                <span>•</span>
                                <span>{formatDateRange(digestData?.created_at, digestData?.timeframe)}</span>
                            </div>
                        </div>

                        {isEditorActive ? (
                            <textarea
                                className="w-full h-[80vh] bg-neutral-900/50 border border-neutral-700 rounded-lg p-4 font-mono text-sm text-white focus:outline-none focus:border-blue-500"
                                value={digestData?.digest || ""}
                                onChange={(e) => setDigestSummary?.(e.target.value)}
                                placeholder="# Write your intelligence report here..."
                            />
                        ) : (
                            <div className="max-w-none">
                                <ReactMarkdown
                                    urlTransform={(url) => url}
                                    components={{
                                        h1: ({ node, ...props }) => <h1 className="text-4xl font-extrabold text-white mb-8 border-b border-white/10 pb-4 mt-8" {...props} />,
                                        h2: ({ node, ...props }) => <h2 className="text-3xl font-bold text-blue-200 mt-12 mb-6 border-l-4 border-blue-500 pl-4" {...props} />,
                                        h3: ({ node, ...props }) => <h3 className="text-xl font-bold text-indigo-300 mt-8 mb-3 uppercase tracking-wide" {...props} />,
                                        p: ({ node, ...props }) => <p className="text-lg text-slate-300 leading-loose mb-8 text-justify" {...props} />,
                                        ul: ({ node, ...props }) => <ul className="list-disc list-outside ml-6 mb-6 space-y-2 text-slate-300" {...props} />,
                                        li: ({ node, ...props }) => <li className="pl-2" {...props} />,
                                        strong: ({ node, ...props }) => <strong className="text-amber-400 font-bold" {...props} />,
                                        blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-slate-600 pl-4 italic text-slate-400 my-6 bg-slate-800/30 py-2 rounded-r" {...props} />,
                                        a: ({ node, ...props }) => {
                                            const href = props.href || '';
                                            if (href.startsWith('citation:')) {
                                                const index = parseInt(href.split(':')[1]);
                                                const article = digestData?.articles?.[index - 1];
                                                const title = article ? (article.title || 'Source') : `Source ${index}`;
                                                const url = article ? article.url : '';
                                                const isValidUrl = url && url.startsWith('http');

                                                return (
                                                    <span className="relative inline-block group mx-1 align-baseline">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                if (isValidUrl) window.open(url, '_blank');
                                                            }}
                                                            className={`font-bold text-xs align-super px-1 rounded transition-colors ${isValidUrl
                                                                ? 'text-blue-400 hover:bg-blue-900/30 cursor-pointer'
                                                                : 'text-slate-500 cursor-help'
                                                                }`}
                                                        >
                                                            [{index}]
                                                        </button>
                                                        {/* Tooltip */}
                                                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 bg-slate-900 border border-slate-700 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 text-xs text-left">
                                                            <span className="block font-bold text-white mb-1 line-clamp-3 leading-tight">{title}</span>
                                                            <span className={`block truncate font-mono mt-1 ${isValidUrl ? 'text-blue-400' : 'text-amber-500'}`}>
                                                                {isValidUrl ? new URL(url).hostname : 'Source URL not available'}
                                                            </span>
                                                        </span>
                                                    </span>
                                                );
                                            }
                                            const isExample = !href.startsWith('http');
                                            return <a className="text-blue-400 hover:text-blue-300 underline decoration-blue-500/50 underline-offset-4" target="_blank" {...props} />;
                                        }
                                    }}
                                >
                                    {(digestData?.digest || digestData?.summary_markdown || "")
                                        .replace(/^#\s+.+$/m, '') // Remove duplicate title (first H1)
                                        .replace(/\[(\d+)\]/g, '[$1](citation:$1)')}
                                </ReactMarkdown>
                            </div>
                        )}

                        {!isReadOnly && onRegenerateSummary && (
                            <div className="mt-12 flex justify-center pb-20">
                                <button
                                    onClick={onRegenerateSummary}
                                    disabled={isSummarizing || selectedArticleUrls.size === 0}
                                    className={`
                                        group relative px-8 py-4 rounded-full font-bold text-white shadow-2xl transition-all duration-500
                                        ${isSummarizing ? 'bg-neutral-800 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-105'}
                                    `}
                                >
                                    <span className="flex items-center gap-3 relative z-10">
                                        {isSummarizing ? (
                                            <>
                                                <RotateCcw className="w-5 h-5 animate-spin" />
                                                Start Thinking...
                                            </>
                                        ) : (
                                            <>
                                                <Sparkles className="w-5 h-5" />
                                                Regenerate Report ({selectedArticleUrls.size})
                                            </>
                                        )}
                                    </span>
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* TAB 3: ANALYTICS */}
                <div className={`p-6 max-w-6xl mx-auto w-full transition-opacity duration-300 ${activeTab === 'analytics' ? 'opacity-100 flex' : 'hidden opacity-0'}`}>
                    <div className="w-full">
                        <div className="flex justify-between items-center mb-6">
                            {/* Left: View Controls */}
                            <div className="flex items-center gap-2">
                                <div className="flex bg-neutral-900 rounded-lg p-1 border border-neutral-800">
                                    <button
                                        onClick={() => handleSetViewMode('cloud')}
                                        className={`p-2 rounded hover:text-white transition-colors ${viewMode === 'cloud' ? 'bg-neutral-800 text-white' : 'text-neutral-400'}`}
                                        title="Word Cloud"
                                    >
                                        <Cloud className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => handleSetViewMode('columns')}
                                        className={`p-2 rounded hover:text-white transition-colors ${viewMode === 'columns' ? 'bg-neutral-800 text-white' : 'text-neutral-400'}`}
                                        title="Columns"
                                    >
                                        <Columns className="w-4 h-4" />
                                    </button>
                                </div>

                                <button
                                    onClick={() => setIsAnalyticsTranslated(!isAnalyticsTranslated)}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-bold transition-colors border ${isAnalyticsTranslated ? 'bg-indigo-900/50 text-indigo-300 border-indigo-700' : 'bg-neutral-900 text-neutral-400 border-neutral-700 hover:text-white'}`}
                                >
                                    <Languages className="w-3 h-3" />
                                    {isAnalyticsTranslated ? 'A/文' : 'A/文'}
                                </button>
                            </div>

                            {/* Right: Refresh (Editable Only) */}
                            {!isReadOnly && onRegenerateAnalytics && (
                                <button
                                    onClick={onRegenerateAnalytics}
                                    disabled={isAnalyzing}
                                    className="flex items-center gap-2 px-4 py-2 bg-neutral-800 hover:bg-neutral-700 rounded text-sm transition-colors"
                                >
                                    <RotateCcw className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
                                    Refresh Intelligence
                                </button>
                            )}
                        </div>

                        {effectiveKeywords.length > 0 ? (
                            viewMode === 'columns' ? (
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    {['Positive', 'Neutral', 'Negative'].map((sentiment) => {
                                        const sentimentColor = sentiment === 'Positive' ? 'text-green-400 border-green-900/50' :
                                            sentiment === 'Negative' ? 'text-red-400 border-red-900/50' :
                                                'text-neutral-400 border-neutral-800';

                                        const items = effectiveKeywords.filter((k: any) => k.sentiment === sentiment);

                                        return (
                                            <div key={sentiment} className="flex flex-col gap-4">
                                                <h3 className={`text-sm font-bold uppercase tracking-widest border-b pb-2 ${sentimentColor.split(' ')[0]}`}>
                                                    {sentiment}
                                                </h3>
                                                {items.length === 0 && <div className="text-neutral-600 italic text-xs">No keywords</div>}
                                                {items.map((kw: any, idx: number) => (
                                                    <div
                                                        key={idx}
                                                        className={`bg-neutral-900/50 border border-neutral-800 p-4 rounded-lg flex justify-between items-start cursor-pointer hover:bg-neutral-800 transition-colors ${selectedKeyword === kw ? 'ring-2 ring-blue-500' : ''}`}
                                                        onClick={() => setSelectedKeyword(kw)}
                                                    >
                                                        <div className="w-full">
                                                            <div className="font-bold text-white text-lg flex justify-between w-full">
                                                                <span>{isAnalyticsTranslated && kw.translation ? kw.translation : kw.word}</span>
                                                                <span className="text-xs font-mono bg-neutral-950 px-2 py-1 rounded text-neutral-500">{kw.sources?.length || 0} src</span>
                                                            </div>
                                                            {isAnalyticsTranslated && kw.translation && kw.translation !== kw.word && (
                                                                <div className="text-xs text-neutral-500 mt-1">{kw.word}</div>
                                                            )}
                                                            <div className="text-xs text-neutral-400 mt-2 flex justify-between">
                                                                <span>Imp: {kw.importance}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="flex flex-wrap gap-3 justify-center">
                                    {effectiveKeywords.map((kw: any, idx: number) => {
                                        const size = 1 + ((kw.importance || 50) / 100) * 2;
                                        let colorClass = "border-slate-700 bg-slate-900/50 text-slate-300";
                                        if (kw.sentiment === 'Positive') colorClass = "border-green-900/50 bg-green-900/20 text-green-400";
                                        if (kw.sentiment === 'Negative') colorClass = "border-red-900/50 bg-red-900/20 text-red-400";

                                        // DISPLAY WORD LOGIC
                                        const displayWord = (isAnalyticsTranslated && kw.translation) ? kw.translation : kw.word;

                                        return (
                                            <div
                                                key={idx}
                                                onClick={(e) => { e.stopPropagation(); setSelectedKeyword(kw); }}
                                                className={`relative group px-4 py-2 rounded-full border ${colorClass} transition-all hover:scale-110 cursor-pointer ${selectedKeyword === kw ? 'ring-2 ring-blue-500 bg-black z-20' : ''}`}
                                                style={{ fontSize: `${Math.max(0.8, size)}rem` }}
                                            >
                                                {displayWord}
                                            </div>
                                        );
                                    })}
                                </div>
                            )
                        ) : (
                            <div className="text-center py-20 text-neutral-500 italic">
                                No analytics generated yet.
                            </div>
                        )}
                    </div>
                </div>

                {/* Selected Keyword Modal/Overlay */}
                {selectedKeyword && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedKeyword(null)}>
                        <div className="bg-neutral-900 border border-neutral-700 rounded-xl shadow-2xl p-6 max-w-md w-full relative" onClick={e => e.stopPropagation()}>
                            <button
                                onClick={() => setSelectedKeyword(null)}
                                className="absolute top-4 right-4 text-neutral-500 hover:text-white"
                            >
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                            </button>

                            <h3 className="text-2xl font-black text-white mb-1">
                                {isAnalyticsTranslated && selectedKeyword.translation ? selectedKeyword.translation : selectedKeyword.word}
                            </h3>
                            {isAnalyticsTranslated && selectedKeyword.translation !== selectedKeyword.word && (
                                <div className="text-neutral-500 text-sm font-mono mb-4">{selectedKeyword.word}</div>
                            )}

                            <div className="flex gap-2 mb-6 mt-2">
                                <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${selectedKeyword.sentiment === 'Positive' ? 'bg-green-900/30 text-green-400 border border-green-900' :
                                    selectedKeyword.sentiment === 'Negative' ? 'bg-red-900/30 text-red-400 border border-red-900' :
                                        'bg-neutral-800 text-neutral-400 border border-neutral-700'
                                    }`}>
                                    {selectedKeyword.sentiment}
                                </span>
                                <span className="px-2 py-1 rounded text-xs font-bold bg-neutral-800 text-neutral-400 border border-neutral-700">
                                    Imp: {selectedKeyword.importance}
                                </span>
                            </div>

                            <div className="border-t border-neutral-800 pt-4">
                                <div className="text-xs text-neutral-500 font-bold uppercase tracking-widest mb-3">
                                    Found in {selectedKeyword.sources?.length || 0} Sources
                                </div>
                                <ul className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                                    {selectedKeyword.sources?.map((s: string, i: number) => {
                                        // Use Safe Parsing inside the render to avoid crashes
                                        return (
                                            <li key={i}>
                                                <a
                                                    href={s}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="block p-3 rounded-lg bg-neutral-950 border border-neutral-800 hover:border-blue-700 hover:bg-blue-900/10 transition-colors group"
                                                >
                                                    <div className="text-sm text-blue-300 font-medium line-clamp-2 group-hover:text-blue-200">
                                                        {(() => {
                                                            const article = digestData?.articles?.find((a: any) => a.url === s);
                                                            if (article) return article.title;
                                                            try { return new URL(s).hostname; } catch { return s; }
                                                        })()}
                                                    </div>
                                                    <div className="text-xs text-neutral-600 mt-1 truncate">
                                                        {(() => {
                                                            try { return new URL(s).hostname; } catch { return 'Source'; }
                                                        })()}
                                                    </div>
                                                </a>
                                            </li>
                                        );
                                    })}
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

            </div>
        </div >
    );
}
