'use client';
import { useState } from 'react';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('loading');

        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiBase}/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });

            // We always show success success for security (unless network error)
            setStatus('success');
            setMessage('If that email is registered, we have sent a reset link properly.');
        } catch (e) {
            setStatus('error');
            setMessage('Something went wrong. Please try again.');
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 font-sans text-slate-200">
            <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
                <h1 className="text-2xl font-bold mb-6 text-white text-center">Reset Password</h1>

                {status === 'success' ? (
                    <div className="text-center">
                        <div className="bg-green-900/30 text-green-300 p-4 rounded-lg mb-6 text-sm">
                            {message}
                        </div>
                        <p className="text-slate-400 text-sm mb-6">
                            Check your inbox (and spam folder) for the reset link.
                        </p>
                        <a href="/" className="inline-block bg-slate-800 hover:bg-slate-700 text-white px-6 py-2 rounded-lg transition-colors">
                            Back to Home
                        </a>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <p className="text-sm text-slate-400">
                            Enter your email address and we'll send you a link to reset your password.
                        </p>

                        <div>
                            <label className="block text-xs font-bold uppercase text-slate-500 mb-2">Email</label>
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>

                        {status === 'error' && (
                            <div className="p-3 bg-red-900/30 border border-red-800 rounded text-red-200 text-sm">
                                {message}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={status === 'loading'}
                            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {status === 'loading' ? 'Sending...' : 'Send Reset Link'}
                        </button>

                        <div className="text-center">
                            <a href="/" className="text-xs text-slate-500 hover:text-slate-300">Cancel</a>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
