'use client';

import { useState, useEffect } from 'react';
import { X, Save, Key, Loader2, LogOut } from 'lucide-react';
import api from '@/lib/api';
import { useAuthStore } from '@/lib/store';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [apiKey, setApiKey] = useState('');
    const [email, setEmail] = useState('');
    const [preferredLanguage, setPreferredLanguage] = useState('English');
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const { isAuthenticated, logout } = useAuthStore();

    useEffect(() => {
        if (isOpen) {
            if (!isAuthenticated) return; // Skip fetch for guests

            setIsLoading(true);
            setMessage(null);

            // AbortController for cleanup ONLY (not timeout)
            const controller = new AbortController();

            api.get('/users/me', {
                signal: controller.signal,
                timeout: 8000 // Use Axios timeout for actual server timeout
            })
                .then(res => {
                    setEmail(res.data.email);
                    setApiKey(res.data.gemini_api_key || '');
                    setPreferredLanguage(res.data.preferred_language || 'English');
                    setIsLoading(false);
                })
                .catch(err => {
                    // Ignore component unmount cleanup
                    if (err.name === 'Canceled') return;

                    console.error("Failed to fetch user settings", err);

                    if (err.code === 'ECONNABORTED') {
                        setMessage({ type: 'error', text: 'Server timed out. Please try again.' });
                    } else {
                        setMessage({ type: 'error', text: 'Failed to load settings' });
                    }
                    setIsLoading(false);
                });

            return () => {
                controller.abort();
            };
        }
    }, [isOpen]);

    const handleSave = async () => {
        setIsSaving(true);
        setMessage(null);
        try {
            // Using new unified endpoint
            await api.put('/users/me/settings', {
                api_key: apiKey,
                preferred_language: preferredLanguage
            });
            setMessage({ type: 'success', text: 'Settings saved successfully!' });
            // Close after short delay
            setTimeout(() => {
                onClose();
            }, 1000);
        } catch (err: any) {
            setMessage({ type: 'error', text: 'Failed to save settings' });
        } finally {
            setIsSaving(false);
        }
    };

    const LANGUAGES = ["English", "Romanian", "Russian", "German", "French", "Spanish", "Italian"];

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <Key className="w-5 h-5 text-blue-400" />
                        Settings
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {isLoading ? (
                        <div className="flex justify-center py-8 text-blue-400">
                            <Loader2 className="w-8 h-8 animate-spin" />
                        </div>
                    ) : (
                        <>
                            {/* Guest View */}
                            {!email && !isLoading ? (
                                <div className="text-center py-8 space-y-4">
                                    <p className="text-slate-400 text-sm">You are currently browsing as a guest.</p>
                                    <p className="text-slate-500 text-xs">Log in to access AI features and save your preferences.</p>
                                    <button
                                        onClick={() => { window.location.href = "/login"; }}
                                        className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-bold text-sm transition-colors"
                                    >
                                        Log In
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div>
                                        <label className="block text-xs uppercase text-slate-500 font-bold mb-1">Authenticated As</label>
                                        <div className="text-slate-300 font-mono text-sm">{email}</div>
                                    </div>

                                    <div>
                                        <label className="block text-xs uppercase text-slate-500 font-bold mb-2">Gemini API Key</label>
                                        <input
                                            type="text"
                                            value={apiKey}
                                            onChange={(e) => setApiKey(e.target.value)}
                                            className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-white font-mono text-xs focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder:text-slate-700"
                                            placeholder="Enter your Google Gemini API Key"
                                        />
                                        <p className="mt-2 text-[10px] text-slate-500">
                                            This key is used for all AI agents (Discovery, Digest, Sentiment).
                                        </p>
                                    </div>

                                    <div>
                                        <label className="block text-xs uppercase text-slate-500 font-bold mb-2">Translation Language</label>
                                        <select
                                            value={preferredLanguage}
                                            onChange={(e) => setPreferredLanguage(e.target.value)}
                                            className="w-full bg-slate-950 border border-slate-700 rounded p-3 text-white text-sm focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                                        >
                                            {LANGUAGES.map(lang => (
                                                <option key={lang} value={lang}>{lang}</option>
                                            ))}
                                        </select>
                                        <p className="mt-2 text-[10px] text-slate-500">
                                            Target language for title translation in digests.
                                        </p>
                                    </div>

                                    {message && (
                                        <div className={`p-3 rounded text-xs border ${message.type === 'success' ? 'bg-green-900/20 border-green-800 text-green-400' : 'bg-red-900/20 border-red-800 text-red-400'}`}>
                                            {message.text}
                                        </div>
                                    )}

                                    <div className="pt-4 flex gap-3">
                                        <button
                                            onClick={handleSave}
                                            disabled={isSaving}
                                            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-bold text-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                                        >
                                            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                            Save Changes
                                        </button>
                                    </div>

                                    <div className="border-t border-slate-800 pt-4 mt-2">
                                        <button
                                            onClick={() => { logout(); onClose(); window.location.href = "/"; }}
                                            className="w-full py-2 bg-red-900/20 hover:bg-red-900/40 text-red-400 border border-red-900/50 rounded font-bold text-sm flex items-center justify-center gap-2 transition-colors"
                                        >
                                            <LogOut className="w-4 h-4" />
                                            Logout
                                        </button>
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
