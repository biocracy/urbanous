import React, { useState, useEffect, useRef } from 'react';
import {
    LayoutGrid, FileText, Sparkles, Check, Download, Copy,
    RotateCcw, Trash2, Languages, Cloud, Columns, X, Save, Image
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import DigestReportRenderer from './DigestReportRenderer';
const AnalyticsTooltip = ({ data, isTranslated, onClose }: { data: { kw: any, rect: DOMRect }, isTranslated: boolean, onClose: () => void }) => {
    const { kw, rect } = data;
    if (!kw || !rect) return null;

    // Position calculation
    // Default: Centered above the element
    const top = rect.top - 10; // 10px buffer
    const left = rect.left + (rect.width / 2);

    return (
        <div
            className="fixed z-[9999] bg-black/95 border border-neutral-700 p-3 rounded-xl text-xs w-64 shadow-2xl overflow-hidden text-left animate-in fade-in zoom-in-95 duration-200"
            style={{
                top: top,
                left: left,
                transform: 'translate(-50%, -100%)', // Shift up and center
                pointerEvents: 'none'
            }}
        >
            <div className="font-bold text-white mb-1 text-base">{kw.translation || kw.word}</div>
            {isTranslated && kw.translation !== kw.word && (
                <div className="text-neutral-500 mb-2 text-[10px] uppercase font-mono">Orig: {kw.word}</div>
            )}

            <div className="flex gap-2 mb-3">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${kw.sentiment === 'Positive' ? 'bg-green-900/30 text-green-400 border border-green-900' :
                    kw.sentiment === 'Negative' ? 'bg-red-900/30 text-red-400 border border-red-900' :
                        'bg-neutral-800 text-neutral-400 border border-neutral-700'
                    }`}>
                    {kw.sentiment}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-neutral-800 text-neutral-400 border border-neutral-700">
                    Imp: {kw.importance}
                </span>
            </div>

            <div className="text-neutral-500 font-bold uppercase tracking-widest text-[10px] mb-1">
                Sources ({kw.sources?.length || 0})
            </div>
            <div className="max-h-32 overflow-y-auto custom-scrollbar space-y-1 mb-2 pr-1">
                {kw.sources?.map((s: any, i: number) => {
                    let hostname = "";
                    const url = typeof s === 'string' ? s : s?.url;
                    if (!url) return null;
                    try { hostname = new URL(url).hostname; } catch { hostname = "Source"; }
                    return (
                        <div key={i} className="text-blue-300/80 truncate border-b border-white/5 pb-0.5 last:border-0">
                            {hostname}
                        </div>
                    );
                })}
            </div>

            <div className="mt-2 py-1 bg-blue-900/20 text-blue-300 font-bold uppercase tracking-wide text-center rounded border border-blue-900/50 text-[10px]">
                Click to Lock & Open Links
            </div>
        </div>
    );
};

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

    // Navigation
    onClose?: () => void;
    initialTab?: 'articles' | 'digest' | 'analytics'; // New Prop
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
    onDebugArticle,
    onClose,
    initialTab = 'articles'
}: UnifiedDigestViewerProps) {

    const [activeTab, setActiveTab] = useState<'articles' | 'digest' | 'analytics'>(initialTab || 'articles');
    const [copiedSlug, setCopiedSlug] = useState<string | null>(null);
    const [isAnalyticsTranslated, setIsAnalyticsTranslated] = useState(false);
    const [isHeadlineTranslated, setIsHeadlineTranslated] = useState(false); // New State
    const [internalAnalyticsViewMode, setInternalAnalyticsViewMode] = useState<'cloud' | 'columns'>('cloud');
    const [selectedKeyword, setSelectedKeyword] = useState<any | null>(null);
    const [hoveredKeywordData, setHoveredKeywordData] = useState<{ kw: any, rect: DOMRect } | null>(null);
    const [isEditing, setIsEditing] = useState(false); // Default to Preview Mode
    const [isGeneratingImage, setIsGeneratingImage] = useState(false);

    // FIX: Use Ref to track latest digest data for async operations (Stale Closure Fix)
    const digestDataRef = useRef(digestData);
    useEffect(() => {
        if (digestData) {
            console.log(`[UnifiedDigestViewer] digestData prop updated. ID: ${digestData.id}, Length: ${digestData.digest?.length}`);
            if (digestData.digest?.includes('[[GENERATING_SKETCH]]')) {
                console.log("[UnifiedDigestViewer] TOKEN DETECTED in prop update!");
            }
        }
        digestDataRef.current = digestData;
    }, [digestData]);

    // Image Generation Handler
    const handleGenerateImage = async () => {
        if (!digestData?.id) return;
        setIsGeneratingImage(true);

        const TOKEN = "[[GENERATING_SKETCH]]";

        // Insert Token at top or after first break
        let currentText = digestData.digest || digestData.summary_markdown || "";
        const parts = currentText.split('\n\n');

        if (parts.length > 1) {
            parts.splice(1, 0, TOKEN);
            const newText = parts.join('\n\n');
            if (setDigestSummary) setDigestSummary(newText);
        } else {
            if (setDigestSummary) setDigestSummary(TOKEN + "\n\n" + currentText);
        }

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiUrl}/digests/${digestData.id}/generate-image`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (res.ok) {
                const data = await res.json();
                const imageUrl = data.image_url;

                if (data.prompt) console.log("[UnifiedDigestViewer] GENERATION PROMPT:", data.prompt);


                let finalUrl = imageUrl;
                if (imageUrl.startsWith('/')) {
                    const api = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
                    finalUrl = `${api}${imageUrl}`;
                }

                const imageMd = `![${digestData.city} Illustration](${finalUrl})`;

                if (setDigestSummary) {
                    setTimeout(() => {
                        let latestText = "";
                        try {
                            latestText = digestDataRef.current?.digest || document.querySelector('textarea')?.value || "";
                        } catch (err) {
                            console.error(err);
                        }

                        // Robustly replace the token
                        if (latestText.includes(TOKEN)) {
                            const newText = latestText.replace(TOKEN, imageMd);
                            setDigestSummary(newText);
                        } else {
                            // Fallback
                            setDigestSummary(imageMd + "\n\n" + latestText);
                        }
                    }, 100);
                }

            } else {
                console.error("Gen failed");
                if (setDigestSummary) {
                    const text = digestDataRef.current?.digest || "";
                    setDigestSummary(text.replace(TOKEN, ""));
                }
            }
        } catch (e) {
            console.error(e);
            if (setDigestSummary) {
                const text = digestDataRef.current?.digest || "";
                setDigestSummary(text.replace(TOKEN, ""));
            }
        } finally {
            setIsGeneratingImage(false);
        }
    };



    // Use prop if available (controlled), else local state
    const viewMode = analyticsViewMode || internalAnalyticsViewMode;
    const handleSetViewMode = (mode: 'cloud' | 'columns') => {
        console.log(`[UnifiedDigestViewer] Switching View Mode to: ${mode}`);
        if (setAnalyticsViewMode) setAnalyticsViewMode(mode);
        else setInternalAnalyticsViewMode(mode);
    };

    // If initial view is empty but we have data, verify tabs
    // Default to 'digest' if summary exists but empty articles? No, stay on articles if articles exist.
    // If initial view is empty but we have data, verify tabs
    // Default to 'digest' if summary exists but empty articles? No, stay on articles if articles exist.
    useEffect(() => {
        if (initialTab) {
            setActiveTab(initialTab);
            return;
        }

        if (!digestData?.digest && digestData?.articles?.length > 0) {
            setActiveTab('articles');
        } else if (digestData?.digest && digestData?.articles?.length === 0) {
            // Only if NO articles but we have a digest (rare?)
            setActiveTab('digest');
        }
    }, [digestData?.id, initialTab]); // Only on new digest load

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

        const msToSubtract = timeframeStr === '24h' ? 24 * 60 * 60 * 1000 :
            timeframeStr === '3days' ? 3 * 24 * 60 * 60 * 1000 :
                (timeframeStr === 'week' || timeframeStr === '1week') ? 7 * 24 * 60 * 60 * 1000 : 0;
        const startDate = new Date(createdDate.getTime() - msToSubtract);

        // Format: DD.MM - DD.MM.YYYY
        const d1 = startDate.getDate().toString().padStart(2, '0');
        const m1 = (startDate.getMonth() + 1).toString().padStart(2, '0');
        const d2 = createdDate.getDate().toString().padStart(2, '0');
        const m2 = (createdDate.getMonth() + 1).toString().padStart(2, '0');
        const y = createdDate.getFullYear();

        // Compact format if months match: DD - DD.MM.YYYY
        if (m1 === m2) {
            return `${d1}-${d2}.${m2}.${y}`;
        }
        return `${d1}.${m1}-${d2}.${m2}.${y}`;
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

                    {/* Copy Link */}
                    {digestData?.is_public && (
                        <button
                            onClick={handleCopyLink}
                            className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors"
                            title="Copy Public Link"
                        >
                            {copiedSlug === digestData.public_slug ? <Check className="w-5 h-5 text-green-500" /> : <Copy className="w-5 h-5" />}
                        </button>
                    )}

                    {/* Download */}
                    {onDownload && (
                        <button
                            onClick={onDownload}
                            className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-white transition-colors"
                            title="Download HTML Report"
                        >
                            <Download className="w-5 h-5" />
                        </button>
                    )}

                    {/* Divider */}
                    <div className="w-px h-6 bg-neutral-800 mx-2"></div>

                    {/* Save */}
                    {!isReadOnly && onSave && (
                        <button
                            onClick={onSave}
                            disabled={isSaving}
                            className="p-2 hover:bg-neutral-800 rounded-full text-neutral-400 hover:text-green-400 transition-colors"
                            title="Save to Library"
                        >
                            <Save className={`w-5 h-5 ${isSaving ? 'animate-pulse' : ''}`} />
                        </button>
                    )}

                    {/* Delete */}
                    {!isReadOnly && onDelete && (
                        <button
                            onClick={onDelete}
                            className="p-2 hover:bg-red-900/20 rounded-full text-neutral-400 hover:text-red-400 transition-colors"
                            title="Delete Digest"
                        >
                            <Trash2 className="w-5 h-5" />
                        </button>
                    )}

                    {/* Closers */}
                    {onClose && (
                        <>
                            <div className="w-px h-6 bg-neutral-800 mx-2"></div>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onClose();
                                }}
                                className="p-2 hover:bg-red-900/30 rounded-full text-neutral-400 hover:text-red-400 transition-colors"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </>
                    )}


                </div>
            </div>

            {/* Content Area */}
            <div className="flex-grow overflow-y-auto custom-scrollbar relative bg-neutral-900/30">

                {/* TAB 1: ARTICLES (DigestReportRenderer) */}
                <div className={`p-6 max-w-5xl mx-auto w-full transition-opacity duration-300 ${activeTab === 'articles' ? 'opacity-100 flex flex-col' : 'hidden opacity-0'}`}>

                    {/* Toolbar / Header */}
                    <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 pb-4 border-b border-neutral-800 gap-4">
                        <div>
                            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
                                <span className="text-blue-400 capitalize">{digestData?.city || 'Global'}</span> Headlines
                            </h2>
                            <p className="text-neutral-400 mt-1 flex flex-wrap items-center gap-2">
                                <span>Discussing <span className="text-slate-200 font-semibold">{digestData?.category}</span></span>
                                <span className="w-1 h-1 rounded-full bg-neutral-600"></span>
                                <span className="text-neutral-500 font-mono text-sm">
                                    {formatDateRange(digestData?.created_at, digestData?.timeframe)}
                                </span>
                            </p>
                        </div>

                        <div className="flex items-center gap-2">
                            {/* NEW: Summarize Button in Headlines Tab */}
                            {!isReadOnly && onRegenerateSummary && (
                                <button
                                    onClick={() => { setActiveTab('digest'); onRegenerateSummary(); }}
                                    disabled={isSummarizing || selectedArticleUrls.size === 0}
                                    className={`
                                        flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all border shadow-lg
                                        ${isSummarizing || selectedArticleUrls.size === 0
                                            ? 'bg-neutral-800 text-neutral-500 border-neutral-700 cursor-not-allowed'
                                            : 'bg-blue-600 hover:bg-blue-500 text-white border-blue-400 shadow-blue-900/20'}
                                    `}
                                >
                                    {isSummarizing ? (
                                        <>
                                            <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                                            Thinking...
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles className="w-3.5 h-3.5" />
                                            Summarize ({selectedArticleUrls.size})
                                        </>
                                    )}
                                </button>
                            )}

                            <button
                                onClick={() => setIsHeadlineTranslated(!isHeadlineTranslated)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all border shadow-lg ${isHeadlineTranslated ? 'bg-indigo-900/40 text-indigo-300 border-indigo-500/50 shadow-indigo-900/20' : 'bg-neutral-900/80 text-neutral-400 border-neutral-700 hover:text-white hover:border-neutral-500'}`}
                            >
                                <Languages className="w-3.5 h-3.5" />
                                {isHeadlineTranslated ? 'Translated' : 'Translate Titles'}
                            </button>
                        </div>
                    </div>

                    <div className="w-full">
                        <DigestReportRenderer
                            articles={digestData?.articles || []}
                            category={digestData?.category}
                            isTranslated={isHeadlineTranslated} // Pass state
                            selectedUrls={selectedArticleUrls}
                            onToggle={onToggleSelection || (() => { })}
                            onReportSpam={!isReadOnly ? onReportSpam : undefined}
                            onAssess={!isReadOnly ? onAssessArticle : undefined}
                            onDebug={!isReadOnly ? onDebugArticle : undefined}
                            spamUrls={spamUrls}
                            excludedArticles={digestData?.excluded_articles || []}
                            isLoading={isSummarizing} // Connected to global loading state
                        />
                    </div>
                </div>

                {/* TAB 2: DIGEST (MarkDown / Editor) */}
                <div className={`h-full flex flex-col transition-opacity duration-300 ${activeTab === 'digest' ? 'opacity-100 flex' : 'hidden opacity-0'}`}>
                    <div className="flex-grow p-6 md:p-12 max-w-4xl mx-auto w-full">
                        {/* Header in Report View */}
                        <div className="mb-12 text-center border-b border-neutral-800 pb-8 relative">
                            {/* Image Generation Button (Top Right) */}
                            {!isReadOnly && !digestData?.image_url && (
                                <div className="absolute top-0 right-0">
                                    <button
                                        onClick={handleGenerateImage}
                                        disabled={isGeneratingImage}
                                        className={`
                                            flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider transition-all border shadow-lg
                                            ${isGeneratingImage
                                                ? 'bg-neutral-800 text-neutral-500 border-neutral-700 cursor-not-allowed'
                                                : 'bg-fuchsia-900/30 text-fuchsia-400 border-fuchsia-800 hover:bg-fuchsia-900/50 hover:text-white'}
                                        `}
                                    >
                                        {isGeneratingImage ? (
                                            <>
                                                <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                                                Sketching digest concept...
                                            </>
                                        ) : (
                                            <>
                                                <Image className="w-3.5 h-3.5" />
                                                Generate Illustration
                                            </>
                                        )}
                                    </button>
                                </div>
                            )}

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
                    </div>





                    {isEditing ? (
                        <textarea
                            className="w-full h-[80vh] bg-neutral-900/50 border border-neutral-700 rounded-lg p-4 font-mono text-sm text-white focus:outline-none focus:border-blue-500"
                            value={digestData?.digest || ""}
                            onChange={(e) => setDigestSummary?.(e.target.value)}
                            placeholder="# Write your intelligence report here..."
                        />
                    ) : (
                        <div className="max-w-3xl mx-auto px-4 md:px-0">
                            {(() => {
                                // const rawContent = digestData?.digest || digestData?.summary_markdown || "";
                                // console.log("[UnifiedDigestViewer] Raw Digest Content:", rawContent.slice(0, 200));
                                return (
                                    <ReactMarkdown
                                        rehypePlugins={[rehypeRaw]}
                                        // Allow 'citation:' protocol
                                        urlTransform={(url) => url}
                                        components={{
                                            // Custom Link Handling (Citations & External)
                                            a: ({ href, children, ...props }) => {
                                                if (href?.startsWith('citation:')) {
                                                    const id = parseInt(href.split(':')[1]);
                                                    const articleHandler = (e: React.MouseEvent) => {
                                                        e.preventDefault();
                                                        e.stopPropagation();
                                                        // Try to find the article
                                                        if (digestData?.articles && digestData.articles[id - 1]) {
                                                            const url = digestData.articles[id - 1].url;
                                                            window.open(url, '_blank');
                                                        } else {
                                                            console.warn(`[UnifiedDigestViewer] Citation [${id}] not found in articles.`);
                                                        }
                                                    };

                                                    return (
                                                        <span
                                                            onClick={articleHandler}
                                                            className="text-blue-400 font-bold cursor-pointer hover:underline hover:text-blue-300 transition-colors"
                                                            title={`Open Source Article ${id}`}
                                                        >
                                                            {children}
                                                        </span>
                                                    );
                                                }
                                                const isExample = !href?.startsWith('http');
                                                if (isExample) return <span className="text-blue-300">{children}</span>;

                                                // Handle raw <a> tags from HTML if any
                                                return <a href={href} className="text-blue-400 hover:text-blue-300 underline decoration-blue-500/50 underline-offset-4" target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
                                            },
                                            // Headings
                                            h1: ({ children }) => <h1 className="text-3xl font-bold mb-6 text-white border-b border-neutral-800 pb-2 mt-8 first:mt-0">{children}</h1>,
                                            h2: ({ children }) => <h2 className="text-2xl font-bold mb-4 text-white mt-8">{children}</h2>,
                                            h3: ({ children }) => <h3 className="text-xl font-bold mb-3 text-blue-200 mt-6">{children}</h3>,
                                            // Text & Layout
                                            p: ({ children }) => {
                                                const childStr = String(children);
                                                if (childStr.includes('[[GENERATING_SKETCH]]')) {
                                                    return (
                                                        <div className="my-8 p-8 border border-fuchsia-500/30 rounded-lg bg-fuchsia-900/10 flex flex-col items-center justify-center gap-3 animate-pulse">
                                                            <div className="w-8 h-8 border-2 border-fuchsia-500 border-t-transparent rounded-full animate-spin"></div>
                                                            <span className="text-fuchsia-300 font-mono text-xs uppercase">Rendering Architectural Sketch...</span>
                                                        </div>
                                                    );
                                                }
                                                return <div className="text-neutral-300 mb-4 leading-relaxed text-lg text-justify tracking-wide">{children}</div>;
                                            },
                                            ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-2 text-neutral-300 pl-4">{children}</ul>,
                                            ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-2 text-neutral-300 pl-4">{children}</ol>,
                                            li: ({ children }) => <li className="pl-1 marker:text-neutral-500">{children}</li>,
                                            blockquote: ({ children }) => <blockquote className="border-l-4 border-blue-500 pl-4 italic my-6 text-neutral-400 bg-neutral-900/30 p-4 rounded-r">{children}</blockquote>,
                                            // Code
                                            code: ({ children }) => <code className="bg-neutral-800 px-1.5 py-0.5 rounded text-sm font-mono text-blue-300">{children}</code>,
                                            pre: ({ children }) => <pre className="bg-neutral-900 p-4 rounded-lg overflow-x-auto mb-6 text-sm border border-neutral-800">{children}</pre>,
                                            // HTML Elements Pass-through (Important for rehype-raw)
                                            div: ({ className, children, ...props }) => <div className={className} {...props}>{children}</div>,
                                            span: ({ className, children, ...props }) => <span className={className} {...props}>{children}</span>,
                                            table: ({ children, ...props }) => <div className="overflow-x-auto mb-8"><table className="w-full text-left border-collapse" {...props}>{children}</table></div>,
                                            thead: ({ children, ...props }) => <thead className="bg-neutral-900 text-neutral-200 uppercase text-xs font-bold tracking-wider" {...props}>{children}</thead>,
                                            tbody: ({ children, ...props }) => <tbody className="divide-y divide-neutral-800" {...props}>{children}</tbody>,
                                            tr: ({ children, ...props }) => <tr className="hover:bg-neutral-800/50 transition-colors" {...props}>{children}</tr>,
                                            th: ({ children, ...props }) => <th className="p-4 border-b border-neutral-700 whitespace-nowrap" {...props}>{children}</th>,
                                            // Images
                                            img: ({ src, alt, ...props }) => {
                                                // console.log("[UnifiedDigestViewer] Rendering Image:", src);
                                                return (
                                                    <span className="block my-8 relative group">
                                                        <img
                                                            src={src}
                                                            alt={alt || "Digest Illustration"}
                                                            className="w-full max-w-2xl mx-auto rounded-lg shadow-2xl border border-neutral-800 transition-transform group-hover:scale-[1.01] block"
                                                            loading="lazy"
                                                            onError={(e) => {
                                                                console.error("[UnifiedDigestViewer] Image Load Failed:", src);
                                                                e.currentTarget.style.display = 'none';
                                                            }}
                                                            {...props}
                                                        />
                                                        {alt && <span className="block text-center text-xs text-neutral-500 mt-2 italic">{alt}</span>}
                                                    </span>
                                                );
                                            },
                                            td: ({ children, ...props }) => <td className="p-4 text-neutral-300 align-top" {...props}>{children}</td>,
                                            details: ({ children, ...props }) => <details className="mb-4 group bg-neutral-900/30 rounded-lg border border-neutral-800 overflow-hidden" {...props}>{children}</details>,
                                            summary: ({ children, ...props }) => <summary className="cursor-pointer p-3 font-bold text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors select-none" {...props}>{children}</summary>,
                                        }}
                                    >
                                        {(digestData?.digest || digestData?.summary_markdown || "")
                                            .replace(/```(?:html|markdown)?\s*([\s\S]*?)\s*```/yi, '$1') // Greedy strip of outer code blocks
                                            .replace(/^#\s+.+$/m, '')  // Remove duplicate top-level title
                                            .replace(/\[([\d,\s]+)\]/g, (match: string, group: string) => {
                                                // Handle multiple citations like [1, 5, 28] by formatting as markdown: [1](citation:1), [5](citation:5)...
                                                // We wrap the whole thing in a blue-styled span text so the brackets are colored too?
                                                // User said: "keep the brackets and commas".
                                                // Let's output pure markdown with styling.
                                                // We can use an HTML span to wrap the whole block if we want the brackets blue too, 
                                                // OR just let the brackets be text and the numbers be links.
                                                // The user previously saw "square brackets... superscript".
                                                // Let's match the request: "remove superscript, keep brackets and commas".
                                                // We'll generate: <span class="text-blue-400 font-bold ml-0.5">[</span><a href="citation:1">1</a>, <a href="citation:2">2</a><span class="text-blue-400 font-bold">]</span>

                                                const links = group.split(',')
                                                    .map((n: string) => {
                                                        const num = n.trim();
                                                        return `[${num}](citation:${num})`;
                                                    })
                                                    .join(', ');

                                                // We wrap the whole thing in a span to give the brackets color, if desired?
                                                // Let's just output text brackets + markdown links for maximum stability.
                                                // If we want the brackets blue, we can wrap in HTML span.
                                                return `<span class="text-blue-400 font-bold ml-0.5">[${links}]</span>`;
                                            })
                                            // Strip 4+ spaces indentation (which triggers code blocks) but preserve structure
                                            .replace(/^[ \t]{4,}/gm, '')
                                            .trim()}
                                    </ReactMarkdown>
                                );
                            })()}
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
                                                    className={`relative group bg-neutral-900/50 border border-neutral-800 p-4 rounded-lg flex justify-between items-start cursor-pointer hover:bg-neutral-800 transition-colors ${selectedKeyword === kw ? 'ring-2 ring-blue-500' : ''}`}
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        console.log("[UnifiedDigestViewer] Clicked Keyword (Column):", kw?.word);
                                                        setSelectedKeyword(kw);
                                                    }}
                                                    onMouseEnter={(e) => setHoveredKeywordData({ kw, rect: e.currentTarget.getBoundingClientRect() })}
                                                    onMouseLeave={() => setHoveredKeywordData(null)}
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
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                console.log("[UnifiedDigestViewer] Clicked Keyword (Cloud):", kw?.word);
                                                setSelectedKeyword(kw);
                                            }}
                                            className={`relative group px-4 py-2 rounded-full border ${colorClass} transition-all hover:scale-110 cursor-pointer ${selectedKeyword === kw ? 'ring-2 ring-blue-500 bg-black' : ''}`}
                                            style={{ fontSize: `${Math.max(0.8, size)}rem` }}
                                            onMouseEnter={(e) => setHoveredKeywordData({ kw, rect: e.currentTarget.getBoundingClientRect() })}
                                            onMouseLeave={() => setHoveredKeywordData(null)}
                                        >
                                            {displayWord}
                                        </div>
                                    );
                                })}
                            </div>
                        )
                    ) : isAnalyzing ? (
                        <div className="flex flex-col items-center justify-center py-20 text-neutral-400">
                            <div className="relative w-16 h-16 mb-6">
                                <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full animate-ping"></div>
                                <div className="absolute inset-0 border-4 border-t-blue-500 rounded-full animate-spin"></div>
                                <Sparkles className="absolute inset-0 m-auto text-blue-400 w-6 h-6 animate-pulse" />
                            </div>
                            <div className="text-lg font-bold text-blue-300 mb-2">Analyzing Intelligence</div>
                            <div className="text-sm text-neutral-500 animate-pulse">Extracting entities & sentiments...</div>
                        </div>
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
                                {(selectedKeyword.sources || []).map((s: any, i: number) => {
                                    // Handle String vs Object source
                                    const url = typeof s === 'string' ? s : s?.url;
                                    if (!url) return null;

                                    return (
                                        <li key={i}>
                                            <a
                                                href={url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="block p-3 rounded-lg bg-neutral-950 border border-neutral-800 hover:border-blue-700 hover:bg-blue-900/10 transition-colors group"
                                                onClick={(e) => e.stopPropagation()} // Prevent closing modal on link click
                                            >
                                                <div className="text-sm text-blue-300 font-medium line-clamp-2 group-hover:text-blue-200">
                                                    {(() => {
                                                        try {
                                                            // Use object title if available, else find in articles
                                                            if (typeof s === 'object' && s.title) return s.title;

                                                            const article = digestData?.articles?.find((a: any) => a.url === url);
                                                            if (article && article.title) return article.title;
                                                            return new URL(url).hostname;
                                                        } catch { return "Source Detail"; }
                                                    })()}
                                                </div>
                                                <div className="text-xs text-neutral-600 mt-1 truncate">
                                                    {(() => {
                                                        try { return new URL(url).hostname; } catch { return 'Source'; }
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


            {/* Fixed Analytics Tooltip */}
            {hoveredKeywordData && <AnalyticsTooltip data={hoveredKeywordData} isTranslated={isAnalyticsTranslated} onClose={() => setHoveredKeywordData(null)} />}

        </div >
    );
}
