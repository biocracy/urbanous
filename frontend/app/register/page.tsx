'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import api from '@/lib/api';
import Link from 'next/link';

export default function RegisterPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [error, setError] = useState('');
    const login = useAuthStore((state) => state.login);
    const router = useRouter();

    const [isSuccess, setIsSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        try {
            await api.post('/register', {
                email,
                password,
                gemini_api_key: apiKey
            });
            // No auto-login. Show success message.
            setIsSuccess(true);
        } catch (err: any) {
            if (err.response) {
                setError(err.response.data.detail || 'Registration failed');
            } else {
                setError('Registration failed');
            }
        }
    };

    if (isSuccess) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-950 text-white">
                <div className="w-full max-w-md p-8 space-y-6 bg-gray-900 rounded-lg shadow-xl border border-gray-800 text-center">
                    <div className="mx-auto w-16 h-16 bg-blue-900/30 rounded-full flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v9a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <h1 className="text-2xl font-bold text-white">Check your Inbox</h1>
                    <p className="text-slate-400">
                        We've sent a verification link to <span className="text-white font-mono">{email}</span>.
                    </p>
                    <p className="text-sm text-slate-500">
                        Please verify your email to activate your account.
                    </p>
                    <div className="pt-4">
                        <Link href="/login" className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded font-bold transition-colors">
                            Return to Login
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-950 text-white">
            <div className="w-full max-w-md p-8 space-y-6 bg-gray-900 rounded-lg shadow-xl border border-gray-800">
                <h1 className="text-3xl font-bold text-center text-green-400">Join Urbanous.net</h1>
                {error && <p className="text-red-500 text-center">{error}</p>}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full p-2 rounded bg-gray-800 border border-gray-700 focus:outline-none focus:border-green-500"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full p-2 rounded bg-gray-800 border border-gray-700 focus:outline-none focus:border-green-500"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Gemini API Key (Optional)</label>
                        <input
                            type="text"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            className="w-full p-2 rounded bg-gray-800 border border-gray-700 focus:outline-none focus:border-green-500"
                            placeholder="AI features require this"
                        />
                    </div>
                    <button type="submit" className="w-full py-2 bg-green-600 hover:bg-green-700 rounded transition-colors font-semibold">
                        Create Account
                    </button>
                </form>
                <div className="text-center text-sm text-gray-400">
                    Already have an account? <Link href="/login" className="text-green-400 hover:underline">Login</Link>
                </div>
            </div>
        </div>
    );
}
