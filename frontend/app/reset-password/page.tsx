'use client';
import { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

function ResetForm() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState('');

    if (!token) {
        return <div className="text-red-400 text-center">Invalid Link: No token found.</div>;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirm) {
            setStatus('error');
            setMessage('Passwords do not match');
            return;
        }

        setStatus('loading');

        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${apiBase}/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, new_password: password }),
            });

            const data = await res.json();

            if (!res.ok) throw new Error(data.detail || 'Failed to reset');

            setStatus('success');
            setMessage(data.message);
        } catch (e: any) {
            setStatus('error');
            setMessage(e.message);
        }
    };

    if (status === 'success') {
        return (
            <div className="text-center">
                <div className="bg-green-900/30 text-green-300 p-4 rounded-lg mb-6 text-sm">
                    {message}
                </div>
                <button
                    onClick={() => router.push('/')}
                    className="inline-block bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-lg transition-colors font-bold"
                >
                    Login Now
                </button>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div>
                <label className="block text-xs font-bold uppercase text-slate-500 mb-2">New Password</label>
                <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                />
            </div>

            <div>
                <label className="block text-xs font-bold uppercase text-slate-500 mb-2">Confirm Password</label>
                <input
                    type="password"
                    required
                    minLength={6}
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
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
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50"
            >
                {status === 'loading' ? 'Resetting...' : 'Set New Password'}
            </button>
        </form>
    );
}

export default function ResetPasswordPage() {
    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 font-sans text-slate-200">
            <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
                <h1 className="text-2xl font-bold mb-6 text-white text-center">Set New Password</h1>
                <Suspense fallback={<div className="text-center text-slate-400">Loading...</div>}>
                    <ResetForm />
                </Suspense>
            </div>
        </div>
    );
}
