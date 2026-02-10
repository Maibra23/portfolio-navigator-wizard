import React, { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

interface TimelineScrollRevealProps {
  children: React.ReactNode;
  className?: string;
  enabled?: boolean;
}

/**
 * Wraps timeline event list and reveals children progressively as user scrolls.
 */
export function TimelineScrollReveal({ children, className = '', enabled = true }: TimelineScrollRevealProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!enabled || !containerRef.current) return;

    const items = containerRef.current.querySelectorAll(':scope > *');
    if (items.length === 0) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        items,
        { opacity: 0, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          stagger: 0.08,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: containerRef.current,
            start: 'top 88%',
            end: 'bottom 12%',
            toggleActions: 'play none none none',
          },
        }
      );
    }, containerRef);

    return () => ctx.revert();
  }, [enabled, children]);

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  );
}
