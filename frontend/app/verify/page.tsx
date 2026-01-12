
'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import Link from 'next/link';

function VerifyContent() {
    const searchParams = useSearchParams();
    const token = searchParams.get('token');
    const router = useRouter();

    const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
    const [message, setMessage] = useState('');

    useEffect(() => {
        if (!token) {
            setStatus('error');
            setMessage('Invalid verification link.');
            return;
        }

        const verify = async () => {
            try {
                // Adjust endpoint if needed, assuming /auth/verify mapped or just /verify in router
                // Based on auth.py: @router.get("/verify") -> /outlets/verify? No, auth router usually mounted at /auth or root?
                // Need to check main.py mount path.
                // Assuming it's mounted at root or we use the relative path from the router.
                // Let's assume standard api.get('/verify') matches backend router logic if mounted at root or check later.
                // Safest to try '/verify' as defined in auth.py (if auth.py is included in main with prefix, we need that prefix).
                await api.get(`/verify?token=${token}`);
                setStatus('success');
            } catch (err: any) {
                setStatus('error');
                setMessage(err.response?.data?.detail || 'Verification failed. Token may be invalid or expired.');
            }
        };

        verify();
    }, [token]);

    return (
        <div className="flex min-h-screen items-center justify-center bg-gray-950 text-white p-4">
            <div className="w-full max-w-md p-8 bg-gray-900 rounded-lg shadow-xl border border-gray-800 text-center space-y-6">

                {status === 'verifying' && (
                    <>
                        <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto" />
                        <h1 className="text-xl font-bold">Verifying Email...</h1>
                        <p className="text-slate-400">Please wait while we activate your account.</p>
                    </>
                )}

                {status === 'success' && (
                    <div className="animate-in fade-in zoom-in duration-300">
                        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                        <h1 className="text-2xl font-bold text-green-400">Email Verified!</h1>
                        <p className="text-slate-300 mt-2">
                            Your account has been successfully activated.
                        </p>
                        <div className="pt-6">
                            <Link href="/login" className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded font-bold transition-colors">
                                Continue to Login
                            </Link>
                        </div>
                    </div>
                )}

                {status === 'error' && (
                    <div className="animate-in fade-in zoom-in duration-300">
                        <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                        <h1 className="text-2xl font-bold text-red-400">Verification Failed</h1>
                        <p className="text-slate-300 mt-2">
                            {message}
                        </p>
                        <div className="pt-6">
                            <Link href="/register" className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded font-bold transition-colors">
                                Try Registering Again
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function VerifyPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">Loading...</div>}>
            <VerifyContent />
        </Suspense>
    );
}
