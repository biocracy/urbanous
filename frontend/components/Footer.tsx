import React from 'react';

interface FooterProps {
    onAboutClick: () => void;
    isAboutActive: boolean;
}

export default function Footer({ onAboutClick, isAboutActive }: FooterProps) {
    return (
        <footer className="mt-20 pt-10 border-t border-neutral-800 flex flex-col md:flex-row items-center justify-between gap-8 pb-10 w-full">

            {/* Left: Logo (Consistent with Header) */}
            <div className="flex items-center gap-0.5 select-none opacity-80 hover:opacity-100 transition-opacity">
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
                <span className="text-xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-400 to-indigo-400">
                    RBANOUS.NET
                </span>
            </div>

            {/* Right: Links */}
            <div className="flex flex-wrap items-center justify-center gap-6 text-sm font-medium text-neutral-500">
                {/* About Button - Highlights when Active */}
                <button
                    onClick={(e) => {
                        e.preventDefault();
                        onAboutClick();
                    }}
                    className={`transition-colors ${isAboutActive ? 'text-fuchsia-400 font-bold' : 'hover:text-white'}`}
                >
                    About
                </button>

                <a href="#" className="hover:text-white transition-colors">Leave Feedback</a>
                <a href="#" className="hover:text-white transition-colors">Register</a>
                <a href="#" className="hover:text-fuchsia-400 transition-colors text-fuchsia-500/80">Donate</a>
                <span className="text-neutral-700 select-none">|</span>
                <span className="text-neutral-600">© 2026 Urbanous</span>
            </div>
        </footer>
    );
}
