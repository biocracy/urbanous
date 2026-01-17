'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import DigestReportRenderer from '@/components/DigestReportRenderer';
import ReactMarkdown from 'react-markdown';
import { Loader2, Globe, Calendar, ArrowRight, Languages, Sparkles, Check, Copy } from 'lucide-react';
import Link from 'next/link';

export default function PublicDigestPage() {
    const params = useParams();
    const slug = params?.slug as string;

    const [digest, setDigest] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'digest' | 'articles' | 'analytics'>('articles');

    // Analytics State
    const [isAnalyticsTranslated, setIsAnalyticsTranslated] = useState(false);
    const [analyticsViewMode, setAnalyticsViewMode] = useState<'cloud' | 'columns'>('cloud');
    const [activeTooltip, setActiveTooltip] = useState<any>(null);
    const [isTooltipLocked, setIsTooltipLocked] = useState(false);
    const hoverTimeout = useRef<NodeJS.Timeout | null>(null);

    // Article Translation State
    const [isArticlesTranslated, setIsArticlesTranslated] = useState(false);
    const [isTranslating, setIsTranslating] = useState(false);

    const handleTranslateArticles = async () => {
        if (isArticlesTranslated) {
            setIsArticlesTranslated(false); // Toggle Off
            return;
        }

        setIsTranslating(true);
        try {
            const res = await api.post(`/digests/public/${slug}/translate_articles`);
            if (res.data.status === 'success' || res.data.status === 'already_translated') {
                if (res.data.articles) {
                    setDigest((prev: any) => ({ ...prev, articles: res.data.articles }));
                }
                setIsArticlesTranslated(true);
            }
        } catch (e) {
            console.error("Translation fail", e);
            alert("Translation failed. Please try again.");
        } finally {
            setIsTranslating(false);
        }
    };

    useEffect(() => {
        if (!slug) return;

        const fetchPublicDigest = async () => {
            try {
                // Use the public endpoint
                const res = await api.get(`/digests/public/${slug}`);
                setDigest(res.data);

                // Auto-detect existing translations
                const hasTranslations = res.data.articles?.some((a: any) => !!a.translated_title);
                if (hasTranslations) {
                    setIsArticlesTranslated(true);
                }
            } catch (err: any) {
                console.error("Fetch failed", err);
                setError("Digest not found or private.");
            } finally {
                setLoading(false);
            }
        };

        fetchPublicDigest();
    }, [slug]);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="animate-spin text-blue-500" size={48} />
                    <p className="text-slate-400 font-mono">Loading Urbanous Report...</p>
                </div>
            </div>
        );
    }

    if (error || !digest) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
                <div className="text-center">
                    <h1 className="text-4xl font-bold mb-4 text-slate-200">404</h1>
                    <p className="text-xl text-red-400 mb-8">{error || "Digest Unavailable"}</p>
                    <Link href="/" className="px-6 py-2 bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors">
                        Go to Urbanous Home
                    </Link>
                </div>
            </div>
        );
    }

    // Prepare keywords for Analytics
    const analyticsKeywords = digest.analysis_source || [];

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
            {/* Header */}
            <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {/* Logo Mask Solution */}
                        <div
                            className="h-8 w-6 bg-gradient-to-r from-fuchsia-400 to-indigo-400"
                            style={{
                                maskImage: 'url(/logo-mask-v5.png)',
                                maskSize: 'contain',
                                maskRepeat: 'no-repeat',
                                maskPosition: 'center',
                                WebkitMaskImage: 'url(/logo-mask-v5.png)',
                                WebkitMaskSize: 'contain',
                                WebkitMaskRepeat: 'no-repeat',
                                WebkitMaskPosition: 'center'
                            }}
                        />
                        <span className="font-bold text-xl tracking-tight text-slate-100">
                            URBANOUS <span className="text-blue-500 text-sm font-normal ml-1 opacity-70">Intelligence Report</span>
                        </span>
                    </div>

                    <Link href="/" className="text-xs font-bold text-slate-400 hover:text-white flex items-center gap-1 group">
                        Create your own
                        <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                    </Link>
                </div>
            </header>

            <main className="container mx-auto px-4 py-8 max-w-5xl">
                {/* Meta Header */}
                <div className="mb-8">
                    <div className="flex items-center gap-2 mb-2">
                        {digest.city && (
                            <span className="bg-blue-900/30 text-blue-400 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider border border-blue-800/50">
                                {digest.city}
                            </span>
                        )}
                        <span className="text-slate-500 text-xs font-mono flex items-center gap-1">
                            <Calendar size={12} />
                            {(() => {
                                const end = new Date(digest.created_at);
                                const start = new Date(end);
                                if (digest.timeframe === '24h') start.setDate(end.getDate() - 1);
                                if (digest.timeframe === '3days') start.setDate(end.getDate() - 3);
                                if (digest.timeframe === '1week') start.setDate(end.getDate() - 7);

                                const fmt = (d: Date) => `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}.${d.getFullYear()}`;
                                return `${fmt(start)} - ${fmt(end)}`;
                            })()}
                        </span>
                    </div>

                    <h1 className="text-3xl md:text-4xl font-bold text-white mb-4 bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                        {digest.title}
                    </h1>

                    <div className="flex justify-between items-end">
                        <div className="flex flex-col gap-2">
                            {/* Navigation Tabs */}
                            <div className="flex gap-1 bg-slate-900/50 p-1 rounded-lg w-fit border border-slate-800">
                                {['articles', 'digest', 'analytics'].map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab as any)}
                                        className={`px-4 py-1.5 rounded-md text-sm font-bold capitalize transition-all ${activeTab === tab
                                            ? 'bg-blue-600 text-white shadow-lg'
                                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                                            }`}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Content Container */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 md:p-8 shadow-2xl min-h-[500px]">
                    {activeTab === 'articles' && (
                        <>
                            <div className="flex justify-end mb-4">
                                <button
                                    onClick={handleTranslateArticles}
                                    disabled={isTranslating}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold transition-all border ${isArticlesTranslated ? 'bg-indigo-900/30 text-indigo-300 border-indigo-700' : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700'}`}
                                >
                                    {isTranslating ? <Loader2 size={14} className="animate-spin" /> : <Languages size={14} />}
                                    {isTranslating ? "Translating..." : (isArticlesTranslated ? "Show Original" : "Translate Titles")}
                                </button>
                            </div>
                            <DigestReportRenderer
                                {...digest}
                                isTranslated={isArticlesTranslated}
                                selectedUrls={new Set()} // Read-only
                                onToggle={() => { }}
                                onAssess={() => { }}
                                onDebug={() => { }}
                            />
                        </>
                    )}

                    {activeTab === 'digest' && (
                        <div className="prose prose-invert prose-slate max-w-none">
                            <ReactMarkdown
                                urlTransform={(url) => url}
                                components={{
                                    h1: ({ node, ...props }) => <h1 className="text-3xl font-extrabold text-white mb-6 border-b border-white/10 pb-4 mt-6" {...props} />,
                                    h2: ({ node, ...props }) => <h2 className="text-2xl font-bold text-blue-200 mt-10 mb-5 border-l-4 border-blue-500 pl-4" {...props} />,
                                    h3: ({ node, ...props }) => <h3 className="text-lg font-bold text-indigo-300 mt-6 mb-2 uppercase tracking-wide" {...props} />,
                                    p: ({ node, ...props }) => <p className="text-base text-slate-300 leading-relaxed mb-6 text-justify" {...props} />,
                                    ul: ({ node, ...props }) => <ul className="list-disc list-outside ml-5 mb-6 space-y-2 text-slate-300" {...props} />,
                                    li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                                    blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-slate-600 pl-4 italic text-slate-400 my-6 bg-slate-800/30 py-2 rounded-r" {...props} />,
                                    strong: ({ node, ...props }) => <strong className="text-amber-400 font-bold" {...props} />,
                                    a: ({ node, ...props }) => {
                                        const href = props.href || '';
                                        if (href.startsWith('citation:')) {
                                            const index = parseInt(href.split(':')[1]);
                                            const article = digest.articles?.[index - 1];
                                            const title = article ? (article.title || 'Source') : `Source ${index}`;
                                            const url = article ? article.url : '';
                                            return (
                                                <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline align-super text-xs font-bold ml-0.5" title={title}>[{index}]</a>
                                            );
                                        }
                                        return <a className="text-blue-400 hover:underline" target="_blank" {...props} />;
                                    }
                                }}
                            >
                                {digest.summary_markdown.replace(/\[(\d+)\]/g, '[$1](citation:$1)')}
                            </ReactMarkdown>
                        </div>
                    )}

                    {activeTab === 'analytics' && (
                        <div className="flex flex-col h-full">
                            {/* Analytics Controls */}
                            <div className="flex justify-end gap-3 mb-6">
                                <button
                                    onClick={() => setIsAnalyticsTranslated(!isAnalyticsTranslated)}
                                    className={`px-3 py-1.5 flex items-center gap-2 text-xs font-bold rounded-lg transition-all ${isAnalyticsTranslated ? 'bg-indigo-600 text-white shadow' : 'bg-slate-800 text-slate-400 hover:text-white border border-slate-700'}`}
                                >
                                    <Languages size={14} /> Translate
                                </button>
                                <div className="flex bg-slate-800 rounded-lg p-0.5 border border-slate-700">
                                    <button
                                        onClick={() => setAnalyticsViewMode('cloud')}
                                        className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${analyticsViewMode === 'cloud' ? 'bg-slate-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
                                    >
                                        ☁️ Cloud
                                    </button>
                                    <button
                                        onClick={() => setAnalyticsViewMode('columns')}
                                        className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${analyticsViewMode === 'columns' ? 'bg-slate-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
                                    >
                                        ||| Columns
                                    </button>
                                </div>
                            </div>

                            {analyticsKeywords.length === 0 ? (
                                <div className="text-slate-500 italic text-center py-20">No analytics data available.</div>
                            ) : (
                                <>
                                    {analyticsViewMode === 'cloud' ? (
                                        <div className="flex flex-wrap gap-3 content-start justify-center py-4">
                                            {analyticsKeywords.map((kw: any, i: number) => {
                                                const displayWord = (isAnalyticsTranslated && kw.translation) ? kw.translation : kw.word;
                                                const scale = 0.8 + ((kw.importance || 50) / 100) * 1.5;
                                                let bg = "bg-slate-800 border-slate-600 text-slate-300";
                                                if (kw.sentiment === 'Positive') bg = "bg-green-950/40 border-green-600/50 text-green-300 shadow-[0_0_10px_rgba(34,197,94,0.1)]";
                                                if (kw.sentiment === 'Negative') bg = "bg-red-950/40 border-red-600/50 text-red-300 shadow-[0_0_10px_rgba(239,68,68,0.1)]";
                                                if (kw.importance > 85) bg += " ring-1 ring-white/20 font-bold";

                                                return (
                                                    <div
                                                        key={i}
                                                        className={`relative group cursor-pointer px-4 py-2 rounded-xl border ${bg} transition-all duration-300 hover:scale-110 hover:shadow-xl hover:z-20`}
                                                        style={{ fontSize: `${Math.max(0.75, scale)}rem` }}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            const rect = e.currentTarget.getBoundingClientRect();
                                                            setActiveTooltip({
                                                                word: kw.word,
                                                                kw,
                                                                left: rect.left + rect.width / 2,
                                                                top: rect.top
                                                            });
                                                            setIsTooltipLocked(true);
                                                        }}
                                                        onMouseEnter={(e) => {
                                                            if (isTooltipLocked) return;
                                                            const rect = e.currentTarget.getBoundingClientRect();
                                                            setActiveTooltip({
                                                                word: kw.word,
                                                                kw,
                                                                left: rect.left + rect.width / 2,
                                                                top: rect.top
                                                            });
                                                        }}
                                                        onMouseLeave={() => !isTooltipLocked && setActiveTooltip(null)}
                                                    >
                                                        {displayWord}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border border-slate-700 rounded-xl overflow-hidden bg-slate-900/50 min-h-[500px]">
                                            {['Positive', 'Neutral', 'Negative'].map((sent) => (
                                                <div key={sent} className="flex flex-col border-b md:border-b-0 md:border-r border-slate-700/50 last:border-0">
                                                    <div className={`p-3 text-center font-bold uppercase text-sm tracking-wider sticky top-0 bg-slate-900/90 backdrop-blur z-10 ${sent === 'Positive' ? 'text-green-400 border-b border-green-900/30' : sent === 'Negative' ? 'text-red-400 border-b border-red-900/30' : 'text-slate-400 border-b border-slate-700/30'}`}>
                                                        {sent}
                                                    </div>
                                                    <div className="p-3 space-y-2 overflow-y-auto max-h-[600px] custom-scrollbar">
                                                        {analyticsKeywords.filter((k: any) => k.sentiment === sent).sort((a: any, b: any) => b.importance - a.importance).map((kw: any, i: number) => (
                                                            <div
                                                                key={i}
                                                                className="bg-slate-800/40 p-3 rounded border border-white/5 hover:bg-slate-800 transition-colors cursor-pointer"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    const rect = e.currentTarget.getBoundingClientRect();
                                                                    setActiveTooltip({
                                                                        word: kw.word,
                                                                        kw,
                                                                        left: rect.left + rect.width / 2,
                                                                        top: rect.top
                                                                    });
                                                                    setIsTooltipLocked(true);
                                                                }}
                                                                onMouseEnter={(e) => {
                                                                    if (isTooltipLocked) return;
                                                                    const rect = e.currentTarget.getBoundingClientRect();
                                                                    setActiveTooltip({
                                                                        word: kw.word,
                                                                        kw,
                                                                        left: rect.left + rect.width / 2,
                                                                        top: rect.top
                                                                    });
                                                                }}
                                                                onMouseLeave={() => !isTooltipLocked && setActiveTooltip(null)}
                                                            >
                                                                <div className="flex justify-between items-start">
                                                                    <span className="font-bold text-slate-200 text-sm">
                                                                        {isAnalyticsTranslated && kw.translation ? kw.translation : kw.word}
                                                                    </span>
                                                                    <span className="text-[10px] text-slate-500 font-mono">{kw.importance}</span>
                                                                </div>
                                                                {isAnalyticsTranslated && kw.translation && kw.translation !== kw.word && (
                                                                    <div className="text-xs text-slate-500 italic">{kw.word}</div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Tooltip */}
                                    {activeTooltip && (
                                        <div
                                            className="fixed z-[100] bg-slate-900/95 backdrop-blur border border-slate-600 rounded-xl p-4 shadow-2xl w-72 transform -translate-x-1/2 -translate-y-full mb-2 pointer-events-auto"
                                            style={{ left: activeTooltip.left, top: activeTooltip.top - 10 }}
                                        >
                                            <div className="font-bold text-white mb-1 flex justify-between items-start">
                                                <span>{activeTooltip.kw.word}</span>
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${activeTooltip.kw.sentiment === 'Positive' ? 'bg-green-900 text-green-400' : activeTooltip.kw.sentiment === 'Negative' ? 'bg-red-900 text-red-400' : 'bg-slate-700 text-slate-400'}`}>
                                                        {activeTooltip.kw.sentiment}
                                                    </span>
                                                    {isTooltipLocked && (
                                                        <button
                                                            className="text-slate-400 hover:text-white"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                setIsTooltipLocked(false);
                                                                setActiveTooltip(null);
                                                            }}
                                                        >
                                                            ✕
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="text-xs text-slate-400 mb-2 font-mono">Importance: {activeTooltip.kw.importance}</div>
                                            <div className="text-[10px] text-slate-500 uppercase font-bold mb-1">Sources</div>
                                            <ul className="space-y-1">
                                                {(activeTooltip.kw.sources || []).slice(0, 3).map((s: any, idx: number) => (
                                                    <li key={idx} className="truncate">
                                                        <a
                                                            href={s.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-blue-400 hover:text-blue-300 hover:underline text-xs block truncate"
                                                            title={s.title || s.url}
                                                        >
                                                            • {s.title || s.url}
                                                        </a>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-800 mt-12 py-8 text-center text-slate-500 text-sm">
                <p>Generated by <strong>Urbanous AI</strong> • Open Source News Intelligence</p>
            </footer>
        </div>
    );
}
