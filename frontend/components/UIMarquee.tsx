'use client';

import React, { useState, useEffect } from 'react';

interface UIMarqueeProps {
    text: string;
    maxLength?: number;
    speed?: number; // pixels per second (approx) or steps per tick
    className?: string;
}

export default function UIMarquee({ text, maxLength = 40, speed = 30, className = "" }: UIMarqueeProps) {
    const [isHovering, setIsHovering] = useState(false);
    const [displayOffset, setDisplayOffset] = useState(0);

    const shouldScroll = text.length > maxLength;

    // Reset offset when text changes or we stop hovering
    useEffect(() => {
        if (!isHovering || !shouldScroll) {
            setDisplayOffset(0);
            return;
        }

        const interval = setInterval(() => {
            setDisplayOffset(prev => {
                const maxOffset = text.length - maxLength;
                if (prev >= maxOffset) {
                    return 0; // Loop back to start
                }
                return prev + 1;
            });
        }, 300); // Fixed speed ~3 chars/sec

        return () => clearInterval(interval);
    }, [isHovering, text, maxLength, shouldScroll]);

    const visibleText = shouldScroll
        ? text.slice(displayOffset, displayOffset + maxLength)
        : text;

    return (
        <span
            className={`${className} overflow-hidden whitespace-nowrap ${shouldScroll ? 'cursor-help' : ''}`}
            onMouseEnter={() => setIsHovering(true)}
            onMouseLeave={() => setIsHovering(false)}
            style={{ display: 'inline-block', maxWidth: '100%' }}
            title={text}
        >
            {visibleText}
            {shouldScroll && (displayOffset + maxLength < text.length) ? "..." : ""}
        </span>
    );
}
