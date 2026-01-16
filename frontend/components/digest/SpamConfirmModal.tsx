'use client';

import React, { useState, useEffect } from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface SpamConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (dontAskAgain: boolean) => void;
    articleTitle?: string;
}

export function SpamConfirmModal({ isOpen, onClose, onConfirm, articleTitle }: SpamConfirmModalProps) {
    const [dontAsk, setDontAsk] = useState(false);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-slate-900 border border-red-500/30 rounded-xl shadow-2xl p-6 w-full max-w-md m-4 relative animate-in zoom-in-95 duration-200">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
                >
                    <X size={20} />
                </button>

                <div className="flex items-center gap-3 text-red-500 mb-4">
                    <AlertTriangle size={24} />
                    <h3 className="text-xl font-bold">Report as Spam?</h3>
                </div>

                <p className="text-slate-300 mb-2">
                    Are you sure you want to flag this article as <b>technical junk or spam</b>?
                </p>
                {articleTitle && (
                    <p className="text-slate-500 text-sm italic mb-6 border-l-2 border-slate-700 pl-3">
                        "{articleTitle}"
                    </p>
                )}

                <div className="flex items-center gap-2 mb-6 cursor-pointer" onClick={() => setDontAsk(!dontAsk)}>
                    <div className={`w-5 h-5 rounded border border-slate-600 flex items-center justify-center transition-colors ${dontAsk ? 'bg-blue-600 border-blue-600' : 'bg-transparent'}`}>
                        {dontAsk && <X size={14} className="text-white" />}
                    </div>
                    <span className="text-sm text-slate-400 select-none">Don't ask me again (Always Report)</span>
                </div>

                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg hover:bg-slate-800 text-slate-300 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => onConfirm(dontAsk)}
                        className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold shadow-lg shadow-red-900/20 transition-all active:scale-95"
                    >
                        Yes, Report It
                    </button>
                </div>
            </div>
        </div>
    );
}
