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
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const { logout } = useAuthStore();

    useEffect(() => {
        if (isOpen) {
            setIsLoading(true);
            setMessage(null);
            api.get('/users/me')
                .then(res => {
                    setEmail(res.data.email);
                    setApiKey(res.data.gemini_api_key || '');
                })
                .catch(err => {
                    console.error("Failed to fetch user settings", err);
                    setMessage({ type: 'error', text: 'Failed to load settings' });
                })
                .finally(() => setIsLoading(false));
        }
    }, [isOpen]);

    const handleSave = async () => {
        setIsSaving(true);
        setMessage(null);
        try {
            await api.put('/users/me/api-key', { api_key: apiKey });
            setMessage({ type: 'success', text: 'API Key saved successfully!' });
            // Close after short delay
            setTimeout(() => {
                onClose();
            }, 1000);
        } catch (err: any) {
            setMessage({ type: 'error', text: 'Failed to save API Key' });
        } finally {
            setIsSaving(false);
        }
    };

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
                                    It is stored securely.
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
                                    onClick={() => { logout(); onClose(); }}
                                    className="w-full py-2 bg-red-900/20 hover:bg-red-900/40 text-red-400 border border-red-900/50 rounded font-bold text-sm flex items-center justify-center gap-2 transition-colors"
                                >
                                    <LogOut className="w-4 h-4" />
                                    Logout
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
