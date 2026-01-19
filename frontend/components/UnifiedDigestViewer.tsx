import React, { useState, useEffect } from 'react';
import {
    LayoutGrid, FileText, Sparkles, Check, Share2, Download, Copy,
    RotateCcw, Trash2
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
    analyticsViewMode = 'cloud',
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
                            Sources
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
                        {(analyticsKeywords?.length > 0 || !isReadOnly) && (
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
                                <span>{digestData?.city || 'Global'}</span>
                                <span>•</span>
                                <span>{new Date(digestData?.created_at || Date.now()).toLocaleDateString()}</span>
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
                            <div className="prose prose-invert prose-lg max-w-none prose-headings:font-bold prose-headings:tracking-tight prose-a:text-blue-400 prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-900/10 prose-blockquote:py-1">
                                <ReactMarkdown>
                                    {digestData?.digest || digestData?.summary_markdown || "*No public summary available.*"}
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
                        {!isReadOnly && onRegenerateAnalytics && (
                            <div className="flex justify-end mb-6">
                                <button
                                    onClick={onRegenerateAnalytics}
                                    disabled={isAnalyzing}
                                    className="flex items-center gap-2 px-4 py-2 bg-neutral-800 hover:bg-neutral-700 rounded text-sm transition-colors"
                                >
                                    <RotateCcw className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
                                    Refresh Intelligence
                                </button>
                            </div>
                        )}

                        {analyticsKeywords?.length > 0 ? (
                            <div className="flex flex-wrap gap-3 justify-center">
                                {analyticsKeywords.map((kw: any, idx: number) => {
                                    const size = 1 + ((kw.importance || 50) / 100) * 2;
                                    let colorClass = "border-slate-700 bg-slate-900/50 text-slate-300";
                                    if (kw.sentiment === 'Positive') colorClass = "border-green-900/50 bg-green-900/20 text-green-400";
                                    if (kw.sentiment === 'Negative') colorClass = "border-red-900/50 bg-red-900/20 text-red-400";

                                    return (
                                        <div
                                            key={idx}
                                            className={`relative group px-4 py-2 rounded-full border ${colorClass} transition-all hover:scale-110 cursor-default`}
                                            style={{ fontSize: `${Math.max(0.8, size)}rem` }}
                                        >
                                            {kw.word}
                                            {/* Tooltip */}
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-black/90 border border-neutral-700 p-3 rounded-lg text-xs w-48 z-50 shadow-xl pointer-events-none">
                                                <div className="font-bold text-white mb-1">{kw.translation || kw.word}</div>
                                                <div className="text-neutral-400">Imp: {kw.importance}</div>
                                                <div className="text-neutral-500 mt-1">Sources: {kw.sources?.length || 0}</div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="text-center py-20 text-neutral-500 italic">
                                No analytics generated yet.
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div >
    );
}
