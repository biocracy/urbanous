'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import api from '@/lib/api';
import Link from 'next/link';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const login = useAuthStore((state) => state.login);
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            // Form data for OAuth2PasswordRequestForm
            const formData = new FormData();
            formData.append('username', email); // backend expects 'username'
            formData.append('password', password);

            const res = await api.post('/token', formData);
            login(res.data.access_token);
            router.push('/');
        } catch (err: any) {
            setError('Invalid credentials');
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-950 text-white">
            <div className="w-full max-w-md p-8 space-y-6 bg-gray-900 rounded-lg shadow-xl border border-gray-800">
                <h1 className="text-3xl font-bold text-center text-blue-400">Urbanous.net Login</h1>
                {error && <p className="text-red-500 text-center">{error}</p>}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full p-2 rounded bg-gray-800 border border-gray-700 focus:outline-none focus:border-blue-500"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full p-2 rounded bg-gray-800 border border-gray-700 focus:outline-none focus:border-blue-500"
                            required
                        />
                    </div>
                    <button type="submit" className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded transition-colors font-semibold">
                        Sign In
                    </button>
                </form>
                <div className="text-center text-sm text-gray-400">
                    Don't have an account? <Link href="/register" className="text-blue-400 hover:underline">Register</Link>
                </div>
            </div>
        </div>
    );
}
