'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import dynamic from 'next/dynamic';

// Dynamic import for Globe (SSR issue prevention)
const NewsGlobe = dynamic(() => import('@/components/NewsGlobe'), {
  ssr: false,
  loading: () => <div className="h-screen w-full flex items-center justify-center bg-black text-white">Loading Globe...</div>
});

import { Settings } from 'lucide-react';
import SettingsModal from '@/components/SettingsModal';
import { useState } from 'react';

export default function Home() {
  const { isAuthenticated, logout } = useAuthStore();
  const router = useRouter();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);



  return (
    <main className="relative min-h-screen bg-black overflow-hidden">
      {/* Header Overlay */}
      <div className="absolute top-0 left-0 w-full z-10 p-4 flex justify-between items-center pointer-events-none">
        <h1 className="text-2xl font-black tracking-tighter pointer-events-auto shadow-sm flex items-center cursor-default select-none">
          {/* Logo with Gradient Mask */}
          <div
            className="h-8 w-6 -mt-1 bg-gradient-to-r from-fuchsia-400 to-indigo-400"
            style={{
              maskImage: 'url(/logo-mask-v5.png)',
              maskSize: 'contain',
              maskRepeat: 'no-repeat',
              maskPosition: 'center',
              WebkitMaskImage: 'url(/logo-mask-v5.png)',
              WebkitMaskSize: 'contain',
              WebkitMaskRepeat: 'no-repeat',
              WebkitMaskPosition: 'center'
            }}
          />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-400 to-indigo-400">
            RBANOUS.NET
          </span>
        </h1>

        <div className="pointer-events-auto flex items-center gap-2">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="p-2 bg-slate-800/80 hover:bg-slate-700 text-white rounded-full backdrop-blur-md transition-all shadow-lg border border-slate-700"
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* Globe Component */}
      <div className="h-screen w-full">
        <NewsGlobe />
      </div>
    </main>
  );
}
