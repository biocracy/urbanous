'use client';

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';


// Utility: Simple Debounce (avoiding lodash dependency issues)
function debounce<F extends (...args: any[]) => any>(func: F, waitFor: number) {
    let timeout: ReturnType<typeof setTimeout> | null = null;

    const debounced = (...args: Parameters<F>) => {
        if (timeout !== null) {
            clearTimeout(timeout);
        }
        timeout = setTimeout(() => func(...args), waitFor);
    };

    return debounced as (...args: Parameters<F>) => void;
}
import * as turf from '@turf/turf';
import api from '@/lib/api'; // Use the axios instance with Auth interceptor
import { useAuthStore } from '@/lib/store';
import {
    Settings, X, Maximize2, Minimize2, ChevronRight, ChevronLeft,
    Share2, Download, Copy, Check, ExternalLink, Search, Filter,
    LayoutGrid, List, Map as MapIcon, Globe as GlobeIcon,
    AlertTriangle, Shield, ShieldAlert, ShieldCheck, Info,
    Play, Pause, RotateCcw, Calendar, Trash2,
    Sliders, Loader2, Sparkles, Languages, FileText, Coffee,
    Plus, Minus
} from 'lucide-react';
import ScraperDebugger from './ScraperDebugger';
import ReactMarkdown from 'react-markdown';
import { CAPITALS } from '../utils/capitals';
import DigestReportRenderer from './DigestReportRenderer';
import SettingsModal from './SettingsModal';
import UIMarquee from './UIMarquee';
import UnifiedDigestViewer from './UnifiedDigestViewer';
import * as THREE from 'three';
import { CITY_ICONS, GENERIC_CITY_ICON } from '../data/landmarks';

// Dynamically import Globe to avoid SSR issues
const Globe = dynamic(() => import('react-globe.gl'), {
    ssr: false,
    loading: () => <div className="flex items-center justify-center h-full text-white">Loading Clean Globe...</div>
});

interface NewsGlobeProps {
    onCountrySelect?: (countryName: string, countryCode: string) => void;
    disableScrollZoom?: boolean;
    isAtTop?: boolean;
}

const isDateCurrent = (extractedDate: string) => {
    if (!extractedDate) return false;
    try {
        const d = new Date(extractedDate);
        if (isNaN(d.getTime())) return false;
        const now = new Date();
        const diff = now.getTime() - d.getTime();
        // Fresh if within 72 hours (3 days)
        return diff < 72 * 60 * 60 * 1000;
    } catch { return false; }
};


// STATIC ACCESSORS (Optimization: Prevent props change on every render)
const getLat = (d: any) => d.lat;
const getLng = (d: any) => d.lng;
const getRadius = (d: any) => d.radius;
const getLabelSize = (d: any) => d.radius * 1.3;
const getLabelColor = (d: any) => d.opacity && d.opacity < 1 ? 'transparent' : 'black';
const getRingMaxR = (d: any) => d.maxR;
const getRingColor = (d: any) => d.color || 'rgba(255,255,255,0.1)';
const getPathPoints = (d: any) => [[d.startLng, d.startLat], [d.endLng, d.endLat]];
const getPathPointLat = (p: any) => p[1];
const getPathPointLng = (p: any) => p[0];
const getPathColor = (d: any) => d.color;

export default function NewsGlobe({ onCountrySelect, disableScrollZoom = false, isAtTop = true }: NewsGlobeProps) {
    console.log("[NewsGlobe] Render Cycle"); // Debug Log
    const globeEl = useRef<any>(null);
    const { isAuthenticated } = useAuthStore();

    // Initial View managed by onGlobeReady

    const [countries, setCountries] = useState({ features: [] });
    const [selectedCountry, setSelectedCountry] = useState<any | null>(null);
    const [cities, setCities] = useState<any[]>([]);
    const [hoverPoint, setHoverPoint] = useState<any | null>(null);
    const [digestData, setDigestData] = useState<any>(null);
    const [isReportSaved, setIsReportSaved] = useState(false); // Track unsaved changes
    const [isMetaPressed, setIsMetaPressed] = useState(false); // Track Cmd/Ctrl key

    // Key Listener for Meta/Ctrl
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Meta' || e.key === 'Control') setIsMetaPressed(true);
        };
        const handleKeyUp = (e: KeyboardEvent) => {
            if (e.key === 'Meta' || e.key === 'Control') setIsMetaPressed(false);
        };

        window.addEventListener('keydown', handleKeyDown);
        window.addEventListener('keyup', handleKeyUp);
        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('keyup', handleKeyUp);
        };
    }, []);
    const [isTranslateActive, setIsTranslateActive] = useState(false);
    const [debuggerConfig, setDebuggerConfig] = useState<{ isOpen: boolean; url: string; domain: string }>({
        isOpen: false,
        url: '',
        domain: ''
    });

    // Discovery Features
    const [discoveredCities, setDiscoveredCities] = useState<string[]>([]);
    const [allOutlets, setAllOutlets] = useState<any[]>([]);
    const [selectedCityOutlets, setSelectedCityOutlets] = useState<any[]>([]);
    const [selectedCityName, setSelectedCityName] = useState<string | null>(null);
    const [selectedCityData, setSelectedCityData] = useState<any>(null);
    const [selectedCityCoords, setSelectedCityCoords] = useState<{ lat: number; lng: number }>({ lat: 46.7712, lng: 23.6236 });

    interface Outlet {
        id?: number;
        name: string;
        url: string;
        type: string;
        origin?: string;
        popularity?: number; // 1-10
        focus?: string; // Local, National
    }

    interface AnalyticsKeyword {
        word: string;
        translation?: string;
        importance: number;
        sentiment: 'Positive' | 'Negative' | 'Neutral';
        source_ids: string[];
    }

    // Use centralized version constant
    const APP_VERSION = "0.160";

    // UI States
    const [isDiscovering, setIsDiscovering] = useState(false);
    const [showOutletPanel, setShowOutletPanel] = useState(false);
    const [showCloseConfirm, setShowCloseConfirm] = useState(false); // Custom Close Dialog
    const [showAddForm, setShowAddForm] = useState(false);
    const [activeTab, setActiveTab] = useState<'manual' | 'import'>('import');
    const [newOutlet, setNewOutlet] = useState({ name: '', url: '', type: 'Online' });
    const [importUrl, setImportUrl] = useState('');
    const [importInstructions, setImportInstructions] = useState('');
    const [isImporting, setIsImporting] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [quotaError, setQuotaError] = useState(false);

    // Search State
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [highlightedCityId, setHighlightedCityId] = useState<string | null>(null); // For Halo effect

    // Aggregation Agent State
    const [selectedCategory, setSelectedCategory] = useState<string>('Politics');
    const [selectedTimeframe, setSelectedTimeframe] = useState<string>('24h');
    const [analyticsMode, setAnalyticsMode] = useState<'source' | 'digest'>('source');
    const [activeTooltip, setActiveTooltip] = useState<{ word: string, data: any, rect: DOMRect | null, placement: 'top' | 'bottom' } | null>(null);
    const [isTooltipLocked, setIsTooltipLocked] = useState(false);
    const hoverTimeout = useRef<NodeJS.Timeout | null>(null);
    const [selectedOutletIds, setSelectedOutletIds] = useState<number[]>([]);
    const [isGeneratingDigest, setIsGeneratingDigest] = useState(false);
    const [cityInfo, setCityInfo] = useState<any>(null);

    const [vizMode, setVizMode] = useState<'3d' | '2d'>('3d');


    // Logging State for Digest Generation
    const [progressLog, setProgressLog] = useState('');

    const [isSaving, setIsSaving] = useState(false);
    const [isSharing, setIsSharing] = useState(false);
    const [copiedSlug, setCopiedSlug] = useState<string | null>(null);
    // Progress Tracking
    const [progress, setProgress] = useState({ current: 0, total: 0 });
    const [savedDigests, setSavedDigests] = useState<any[]>([]);
    const [activeSideTab, setActiveSideTab] = useState<'sources' | 'digests'>('sources');
    const [activeModalTab, setActiveModalTab] = useState<'articles' | 'digest' | 'analytics'>('articles');
    const [isGlobalSidebarOpen, setIsGlobalSidebarOpen] = useState(false);

    // Global Stream Filters
    const [globalStreamTab, setGlobalStreamTab] = useState<'stream' | 'my'>('stream');

    // Auth & User State
    const [currentUser, setCurrentUser] = useState<any>(null); // Load from /users/me
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    // Refresh user when settings close (to update username in UI if changed)
    useEffect(() => {
        if (!isSettingsOpen && isAuthenticated) {
            api.get('/users/me').then(res => setCurrentUser(res.data)).catch(err => console.error("Auth Error", err));
        }
    }, [isSettingsOpen, isAuthenticated]);

    // Helper: Mask Username
    const getOwnerName = (digest: any) => {
        if (!digest.owner_id) return "Unknown";
        if (currentUser && digest.owner_id === currentUser.id) return currentUser.username || "Me";
        if (digest.owner_is_visible) return digest.owner_username || "Anonymous";
        // Mask: u****e
        const u = digest.owner_username || "user";
        if (u.length <= 2) return u[0] + "*";
        return u[0] + "*".repeat(u.length - 2) + u[u.length - 1];
    };

    // Digest Summarization State
    const [selectedArticleUrls, setSelectedArticleUrls] = useState<Set<string>>(new Set());
    const [spamUrls, setSpamUrls] = useState<Set<string>>(new Set());
    const [digestSummary, setDigestSummary] = useState<string>("");
    const [isSummarizing, setIsSummarizing] = useState(false);

    // Analytics State
    const [analyticsKeywords, setAnalyticsKeywords] = useState<AnalyticsKeyword[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isAnalyticsTranslated, setIsAnalyticsTranslated] = useState(false);
    const [analyticsViewMode, setAnalyticsViewMode] = useState<'cloud' | 'columns'>('cloud');
    const [analyzingTickerText, setAnalyzingTickerText] = useState<string>('');
    const [digestFetchStatus, setDigestFetchStatus] = useState<string>('idle');
    const [isSpotlightOpen, setIsSpotlightOpen] = useState(false);
    const [spotlightQuery, setSpotlightQuery] = useState('');
    const [spotlightSelectedIndex, setSpotlightSelectedIndex] = useState(0);

    const handleToggleSelection = (url: string) => {
        setIsReportSaved(false); // Mark as modified
        const newSet = new Set(selectedArticleUrls);
        if (newSet.has(url)) newSet.delete(url);
        else newSet.add(url);
        setSelectedArticleUrls(newSet);
    };

    // Stable list of selected articles for Index-based citation
    const selectedArticlesList = useMemo(() => {
        if (!digestData?.articles) return [];

        // If user has actively selected articles (e.g. for re-summarization), use that subset.
        if (selectedArticleUrls.size > 0) {
            const subset = digestData.articles.filter((a: any) => selectedArticleUrls.has(a.url));
            // If subset is valid, return it. If empty (mismatch), fallback to full list to prevent crashes.
            if (subset.length > 0) return subset;
        }

        // Default: If no selection (Viewing Saved Digest), use the full stored article list associated with this digest.
        return digestData.articles;
    }, [digestData, selectedArticleUrls]);

    // Ticker Effect
    useEffect(() => {
        if (!isSummarizing || selectedArticlesList.length === 0) {
            setAnalyzingTickerText('');
            return;
        }
        let idx = 0;
        const interval = setInterval(() => {
            const art = selectedArticlesList[idx % selectedArticlesList.length];
            const title = art.title || "Article";
            setAnalyzingTickerText(`Analyzing: ${title.substring(0, 40)}...`);
            idx++;
        }, 150);
        return () => clearInterval(interval);
    }, [isSummarizing, selectedArticlesList]);

    const handleSmartSelect = () => {
        if (!digestData?.articles) return;
        const smartSet = new Set<string>();
        digestData.articles.forEach((a: any) => {
            const s = a.scores || {};
            let isGreenDate = s.is_fresh || (a.relevance_score > 0 && s.date > 0);

            // Fallback: Calculate freshness manually if scores missing (Stream Mode)
            if (!isGreenDate && a.date_str) {
                const artDate = new Date(a.date_str);
                const now = new Date();
                const diffMs = now.getTime() - artDate.getTime();
                const diffHours = diffMs / (1000 * 60 * 60);

                // Dynamic Cutoff based on Timeframe
                let limitHours = 30; // 24h + buffer
                if (selectedTimeframe === "3days") limitHours = 72 + 6;
                else if (selectedTimeframe === "1week") limitHours = 168 + 12;
                else if (selectedTimeframe === "1month") limitHours = 720 + 24;

                if (diffHours <= limitHours) {
                    isGreenDate = true;
                }
            }

            // AI Logic: Content Check > Title Check
            const aiVerdict = a.ai_verdict;

            // Check if we have a deep content assessment (Object)
            const isContentAssessment = typeof aiVerdict === 'object' && aiVerdict !== null;

            let shouldSelect = false;

            if (isContentAssessment) {
                // STRONG SIGNAL: If Content Check exists, we obey it strictly.
                // If is_politics is TRUE -> Select.
                // If FALSE -> Reject (even if title seemed ok).
                if (aiVerdict.is_politics) {
                    shouldSelect = true;
                }
            } else {
                // WEAK SIGNAL: Fallback to Title Check
                // "VERIFIED" string comes from the stream pipeline
                if (aiVerdict === "VERIFIED") {
                    shouldSelect = true;
                }
            }

            // Must satisfy Date + AI
            if (isGreenDate && shouldSelect) {
                smartSet.add(a.url);
            }
        });
        setSelectedArticleUrls(smartSet);
    };

    const handleGenerateBackendSummary = async () => {
        if (selectedArticleUrls.size === 0) return;
        setIsSummarizing(true);
        // setSummaryStream(""); // State does not exist
        setAnalyzingTickerText("Initializing AI...");

        // try {
        // Filter articles
        const articles = selectedArticlesList; // already filtered by memo

        // Build Context String
        // We only send title + snippet to save tokens, or full text if needed?
        // "Gather" usually implies we want them to be rewriting the summary based on these articles.
        // But here we are generating a summary OF the selected articles.

        // Current Backend `stream_digest` logic:
        // It expects `digest_id`? Or `articles`?
        // Actually `handleGenerateBackendSummary` calls `/outlets/stream_digest`.
        // Let's verify payload.

        const payload = {
            article_urls: Array.from(selectedArticleUrls),
            category: selectedCategory || "General",
            city: selectedCityName || "Bucharest"
        };

        // ... (rest of function is fine)

        setIsSummarizing(true);
        // "Gathering Articles..." text update
        // We handle the text in the button, but if there's a global loader, we can set it here.
        // For now, the user asked for text "somewhere". We updated the button text logic below.
        try {
            // Calculate Period Label
            const end = new Date();
            const start = new Date();
            const effectiveTimeframe = digestData.timeframe || selectedTimeframe;
            if (effectiveTimeframe === '3days') start.setDate(end.getDate() - 3);
            else if (effectiveTimeframe === '1week') start.setDate(end.getDate() - 7);
            else start.setDate(end.getDate() - 1);

            const fmt = (d: Date) => `${d.getDate()}.${d.getMonth() + 1}.${d.getFullYear()}`;
            const periodLabel = `${fmt(start)} - ${fmt(end)}`;

            // Merge existing and excluded to form the full pool
            const allArts = [...(digestData.articles || []), ...(digestData.excluded_articles || [])];
            // If we have duplicates (shouldn't happen but safety first), dedup by URL
            const uniqueArtsMap = new Map();
            allArts.forEach((a: any) => uniqueArtsMap.set(a.url, a));
            // Cast to array of any to satisfy type checker if needed, avoiding 'unknown'
            const uniquePool = Array.from(uniqueArtsMap.values());

            const selectedArts = uniquePool.filter((a: any) => selectedArticleUrls.has(a.url));
            const excludedArts = uniquePool.filter((a: any) => !selectedArticleUrls.has(a.url));

            const res = await api.post('/outlets/digest/summarize', {
                articles: selectedArts,
                category: selectedCategory,
                city: digestData.city || selectedCityName || "Global",
                timeframe_label: periodLabel
            });

            // CRITICAL: Update the local digest Data to reflect selected vs excluded
            setDigestData((prev: any) => prev ? ({ ...prev, articles: selectedArts, excluded_articles: excludedArts }) : null);

            setDigestSummary(res.data.summary);

            // Also clear selection since the new list is effectively "all selected" contextually,
            // or keep them selected visually? Keeping them is fine, but the indices now align 1:1.

            setActiveModalTab('digest');
        } catch (e) {
            console.error("Summarization failed", e);
            alert("Failed to generate summary");
        } finally {
            setIsSummarizing(false);
        }
    };

    const handleGenerateAnalytics = async () => {
        setIsAnalyzing(true);
        try {
            // Analyze selected articles if any, otherwise all available articles
            let targetArticles = digestData.articles;
            if (selectedArticleUrls.size > 0) {
                targetArticles = digestData.articles.filter((a: any) => selectedArticleUrls.has(a.url));
            }

            if (!targetArticles || targetArticles.length === 0) {
                alert("No articles available to analyze.");
                return;
            }

            const res = await api.post('/outlets/digest/analytics', {
                articles: targetArticles,
                category: selectedCategory,
                city: selectedCityName || "Global"
            });
            setAnalyticsKeywords(res.data.keywords);
        } catch (e) {
            console.error("Analytics failed", e);
            alert("Failed to generate analytics");
        } finally {
            setIsAnalyzing(false);
        }
    };

    useEffect(() => {
        if (isAuthenticated && (activeSideTab === 'digests' || isGlobalSidebarOpen)) {
            fetchSavedDigests();
        }
    }, [activeSideTab, isGlobalSidebarOpen, isAuthenticated]);

    // Spotlight Search Listener
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.code === 'Space') {
                const tag = (e.target as HTMLElement).tagName;
                if (['INPUT', 'TEXTAREA'].includes(tag) || (e.target as HTMLElement).isContentEditable) return;

                e.preventDefault();
                setIsSpotlightOpen(true);
            }
            if (e.code === 'Escape') {
                setIsSpotlightOpen(false);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isSpotlightOpen]);

    const fetchSavedDigests = async () => {
        if (!currentUser) return;
        try {
            console.log("DIGEST_DEBUG: Fetching saved digests...");
            const res = await api.get('/digests');
            console.log("DIGEST_DEBUG: Fetched Saved Digests:", res.data);
            setSavedDigests(res.data);
            setDigestFetchStatus(`success (${res.data.length} items)`);
        } catch (err: any) {
            console.error("Failed to fetch digests", err);
            // Robust logging
            console.log("DIGEST_DEBUG: Digest fetch error details:", err.response?.data || err.message);
            setDigestFetchStatus(`error: ${err.message}`);
        }
    };
    // Scraper Debugger State
    const [scraperDebuggerOpen, setScraperDebuggerOpen] = useState(false);
    const [debugTarget, setDebugTarget] = useState<{ url: string, domain: string } | null>(null);

    const handleOpenDebugger = (url: string) => {
        try {
            const domain = new URL(url).hostname.replace('www.', '');
            setDebugTarget({ url, domain });
            setScraperDebuggerOpen(true);
        } catch (e) {
            console.error("Invalid URL for debugger", url);
        }
    };




    const handleRuleSaving = () => {
        if (!debugTarget || !digestData) return;

        let newDigestHtml = digestData.digest;
        if (typeof document !== 'undefined') {
            try {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = newDigestHtml;

                const triggers = tempDiv.querySelectorAll(`.scraper-debug-trigger[data-url="${debugTarget.url}"]`);
                triggers.forEach((trigger: any) => {
                    if (trigger.previousElementSibling) {
                        trigger.previousElementSibling.innerHTML = "⏳";
                        trigger.previousElementSibling.className = "animate-spin inline-block";
                    }
                });

                newDigestHtml = tempDiv.innerHTML;
            } catch (e) { console.warn("Saving spinner patch failed", e); }
        }

        setDigestData({
            ...digestData,
            digest: newDigestHtml
        });
    }

    // Actually, backend sets SCORE to 0 if invalid. Let's use that signal for reliability.
    const isArticleValid = (art: any) => art.relevance_score > 0;

    const handleShareDigest = async () => {
        if (!digestData?.id) {
            alert("Please save the digest to your library before sharing.");
            return;
        }
        setIsSharing(true);
        try {
            // URL: /outlets/digests/{id}/share (Standardized)
            const res = await api.post(`/outlets/digests/${digestData.id}/share`);
            const slug = res.data.slug;

            setDigestData((prev: any) => ({ ...prev, is_public: true, public_slug: slug }));
            setSavedDigests(prev => prev.map(d => d.id === digestData.id ? { ...d, is_public: true, public_slug: slug } : d));
        } catch (err: any) {
            alert(`Sharing failed: ${err.message}`);
        } finally {
            setIsSharing(false);
        }
    };

    const handleDeleteDigest = async (id: number) => {
        if (!confirm("Are you sure you want to delete this digest?")) return;
        try {
            await api.delete(`/digests/${id}`);
            setSavedDigests(prev => prev.filter(d => d.id !== id));
            if (digestData?.id === id) {
                setDigestData(null); // Close if currently viewing
                setActiveModalTab('articles');
            }
        } catch (e: any) {
            console.error("Delete failed", e);
            alert(`Delete failed: ${e.response?.data?.detail || e.message}`);
        }
    };

    const handleSaveDigest = async () => {
        if (!digestData) return;
        setIsSaving(true);
        try {
            // Extract Title from Markdown (First line # Title)
            const contentToCheck = digestSummary || digestData.digest;
            const titleMatch = contentToCheck.match(/^# (.*)$/m);
            // Default to empty string so backend knows to generate one if needed, 
            // OR use a very generic one that triggers the backend check ("Digest")
            const title = titleMatch ? titleMatch[1] : `Daily ${selectedCategory} Digest`;

            const payload = {
                title: title,
                category: digestData.category || selectedCategory,
                city: digestData.city || selectedCityName || "Global",
                timeframe: digestData.timeframe || selectedTimeframe,
                summary_markdown: digestSummary || digestData.digest,
                articles: digestData.articles,
                selected_article_urls: Array.from(selectedArticleUrls),
                analysis_source: analyticsKeywords.length > 0 ? analyticsKeywords : (digestData.analysis_source || []),
                analysis_digest: digestData.analysis_digest || null
            };

            let savedItem;
            if (digestData.id) {
                // Update existing
                const res = await api.put(`/digests/${digestData.id}`, payload);
                savedItem = res.data;
            } else {
                // Create new
                const res = await api.post('/digests', payload);
                savedItem = res.data;
            }

            // Sync ID back to current view to prevent duplicates on next save
            setDigestData((prev: any) => ({ ...prev, id: savedItem.id }));

            await fetchSavedDigests();
            setIsReportSaved(true); // Mark as saved
            alert("Digest saved!");
            // Show toast? relying on button state for now
        } catch (err: any) {
            console.error("Failed to save digest", err);
            const msg = err.response?.data?.detail || "Failed to save digest.";
            setErrorMessage(msg);
            alert(`Error: ${msg}`); // Force user visibility
        } finally {
            setIsSaving(false);
        }
    };

    const handleDownloadDigest = () => {
        if (!digestData) return;

        // Extract Title
        let title = "OpenNews Digest";
        const titleMatch = (digestSummary || digestData.digest).match(/^# (.*)$/m);
        if (titleMatch) title = titleMatch[1];
        else title = `${selectedCategory} Digest - ${new Date().toLocaleDateString()}`;

        const filename = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.html`;

        // 1. Prepare Summary & Linkify Citations
        // Turn [n] into markdown links [n](#source-n) if they aren't already links.
        // Regex: Matches [n] not followed by (.
        let summaryRaw = digestSummary || "";
        summaryRaw = summaryRaw.replace(/\[(\d+)\](?!\()/g, '[$1](#source-$1)');

        // 2. Prepare Wordcloud HTML
        const keywords = analyticsKeywords.length > 0 ? analyticsKeywords : (digestData.analysis_source || []);
        let wordcloudHtml = "";
        if (keywords.length > 0) {
            wordcloudHtml = `<div class="wordcloud-container">`;
            keywords.forEach((kw: any) => { // Fixed 'any' type
                const size = 0.8 + ((kw.importance || 50) / 100) * 1.5;
                let colorClass = "neutral";
                let colorStyle = "#cbd5e1"; // slate-300
                if (kw.sentiment === 'Positive') { colorClass = "positive"; colorStyle = "#86efac"; } // green-300
                if (kw.sentiment === 'Negative') { colorClass = "negative"; colorStyle = "#fca5a5"; } // red-300

                wordcloudHtml += `
                    <span class="cloud-tag ${colorClass}" style="font-size: ${size}rem; color: ${colorStyle}; border-color: ${colorStyle}40;">
                        ${kw.word}
                        <span class="tooltip">
                           <strong>${kw.translation || kw.word}</strong><br/>
                           Imp: ${kw.importance}<br/>
                           Sources: ${kw.sources?.length || 0}
                        </span>
                    </span>
                 `;
            });
            wordcloudHtml += `</div>`;
        }

        // 3. GENERATE SOURCE TABLES (Part III)
        // We rebuild this from data to ensure styling and anchors match user expectation.
        let tableHtml = "";
        if (digestData.articles && digestData.articles.length > 0) {
            tableHtml = `
             <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr>
                            <th class="p-3 border-b border-slate-700 bg-slate-900 text-slate-400 font-semibold w-24">Assess</th>
                            <th class="p-3 border-b border-slate-700 bg-slate-900 text-slate-400 font-semibold w-20 text-center">AI</th>
                            <th class="p-3 border-b border-slate-700 bg-slate-900 text-slate-400 font-semibold w-32">Date</th>
                            <th class="p-3 border-b border-slate-700 bg-slate-900 text-slate-400 font-semibold w-20 text-center">Score</th>
                            <th class="p-3 border-b border-slate-700 bg-slate-900 text-slate-400 font-semibold">Article</th>
                        </tr>
                    </thead>
                    <tbody>
             `;

            digestData.articles.forEach((art: any, idx: number) => {
                const id = `source-${idx + 1}`;
                const scoreColor = art.relevance_score > 80 ? 'text-green-400' : (art.relevance_score > 50 ? 'text-yellow-400' : 'text-red-400');
                const dateColor = art.scores?.is_fresh ? 'text-green-400' : 'text-red-400';
                const aiVerdict = art.ai_verdict === 'VERIFIED' ? '✅' : (art.ai_verdict === 'REJECTED' ? '❌' : '❓');

                tableHtml += `
                    <tr id="${id}" class="hover:bg-slate-800/50 transition-colors border-b border-slate-800/50">
                        <td class="p-3 align-top">
                            <span class="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-700 bg-slate-800 text-slate-400 text-xs font-bold select-none cursor-not-allowed">
                                🤖 Assess
                            </span>
                        </td>
                        <td class="p-3 align-top text-center">${aiVerdict}</td>
                        <td class="p-3 align-top whitespace-nowrap ${dateColor} font-mono text-sm">${art.date_str || 'N/A'}</td>
                        <td class="p-3 align-top text-center ${scoreColor} font-bold">${art.relevance_score}</td>
                        <td class="p-3 align-top">
                            <a href="${art.url}" target="_blank" class="text-blue-400 hover:text-blue-300 hover:underline font-medium block mb-1">
                                [${idx + 1}] ${art.title}
                            </a>
                            <div class="text-slate-500 text-xs flex items-center gap-2">
                                <span class="uppercase tracking-wider font-semibold">${art.source}</span>
                            </div>
                        </td>
                    </tr>
                 `;
            });
            tableHtml += `</tbody></table></div>`;
        } else {
            // Fallback to existing if available
            if (digestData.digest && digestData.digest !== digestSummary) {
                tableHtml = digestData.digest;
            }
        }

        const htmlContent = `
            <!DOCTYPE html>
            <html class="dark">
            <head>
                <meta charset="utf-8">
                <title>${title}</title>
                <script src="https://cdn.tailwindcss.com"></script>
                <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
                <style>
                    body { background-color: #020617; color: #e2e8f0; font-family: 'Segoe UI', system-ui, sans-serif; padding: 2rem; max-width: 1000px; margin: 0 auto; line-height: 1.6; }
                    
                    /* Typography */
                    h1, h2, h3 { color: #f8fafc; margin-top: 1.5em; margin-bottom: 0.5em; line-height: 1.2; }
                    h1 { font-size: 2.5rem; font-weight: 800; border-bottom: 2px solid #3b82f6; padding-bottom: 0.5rem; }
                    h2 { font-size: 1.8rem; font-weight: 700; border-bottom: 1px solid #1e293b; padding-bottom: 0.5rem; }
                    h3 { font-size: 1.4rem; font-weight: 600; color: #cbd5e1; }
                    p { margin-bottom: 1em; }
                    a { color: #60a5fa; text-decoration: none; transition: color 0.2s; }
                    a:hover { color: #93c5fd; text-decoration: underline; }
                    blockquote { border-left: 4px solid #3b82f6; padding-left: 1rem; color: #94a3b8; font-style: italic; background: #1e293b50; padding: 1rem; border-radius: 0 8px 8px 0; }
                    ul, ol { margin-bottom: 1em; padding-left: 2em; }
                    li { margin-bottom: 0.5em; }
                    code { background: #1e293b; padding: 0.2em 0.4em; rounded: 4px; font-family: monospace; font-size: 0.9em; color: #e2e8f0; }

                    /* Wordcloud */
                    .wordcloud-section { margin: 3rem 0; padding: 2rem; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
                    .wordcloud-container { display: flex; flex-wrap: wrap; gap: 0.8rem; justify-content: center; align-items: center; }
                    .cloud-tag { 
                        display: inline-block; padding: 0.3rem 0.8rem; border: 1px solid transparent; border-radius: 20px; 
                        background: #1e293b; cursor: default; position: relative; transition: all 0.2s;
                    }
                    .cloud-tag:hover { transform: scale(1.1); z-index: 10; background: #334155; }
                    .cloud-tag .tooltip {
                        visibility: hidden; opacity: 0; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
                        background: #020617; border: 1px solid #475569; padding: 0.5rem; border-radius: 6px;
                        font-size: 0.8rem; white-space: nowrap; z-index: 20; transition: opacity 0.2s;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5); pointer-events: none; margin-bottom: 0.5rem;
                    }
                    .cloud-tag:hover .tooltip { visibility: visible; opacity: 1; }
                    
                    /* Custom Scrollbar for Pre blocks if any */
                    ::-webkit-scrollbar { width: 8px; height: 8px; }
                    ::-webkit-scrollbar-track { background: #0f172a; }
                    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
                    ::-webkit-scrollbar-thumb:hover { background: #475569; }

                    /* Tables (Inherited from Stream) */
                    table { width: 100%; border-collapse: separate; border-spacing: 0; margin: 2rem 0; border: 1px solid #334155; border-radius: 8px; overflow: hidden; }
                    th { background: #1e293b; color: #94a3b8; font-weight: 600; text-align: left; padding: 1rem; }
                    td { border-top: 1px solid #334155; padding: 1rem; }
                    tr:hover td { background: #1e293b50; }
                    
                    .section-label { text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px; color: #64748b; font-weight: 700; margin-bottom: 1rem; display: block; border-left: 3px solid #3b82f6; padding-left: 10px; }
                    .citation-link { color: #facc15; font-weight: bold; background: #422006; padding: 0 4px; rounded: 4px; font-size: 0.9em; }
                    .citation-link:hover { background: #a16207; color: white; text-decoration: none; }
                </style>
            </head>
            <body>
                <header style="text-align: center; margin-bottom: 4rem; border-bottom: 1px solid #1e293b; padding-bottom: 2rem;">
                    <h1 style="border:none; margin: 0 0 1rem 0; font-size: 3rem; background: linear-gradient(to right, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        ${title}
                    </h1>
                    <div style="color: #94a3b8; font-family: monospace; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 3px;">
                        OpenNews Intelligence • ${new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </div>
                </header>

                <!-- I. DIGEST REPORT -->
                ${summaryRaw ? `
                <section id="digest-report">
                    <span class="section-label">Part I: Intelligence Report</span>
                    <div id="markdown-content"></div>
                    <script>
                        // Configure Marked to handle custom classes if needed, or just run it.
                        // We replaced [n] with links in summaryRaw before embedding.
                        document.getElementById('markdown-content').innerHTML = marked.parse(\`${summaryRaw.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`);
                    </script>
                </section>
                <hr style="border-color: #334155; margin: 4rem 0;" />
                ` : ''}

                <!-- II. WORDCLOUD -->
                ${wordcloudHtml ? `
                <section id="analytics-cloud">
                    <span class="section-label">Part II: Key Entities & Sentiment</span>
                    <div class="wordcloud-section">
                        ${wordcloudHtml}
                    </div>
                </section>
                <hr style="border-color: #334155; margin: 4rem 0;" />
                ` : ''}

                <!-- III. SOURCE TABLES -->
                ${tableHtml ? `
                <section id="source-tables">
                    <span class="section-label">Part III: Source Data Verification</span>
                    ${tableHtml}
                </section>
                ` : ''}

                <footer style="margin-top: 5rem; padding-top: 2rem; border-top: 1px solid #1e293b; color: #64748b; font-size: 0.875rem; text-align: center;">
                    Generated by OpenNews • ${new Date().toLocaleString()}
                </footer>
            </body>
            </html>
        `;

        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const abortControllerRef = useRef<AbortController | null>(null);

    const handleStopDigest = () => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
            setProgressLog("🛑 Stopped by user.");
            setIsGeneratingDigest(false);
        }
    };

    const handleGenerateDigest = async () => {
        console.log("DIGEST_DEBUG: handleGenerateDigest triggered");
        if (!isAuthenticated) {
            console.log("DIGEST_DEBUG: User not authenticated");
            setErrorMessage("Please log in to use AI features.");
            return;
        }

        if (selectedOutletIds.length === 0) {
            console.log("DIGEST_DEBUG: No outlets selected");
            setErrorMessage("Please select at least one outlet.");
            return;
        }
        console.log(`DIGEST_DEBUG: Starting generation. Category=${selectedCategory}, Timeframe=${selectedTimeframe}, Outlets=${selectedOutletIds.length}`);

        setIsGeneratingDigest(true);
        setErrorMessage(null);
        // Initialize with context so UI renders immediately
        setDigestData({
            city: selectedCityName || "Global",
            category: selectedCategory,
            timeframe: selectedTimeframe,
            articles: [],
            digest: '',
            analysis_source: []
        });
        setSelectedArticleUrls(new Set());
        const localSelectedIds = new Set<string>(); // Accumulate auto-selections locally
        setDigestSummary("");
        setProgressLog('Connecting to stream...');
        setProgress({ current: 0, total: selectedOutletIds.length });

        try {
            // Retrieve token from storage/api helper if needed
            const token = localStorage.getItem('token');
            // Init AbortController
            abortControllerRef.current = new AbortController();

            console.log("DIGEST_DEBUG: Initiating fetch to /outlets/digest/stream");
            const response = await fetch(`${api.defaults.baseURL}/outlets/digest/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    outlet_ids: selectedOutletIds,
                    category: selectedCategory,
                    timeframe: selectedTimeframe,
                    city: selectedCityName || "Global"
                }),
                signal: abortControllerRef.current.signal
            });

            console.log("DIGEST_DEBUG: Fetch response received. Status:", response.status);

            if (!response.body) {
                console.error("DIGEST_DEBUG: Response body is null!");
                throw new Error("No stream body");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;
            let buffer = '';
            let lastLogUpdate = 0;
            let lastDataUpdate = 0;
            // Accumulator for throttled updates
            let currentDigestState: any = {
                articles: [],
                digest: '',
                analysis_source: [],
                city: selectedCityName || "Global",
                category: selectedCategory,
                timeframe: selectedTimeframe
            };

            console.log("DIGEST_DEBUG: Starting stream reader loop");

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                const chunkValue = decoder.decode(value || new Uint8Array(), { stream: !done });

                // console.log(`DIGEST_DEBUG: Chunk received. Done=${done}, Size=${chunkValue.length}`);

                buffer += chunkValue;
                const lines = buffer.split('\n');

                // Keep the last line in the buffer as it might be incomplete
                // unless we are done, in which case process everything.
                buffer = done ? '' : lines.pop() || '';

                for (const line of lines) {
                    if (line.trim() === '') continue;
                    try {
                        const msg = JSON.parse(line);
                        // console.log("DIGEST_DEBUG: Parsed message type:", msg.type);

                        if (msg.type === 'log') {
                            // Throttle log updates to prevent UI/WebGL thrashing (max 5fps)
                            const now = Date.now();
                            if (now - lastLogUpdate > 200 || msg.message.includes("Done") || msg.message.includes("Error")) {
                                setProgressLog(`> ${msg.message}`);
                                lastLogUpdate = now;
                                console.log("DIGEST_DEBUG: Log:", msg.message);
                            }

                            // Progress detection (Unique Outlets)
                            // Log format: "Processing {outlet.name}..." or "Found X articles from {outlet.name}"
                            if (msg.message.includes("Processing") || msg.message.includes("from")) {
                                // Extract potential outlet name (simple heuristic: generic match or rely on server to act rationally)
                                // Better approach: The server should send explicit "progress" events. 
                                // Fallback: Increment only on "Processing" which happens once per outlet start.
                                if (msg.message.includes("Processing")) {
                                    setProgress(prev => {
                                        const next = prev.current + 1;
                                        return { ...prev, current: Math.min(next, prev.total) };
                                    });
                                }
                            }
                        }
                        // --- New Partial Handlers ---
                        else if (msg.type === 'partial_digest') {
                            console.log("DIGEST_DEBUG: Received partial_digest html update");
                            currentDigestState.digest = msg.html;

                            const now = Date.now();
                            if (now - lastDataUpdate > 200) {
                                setDigestData({ ...currentDigestState });
                                lastDataUpdate = now;
                            }
                        }
                        else if (msg.type === 'meta') {
                            console.log("DIGEST_DEBUG: Received Meta:", msg);
                            currentDigestState.owner_id = msg.owner_id;
                            currentDigestState.owner_username = msg.owner_username;
                            // Immediate update to show user name
                            setDigestData({ ...currentDigestState });
                        }
                        else if (msg.type === 'partial_articles') {
                            console.log(`DIGEST_DEBUG: Received partial_articles (${msg.articles.length})`);

                            // FRONTEND DEDUPLICATION SAFETY NET
                            const newUniqueArticles = msg.articles.filter((newArt: any) => {
                                // Check if URL already exists in current state
                                const exists = currentDigestState.articles.some((existing: any) => existing.url === newArt.url);
                                if (exists) {
                                    console.log(`DIGEST_DEBUG: Frontend filtered duplicate: ${newArt.title}`);
                                }
                                return !exists;
                            });

                            if (newUniqueArticles.length > 0) {
                                if (currentDigestState.articles) {
                                    currentDigestState.articles.push(...newUniqueArticles);
                                } else {
                                    currentDigestState.articles = [...newUniqueArticles];
                                }

                                // Show modal implicitly by having digestData populated
                                currentDigestState.category = msg.category;

                                // AUTO-SELECT LOGIC (Incremental)
                                newUniqueArticles.forEach((a: any) => {
                                    const s = a.scores || {};
                                    // Use backend provided freshness
                                    const isFresh = s.is_fresh === true;
                                    const isVerified = a.ai_verdict === "VERIFIED";
                                    if (isFresh && isVerified) {
                                        localSelectedIds.add(a.url);
                                    }
                                });
                                // Update UI Selection State dynamically
                                setSelectedArticleUrls(new Set(localSelectedIds));
                            }

                            const now = Date.now();
                            if (now - lastDataUpdate > 200) {
                                setDigestData({ ...currentDigestState });
                                lastDataUpdate = now;
                            }
                        }
                        else if (msg.type === 'partial_analysis') {
                            console.log("DIGEST_DEBUG: Received partial_analysis");
                            currentDigestState.analysis_source = msg.source;

                            const now = Date.now();
                            if (now - lastDataUpdate > 200) {
                                setDigestData({ ...currentDigestState });
                                lastDataUpdate = now;
                            }
                        }
                        else if (msg.type === 'ping') {
                            // Keep-alive, do nothing
                            // console.log("Ping received");
                        }
                        else if (msg.type === 'done') {
                            console.log("DIGEST_DEBUG: Stream 'done' message received. Finalizing.");
                            // Final Update
                            setDigestData({ ...currentDigestState });

                            // Final Sync of Selection State
                            setSelectedArticleUrls(new Set(localSelectedIds));

                            setActiveModalTab('articles');
                            setShowOutletPanel(true);

                            // Check for rate limits in the accumulated data
                            if (currentDigestState.analysis_source) {
                                const hasRateLimit = currentDigestState.analysis_source.some((k: any) => k.type === "System:RateLimit");
                                if (hasRateLimit) {
                                    console.warn("DIGEST_DEBUG: Rate Limit detected in analysis");
                                    alert("⚠️ Rate Limit Warning: Some articles could not be fully analyzed.");
                                }
                            }
                        }
                        // --- Legacy Fallback ---
                        else if (msg.type === 'result') {
                            const data = msg.payload;
                            console.log("DIGEST_DEBUG: Received legacy 'result' payload. Articles:", data.articles?.length);
                            currentDigestState = data; // Update local
                            setDigestData(data);

                            // Auto-Select Fresh & Verified
                            const autoSelectedResult = new Set<string>(
                                data.articles
                                    .filter((a: any) => {
                                        const s = a.scores || {};
                                        const isFresh = s.is_fresh || (a.relevance_score > 0 && s.date > 0);
                                        const isVerified = a.ai_verdict === "VERIFIED";
                                        return isFresh && isVerified;
                                    })
                                    .map((a: any) => a.url)
                            );
                            setSelectedArticleUrls(autoSelectedResult);

                            setActiveModalTab('articles');
                            setShowOutletPanel(true);
                        } else if (msg.type === 'error') {
                            console.error("DIGEST_DEBUG: Stream reported error:", msg.message);
                            setErrorMessage(msg.message);
                        }
                    } catch (e) {
                        console.warn("DIGEST_DEBUG: Stream parse error for line:", line.substring(0, 50) + "...", e);
                    }
                }
            }

            console.log("DIGEST_DEBUG: Stream loop finished.");
            if (!currentDigestState.articles || currentDigestState.articles.length === 0) {
                console.warn("DIGEST_DEBUG: Final state checking - No articles found in digest state!");
            }

        } catch (err: any) {
            if (err.name === 'AbortError') {
                console.log("DIGEST_DEBUG: Digest generation aborted by user.");
                return; // Clean exit
            }
            console.error("DIGEST_DEBUG: Digest generation failed with exception", err);
            if (err.message && err.message.includes("network")) {
                setErrorMessage("Network Timeout. Please try fewer outlets or a smaller timeframe.");
            } else {
                setErrorMessage(err.message || 'Failed to generate digest');
            }
        } finally {
            console.log("DIGEST_DEBUG: Finally block reached. isGeneratingDigest = false");
            setIsGeneratingDigest(false);
        }
    };

    const handleLoadDigest = (digest: any) => {
        setDigestData({
            ...digest, // Preserve ID, City, Title, Created_At
            digest: digest.summary_markdown, // Map content to UI prop
        });
        // Restore State Content
        setDigestSummary(digest.summary_markdown);
        setAnalyticsKeywords(digest.analysis_source || []);

        setSelectedCategory(digest.category);
        if (digest.timeframe) setSelectedTimeframe(digest.timeframe);

        // Restore Article Selection (if any)
        if (digest.selected_article_urls && Array.isArray(digest.selected_article_urls)) {
            setSelectedArticleUrls(new Set(digest.selected_article_urls));
        }

        setActiveModalTab('articles');
    };

    // Duplicate handleDeleteDigest removed


    const CATEGORIES = ['Politics', 'Internal Affairs', 'External Affairs', 'Sports', 'Business', 'Tech'];
    const countryMap = useRef<Record<string, string>>({});

    useEffect(() => {
        console.log("NewsGlobe Mounted. Fetching initial data...");
        // Load countries polygons
        fetch('/datasets/ne_110m_admin_0_countries.geojson')
            .then(res => res.json())
            .then(data => {
                setCountries(data);
                const map: Record<string, string> = {};
                data.features.forEach((f: any) => {
                    if (f.properties && f.properties.ISO_A2) {
                        map[f.properties.ISO_A2] = f.properties.ADMIN;
                    }
                });
                countryMap.current = map;
            });

        // Load cities - DISABLED for Optimization (Phase 2)
        // fetch('https://raw.githubusercontent.com/lmfmaier/cities-json/master/cities500.json')
        //     .then(res => {
        //         console.log("Cities Loaded");
        //         if (!res.ok) throw new Error("Failed to load cities");
        //         return res.json();
        //     })
        //     .then(data => {
        //         const largeCities = Array.isArray(data) ? data.filter((d: any) => parseInt(d.pop || '0') > 100000) : [];
        //         setCities(largeCities);
        //     })
        //     .catch(err => console.error("Failed to load cities data", err));

        // Load initially discovered cities (Auth required)
        api.get('/outlets/cities/list')
            .then(res => {
                console.log("Discovered Cities Loaded:", res.data?.length);
                setDiscoveredCities(res.data);
            })
            .catch(err => console.error("Failed to load discovered cities", err));

        // Load all outlets for mapping - DISABLED for Optimization (Memory < 500MB)
        // api.get('/outlets/')
        //     .then(res => {
        //         console.log("All Outlets Loaded:", res.data?.length);
        //         setAllOutlets(res.data);
        //     })
        //     .catch(err => console.error("Failed to load outlets map", err));
    }, []);

    // Search Logic
    useEffect(() => {
        if (!searchQuery || searchQuery.length < 2) {
            setSearchResults([]);
            return;
        }

        // Normalize helper: remove diacritics (e.g. ș -> s, ă -> a)
        const normalizeText = (text: string) =>
            text.normalize('NFD').replace(/[\u0300-\u036f]/g, "").toLowerCase();

        const lowerQuery = normalizeText(searchQuery);

        // Search in processedData (to find active nodes) or raw cities?
        // Raw cities is better for complete coverage.
        const results = cities.filter(c =>
            c.name && normalizeText(c.name).includes(lowerQuery)
        ).slice(0, 10);

        setSearchResults(results);
    }, [searchQuery, cities]);

    const handleDebugArticle = (article: any) => {
        let domain = article.source;
        // CRITICAL: Backend matches rules by DOMAIN (e.g. "g4media.ro"), not Outlet Name (e.g. "G4Media").
        // We must extract the actual hostname from the URL for the rule to be effective.
        try {
            if (article.url) {
                const urlObj = new URL(article.url);
                domain = urlObj.hostname.replace('www.', '');
            }
        } catch (e) {
            console.error("Failed to parse URL for debugger", e);
        }

        setDebuggerConfig({
            isOpen: true,
            url: article.url,
            domain: domain
        });
    };

    const handleSearchSelect = (city: any) => {
        setSearchQuery('');
        setSearchResults([]);

        // Find the node in the globe data
        // It's either a point, or inside a cluster point.
        let targetNode = processedData.points.find(p => p.id === city.id || p.name === city.name);
        let parentCluster = null;

        if (!targetNode) {
            // Check inside clusters
            for (const p of processedData.points) {
                if (p.isCluster && p.subPoints) {
                    const found = p.subPoints.find((sub: any) => sub.name === city.name);
                    if (found) {
                        targetNode = found; // The city itself
                        parentCluster = p; // The cluster it belongs to
                        break;
                    }
                }
            }
        }

        // Coordinate safety check
        // Raw dataset often uses 'lon', processed might use 'lng'
        const rawLat = city.lat || city.latitude;
        const rawLng = city.lng || city.lon || city.longitude;
        const targetLat = parseFloat(rawLat);
        const targetLng = parseFloat(rawLng);

        if (isNaN(targetLat) || isNaN(targetLng)) {
            console.error("Invalid coordinates for city:", city);
            return;
        }

        if (targetNode || parentCluster) {
            // If in cluster, Expand Cluster first
            if (parentCluster) {
                setExpandedCluster(parentCluster);
                // The view will re-render, showing the spiders.
                if (globeEl.current) {
                    globeEl.current.pointOfView({ lat: targetLat, lng: targetLng, altitude: 0.1 }, 1500);
                }
            } else {
                if (globeEl.current) {
                    globeEl.current.pointOfView({ lat: targetLat, lng: targetLng, altitude: 0.1 }, 1500);
                }
            }

            // Set Halo
            setHighlightedCityId(city.name); // Using Name as ID for highlight matching
            setTimeout(() => setHighlightedCityId(null), 4000); // Remove halo after 4s

            // Select it (Trigger sidebar)
            // handleCityClick requires the 'd' object. 
            // If we found a targetNode (from processed data), use that as it has correct structure/stats.
            // If not (searched city not on map?), fallback to raw city but it might lack 'country' code used by handleCityClick.
            // But 'cities' dataset usually has country code.
            const cityToSelect = targetNode || { ...city, lat: targetLat, lng: targetLng, lon: targetLng };
            handleCityClick(cityToSelect);
        } else {
            // City found in search but not currently visualized (maybe filtered out?)
            // Just fly there and select it.
            if (globeEl.current) {
                globeEl.current.pointOfView({ lat: targetLat, lng: targetLng, altitude: 0.1 }, 1500);
            }
            // Set Halo
            setHighlightedCityId(city.name);
            setTimeout(() => setHighlightedCityId(null), 4000);

            const cityToSelect = { ...city, lat: targetLat, lng: targetLng, lon: targetLng };
            handleCityClick(cityToSelect);
        }
    };

    // --- Visual Controls ---
    const [clusterThreshold, setClusterThreshold] = useState(0.7); // Default 0.7 deg
    // Split markerScale for 2D and 3D
    const [markerScales, setMarkerScales] = useState({ '3d': 0.6, '2d': 0.25 });

    // Derived helper to get current scale (for use in renders)
    const currentMarkerScale = markerScales[vizMode];

    const [showControls, setShowControls] = useState(false); // Toggle for Viz Controls

    // ... (rest of code)
    const MAP_STYLES = [
        { name: 'Satellite', url: '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg' },
        { name: 'Day', url: '//unpkg.com/three-globe/example/img/earth-day.jpg' },
        { name: 'Night', url: '//unpkg.com/three-globe/example/img/earth-night.jpg' },
        { name: 'Dark', url: '//unpkg.com/three-globe/example/img/earth-dark.jpg' }
    ];
    const [mapStyle, setMapStyle] = useState(MAP_STYLES[0].url);
    const [editingOutletId, setEditingOutletId] = useState<number | null>(null);
    const [editUrl, setEditUrl] = useState('');

    // --- Advanced Visualization State ---

    const [expandedCluster, setExpandedCluster] = useState<any | null>(null);
    const [rawClusters, setRawClusters] = useState<any[]>([]); // Moved up for scope availability

    // OPTIMIZATION: Memoize complex props to prevent Globe re-evaluation
    const getPointColor = useCallback((d: any) => {
        if (selectedCityData && d.name === selectedCityData.name) {
            return '#00FFFF'; // Force Cyan for selected
        }
        // Inject opacity if present
        if (d.opacity !== undefined && d.opacity < 1) {
            const c = d.color;
            if (c.startsWith('#')) {
                const r = parseInt(c.slice(1, 3), 16);
                const g = parseInt(c.slice(3, 5), 16);
                const b = parseInt(c.slice(5, 7), 16);
                return `rgba(${r},${g},${b},${d.opacity})`;
            }
            return d.color;
        }
        return d.color;
    }, [selectedCityData]);

    // State for Globe Data
    const [processedData, setProcessedData] = useState<{ points: any[], rings: any[], links: any[], sprites: any[] }>({
        points: [],
        rings: [],
        links: [],
        sprites: []
    });

    const ringsData = useMemo(() => {
        return [
            ...processedData.rings,
            // 1. Temporary Halo for Search Highlight
            ...(highlightedCityId ? (() => {
                const c = rawClusters.find(x => x.name === highlightedCityId); // Optimization: Use rawClusters instead of 'cities' which is empty
                if (!c) return [];
                return [{
                    lat: parseFloat(c.lat),
                    lng: parseFloat(c.lng),
                    maxR: 2.5,
                    color: 'rgba(50, 255, 255, 0.8)',
                    propagationSpeed: 5,
                    repeatPeriod: 800
                }];
            })() : []),
            // 2. Persistent Halo
            ...(selectedCityData ? (() => {
                const lat = parseFloat(selectedCityData.lat);
                const lng = parseFloat(selectedCityData.lng || selectedCityData.lon);
                if (isNaN(lat) || isNaN(lng)) return [];
                return [{
                    lat: lat,
                    lng: lng,
                    maxR: 1.5,
                    color: 'rgba(50, 200, 255, 0.6)',
                    propagationSpeed: 2,
                    repeatPeriod: 1500
                }];
            })() : [])
        ];
    }, [processedData.rings, highlightedCityId, selectedCityData, rawClusters]);

    // Clustering Logic (Simple Distance)
    // const CLUSTER_THRESHOLD = 2.5; // Degrees // Removed, using state variable

    // OPTIMIZATION: Memoize Outlet Lookup to avoid O(N*M) in render loop
    const outletLookup = useMemo(() => {
        const map = new Map<string, any>();
        const nameMap = new Map<string, any>();
        allOutlets.forEach((o: any) => {
            try {
                const d = new URL(o.url).hostname.replace('www.', '');
                map.set(d, o);
            } catch { }
            if (o.name) nameMap.set(o.name, o);
        });
        return { byDomain: map, byName: nameMap };
    }, [allOutlets]);


    // --- OPTIMIZED CLUSTERING (Phase 2) ---
    // --- OPTIMIZED CLUSTERING (Phase 2) ---

    // 1. Fetch Clusters from Backend (Static JSONs)
    useEffect(() => {
        const availableRadii = [0.1, 0.3, 0.5, 0.7, 1.0];
        // Find closest supported radius
        const radius = availableRadii.reduce((prev, curr) =>
            Math.abs(curr - clusterThreshold) < Math.abs(prev - clusterThreshold) ? curr : prev
        );

        console.log(`Loading clusters for radius: ${radius} (requested: ${clusterThreshold})`);
        const url = `/static/clusters/cities_${radius.toFixed(1)}.json?v=120.73`; // e.g. cities_0.7.json

        // Use api (axios) or fetch. Since it's valid static file, fetch is fine/faster? 
        // Using api to keep baseURL consistent if set.
        api.get(url)
            .then(res => {
                console.log(`Loaded ${res.data.length} clusters.`);
                setRawClusters(res.data);

                // FIX: Populate 'cities' for Spotlight Search from the loaded clusters
                // Flatten: Clusters (centers) + SubPoints, avoiding duplicates
                const seen = new Set<string>();
                const flatCities: any[] = [];
                res.data.forEach((c: any) => {
                    if (!seen.has(c.name)) {
                        flatCities.push(c);
                        seen.add(c.name);
                    }
                    if (c.subPoints) {
                        c.subPoints.forEach((sc: any) => {
                            if (!seen.has(sc.name)) {
                                flatCities.push(sc);
                                seen.add(sc.name);
                            }
                        });
                    }
                });
                setCities(flatCities);
            })
            .catch(err => console.error("Failed to load clusters", err));

    }, [clusterThreshold]); // Re-fetch only when user changes slider

    // --- USER VIZ SETTINGS PERSISTENCE ---
    const [vizSettingsLoaded, setVizSettingsLoaded] = useState(false);

    // 1. Load Settings on Mount / User Login
    useEffect(() => {
        if (currentUser && currentUser.viz_settings && !vizSettingsLoaded) {
            try {
                const settings = JSON.parse(currentUser.viz_settings);
                console.log("[NewsGlobe] Loading saved viz settings:", settings);

                if (settings.vizMode) setVizMode(settings.vizMode);
                if (settings.markerScales) setMarkerScales(settings.markerScales);
                if (settings.mapStyle) setMapStyle(settings.mapStyle);
                if (settings.clusterThreshold) setClusterThreshold(settings.clusterThreshold);

                setVizSettingsLoaded(true);
            } catch (e) {
                console.error("Failed to parse user viz settings", e);
            }
        } else if (!currentUser) {
            // Reset to defaults if logged out? Or keep last interaction?
            // Keeping last interaction is better UX for "just checking"
            setVizSettingsLoaded(false); // Enable re-load on next login
        }
    }, [currentUser]);

    // 2. Auto-Save Settings (Debounced)
    const saveVizSettings = useCallback(debounce((newSettings: any) => {
        if (!currentUser) return;

        api.put('/users/me/settings', {
            viz_settings: JSON.stringify(newSettings)
        }).catch(err => console.warn("Failed to auto-save viz settings", err));

    }, 2000), [currentUser]);

    // 3. Trigger Save on Change
    useEffect(() => {
        if (!currentUser || !vizSettingsLoaded) return; // Don't save initial hydration

        const currentSettings = {
            vizMode,
            markerScales,
            mapStyle,
            clusterThreshold
        };
        saveVizSettings(currentSettings);

    }, [vizMode, markerScales, mapStyle, clusterThreshold, currentUser, vizSettingsLoaded]);

    // Helpers
    const getPopScale = (pop: any) => {
        const val = parseInt(pop || '0');
        if (val < 1000) return 0.02 * currentMarkerScale;
        return Math.max(0.08, Math.log10(val) * 0.03) * currentMarkerScale;
    };

    // 2. Apply Dynamic Styling (Colors, Active News) - O(N) efficient
    // --- OPTIMIZATION (Fix Leak): Isolate 'active' cities check from digest updates ---
    const activeDigestCities = useMemo(() => {
        const active = new Set<string>();
        if (digestData?.articles && allOutlets.length > 0) {
            const { byDomain, byName } = outletLookup;
            digestData.articles.forEach((art: any) => {
                try {
                    let outlet = null;
                    if (art.url) {
                        try { outlet = byDomain.get(new URL(art.url).hostname.replace('www.', '')); } catch { }
                    }
                    if (!outlet && art.source) outlet = byName.get(art.source);
                    if (outlet && outlet.city) active.add(outlet.city);
                } catch { }
            });
        }
        return active;
    }, [digestData?.articles, digestData?.articles?.length, allOutlets.length, outletLookup]);
    // console.log("[NewsGlobe] activeDigestCities Ref Change:", activeDigestCities);

    const clusters = useMemo(() => {
        if (!rawClusters.length) return [];
        // console.log("[NewsGlobe] Regenerating Clusters Memo!"); 

        return rawClusters.map(c => {
            const isActive = activeDigestCities.has(c.name);
            const isDiscovered = discoveredCities.includes(c.name);
            const hasNewsGeneric = c.hasNews;

            const isCapital = CAPITALS[c.country] === c.name;

            // Pre-process subPoints to identify capitals inside
            const processedSubPoints = c.subPoints ? c.subPoints.map((sp: any) => ({
                ...sp,
                isCapital: CAPITALS[sp.country] === sp.name,
                radius: getPopScale(sp.pop || 0) * currentMarkerScale
            })) : [];

            const hasCapitalInside = isCapital || processedSubPoints.some((sp: any) => sp.isCapital);

            let color = '#64748b'; // Default Slate-500

            if (isCapital) color = '#db2777'; // Pink-600
            if (isDiscovered) color = '#34d399'; // Emerald-400
            if (hasNewsGeneric) color = '#22d3ee'; // Cyan-400
            if (isActive) color = '#4ade80'; // Bright Green matches Digest

            const isMultiCity = c.subPoints && c.subPoints.length > 0;
            const isCluster = isMultiCity; // Explicit assignment

            // OPTIMIZATION: Distinct Color for Real Clusters (Multi-city)
            if (isMultiCity && !isActive && !isDiscovered) {
                // If cluster contains a capital, force "Red" (Pink-600)
                if (hasCapitalInside) {
                    color = '#db2777';
                } else {
                    color = '#a78bfa'; // Purple-400 for Normal Clusters
                }
            }

            // FIX: Backend radius (1.0-4.5) is too large. tailored for backend graph.
            const radius = getPopScale(c.pop) * currentMarkerScale;

            return {
                ...c,
                isCapital,
                isCluster, // Pass explicitly
                color,
                radius,
                subPoints: processedSubPoints
            };
        });
    }, [rawClusters, activeDigestCities, discoveredCities, currentMarkerScale]);

    // ----------------------------------------------------
    // COMPONENT RENDER LOGGING
    // ----------------------------------------------------
    // console.log("[NewsGlobe] RENDER CALL"); // If this spams, parent is cause or state loop.

    useEffect(() => {
        console.log("[NewsGlobe] MOUNTED");
        return () => console.log("[NewsGlobe] UNMOUNTED");
    }, []);

    // 2. Generate Render Objects based on Expanded State (Fast)
    useEffect(() => {
        // console.log("[NewsGlobe] Generating Processed Data", { expId: expandedCluster?.id });
        const renderPoints: any[] = [];
        const renderRings: any[] = [];
        const renderLinks: any[] = [];
        const isAnyExpanded = !!expandedCluster;

        try {
            clusters.forEach((c: any) => {
                if (expandedCluster) {
                    // FOCUS MODE: Only render the expanded cluster logic.
                    // Match by ID or Name to be robust
                    const isMatch = (c.id && c.id == expandedCluster.id) || (c.name && c.name === expandedCluster.name);

                    if (isMatch) {
                        // console.log("Expanding matched cluster:", c.name);
                        const items = [c, ...c.subPoints];
                        // const count = items.length; // Removed, not used
                        // const goldenAngle = Math.PI * (3 - Math.sqrt(5)); // Removed, not used
                        const spreadFactor = clusterThreshold * 0.5;

                        // 1. Prepare Items with Parsed Coordinates
                        const preparedItems = items.map((item: any) => ({
                            ...item,
                            pLat: parseFloat(item.lat || item.latitude),
                            pLng: parseFloat(item.lng || item.lon || item.longitude),
                            pRadius: getPopScale(item.pop)
                        }));

                        // 2. Iterative Relaxation (Force-Directed Packing)
                        // 2. Iterative Relaxation (Force-Directed Packing)
                        // 2. Iterative Relaxation (Force-Directed Packing)
                        const ITERATIONS = 80; // Increased for better settling

                        // SCALE LINKED SPREAD:
                        let basePadding = 0.05; // Increased default padding
                        if (preparedItems.length > 10) basePadding = 0.07; // Extra space for dense clusters (e.g. London)

                        const padding = basePadding * (currentMarkerScale / 0.25);

                        // ... (cloning logic)
                        // ... existing loop ...

                        // (Skipping to Color Logic below loop) for context match in next replace block

                        /* Keeping the loop logic implied, replacing the BLOCK around it if needed or just the settings?
                           The tool 'replace_file_content' replaces a contiguous block. 
                           I'll target the top variable block first. */

                        // ... (cloning logic)
                        const simItems = preparedItems.map((p: any) => ({
                            ...p,
                            x: p.pLng,
                            y: p.pLat,
                            // precise collision radius matching customThreeObject size
                            // Hierarchy: Capital (1.5), Cluster (1.2), Dot (0.8)
                            // Visual Scale = Hierarchy * currentMarkerScale * 1.5
                            // Sim Radius = Visual Scale / 2 * SafetyFactor (1.1)
                            r: (() => {
                                // Determine effective type for sizing (mimic sprite logic)
                                const isCap = p.isCapital || CITY_ICONS[p.name];
                                const isClust = p.isCluster; // Note: preparedItems don't have subPoint check here yet, assume simple
                                const hierarchy = isCap ? 1.5 : (isClust ? 1.2 : 0.8);
                                const visualSize = hierarchy * currentMarkerScale * 1.5;
                                return (visualSize / 2.0) * 1.1; // 10% safety margin
                            })(),
                            vx: 0,
                            vy: 0
                        }));

                        // ... (simulation loop same as before, using dynamic padding)
                        for (let iter = 0; iter < ITERATIONS; iter++) {
                            let moved = false;
                            for (let i = 0; i < simItems.length; i++) {
                                for (let j = i + 1; j < simItems.length; j++) {
                                    const p1 = simItems[i];
                                    const p2 = simItems[j];

                                    const dx = p2.x - p1.x;
                                    const dy = p2.y - p1.y;
                                    const distSq = dx * dx + dy * dy;
                                    const dist = Math.sqrt(distSq);

                                    const minDist = p1.r + p2.r + padding;

                                    if (dist < minDist) {
                                        const overlap = minDist - dist;
                                        const nx = dist > 0 ? dx / dist : 1;
                                        const ny = dist > 0 ? dy / dist : 0;
                                        const moveX = nx * (overlap * 0.51);
                                        const moveY = ny * (overlap * 0.51);

                                        if (i !== 0) { p1.x -= moveX; p1.y -= moveY; }
                                        if (j !== 0) { p2.x += moveX; p2.y += moveY; }
                                        moved = true;
                                    }
                                }
                            }
                            if (!moved) break;
                        }

                        simItems.forEach((item: any, idx: number) => {
                            const exLat = item.y;
                            const exLng = item.x;
                            let itemColor = '#a78bfa';
                            if (discoveredCities.includes(item.name)) itemColor = '#34d399';
                            else if (item.isCapital) itemColor = '#db2777';

                            renderPoints.push({
                                ...item,
                                lat: exLat,
                                lng: exLng,
                                lon: exLng,
                                color: itemColor,
                                radius: item.pRadius,
                                opacity: 1.0,
                                isSpider: true
                            });

                            // Add spider legs
                            if (idx !== 0) { // Don't link center to itself
                                const centerLat = parseFloat(c.lat || c.latitude);
                                const centerLng = parseFloat(c.lng || c.lon || c.longitude);
                                if (!isNaN(centerLat) && !isNaN(centerLng)) {
                                    renderLinks.push({
                                        type: 'spider',
                                        startLat: centerLat,
                                        startLng: centerLng,
                                        endLat: exLat,
                                        endLng: exLng,
                                        color: 'rgba(255,255,255,0.2)'
                                    });
                                }
                            }
                        });

                        renderRings.push({ lat: parseFloat(c.lat), lng: parseFloat(c.lng || c.lon), maxR: spreadFactor * 2.0 * (currentMarkerScale / 0.25), color: 'rgba(255,255,255,0.05)' });
                    }
                } else {
                    renderPoints.push({
                        ...c,
                        lat: parseFloat(c.lat),
                        lng: parseFloat(c.lng || c.lon),
                        opacity: 1.0
                    });

                    if (c.isCluster) {
                        renderRings.push({
                            lat: parseFloat(c.lat),
                            lng: parseFloat(c.lng || c.lon),
                            maxR: c.radius * 1.5,
                            color: 'rgba(124, 58, 237, 0.3)'
                        });
                    }
                }
            });

            // 2D SPRITE GENERATION
            const spriteData = renderPoints.map(p => {
                // ROBUST Check: Use the prop calculated in 'clusters' memo, fallback to name lookup
                const isCapital = p.isCapital || CITY_ICONS[p.name];

                // Check if this is a cluster containing a hidden capital
                // Use the sub-point's 'isCapital' prop if available
                const containsCapital = p.isCluster && p.subPoints && p.subPoints.some((sub: any) => sub.isCapital || CITY_ICONS[sub.name]);

                const effectiveIsCluster = p.isSpider ? false : p.isCluster;

                let imgUrl = GENERIC_CITY_ICON;
                let type = 'dot';

                // 1. Determine Type & Color Logic
                if (isCapital || containsCapital) {
                    // Rule: Capital or Cluster containing Capital = Red
                    imgUrl = "/icons/capital_dot.png";
                    type = 'capital';
                } else if (effectiveIsCluster) {
                    // Rule: Expandable Cluster (no capital) = Cyan
                    imgUrl = "/icons/cluster_dot.png";
                    type = 'cluster';
                } else {
                    // Rule: Single City or Expanded Point = Blue (default 'dot')
                    type = 'dot';
                    imgUrl = GENERIC_CITY_ICON;
                }

                return {
                    ...p,
                    lat: p.lat || p.pLat,
                    lng: p.lon || p.lng || p.pLng,
                    name: p.name,
                    initial: p.name ? p.name.charAt(0).toUpperCase() : '',
                    type: type,
                    // imgUrl removed, using type+initial for canvas gen
                    // size prop is not used by customThreeObject, but we keep it for reference
                    size: isCapital ? 1.5 : (effectiveIsCluster ? 1.2 : 0.8),
                    data: p
                };
            });

            setProcessedData({
                points: vizMode === '3d' ? renderPoints : [],
                rings: vizMode === '3d' ? renderRings : [],
                sprites: vizMode === '2d' ? spriteData : [],
                links: renderLinks
            });

        } catch (e) {
            console.error("Critical Error in Expansion Logic:", e);
            // Fallback: render baseline
            setProcessedData({ points: [], rings: [], links: [], sprites: [] });
        }
    }, [clusters, expandedCluster, vizMode, currentMarkerScale]);


    // ESC Key to close cluster / digest report
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                // If Digest is open, ask for confirmation
                if (digestData && !isReportSaved && !confirm("Close report? Unsaved progress will be lost.")) {
                    return;
                }
                setExpandedCluster(null);
                setDigestData(null); // Ensure digest closes too
            }
        };
        window.addEventListener('keydown', handleEsc);
        return () => window.removeEventListener('keydown', handleEsc);
    }, [digestData]); // Add digestData dependency to access current state

    const getTooltip = useCallback((d: any) => {
        // STRICTER CHECK: Only show "Media Hub" if it actually has sub-points (> 0)
        const isMultiCity = d.isCluster && d.subPoints && d.subPoints.length > 0;

        if (isMultiCity && !d.isSpider) {
            return `
            <div class="px-2 py-1 bg-amber-500/90 text-black font-bold rounded text-xs border border-amber-300 z-50 shadow-xl">
                <div class="flex items-center gap-2 mb-0.5 border-b border-black/10 pb-0.5">
                    <span class="text-[10px] uppercase opacity-80 tracking-wider">Media Hub</span>
                    <span class="text-[9px] bg-black/20 px-1 rounded-full">+${d.subPoints.length}</span>
                </div>
                <div class="text-sm font-extrabold leading-tight">${d.name}</div>
                <div class="text-[10px] opacity-90 font-mono mt-0.5">Pop: ${parseInt(d.pop || 0).toLocaleString()}</div>
            </div>
            `;
        }
        return `
            <div style="background: rgba(0,0,0,0.9); color: ${d.color}; padding: 4px 8px; border-radius: 4px; font-family: sans-serif; font-weight: bold; font-size: 12px; border: 1px solid ${d.color}; pointer-events: none;">
                ${d.name} <span style="opacity:0.7">(${parseInt(d.pop || 0).toLocaleString()})</span>
            </div>
            `;
    }, []);

    const handleCityClick = useCallback((d: any) => {
        setSelectedCityName(d.name);
        setSelectedCityData(d);
        setShowOutletPanel(true);
        setIsDiscovering(true);
        setSelectedCityOutlets([]);
        setShowAddForm(false);
        // Reset UI State for new generation
        setDigestData(null);

        // UX Enhancement: Reset Analytics to prevent old data persistence
        setAnalyticsKeywords([]);

        // Keep articles visible while generating? Or clear?
        // Let's keep them for context.
        setImportUrl('');
        setImportInstructions('');
        setErrorMessage(null);
        // setDigestData(null); // This was moved up

        const countryCode = d.country || "XX";
        const countryName = countryMap.current[countryCode] || countryCode;
        const forceRefresh = false;

        // DEBUG: Switch to GET to bypass POST/Option issues
        /*
        api.post('/outlets/discover_city', {
            city: d.name,
            country: countryName,
            lat: parseFloat(d.lat || d.latitude || '0'),
            lng: parseFloat(d.lng || d.lon || d.longitude || '0')
        })
        */
        api.get(`/outlets/discover_city_debug?city=${encodeURIComponent(d.name)}&country=${encodeURIComponent(countryName)}&lat=${parseFloat(d.lat || 0)}&lng=${parseFloat(d.lng || d.lon || 0)}&force_refresh=${forceRefresh}`)
            .then(res => {
                const data = res.data;
                if (Array.isArray(data)) {
                    setSelectedCityOutlets(data);
                    setSelectedOutletIds(data.map((o: any) => o.id));
                    if (data.length > 0 && !discoveredCities.includes(d.name)) {
                        setDiscoveredCities(prev => [...prev, d.name]);
                    }
                }
            })
            .catch(err => {
                const msg = err.response?.data?.detail || err.message || "Discovery Failed";
                console.error("Discovery failed", err);
                setErrorMessage(`Error: ${msg}`);
                if (err.response?.status === 429) setQuotaError(true);
            })
            .finally(() => setIsDiscovering(false));

        // Get City Info
        setCityInfo(null);
        api.get(`/outlets/city_info?city=${d.name}&country=${countryName}`)
            .then(res => setCityInfo(res.data))
            .catch(err => console.error("City Info failed", err));
    }, [discoveredCities]);

    const handleMapClick = useCallback((d: any) => {
        // If Spider Point OR "Fake" Cluster (Single City), treat as city click
        // STRICTER CHECK: > 0 (1+ subpoints means 2+ cities)
        const isMultiCity = d.isCluster && d.subPoints && d.subPoints.length > 0;

        if (d.isSpider || !isMultiCity) {
            handleCityClick(d);
            return;
        }

        // If Real Cluster, Expand
        if (isMultiCity) {
            console.log("Cluster Clicked:", d.name, d.id, "SubPoints:", d.subPoints.length);
            if (expandedCluster && expandedCluster.id === d.id) {
                console.log(" collapsing");
                setExpandedCluster(null); // Collapse
                // Reset zoom? optional
            } else {
                const lat = parseFloat(d.lat || d.latitude);
                const lng = parseFloat(d.lng || d.lon || d.longitude);

                if (isNaN(lat) || isNaN(lng)) {
                    console.error("Invalid Cluster Coordinates:", d);
                    return;
                }

                // const center = turf.point([lng, lat]); // Turf not strictly needed for just zooming?
                // Adaptive Zoom: Closer! (User Req: "more zoom in")
                const count = d.subPoints.length + 1;
                // Min altitude 0.025 for extremely close view
                const adaptiveAlt = Math.max(0.025, 0.25 - (count * 0.008));

                if (globeEl.current) {
                    globeEl.current.pointOfView({ lat: lat, lng: lng, altitude: adaptiveAlt }, 800);
                }
                setExpandedCluster(d);
            }
        }
    }, [expandedCluster, handleCityClick]);


    const handleRediscoverCity = () => {
        if (!selectedCityData) return;
        setIsDiscovering(true);
        setQuotaError(false);
        setSelectedCityOutlets([]);

        const d = selectedCityData;
        const countryCode = d.country || "XX";
        const countryName = countryMap.current[countryCode] || countryCode;

        api.get(`/outlets/discover_city_debug?city=${encodeURIComponent(d.name)}&country=${encodeURIComponent(countryName)}&lat=${parseFloat(d.lat)}&lng=${parseFloat(d.lon)}&force_refresh=true`)
            .then(res => {
                const data = res.data;
                if (Array.isArray(data)) {
                    setSelectedCityOutlets(data);
                    setSelectedOutletIds(data.map((o: any) => o.id));
                }
            })
            .catch(err => {
                if (err.response?.status === 429) setQuotaError(true);
            })
            .finally(() => setIsDiscovering(false));
    };

    const toggleOutletSelection = (id: number) => {
        setSelectedOutletIds(prev =>
            prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
        );
    };



    const handleDeleteOutlet = (e: any, outletId: number) => {
        e.stopPropagation();
        if (!confirm('Are you sure you want to delete this outlet?')) return;
        api.delete(`/outlets/${outletId}`)
            .then(() => {
                setSelectedCityOutlets(prev => prev.filter(o => o.id !== outletId));
            })
            .catch(err => alert(`Failed to delete: ${err.message}`));
    };

    const handleUpdateOutlet = (outletId: number) => {
        if (!editUrl) return;
        api.put(`/outlets/${outletId}`, { url: editUrl })
            .then(res => {
                setSelectedCityOutlets(prev => prev.map(o => o.id === outletId ? { ...o, url: res.data.url } : o));
                setEditingOutletId(null);
            })
            .catch(err => alert(`Failed to update: ${err.message}`));
    };

    const handleImportUrl = (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedCityData || !importUrl) return;
        setIsImporting(true);
        setErrorMessage(null);

        const countryCode = selectedCityData.country || "XX";
        const countryName = countryMap.current[countryCode] || countryCode;

        api.post('/outlets/import_from_url', {
            url: importUrl,
            city: selectedCityData.name,
            country: countryName,
            lat: parseFloat(selectedCityData.lat),
            lng: parseFloat(selectedCityData.lon),
            instructions: importInstructions || undefined
        })
            .then(res => {
                const data = res.data;
                if (Array.isArray(data)) {
                    // Check if new items were added
                    const prevCount = selectedCityOutlets.length;
                    const newCount = data.length;

                    setSelectedCityOutlets(data);
                    setImportUrl('');
                    setImportInstructions('');
                    setShowAddForm(false);
                    if (data.length > 0 && !discoveredCities.includes(selectedCityData.name)) {
                        setDiscoveredCities(prev => [...prev, selectedCityData.name]);
                    }

                    // Feedback
                    if (newCount > prevCount) {
                        // Logic to highlight? For now just rely on Manual highlight
                    } else {
                        alert('Import completed, but no new unique outlets were added (duplicates skipped).');
                    }
                }
            })
            .catch(err => {
                setErrorMessage(err.response?.data?.detail || err.message);
            })
            .finally(() => setIsImporting(false));
    };

    // Helper to update a single article's date in state
    const updateLocalArticleDate = (targetUrl: string, dateStr: string) => {
        setDigestData((prev: any) => {
            if (!prev) return prev;

            // Calculate cutoff based on active configuration
            const timeframe = selectedTimeframe || "24h";
            const now = new Date();
            const cutoff = new Date();
            if (timeframe === "3days") cutoff.setDate(now.getDate() - 3);
            else if (timeframe === "1week") cutoff.setDate(now.getDate() - 7);
            else if (timeframe === "1month") cutoff.setDate(now.getDate() - 30);
            else cutoff.setDate(now.getDate() - 1); // 24h default

            const newDate = new Date(dateStr);
            const isFresh = newDate >= cutoff;

            const updatedArticles = prev.articles.map((art: any) => {
                if (art.url === targetUrl) {
                    return {
                        ...art,
                        date_str: dateStr,
                        // Update scores based on freshness logic (mimic backend)
                        relevance_score: isFresh ? Math.max(art.relevance_score, 50) : 0,
                        scores: {
                            ...art.scores,
                            date: isFresh ? 30 : 0,
                            is_fresh: isFresh,
                            is_old: !isFresh
                        }
                    };
                }
                return art;
            });
            return { ...prev, articles: updatedArticles };
        });
    };

    const handleDateExtracted = (dateStr: string) => {
        if (debuggerConfig.url) {
            updateLocalArticleDate(debuggerConfig.url, dateStr);
        }
    };

    const handleRulesUpdated = async (domain: string, result?: any, config?: any) => {
        console.log("handleRulesUpdated CALLED", { domain, result, config });

        if (!digestData?.articles) {
            console.warn("handleRulesUpdated: digestData/articles missing!");
            return;
        }

        const updateList = async (list: any[]) => {
            if (!list) return [];
            const updatedList = [...list];
            let changesMade = false;

            // Determine active target URL from either debugger state
            const targetUrl = debuggerConfig?.url || debugTarget?.url;

            console.log(`handleRulesUpdated: Scanning ${updatedList.length} articles target=${targetUrl}`);

            for (let i = 0; i < updatedList.length; i++) {
                const art = updatedList[i];
                let shouldUpdate = false;
                let isDebugTarget = false;

                // Match by URL (Guarantee target update)
                if (targetUrl && art.url === targetUrl) {
                    shouldUpdate = true;
                    isDebugTarget = true;
                    console.log("handleRulesUpdated: MATCHED TARGET URL", art.url);
                }
                // Match by Domain (Broad update)
                else {
                    try {
                        const artDomain = new URL(art.url).hostname.replace('www.', '');
                        if (artDomain === domain) shouldUpdate = true;
                    } catch (e) { /* ignore invalid urls */ }
                }

                if (!shouldUpdate) continue;

                console.log(`handleRulesUpdated: Updating ${art.url} (Target=${isDebugTarget})`);

                try {
                    let responseData;

                    if (isDebugTarget && result) {
                        responseData = result;
                    } else {
                        // For others, re-test using the new config
                        const testPayload: any = { url: art.url };
                        if (config) testPayload.rule_config = config;

                        // We do this sequentially here for simplicity, or could parallelize like before
                        // But for "Live Update" of one debugged article, sequential is fine.
                        // If updating 100 articles, this might be slow. 
                        // But usually the user just wants to see the ONE they fixed.
                        const resp = await api.post('/scraper/test', testPayload);
                        responseData = resp.data;
                    }

                    if (responseData && (responseData.extracted_date || responseData.extracted_title)) {
                        console.log("DEBUG TITLE UPDATE:", {
                            url: art.url,
                            extractedTitle: responseData.extracted_title,
                            oldTitle: art.title,
                            extractedDate: responseData.extracted_date
                        });

                        const newDate = responseData.extracted_date;
                        const newTitle = responseData.extracted_title || art.title;

                        // Check if actually changed
                        const isTitleChanged = newTitle && newTitle !== art.title;
                        const isDateChanged = newDate && newDate !== art.date_str;

                        // Recalc Freshness Locally
                        const timeframe = selectedTimeframe || "24h";
                        const cutoff = new Date();
                        const now = new Date();
                        if (timeframe === "3days") cutoff.setDate(now.getDate() - 3);
                        else if (timeframe === "1week") cutoff.setDate(now.getDate() - 7);
                        else if (timeframe === "1month") cutoff.setDate(now.getDate() - 30);
                        else cutoff.setDate(now.getDate() - 1);

                        let isFresh = false;
                        if (newDate) {
                            // Simple parse or use helper if available? Date(newDate) usually works for ISO YYYY-MM-DD
                            const d = new Date(newDate);
                            isFresh = d >= cutoff;
                        }

                        // Update with fresh scores
                        updatedList[i] = {
                            ...art,
                            title: newTitle,
                            date_str: newDate,
                            relevance_score: isFresh ? Math.max(art.relevance_score, 50) : 0,
                            scores: {
                                ...art.scores,
                                date: isFresh ? 30 : 0,
                                is_fresh: isFresh,
                                is_old: !isFresh
                            }
                        };


                        if (isTitleChanged) {
                            // Reset AI verdicts if title changed
                            updatedList[i].ai_verdict = null;
                            updatedList[i].translated_title = null;

                            // Background Assessment
                            // We create a self-contained updater that runs after the main update
                            const artUrl = art.url;
                            const freshTitle = newTitle;

                            // We don't await this to keep the UI snappy
                            // But we must chain it to update state LATER
                            assessQueue.push(async () => {
                                try {
                                    const assessment = await handleAssessArticle({ url: artUrl, title: freshTitle });
                                    if (assessment) {
                                        setDigestData((prev: any) => {
                                            if (!prev?.articles) return prev;
                                            const newArts = prev.articles.map((a: any) => {
                                                if (a.url === artUrl) {
                                                    return {
                                                        ...a,
                                                        ai_verdict: assessment,
                                                        // If we have a translation from assessment? (API usually returns it in labels or reasoning?)
                                                        // Actually assess_article returns { is_politics, confidence, reasoning, labels }
                                                        // It DOES NOT return translated_title. That's a different endpoint usually?
                                                        // Wait, checking ArticleRow... it uses ai_verdict for "Is Politics".
                                                        // Translation is usually separate. 
                                                        // For now, updating ai_verdict is what "AI-title check" likely refers to (politics check).
                                                    };
                                                }
                                                return a;
                                            });
                                            return { ...prev, articles: newArts };
                                        });
                                    }
                                } catch (e) { console.error("Background Assessment Failed", e); }
                            });
                        }

                        // Update Local Date Helper if needed
                        if (newDate) updateLocalArticleDate(art.url, newDate);

                        changesMade = true;
                    }
                } catch (e) {
                    console.warn(`Update failed for ${art.url}`, e);
                }
            }
            return changesMade ? updatedList : list;
        };

        const assessQueue: (() => Promise<void>)[] = [];
        const updatedArticles = await updateList(digestData.articles);
        const updatedExcluded = await updateList(digestData.excluded_articles || []);

        // 1. Immediate Update (Titles)
        if (updatedArticles !== digestData.articles || updatedExcluded !== digestData.excluded_articles) {
            setDigestData({
                ...digestData,
                articles: updatedArticles,
                excluded_articles: updatedExcluded
            });
            console.log("handleRulesUpdated: State Updated (Titles)!");
        } else {
            console.log("handleRulesUpdated: No changes detected.");
        }

        // 2. Follow-up Update (AI Assessment)
        if (assessQueue.length > 0) {
            console.log(`handleRulesUpdated: Processing ${assessQueue.length} background assessments...`);
            // Run them
            assessQueue.forEach(fn => fn());
        }
    };

    const handleAssessArticle = async (article: any) => {
        setIsReportSaved(false); // Mark as modified
        if (!article.url || !article.title) return null;

        try {
            const res = await api.post('/outlets/assess_article', {
                url: article.url,
                title: article.title,
                content: null // force fetch
            });
            const data = res.data;
            const verdict = {
                is_politics: data.is_politics,
                confidence: data.confidence,
                reasoning: data.reasoning,
                labels: data.labels
            };

            // CRITICAL FIX: Update Main State (digestData) logic so Auto-Select sees this result!
            setDigestData((prev: any) => {
                if (!prev?.articles) return prev;
                const newArgs = prev.articles.map((a: any) => {
                    if (a.url === article.url) {
                        return { ...a, ai_verdict: verdict };
                    }
                    return a;
                });
                // Also check excluded?
                const newExcl = (prev.excluded_articles || []).map((a: any) => {
                    if (a.url === article.url) return { ...a, ai_verdict: verdict };
                    return a;
                });
                return { ...prev, articles: newArgs, excluded_articles: newExcl };
            });

            return verdict;
        } catch (err: any) {
            console.error(err);
            alert(`Assessment process failed: ${err.response?.data?.detail || err.message}`);
            return null;
        }
    };

    const handleReportSpam = async (article: any) => {
        setIsReportSaved(false); // Mark as modified
        if (!article.url) return;
        const url = article.url;

        // Toggle Logic
        if (spamUrls.has(url)) {
            // UNFLAG (Undo)
            try {
                await api.delete(`/feedback/spam?url=${encodeURIComponent(url)}`);
                const newSpam = new Set(spamUrls);
                newSpam.delete(url);
                setSpamUrls(newSpam);
            } catch (err) {
                console.error("Failed to unflag spam", err);
            }
        } else {
            // FLAG (Report)
            try {
                await api.post('/feedback/spam', {
                    url: url,
                    title: article.title,
                    reason: 'technical_junk'
                });
                const newSpam = new Set(spamUrls);
                newSpam.add(url);
                setSpamUrls(newSpam);

                // Auto-Deselect
                if (selectedArticleUrls.has(url)) {
                    const newSelected = new Set(selectedArticleUrls);
                    newSelected.delete(url);
                    setSelectedArticleUrls(newSelected);
                }
            } catch (err: any) {
                console.error("Spam report failed", err);
                throw err;
            }
        }
    };


    // ... (Add manual outlet implementation similar to above using api.post)


    // --- Optimization: Hoist handlers to prevent Hook Violations (Error #300) ---
    // These must be defined at the top level, NOT inside useMemo.

    const handlePolygonCapColor = useCallback(() => 'rgba(0, 0, 0, 0)', []);
    const handlePolygonSideColor = useCallback(() => 'rgba(0, 0, 0, 0)', []);
    const handlePolygonStrokeColor = useCallback(() => mapStyle.includes('day') ? '#000000' : '#888', [mapStyle]);

    const handlePolygonClick = useCallback((d: any) => {
        setExpandedCluster(null); // Click background to close cluster
        setSelectedCountry(d);
        if (globeEl.current) {
            const centroid = turf.centroid(d);
            const [lng, lat] = centroid.geometry.coordinates;
            globeEl.current.pointOfView({ lat, lng, altitude: 0.5 }, 1000);
        }
        if (onCountrySelect) onCountrySelect(d.properties.NAME, d.properties.ISO_A2);
    }, [onCountrySelect]);

    // Filter Labels
    const labelsData = useMemo(() => {
        return processedData.points.filter(p =>
            p.isSpider || p.isCluster || (parseInt(p.pop || '0') > 1000000) || p.isCapital
        );
    }, [processedData.points]);

    const getLabelText = useCallback((d: any) => {
        if (!d.name) return '?';
        const char = d.name.charAt(0).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        return char.toUpperCase();
    }, []);

    const handleCursorPointer = useCallback((d: any) => {
        document.body.style.cursor = d ? 'pointer' : 'default';
    }, []);

    const globeComponent = (
        <Globe
            // MEMORY LEAK DIAGNOSIS: Reverted forced remount (User Request)
            // key={expandedCluster ? `cluster-${expandedCluster.id}` : 'global-view'}

            ref={globeEl}
            onGlobeReady={() => {
                // Reliable initialization for Romania
                if (globeEl.current) {
                    globeEl.current.pointOfView({ lat: 45.9432, lng: 24.9668, altitude: 2.0 });
                }
            }}
            globeImageUrl={mapStyle}
            bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
            backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"

            // Polygons (Borders)
            polygonsData={countries.features}
            polygonAltitude={0.005}
            polygonCapColor={handlePolygonCapColor}
            polygonSideColor={handlePolygonSideColor}
            polygonStrokeColor={handlePolygonStrokeColor}
            // @ts-ignore
            polygonStrokeWidth={mapStyle.includes('day') ? 2 : 0.6}
            onPolygonClick={handlePolygonClick}

            // Labels (Initials on Marker) - OPTIMIZATION: Only show for Clusters or Large Cities
            labelsData={labelsData}
            labelLat={getLat}
            labelLng={getLng}
            labelText={getLabelText}
            labelLabel={getTooltip}
            onLabelClick={handleMapClick}
            onLabelHover={handleCursorPointer}

            // Use default system font for max compatibility
            labelTypeFace={undefined}
            labelFont={undefined}

            // Points (Cities & Clusters)
            pointsData={processedData.points}
            pointLat={getLat}
            pointLng={getLng}
            pointColor={getPointColor} // Memoized
            pointRadius={getRadius}
            pointAltitude={0.005}
            // VISUAL BALANCE: 12 is decent looking, 32 is overkill.
            pointResolution={12}
            onPointHover={handleCursorPointer}
            onPointClick={handleMapClick} // Memoized
            pointLabel={getTooltip} // Memoized

            // Radius is "radius", Diameter is 2x. Text height needs to fill diameter.
            labelSize={getLabelSize}
            labelColor={getLabelColor}
            labelDotRadius={0}
            labelAltitude={0.0051}
            // MEMORY OPTIMIZATION: Text sprites are flat, no need for 3D resolution
            labelResolution={1}
            labelIncludeDot={false}

            // 2D Sprite Layer
            // 2D Sprite Layer
            customLayerData={processedData.sprites}
            // ENABLE INTERACTION:
            onCustomLayerClick={handleMapClick}
            customThreeObject={(d: any) => {
                // Optimization: Memoize textures globally
                if (!(window as any)._canvasTextures) {
                    (window as any)._canvasTextures = {};
                }
                const cache = (window as any)._canvasTextures;

                // Key based on type+initial (only ~26*3 = 78 vars max)
                // CACHE BUST v2: Added version prefix to force color update
                const key = `v2_${d.type}_${d.initial || ''}`;

                if (!cache[key]) {
                    const canvas = document.createElement('canvas');
                    const size = 128;
                    canvas.width = size;
                    canvas.height = size;
                    const ctx = canvas.getContext('2d');
                    if (ctx) {
                        ctx.imageSmoothingEnabled = true;

                        // Colors
                        let fillColor = '#3B82F6'; // Std Blue
                        let strokeColor = '#FFFFFF';

                        if (d.type === 'capital') fillColor = '#A0283C'; // Wine Red
                        else if (d.type === 'cluster') fillColor = '#06B6D4'; // Cyan

                        // Draw Circle
                        const radius = size / 2 - 4;
                        ctx.beginPath();
                        ctx.arc(size / 2, size / 2, radius, 0, 2 * Math.PI);
                        ctx.fillStyle = fillColor;
                        ctx.fill();
                        ctx.lineWidth = 6;
                        ctx.strokeStyle = strokeColor;
                        ctx.stroke();

                        // Draw Initial
                        if (d.initial) {
                            ctx.fillStyle = "#FFFFFF";
                            ctx.font = "bold 60px Inter, sans-serif";
                            ctx.textAlign = "center";
                            ctx.textBaseline = "middle";
                            // Slight y-offset for visual centering
                            ctx.fillText(d.initial, size / 2, size / 2 + 4);
                        }
                    }

                    const texture = new THREE.CanvasTexture(canvas);
                    texture.colorSpace = THREE.SRGBColorSpace;

                    cache[key] = new THREE.SpriteMaterial({
                        map: texture,
                        transparent: true,
                        opacity: 1,
                        depthWrite: false,
                        depthTest: true
                    });
                }

                const sprite = new THREE.Sprite(cache[key]);

                // Scale Logic: Base * markerScale
                // Capital: 1.2, Cluster: 1.0, Dot: 0.6
                // const baseScale = d.type === 'capital' ? 1.2 : (d.type === 'cluster' ? 1.0 : 0.6);

                // Using markerScale directly now for easier control
                // But preserving relative hierarchy
                const hierarchyMult = d.type === 'capital' ? 1.5 : (d.type === 'cluster' ? 1.2 : 0.8);

                // Final Scale = Hierarchy * UserSlider * BaseUnit
                const finalScale = hierarchyMult * currentMarkerScale * 1.5;

                sprite.scale.set(finalScale, finalScale, 1);

                return sprite;
            }}
            customThreeObjectUpdate={(obj, d: any) => {
                // LOWER ALTITUDE: 0.012 (Balance between floating and clipping)
                Object.assign(obj.position, globeEl.current?.getCoords(d.lat, d.lng, 0.012));
            }}

            // Rings - DIAGNOSIS: DISABLED to check for Animation Leak
            ringsData={[]}
            // ringsData={ringsData}
            ringLat={getLat}
            ringLng={getLng}
            ringMaxRadius={getRingMaxR}
            ringColor={getRingColor}
            ringPropagationSpeed={2}
            ringRepeatPeriod={1000}
            // VISUAL BALANCE: 32 is smooth enough
            ringResolution={32}

            // Paths
            pathsData={processedData.links}
            pathPoints={getPathPoints}
            pathPointLat={getPathPointLat}
            pathPointLng={getPathPointLng}
            pathColor={getPathColor}
            // MEMORY OPTIMIZATION: Use 2 radial segments (flat tube)
            pathResolution={2}

            // CONTROLS: Enable Zoom only when Meta/Ctrl is pressed (if disableScrollZoom is true)
            // If disableScrollZoom is false (default), zoom is always enabled
            // CONTROLS: Default = Zoom Enabled (Scroll Trap) ONLY if At Top.
            // If scrolled down OR Meta pressed -> Zoom Disabled (Page Scroll).
            enableZoom={isAtTop && !isMetaPressed}
        />
    );

    // Dynamic Control Update
    useEffect(() => {
        if (globeEl.current) {
            const controls = globeEl.current.controls();
            if (controls) {
                // Logic: Zoom enabled ONLY if At Top AND Meta not pressed
                const shouldEnableZoom = isAtTop && !isMetaPressed;
                controls.enableZoom = shouldEnableZoom;
                controls.update?.();
            }
        }
    }, [isMetaPressed, isAtTop]);

    return (
        <div className={`relative w-full h-full bg-slate-950 transition-cursor ${(isAtTop && !isMetaPressed) ? 'cursor-move' : 'cursor-default'}`}>
            {/* Visual Controls Toggle & Overlay */}
            <div className="absolute bottom-4 left-4 z-20 flex flex-col items-start gap-2">
                {!showControls && (
                    <button
                        onClick={() => setShowControls(true)}
                        className="p-2 rounded-lg border border-slate-700 text-white transition-colors shadow-lg bg-slate-900/80 backdrop-blur hover:bg-slate-800"
                        title="Open Visualization Controls"
                    >
                        <Sliders size={20} />
                    </button>
                )}


                {expandedCluster && (
                    <button
                        onClick={() => {
                            if (digestData && !isReportSaved && !confirm("Close report? Unsaved progress will be lost.")) return;
                            setExpandedCluster(null);
                            setDigestData(null);
                        }}
                        className="bg-red-500/80 hover:bg-red-500 text-white p-2 rounded-lg backdrop-blur shadow-lg border border-red-400 animate-in zoom-in duration-200"
                        title="Close Cluster View"
                    >
                        <X size={20} />
                    </button>
                )}

                {showControls && (
                    <div className="bg-slate-900/80 backdrop-blur p-4 rounded-lg border border-slate-700 text-xs text-white space-y-3 w-64 animate-in fade-in slide-in-from-bottom-2 duration-200">
                        <div className="flex items-center justify-between border-b border-slate-700 pb-1 mb-2">
                            <h4 className="font-bold">Viz Controls</h4>
                            <button
                                onClick={() => setShowControls(false)}
                                className="text-slate-400 hover:text-white transition-colors"
                            >
                                <X size={16} />
                            </button>
                        </div>
                        <div>
                            <label className="flex justify-between mb-1">
                                <span>Cluster Radius: {clusterThreshold.toFixed(1)}°</span>
                            </label>
                            <input
                                type="range" min="0.5" max="1.0" step="0.1"
                                value={clusterThreshold}
                                onChange={e => setClusterThreshold(parseFloat(e.target.value))}
                                className="w-full accent-blue-500"
                            />
                        </div>
                        <div>
                            <label className="flex justify-between mb-1">
                                <span>Marker Scale ({vizMode === '2d' ? '2D' : '3D'}): {currentMarkerScale.toFixed(2)}x</span>
                            </label>
                            <input
                                type="range"
                                min={vizMode === '2d' ? "0.05" : "0.2"}
                                max={vizMode === '2d' ? "0.5" : "2.0"}
                                step={vizMode === '2d' ? "0.05" : "0.1"}
                                value={currentMarkerScale}
                                onChange={e => setMarkerScales(prev => ({ ...prev, [vizMode]: parseFloat(e.target.value) }))}
                                className="w-full accent-blue-500"
                            />
                        </div>


                        {/* Map Style Toggle */}
                        <div>
                            <label className="mb-2 block font-semibold text-slate-400">Map Mode</label>
                            <div className="grid grid-cols-2 gap-2">
                                {MAP_STYLES.map(style => (
                                    <button
                                        key={style.name}
                                        onClick={() => setMapStyle(style.url)}
                                        className={`px-2 py-1 rounded text-xs transition-colors border ${mapStyle === style.url
                                            ? 'bg-blue-600 border-blue-500 text-white font-bold'
                                            : 'bg-slate-800 border-slate-600 text-slate-400 hover:bg-slate-700'
                                            }`}
                                    >
                                        {style.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Debugger Modal */}
            <ScraperDebugger
                isOpen={debuggerConfig.isOpen}
                initialUrl={debuggerConfig.url}
                domain={debuggerConfig.domain}
                onClose={() => setDebuggerConfig(prev => ({ ...prev, isOpen: false }))}
                onDateExtracted={handleDateExtracted}
                onSave={handleRulesUpdated}
            />

            {/* Digest Modal / Full Screen View */}
            {
                digestData && (
                    <div className="absolute inset-0 z-50 bg-slate-950/95 backdrop-blur-sm flex items-center justify-center p-8 animate-in fade-in duration-200">
                        <div className="bg-black border border-neutral-800 rounded-xl shadow-2xl w-full max-w-7xl h-[95vh] flex flex-col overflow-hidden relative">
                            <UnifiedDigestViewer
                                digestData={digestData}
                                onClose={() => {
                                    if (!isReportSaved && digestSummary && digestSummary !== digestData.digest) {
                                        setShowCloseConfirm(true);
                                        return;
                                    }
                                    setDigestData(null);
                                    setActiveModalTab('articles');
                                    setIsTranslateActive(false);
                                }}
                                onSave={handleSaveDigest}
                                onShare={handleShareDigest}
                                onDownload={handleDownloadDigest}
                                onDelete={() => handleDeleteDigest(digestData.id)}
                                onRegenerateSummary={handleGenerateBackendSummary}
                                onRegenerateAnalytics={handleGenerateAnalytics}
                                setDigestSummary={setDigestSummary}
                                selectedArticleUrls={selectedArticleUrls}
                                onToggleSelection={handleToggleSelection}
                                analyticsKeywords={analyticsKeywords}
                                isReadOnly={false}
                                isSaving={isSaving}
                                isSharing={isSharing}
                                isSummarizing={isSummarizing || isGeneratingDigest}
                                tickerText={analyzingTickerText}
                                spamUrls={spamUrls}
                                onReportSpam={handleReportSpam}
                                onAssessArticle={handleAssessArticle}
                                onDebugArticle={handleDebugArticle}
                            />
                            {showCloseConfirm && (
                                <div className="absolute inset-0 z-[60] bg-black/80 backdrop-blur-sm flex items-center justify-center animate-in fade-in">
                                    <div className="bg-slate-900 border border-slate-700 p-6 rounded-xl shadow-2xl max-w-sm w-full text-center">
                                        <h3 className="text-xl font-bold text-white mb-2">Unsaved Changes</h3>
                                        <p className="text-slate-400 mb-6">You have unsaved edits in your report. Closing will discard them.</p>
                                        <div className="flex gap-3 justify-center">
                                            <button
                                                onClick={() => setShowCloseConfirm(false)}
                                                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold transition-colors"
                                            >
                                                Keep Editing
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setShowCloseConfirm(false);
                                                    setDigestData(null);
                                                    setActiveModalTab('articles');
                                                    setIsTranslateActive(false);
                                                }}
                                                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-bold transition-colors"
                                            >
                                                Discard & Close
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div >
                )
            }

            {globeComponent}
            {
                showOutletPanel && (
                    <div className="absolute top-20 left-4 w-96 bg-slate-900/95 backdrop-blur border border-slate-700 rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[calc(100vh-140px)]">
                        <div className="p-4 border-b border-slate-700 bg-slate-900">
                            {/* Search Bar */}


                            <div className="flex justify-between items-start mb-3">
                                <div className="flex flex-col gap-1 items-start w-full pr-8">
                                    <h3 className="font-bold text-white text-2xl tracking-tight flex items-baseline gap-3">
                                        {selectedCityName}
                                        {cityInfo && (cityInfo.city_native_name || cityInfo.city_phonetic_name) && (
                                            <span className="text-sm font-normal text-slate-400 font-serif italic">
                                                {cityInfo.city_native_name} {cityInfo.city_phonetic_name && `(${cityInfo.city_phonetic_name})`}
                                            </span>
                                        )}
                                    </h3>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {cityInfo?.country_flag_url ? (
                                            <img
                                                src={cityInfo.country_flag_url}
                                                alt="Country Flag"
                                                className="h-5 w-auto object-contain rounded-sm shadow-sm"
                                            />
                                        ) : (
                                            cityInfo?.flag_url && (
                                                <img
                                                    src={cityInfo.flag_url}
                                                    alt="Flag"
                                                    className="h-5 w-auto object-contain rounded-sm"
                                                />
                                            )
                                        )}
                                        <span className="text-sm font-bold text-slate-400">
                                            {cityInfo?.country_english || selectedCityData?.country || "Country"}
                                        </span>
                                        {(cityInfo?.country_native || cityInfo?.country_phonetic) && (
                                            <span className="text-xs text-slate-500 font-serif italic border-l border-slate-700 pl-2">
                                                {cityInfo.country_native} {cityInfo.country_phonetic && `(${cityInfo.country_phonetic})`}
                                            </span>
                                        )}
                                    </div>
                                </div>


                                <button onClick={() => setShowOutletPanel(false)} className="text-gray-400 hover:text-white">✕</button>
                            </div>
                            {cityInfo && (
                                <div className="text-xs text-slate-400 space-y-2 animate-in slide-in-from-left-2 fade-in duration-300">
                                    <div className="flex flex-wrap gap-2 text-[10px] items-center">
                                        <span className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-300 font-mono">
                                            👥 {cityInfo.population}
                                        </span>
                                        {cityInfo.ruling_party && (
                                            <span className="px-1.5 py-0.5 bg-slate-800 rounded text-slate-300">
                                                🏛 {cityInfo.ruling_party}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-slate-500 italic leading-relaxed border-l-2 border-slate-700 pl-2">
                                        {cityInfo.description}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Controls */}
                        <div className="p-4 space-y-4">
                            <div className="flex gap-2 flex-wrap">
                                {CATEGORIES.map(cat => (
                                    <button
                                        key={cat}
                                        onClick={() => setSelectedCategory(cat)}
                                        className={`px-2 py-1 text-xs rounded border ${selectedCategory === cat ? 'bg-blue-600 border-blue-500 text-white' : 'border-slate-700 text-gray-400'}`}
                                    >
                                        {cat}
                                    </button>
                                ))}
                            </div>

                            {/* Timeframe Selector */}
                            <div className="flex gap-2 bg-slate-900/40 p-1 rounded-lg border border-slate-700/50 my-2">
                                {[
                                    { label: '24h', value: '24h' },
                                    { label: '3 Days', value: '3days' },
                                    { label: '7 Days', value: '1week' }
                                ].map((tf) => (
                                    <button
                                        key={tf.value}
                                        onClick={() => setSelectedTimeframe(tf.value)}
                                        className={`flex-1 py-1 text-[10px] uppercase font-bold rounded text-center transition-all ${selectedTimeframe === tf.value
                                            ? 'bg-blue-600/20 text-blue-400 border border-blue-500/50 shadow-[0_0_10px_rgba(59,130,246,0.2)]'
                                            : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                                            }`}
                                    >
                                        {tf.label}
                                    </button>
                                ))}
                            </div>

                            <div className="flex gap-2 relative w-full">
                                <button
                                    onClick={handleGenerateDigest}
                                    disabled={!isGeneratingDigest && selectedOutletIds.length === 0}
                                    className={`w-full font-medium py-3 rounded-lg shadow-lg transition-all text-base flex justify-center items-center gap-2 h-14 min-w-[300px]
                                        ${isGeneratingDigest
                                            ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-900/40 border border-blue-500/30'
                                            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-900/40 border border-blue-500/30'
                                        }
                                    `}
                                >
                                    {isGeneratingDigest ? (
                                        <>
                                            <div className="flex flex-col items-center">
                                                <span className="flex items-center gap-2">
                                                    <Loader2 className="w-5 h-5 animate-spin" />
                                                    Gathering Articles...
                                                </span>
                                                {progressLog && (
                                                    <div className="mt-1 min-w-[250px] text-center">
                                                        <UIMarquee
                                                            text={progressLog}
                                                            maxLength={40}
                                                            className="text-xs text-blue-200 font-mono opacity-80"
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <FileText className="w-5 h-5" />
                                            Gather Articles
                                        </>
                                    )}
                                </button>

                                {isGeneratingDigest && (
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleStopDigest();
                                        }}
                                        title="Stop Generation"
                                        className="absolute -top-2 -right-2 p-1.5 bg-red-500 hover:bg-red-600 text-white rounded shadow-lg transition-transform hover:scale-110 z-20 border-2 border-slate-900 flex items-center justify-center"
                                    >
                                        <div className="h-3 w-3 bg-white rounded-[1px]" />
                                    </button>
                                )}
                            </div>

                            {/* Sidebar Tabs */}

                            <div className="flex border-b border-slate-700 mt-4">
                                <button
                                    onClick={() => setActiveSideTab('sources')}
                                    className={`flex-1 pb-2 text-sm font-bold transition-colors ${activeSideTab === 'sources' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    Sources
                                </button>
                                <button
                                    onClick={() => setActiveSideTab('digests')}
                                    className={`flex-1 pb-2 text-sm font-bold transition-colors ${activeSideTab === 'digests' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-slate-500 hover:text-slate-300'}`}
                                >
                                    Saved Digests
                                </button>
                            </div>
                        </div>

                        {/* Results / List */}
                        <div className="flex-1 overflow-y-auto p-4 text-white text-sm custom-scrollbar">
                            {activeSideTab === 'sources' ? (
                                <>
                                    {isDiscovering && <div className="text-center text-blue-400 mb-4 animate-pulse">Discovering landscape...</div>}

                                    {(!digestData || isGeneratingDigest) && !isDiscovering && (
                                        <div className="space-y-2">
                                            {/* Filters & Header */}
                                            <div className="flex items-center justify-between gap-4 mb-4">
                                                <div className="flex items-center gap-2 text-xs">
                                                    <span className="text-gray-400 font-bold uppercase">Show:</span>
                                                    <label className="flex items-center gap-1 cursor-pointer text-slate-300 hover:text-white">
                                                        <input type="checkbox" defaultChecked className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-0"
                                                            onChange={(e) => {
                                                                // TODO: filtering logic state not yet implemented fully, relying on visual scanning for MVP
                                                            }}
                                                        />
                                                        Local
                                                    </label>
                                                    <label className="flex items-center gap-1 cursor-pointer text-slate-300 hover:text-white">
                                                        <input type="checkbox" defaultChecked className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-0" />
                                                        National
                                                    </label>
                                                </div>
                                                {/* Moved Refresh Button */}
                                                <button
                                                    onClick={handleRediscoverCity}
                                                    title="Rediscover Media Landscape"
                                                    className="p-1 hover:bg-slate-800 rounded text-slate-500 hover:text-blue-400 transition-colors text-xs flex items-center gap-1 border border-slate-700 px-2"
                                                >
                                                    🔄 Refresh
                                                </button>
                                            </div>

                                            {selectedCityOutlets.length === 0 && (
                                                <div className="text-center py-4 text-gray-500 text-sm">
                                                    <p>No major outlets automatically found.</p>
                                                    <p>Try the Magic Import below!</p>
                                                </div>
                                            )}

                                            {/* Groups: Manual Top, then AI Sorted by Popularity */}
                                            {(() => {
                                                const manual = selectedCityOutlets.filter(o => o.origin === 'manual');
                                                const auto = selectedCityOutlets.filter(o => o.origin !== 'manual').sort((a, b) => (b.popularity || 0) - (a.popularity || 0));

                                                const renderOutlet = (outlet: any) => (
                                                    <div key={outlet.id} className={`group p-3 rounded transition-all border mb-2 ${selectedOutletIds.includes(outlet.id) ? 'bg-slate-800/80 border-blue-500/30' : 'bg-slate-900/50 border-slate-800 opacity-80 hover:opacity-100'}`}>
                                                        <div className="flex justify-between items-start">
                                                            <div className="flex items-center gap-2">
                                                                <input
                                                                    type="checkbox"
                                                                    checked={selectedOutletIds.includes(outlet.id)}
                                                                    onChange={() => toggleOutletSelection(outlet.id)}
                                                                    className="rounded bg-slate-700 border-slate-600 text-blue-500 focus:ring-0 cursor-pointer"
                                                                />
                                                                <div className="flex flex-col">
                                                                    <div className="flex items-center gap-2">
                                                                        <h4 className={`font-bold transition-colors ${selectedOutletIds.includes(outlet.id) ? 'text-blue-100' : 'text-slate-300'}`}>{outlet.name}</h4>
                                                                        {/* Focus Badge */}
                                                                        {outlet.focus === 'National' && <span className="px-1 py-0.5 rounded bg-indigo-900/50 text-indigo-300 text-[9px] uppercase font-bold border border-indigo-700/50">National</span>}
                                                                        {outlet.focus === 'Local and National' && <span className="px-1 py-0.5 rounded bg-purple-900/50 text-purple-300 text-[9px] uppercase font-bold border border-purple-700/50">Mixed</span>}
                                                                    </div>
                                                                    <div className="flex items-center gap-2 mt-0.5">
                                                                        <span className="text-[10px] uppercase font-mono text-slate-500">{outlet.type || 'Media'}</span>
                                                                        {/* Popularity Stars */}
                                                                        {(outlet.popularity > 0) && (
                                                                            <span className="text-[10px] text-amber-500/80 font-mono" title={`Popularity Score: ${outlet.popularity}/10`}>
                                                                                {"★".repeat(Math.min(outlet.popularity, 5))}
                                                                                <span className='opacity-30'>{"★".repeat(Math.max(0, 5 - outlet.popularity))}</span>
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            {outlet.origin === 'manual' && <span className="text-[9px] text-emerald-500 font-bold uppercase tracking-wider bg-emerald-900/20 px-1 rounded">Manually Added</span>}
                                                        </div>
                                                        {outlet.url && selectedOutletIds.includes(outlet.id) && (
                                                            <a
                                                                href={outlet.url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="mt-2 ml-6 block text-xs text-blue-400 hover:text-blue-300 hover:underline truncate"
                                                            >
                                                                {outlet.url}
                                                            </a>
                                                        )}
                                                    </div>
                                                );

                                                return (
                                                    <>
                                                        {manual.map(renderOutlet)}
                                                        {manual.length > 0 && auto.length > 0 && (
                                                            <div className="my-2 border-t border-slate-800 flex items-center justify-center">
                                                                <span className="bg-slate-900 px-2 text-[10px] text-slate-600 uppercase font-bold -mt-2.5">AI Discovered</span>
                                                            </div>
                                                        )}
                                                        {auto.map(renderOutlet)}
                                                    </>
                                                )
                                            })()}
                                            {editingOutletId !== null && ( // This block was moved outside the renderOutlet function
                                                <div className="flex gap-1 animate-in fade-in zoom-in duration-200 w-full">
                                                    <input
                                                        className="bg-slate-900 border border-blue-500 rounded text-xs px-1 py-0.5 flex-1 text-white outline-none"
                                                        value={editUrl}
                                                        onChange={e => setEditUrl(e.target.value)}
                                                        onKeyDown={e => {
                                                            if (e.key === 'Enter') handleUpdateOutlet(editingOutletId);
                                                            if (e.key === 'Escape') setEditingOutletId(null);
                                                        }}
                                                        autoFocus
                                                    />
                                                    <button onClick={() => handleUpdateOutlet(editingOutletId)} className="text-green-400 hover:text-green-300 px-1">✓</button>
                                                    <button onClick={() => setEditingOutletId(null)} className="text-slate-500 hover:text-slate-300 px-1">✕</button>
                                                </div>
                                            )}

                                        </div >
                                    )}

                                    {
                                        !showAddForm && !digestData && (
                                            <div className="p-4 border-t border-slate-700 mt-4">
                                                <button onClick={() => setShowAddForm(true)} className="w-full py-2 bg-slate-800 text-blue-400 rounded text-sm font-bold border border-slate-600 border-dashed hover:border-blue-500 transition-colors">+ Add Source</button>
                                            </div>
                                        )
                                    }

                                    {
                                        showAddForm && (
                                            <div className="p-4 border-t border-slate-700 space-y-2 mt-4">
                                                <input
                                                    className="w-full bg-slate-800 border-slate-600 rounded p-2 text-white text-xs"
                                                    placeholder="https://example.com"
                                                    value={importUrl}
                                                    onChange={e => setImportUrl(e.target.value)}
                                                />
                                                <div className="flex gap-2">
                                                    <button onClick={handleImportUrl} className="flex-1 bg-purple-600 text-white rounded py-1 text-xs font-bold hover:bg-purple-500">Import</button>
                                                    <button onClick={() => setShowAddForm(false)} className="px-3 bg-slate-700 text-gray-300 rounded py-1 text-xs hover:bg-slate-600">Cancel</button>
                                                </div>
                                            </div>
                                        )
                                    }
                                </>
                            ) : (
                                <div className="space-y-2">
                                    {savedDigests.length === 0 ? (
                                        <div className="text-center text-slate-500 py-6 px-2 flex flex-col gap-3">
                                            <div>No saved digests found for this city.</div>

                                            {/* Debug Info */}
                                            <div className="bg-slate-900 border border-slate-700/50 rounded p-2 text-[10px] font-mono text-left space-y-1 w-full overflow-hidden">
                                                <div className="text-slate-400">UID: <span className="text-white">{currentUser?.id}</span></div>
                                                <div className="text-slate-400">Name: <span className="text-white">{currentUser?.username}</span></div>
                                                <div className="text-slate-400">Status: <span className={digestFetchStatus.includes('error') ? "text-red-400" : "text-green-400"}>{digestFetchStatus}</span></div>
                                            </div>

                                            <button onClick={fetchSavedDigests} className="text-xs text-blue-400 hover:text-blue-300 underline">
                                                Refresh List
                                            </button>
                                        </div>
                                    ) : (
                                        (savedDigests || [])
                                            // Left Sidebar: Show ONLY digests for current city
                                            .filter((d: any) => !selectedCityName || d.city === selectedCityName)
                                            .map((digest: any) => {
                                                const createdAt = digest.created_at || new Date().toISOString();
                                                const end = new Date(createdAt);
                                                if (isNaN(end.getTime())) {
                                                    // Fallback for invalid dates
                                                    const safeDate = new Date();
                                                    end.setTime(safeDate.getTime());
                                                }
                                                const start = new Date(end);

                                                if (digest.timeframe === "24h") start.setDate(end.getDate() - 1);
                                                else if (digest.timeframe === "3days") start.setDate(end.getDate() - 3);
                                                else if (digest.timeframe === "1week") start.setDate(end.getDate() - 7);
                                                else if (digest.timeframe === "1month") start.setDate(end.getDate() - 30);

                                                const f = (d: Date) => d.getDate().toString().padStart(2, '0') + "." + (d.getMonth() + 1).toString().padStart(2, '0');
                                                const y = (d: Date) => d.getFullYear();
                                                const dateRange = `${f(start)} - ${f(end)}.${y(end)}`;

                                                const title = digest.title || "";
                                                const cat = digest.category || "";
                                                const showCategory = cat && !title.toLowerCase().includes(cat.toLowerCase());

                                                // Marquee Logic: Check length (approx chars)
                                                const isLongTitle = title.length > 28;

                                                return (
                                                    <div
                                                        key={digest.id}
                                                        onClick={() => handleLoadDigest(digest)}
                                                        className="bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-blue-500 p-3 rounded cursor-pointer transition-all group"
                                                    >
                                                        <div className="flex justify-between items-start mb-1 overflow-hidden">
                                                            <div className="flex-1 overflow-hidden relative h-5">
                                                                <h4 className={`font-bold text-slate-200 text-sm whitespace-nowrap absolute left-0 top-0 ${isLongTitle ? 'group-hover:animate-marquee' : ''}`}>
                                                                    {title}
                                                                </h4>
                                                            </div>
                                                            {/* Delete only if Owner - Relaxed Check & Always Visible */}
                                                            {/* Delete only if Owner */}
                                                            {currentUser && String(digest.owner_id) === String(currentUser.id) && (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleDeleteDigest(digest.id);
                                                                    }}
                                                                    className="text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded p-1 transition-colors ml-1 z-10 bg-slate-800/50"
                                                                    title="Delete Digest"
                                                                >
                                                                    <Trash2 size={12} />
                                                                </button>
                                                            )}
                                                        </div>
                                                        <div className="text-[10px] text-slate-500 mb-1">
                                                            by <span className="text-slate-400 font-medium">{getOwnerName(digest)}</span>
                                                        </div>
                                                        <div className="flex flex-col gap-0.5 text-[10px] text-slate-500 font-medium mt-1">
                                                            <div className="flex items-center gap-2 uppercase font-bold">
                                                                {digest.city && <span className="text-blue-400">{digest.city}</span>}
                                                                {showCategory && <span>• {cat}</span>}
                                                                {digest.is_public && (
                                                                    <span className="flex items-center gap-0.5 text-emerald-400 bg-emerald-900/30 px-1 rounded border border-emerald-800/50 text-[9px] transform scale-90" title="Public Link Active">
                                                                        <GlobeIcon size={8} /> Public
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="text-slate-400">
                                                                {dateRange}
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            }))}
                                </div>
                            )}
                        </div>
                    </div>
                )
            }


            {
                debugTarget && (
                    <ScraperDebugger
                        isOpen={scraperDebuggerOpen}
                        onClose={() => setScraperDebuggerOpen(false)}
                        initialUrl={debugTarget.url}
                        domain={debugTarget.domain}

                        onSave={handleRulesUpdated}
                        onSaving={handleRuleSaving}
                    />
                )
            }
            {/* Right Sidebar - Global Digests */}
            <div className={`absolute right-0 top-20 z-40 transition-all duration-300 ease-in-out ${isGlobalSidebarOpen ? 'w-80' : 'w-0'} h-[calc(100vh-100px)]`}>
                {/* Toggle Handle - Custom Tall Arrow */}
                <button
                    onClick={() => setIsGlobalSidebarOpen(!isGlobalSidebarOpen)}
                    className={`absolute -left-5 top-1/2 -translate-y-1/2 bg-slate-900 border border-slate-600 border-r-0 rounded-l-lg 
                        h-24 w-5 flex items-center justify-center hover:bg-slate-800 hover:text-blue-400 text-slate-500 shadow-[0_0_15px_rgba(0,0,0,0.5)] transition-all group overflow-hidden`}
                    title="Toggle Global Digests"
                >
                    <div className={`transition-transform duration-500 ${isGlobalSidebarOpen ? 'rotate-180' : ''}`}>
                        <svg width="10" height="40" viewBox="0 0 10 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M8 2L2 20L8 38" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </div>
                </button>

                {/* Content Panel */}
                <div className="w-full h-full bg-slate-900/95 backdrop-blur border-l border-slate-700 shadow-2xl overflow-hidden flex flex-col">
                    <div className="p-4 border-b border-slate-700 bg-slate-900 sticky top-0 z-10">
                        <h3 className="font-bold text-white text-lg flex items-center gap-2 mb-2">
                            <List size={18} className="text-blue-400" />
                            Global Stream
                        </h3>

                        <div className="flex bg-slate-800 rounded p-1">
                            <button
                                onClick={() => setGlobalStreamTab('stream')}
                                className={`flex-1 text-xs font-bold py-1.5 rounded transition-all ${globalStreamTab === 'stream' ? 'bg-slate-700 text-blue-400 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                Stream
                            </button>
                            <button
                                onClick={() => setGlobalStreamTab('my')}
                                className={`flex-1 text-xs font-bold py-1.5 rounded transition-all ${globalStreamTab === 'my' ? 'bg-slate-700 text-blue-400 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                My Digests
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                        {(savedDigests || [])
                            .filter((d: any) => {
                                if (globalStreamTab === 'my') {
                                    return currentUser && d.owner_id === currentUser.id;
                                }
                                return true; // Show all
                            })
                            .length === 0 ? (
                            <div className="text-center text-slate-500 py-8 text-sm">
                                {globalStreamTab === 'my' ? "You haven't saved any digests." : "No digests found."}
                            </div>
                        ) : (
                            (savedDigests || []).map((digest: any) => {
                                const end = new Date(digest.created_at);
                                const start = new Date(end);
                                if (digest.timeframe === "24h") start.setDate(end.getDate() - 1);
                                else if (digest.timeframe === "3days") start.setDate(end.getDate() - 3);
                                else if (digest.timeframe === "1week") start.setDate(end.getDate() - 7);
                                else if (digest.timeframe === "1month") start.setDate(end.getDate() - 30);

                                const f = (d: Date) => d.getDate().toString().padStart(2, '0') + "." + (d.getMonth() + 1).toString().padStart(2, '0');
                                const y = (d: Date) => d.getFullYear();
                                const dateRange = `${f(start)} - ${f(end)}.${y(end)}`;
                                const title = digest.title || "";
                                const cat = digest.category || "";
                                const showCategory = cat && !title.toLowerCase().includes(cat.toLowerCase());

                                // Marquee Logic
                                const isLongTitle = title.length > 28;

                                return (
                                    <div
                                        key={digest.id}
                                        onClick={() => handleLoadDigest(digest)}
                                        className="bg-slate-800/50 hover:bg-slate-800 border border-slate-700 hover:border-blue-500 p-3 rounded cursor-pointer transition-all group mb-2"
                                    >
                                        <div className="relative">
                                            <div className="flex justify-between items-start pr-8 overflow-hidden">
                                                {isLongTitle ? (
                                                    <div className="w-full overflow-hidden">
                                                        <div className="flex whitespace-nowrap group-hover:animate-marquee-seamless w-max">
                                                            <h4 className="font-bold text-slate-200 text-sm mr-8">{title}</h4>
                                                            <h4 className="font-bold text-slate-200 text-sm mr-8">{title}</h4>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <h4 className="font-bold text-slate-200 text-sm whitespace-nowrap overflow-hidden text-ellipsis">
                                                        {title}
                                                    </h4>
                                                )}
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (confirm("Delete this digest?")) handleDeleteDigest(digest.id!);
                                                }}
                                                className="absolute top-0 right-0 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded p-1 transition-colors z-10"
                                                title="Delete Digest"
                                            >
                                                <Trash2 size={12} />
                                            </button>
                                            <div className="flex flex-col gap-0.5 text-[10px] text-slate-500 font-medium mt-1">
                                                <div className="flex items-center gap-2 uppercase font-bold flex-wrap">
                                                    {digest.city && <span className="text-blue-400 bg-blue-900/20 px-1 rounded">{digest.city}</span>}
                                                    {showCategory && <span className="text-slate-400">• {cat}</span>}
                                                    {digest.is_public && (
                                                        <span className="flex items-center gap-0.5 text-emerald-400 bg-emerald-900/30 px-1 rounded border border-emerald-800/50 text-[9px] transform scale-90" title="Public Link Active">
                                                            <GlobeIcon size={8} /> Public
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-slate-600 font-mono mt-0.5">
                                                    {dateRange}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>

            {/* Settings Button (Top Right Fixed) */}
            {
                !digestData && (
                    <>
                        <button
                            onClick={() => setVizMode(prev => prev === '3d' ? '2d' : '3d')}
                            className="fixed top-4 right-32 z-40 p-2 bg-slate-900/80 backdrop-blur border border-slate-700 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition-all shadow-xl w-10 h-10 flex items-center justify-center font-bold text-xs"
                            title={vizMode === '3d' ? "Switch to 2D Sprites" : "Switch to 3D Geometry"}
                        >
                            {vizMode === '3d' ? '2D' : '3D'}
                        </button>

                        <button
                            onClick={() => setIsSettingsOpen(true)}
                            className="fixed top-4 right-4 z-40 p-2 bg-slate-900/80 backdrop-blur border border-slate-700 rounded-full text-slate-400 hover:text-white hover:bg-slate-800 transition-all shadow-xl"
                            title="User Settings"
                        >
                            <Settings size={20} />
                        </button>
                    </>
                )
            }

            {/* Settings Modal */}
            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

            {/* Global Analytics Tooltip */}
            {
                activeTooltip && activeTooltip.rect && (
                    <div
                        className="fixed z-[9999] w-80 bg-slate-950 backdrop-blur-xl border border-slate-700 rounded-xl shadow-[0_0_50px_rgba(0,0,0,0.8)] p-4 text-xs text-left cursor-auto animate-in fade-in zoom-in-95 duration-200"
                        style={{
                            top: activeTooltip.placement === 'bottom'
                                ? activeTooltip.rect.bottom + 8
                                : activeTooltip.rect.top - 8 - (200),
                            left: activeTooltip.rect.left + (activeTooltip.rect.width / 2) - 160,
                        }}
                        onMouseEnter={() => {
                            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
                        }}
                        onMouseLeave={() => {
                            if (isTooltipLocked) return;
                            hoverTimeout.current = setTimeout(() => {
                                setActiveTooltip(null);
                                setIsTooltipLocked(false);
                            }, 150);
                        }}
                    >
                        <div className="flex justify-between items-start border-b border-slate-800 pb-2 mb-3">
                            <div className="font-bold text-white text-base">
                                {isAnalyticsTranslated && activeTooltip.data?.translation ? activeTooltip.data.translation : activeTooltip.word}
                                {isTooltipLocked && <span className="ml-2 text-[10px] text-blue-400 border border-blue-900 bg-blue-950/50 px-1 rounded align-middle">LOCKED</span>}
                            </div>
                            <div className="flex flex-col items-end gap-1">
                                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${activeTooltip.data?.sentiment === 'Positive' ? 'bg-green-900/50 text-green-400 border border-green-800' : activeTooltip.data?.sentiment === 'Negative' ? 'bg-red-900/50 text-red-400 border border-red-800' : 'bg-slate-800 text-slate-400 border border-slate-700'}`}>
                                    {activeTooltip.data?.sentiment}
                                </span>
                                <div className="text-[10px] text-white/30 font-mono">v{APP_VERSION}</div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-1">
                                Found in {activeTooltip.data?.sources?.length || 0} sources
                            </div>
                            <ul className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar pr-1">
                                {activeTooltip.data?.sources && activeTooltip.data.sources.length > 0 ? (
                                    activeTooltip.data.sources.map((src: any, idx: number) => (
                                        <li key={idx} className="flex flex-col gap-0.5 bg-slate-900/50 p-2 rounded hover:bg-slate-900 transition-colors border border-white/5">
                                            <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 hover:underline font-medium line-clamp-2 leading-tight">
                                                {src.title}
                                            </a>
                                            <span className="text-[10px] text-slate-500">{src.source}</span>
                                        </li>
                                    ))
                                ) : (
                                    <li className="text-slate-600 italic">No direct sources mapped.</li>
                                )}
                            </ul>
                        </div>
                    </div>
                )
            }

            {/* Support / Donation Button */}
            <a
                href="https://buymeacoffee.com/urbanous"
                target="_blank"
                rel="noopener noreferrer"
                title="Support OpenNews"
                className="absolute top-4 right-16 z-20 p-2 rounded-lg bg-yellow-500/90 text-white shadow-lg shadow-yellow-500/20 hover:bg-yellow-400 hover:scale-110 transition-all flex items-center gap-2 font-bold text-sm"
            >
                <Coffee className="w-5 h-5" />
                <span className="hidden group-hover:block whitespace-nowrap">Support Us</span>
            </a>

            {/* Spotlight Search Overlay */}
            {
                isSpotlightOpen && (
                    <div className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 transition-opacity" onClick={() => setIsSpotlightOpen(false)}>
                        <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200" onClick={e => e.stopPropagation()}>
                            <div className="p-4 border-b border-slate-800 flex items-center gap-3">
                                <Search className="w-5 h-5 text-slate-400" />
                                <input
                                    autoFocus
                                    className="flex-1 bg-transparent border-none outline-none text-white placeholder-slate-500 text-lg"
                                    placeholder="Search City..."
                                    value={spotlightQuery}
                                    onChange={e => {
                                        setSpotlightQuery(e.target.value);
                                        setSpotlightSelectedIndex(0);
                                    }}
                                    onKeyDown={e => {
                                        const candidates = cities
                                            .filter(c => c.name.toLowerCase().includes(spotlightQuery.toLowerCase()))
                                            .slice(0, 8);

                                        if (e.key === 'ArrowDown') {
                                            e.preventDefault();
                                            setSpotlightSelectedIndex(prev => (prev + 1) % candidates.length);
                                        } else if (e.key === 'ArrowUp') {
                                            e.preventDefault();
                                            setSpotlightSelectedIndex(prev => (prev - 1 + candidates.length) % candidates.length);
                                        } else if (e.key === 'Enter') {
                                            e.preventDefault();
                                            const match = candidates[spotlightSelectedIndex];
                                            if (match) {
                                                handleSearchSelect(match);
                                                setIsSpotlightOpen(false);
                                                setSpotlightQuery('');
                                                setSpotlightSelectedIndex(0);
                                            }
                                        }
                                    }}
                                />
                                <div className="flex gap-2">
                                    <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">ESC</span>
                                </div>
                            </div>
                            {spotlightQuery && (
                                <div className="max-h-[300px] overflow-y-auto">
                                    {cities
                                        .filter(c => c.name.toLowerCase().includes(spotlightQuery.toLowerCase()))
                                        .slice(0, 8)
                                        .map((city: any, idx: number) => (
                                            <button
                                                key={city.id || city.name}
                                                className={`w-full text-left px-4 py-3 flex items-center justify-between group transition-colors ${idx === spotlightSelectedIndex ? 'bg-slate-800 border-l-2 border-blue-500' : 'hover:bg-slate-800/50 border-l-2 border-transparent'}`}
                                                onClick={() => {
                                                    handleSearchSelect(city);
                                                    setIsSpotlightOpen(false);
                                                    setSpotlightQuery('');
                                                }}
                                                onMouseEnter={() => setSpotlightSelectedIndex(idx)}
                                            >
                                                <span className={`font-medium ${idx === spotlightSelectedIndex ? 'text-white' : 'text-slate-200 group-hover:text-white'}`}>{city.name}</span>
                                                <span className="text-xs text-slate-500 uppercase">{city.country_code}</span>
                                            </button>
                                        ))}
                                    {cities.filter(c => c.name.toLowerCase().includes(spotlightQuery.toLowerCase())).length === 0 && (
                                        <div className="p-4 text-center text-slate-500 italic">No cities found</div>
                                    )}
                                </div>
                            )}
                            {!spotlightQuery && (
                                <div className="p-8 text-center text-slate-600 text-sm">
                                    Type to fly to a city...
                                </div>
                            )}
                        </div>
                    </div>
                )
            }

            {/* Version Indicator */}
            <div className="absolute bottom-2 right-2 z-[100] text-[10px] text-white/30 font-mono hover:text-white/80 cursor-default select-none transition-colors">
                v{APP_VERSION} Sprite Viz
            </div>
        </div >
    );
}
