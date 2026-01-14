import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import api from '@/lib/api'; // Use shared api client

interface ScraperDebuggerProps {
    isOpen: boolean;
    onClose: () => void;
    initialUrl: string;
    domain: string;
    onSave?: (domain: string, result?: TestResult, config?: any) => void;
    onSaving?: () => void; // New: Trigger when save starts
    onDateExtracted?: (date: string) => void;
    initialMode?: 'date' | 'title';
}

interface TestResult {
    status: string;
    extracted_date: string | null;
    extracted_title?: string | null;
    used_rule: any;
    error?: string;
}

const ScraperDebugger: React.FC<ScraperDebuggerProps> = ({ isOpen, onClose, initialUrl, domain, onSave, onSaving, onDateExtracted, initialMode = 'date' }) => {
    const [testUrl, setTestUrl] = useState(initialUrl);
    const [targetType, setTargetType] = useState<'date' | 'title'>(initialMode);

    // Config State
    const [selectors, setSelectors] = useState("");
    const [regex, setRegex] = useState("");
    const [titleSelectors, setTitleSelectors] = useState(""); // New: Title Selectors
    const [useJsonLd, setUseJsonLd] = useState(true);
    const [useDataLayer, setUseDataLayer] = useState(false);
    const [dataLayerVar, setDataLayerVar] = useState("dataLayer");

    useEffect(() => {
        if (targetType === 'title') setActiveMode('selectors');
    }, [targetType]);

    const [loading, setLoading] = useState(false);
    const [testResult, setTestResult] = useState<TestResult | null>(null);
    const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

    // Load existing rule on mount
    useEffect(() => {
        if (isOpen && domain) {
            // Reset state
            setTestUrl(initialUrl);
            setTestResult(null);
            setLoading(false);
            setSaveStatus("idle");

            // Fetch rules
            // Ideally we iterate local list or have a specific endpoint. 
            // For now, let's just list all and find match, or assume defaults.
            // TODO: Add specific GET /scraper/rules/{domain} if list grows too big.
            api.get('/scraper/rules')
                .then(res => {
                    const rule = res.data.find((r: any) => r.domain === domain);
                    if (rule) {
                        setSelectors(rule.config.date_selectors?.join(", ") || "");
                        setRegex(rule.config.date_regex?.join(", ") || "");
                        setTitleSelectors(rule.config.title_selectors?.join(", ") || "");

                        setUseJsonLd(rule.config.use_json_ld ?? true);
                        setUseDataLayer(rule.config.use_data_layer ?? false);
                        setDataLayerVar(rule.config.data_layer_var || "dataLayer");
                    } else {
                        // clear defaults
                        setSelectors("");
                        setRegex("");
                        setTitleSelectors("");

                        setUseJsonLd(true);
                        setUseDataLayer(false);
                    }
                })
                .catch(err => console.error("Failed to load rules", err));
        }
    }, [isOpen, domain, initialUrl]);

    const handleTest = async () => {
        setLoading(true);
        setTestResult(null);
        try {
            const config = {
                domain: domain,
                date_selectors: selectors ? selectors.split(",").map(s => s.trim()).filter(s => s) : [],
                date_regex: regex ? regex.split(",").map(s => s.trim()).filter(s => s) : [],
                title_selectors: titleSelectors ? titleSelectors.split(",").map(s => s.trim()).filter(s => s) : [],
                use_json_ld: useJsonLd,
                use_data_layer: useDataLayer,
                data_layer_var: dataLayerVar
            };

            const response = await api.post('/scraper/test', {
                url: testUrl,
                rule_config: config
            });

            setTestResult(response.data);

            // Trigger update if successful
            if (response.data.extracted_date && onDateExtracted) {
                onDateExtracted(response.data.extracted_date);
            }
            return response.data;
        } catch (error: any) {
            const errResult: TestResult = {
                status: "error",
                extracted_date: null,
                used_rule: null,
                error: error.response?.data?.detail || error.message
            }
            setTestResult(errResult);
            return errResult;
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaveStatus("saving");
        if (onSaving) onSaving(); // Trigger spinner immediately
        try {
            const config = {
                domain: domain,
                date_selectors: selectors ? selectors.split(",").map(s => s.trim()).filter(s => s) : [],
                date_regex: regex ? regex.split(",").map(s => s.trim()).filter(s => s) : [],
                title_selectors: titleSelectors ? titleSelectors.split(",").map(s => s.trim()).filter(s => s) : [],
                use_json_ld: useJsonLd,
                use_data_layer: useDataLayer,
                data_layer_var: dataLayerVar
            };

            await api.post('/scraper/rules', config);
            setSaveStatus("saved");

            // Auto-Run Test to update UI immediately
            const latestResult = await handleTest();

            setTimeout(() => setSaveStatus("idle"), 2000);
            // Schema matching ScraperRuleCreate for backend
            const ruleConfigForBackend = {
                domain: domain,
                date_selectors: config.date_selectors,
                date_regex: config.date_regex,
                title_selectors: config.title_selectors,
                use_json_ld: config.use_json_ld,
                use_data_layer: config.use_data_layer,
                data_layer_var: config.data_layer_var
            };
            if (onSave) onSave(domain, latestResult, ruleConfigForBackend);
        } catch (error) {
            console.error("Save failed", error);
            setSaveStatus("error");
        }
    };

    type ExtractionMode = 'selectors' | 'regex' | 'datalayer' | 'jsonld';
    const [activeMode, setActiveMode] = useState<ExtractionMode>('selectors');

    const MODES: { id: ExtractionMode, label: string, icon: string }[] = [
        { id: 'selectors', label: 'CSS Selectors', icon: '🎯' },
        { id: 'regex', label: 'Regex Pattern', icon: '🧩' },
        { id: 'datalayer', label: 'JS DataLayer', icon: '📦' },
        { id: 'jsonld', label: 'JSON-LD', icon: '📝' },
    ];

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl shadow-2xl max-h-[90vh] overflow-y-auto flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/50">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <span className="text-blue-400">🔧</span> Debug Extraction
                    </h2>

                    {/* Target Toggle */}
                    <div className="flex bg-slate-800 p-1 rounded-lg">
                        <button
                            onClick={() => setTargetType('date')}
                            className={`px-3 py-1 text-xs font-bold rounded transition-colors ${targetType === 'date' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Date
                        </button>
                        <button
                            onClick={() => setTargetType('title')}
                            className={`px-3 py-1 text-xs font-bold rounded transition-colors ${targetType === 'title' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                        >
                            Title
                        </button>
                    </div>

                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors text-2xl leading-none">&times;</button>
                </div>

                <div className="p-4 bg-slate-900 border-b border-slate-800">
                    <div className="text-xs font-mono text-slate-500 mb-2 uppercase font-bold tracking-wider">Target Domain</div>
                    <div className="text-yellow-400 font-mono text-sm bg-yellow-900/20 py-1 px-2 rounded border border-yellow-700/30 inline-block">
                        {domain}
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                    {/* Mode Tabs */}
                    <div className="flex border-b border-slate-800 bg-slate-900/50 sticky top-0 z-10 backdrop-blur">
                        {MODES.filter(m => targetType === 'date' || m.id === 'selectors').map(mode => (
                            <button
                                key={mode.id}
                                onClick={() => setActiveMode(mode.id)}
                                className={`flex-1 py-3 text-sm font-medium transition-all relative
                                    ${activeMode === mode.id ? 'text-blue-400' : 'text-slate-500 hover:text-slate-300'}
                                `}
                            >
                                <span className="flex items-center justify-center gap-2">
                                    <span>{mode.icon}</span> {mode.label}
                                </span>
                                {activeMode === mode.id && (
                                    <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
                                )}
                            </button>
                        ))}
                    </div>

                    <div className="p-6 space-y-6">
                        {/* Tab Content */}
                        <div className="min-h-[200px]">
                            {activeMode === 'selectors' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-left-4 duration-200">
                                    <div className="p-4 bg-blue-900/10 border border-blue-900/30 rounded-lg mb-4">
                                        <h3 className="text-sm font-bold text-blue-200 mb-2">Strategy: HTML Elements ({targetType === 'title' ? 'Title' : 'Date'})</h3>
                                        <p className="text-xs text-blue-300/70">
                                            Extracts text from specific HTML tags. Use typical CSS selectors like classes or IDs.
                                        </p>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-mono text-slate-400 mb-1 uppercase">
                                            {targetType === 'title' ? 'Title Selectors' : 'Date Selectors'} (comma separated)
                                        </label>
                                        <input
                                            type="text"
                                            value={targetType === 'title' ? titleSelectors : selectors}
                                            onChange={e => targetType === 'title' ? setTitleSelectors(e.target.value) : setSelectors(e.target.value)}
                                            placeholder={targetType === 'title' ? "h1.entry-title, .post-title" : ".post-date, time.entry-date"}
                                            className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:ring-2 focus:ring-blue-500 outline-none font-mono"
                                        />
                                        <p className="text-[10px] text-slate-500 mt-1">Example: <code className="bg-slate-800 px-1 rounded">span.date, .meta-time</code></p>
                                    </div>
                                </div>
                            )}

                            {activeMode === 'regex' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-left-4 duration-200">
                                    <div className="p-4 bg-purple-900/10 border border-purple-900/30 rounded-lg mb-4">
                                        <h3 className="text-sm font-bold text-purple-200 mb-2">Strategy: Regex Pattern</h3>
                                        <p className="text-xs text-purple-300/70">
                                            Scans the entire page text for a specific pattern. Useful when the date is just text inside a large paragraph.
                                        </p>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-mono text-slate-400 mb-1 uppercase">Regex Patterns (comma separated)</label>
                                        <input
                                            type="text"
                                            value={regex}
                                            onChange={e => setRegex(e.target.value)}
                                            placeholder="la\s+(\d{2}\.\d{2}\.\d{4})"
                                            className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-sm text-white focus:ring-2 focus:ring-purple-500 outline-none font-mono"
                                        />
                                        <p className="text-[10px] text-slate-500 mt-1">
                                            Tip: Use parentheses <code>()</code> to capture the date part. <br />
                                            Example: <code>Published on: (\d\d-\d\d-\d\d\d\d)</code>
                                        </p>
                                    </div>
                                </div>
                            )}

                            {activeMode === 'datalayer' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-left-4 duration-200">
                                    <div className="p-4 bg-emerald-900/10 border border-emerald-900/30 rounded-lg mb-4">
                                        <h3 className="text-sm font-bold text-emerald-200 mb-2">Strategy: JavaScript DataLayer</h3>
                                        <p className="text-xs text-emerald-300/70">
                                            Extracts date from global JavaScript variables (common in larger news sites).
                                        </p>
                                    </div>
                                    <label className="flex items-center gap-3 cursor-pointer group bg-slate-800 p-3 rounded border border-slate-700">
                                        <input
                                            type="checkbox"
                                            checked={useDataLayer}
                                            onChange={e => setUseDataLayer(e.target.checked)}
                                            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-slate-900"
                                        />
                                        <span className="text-sm text-slate-200 group-hover:text-white font-bold">Enable DataLayer Extraction</span>
                                    </label>

                                    {useDataLayer && (
                                        <div className="pl-7">
                                            <label className="block text-xs font-mono text-slate-400 mb-1 uppercase">Variable Name</label>
                                            <input
                                                type="text"
                                                value={dataLayerVar}
                                                onChange={e => setDataLayerVar(e.target.value)}
                                                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-white font-mono focus:ring-emerald-500 border-emerald-500/50"
                                                placeholder="dataLayer"
                                            />
                                            <p className="text-[10px] text-slate-500 mt-1">Default is `dataLayer`. Sometimes `adobeDataLayer` or `sp_layer`.</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {activeMode === 'jsonld' && (
                                <div className="space-y-4 animate-in fade-in slide-in-from-left-4 duration-200">
                                    <div className="p-4 bg-orange-900/10 border border-orange-900/30 rounded-lg mb-4">
                                        <h3 className="text-sm font-bold text-orange-200 mb-2">Strategy: Semantic Metadata (JSON-LD)</h3>
                                        <p className="text-xs text-orange-300/70">
                                            Checks for hidden Schema.org metadata (e.g. <code>datePublished</code>). This is often the most reliable method.
                                        </p>
                                    </div>
                                    <label className="flex items-center gap-3 cursor-pointer group bg-slate-800 p-3 rounded border border-slate-700">
                                        <input
                                            type="checkbox"
                                            checked={useJsonLd}
                                            onChange={e => setUseJsonLd(e.target.checked)}
                                            className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-orange-500 focus:ring-orange-500 focus:ring-offset-slate-900"
                                        />
                                        <span className="text-sm text-slate-200 group-hover:text-white font-bold">Use JSON-LD Schema</span>
                                    </label>
                                </div>
                            )}
                        </div>

                        {/* Test Area */}
                        <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 mt-6">
                            <h4 className="text-xs font-bold text-slate-500 uppercase mb-3 text-center border-b border-slate-800 pb-2">Verification</h4>
                            <div className="flex gap-2 mb-4">
                                <input
                                    type="text"
                                    value={testUrl}
                                    onChange={e => setTestUrl(e.target.value)}
                                    placeholder="https://example.com/article-123"
                                    className="flex-1 bg-slate-900 border border-slate-700 rounded-md px-3 py-2 text-sm text-blue-300 font-mono focus:ring-1 focus:ring-blue-500 outline-none"
                                />
                                <button
                                    onClick={handleTest}
                                    disabled={loading}
                                    className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {loading ? (
                                        <>⏳ Testing...</>
                                    ) : (
                                        <>🚀 Test Mode</>
                                    )}
                                </button>
                            </div>

                            {testResult && (
                                <div className={`p-4 rounded border animate-in zoom-in duration-200 ${testResult.extracted_date ? 'bg-green-950/30 border-green-900/50' : 'bg-red-950/30 border-red-900/50'}`}>
                                    {testResult.error ? (
                                        <div className="text-red-400 text-sm font-mono">
                                            Error: {testResult.error}
                                        </div>
                                    ) : (
                                        <div className="flex flex-col gap-4">
                                            {/* Date Result */}
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold mb-1">Extracted Date</div>
                                                    <div className={`text-xl font-mono font-bold ${testResult.extracted_date ? 'text-green-400' : 'text-red-400'}`}>
                                                        {testResult.extracted_date || "NULL"}
                                                    </div>
                                                    <div className="text-[10px] text-slate-600 mt-1">Rule Used: {JSON.stringify(testResult.used_rule?.date_selectors || testResult.used_rule?.date_regex || "Default")}</div>
                                                </div>
                                                {testResult.extracted_date && targetType === 'date' && (
                                                    <div className="text-4xl">✅</div>
                                                )}
                                            </div>

                                            {/* Title Result (Only show if present or target is title) */}
                                            {(testResult.extracted_title || targetType === 'title') && (
                                                <div className="flex items-center justify-between border-t border-slate-800 pt-3">
                                                    <div>
                                                        <div className="text-[10px] uppercase tracking-wide text-slate-500 font-bold mb-1">Extracted Title</div>
                                                        <div className={`text-md font-bold text-white`}>
                                                            {testResult.extracted_title || "NULL"}
                                                        </div>
                                                    </div>
                                                    {testResult.extracted_title && targetType === 'title' && (
                                                        <div className="text-4xl">✅</div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                        </div>
                    </div>
                </div>

                <div className="p-4 border-t border-slate-800 bg-slate-950/50 flex justify-end gap-3 rounded-b-xl">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors text-sm"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saveStatus === 'saving'}
                        className={`px-6 py-2 rounded-md text-white font-medium transition-all transform active:scale-95 flex items-center gap-2 shadow-lg
                            ${saveStatus === 'saved' ? 'bg-green-600' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500'}
                        `}
                    >
                        {saveStatus === 'saving' && (
                            <>
                                <Loader2 className="animate-spin" size={16} />
                                Saving & Updating...
                            </>
                        )}
                        {saveStatus === 'saved' && "Saved! ✨"}
                        {saveStatus === 'idle' && "💾 Save Configuration"}
                        {saveStatus === 'error' && "Error Saving"}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ScraperDebugger;
