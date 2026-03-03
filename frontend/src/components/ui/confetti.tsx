/**
 * Confetti Celebration Component
 * Displays celebratory confetti animation for completion states
 * Uses canvas-confetti library
 */

import { useEffect, useCallback, useRef } from "react";

// Dynamically import confetti to avoid SSR issues
let confetti: typeof import("canvas-confetti").default | null = null;

export interface ConfettiOptions {
  particleCount?: number;
  spread?: number;
  startVelocity?: number;
  decay?: number;
  gravity?: number;
  colors?: string[];
  origin?: { x: number; y: number };
  scalar?: number;
}

const defaultOptions: ConfettiOptions = {
  particleCount: 100,
  spread: 70,
  startVelocity: 30,
  decay: 0.95,
  gravity: 1,
  colors: [
    "#6366f1", // primary indigo
    "#22c55e", // green
    "#eab308", // yellow
    "#3b82f6", // blue
    "#ec4899", // pink
    "#8b5cf6", // purple
  ],
  origin: { x: 0.5, y: 0.6 },
  scalar: 1,
};

/**
 * Hook to trigger confetti celebrations
 */
export function useConfetti() {
  const isLoadedRef = useRef(false);

  useEffect(() => {
    // Dynamically load canvas-confetti
    import("canvas-confetti")
      .then((module) => {
        confetti = module.default;
        isLoadedRef.current = true;
      })
      .catch((err) => {
        console.warn("Failed to load confetti:", err);
      });
  }, []);

  const fire = useCallback((options: ConfettiOptions = {}) => {
    if (!confetti || !isLoadedRef.current) return;

    const mergedOptions = { ...defaultOptions, ...options };
    confetti(mergedOptions);
  }, []);

  const fireMultiple = useCallback(
    (count: number = 3, interval: number = 150) => {
      if (!confetti || !isLoadedRef.current) return;

      const directions = [
        { x: 0.3, y: 0.6 },
        { x: 0.5, y: 0.5 },
        { x: 0.7, y: 0.6 },
      ];

      for (let i = 0; i < count; i++) {
        setTimeout(() => {
          confetti({
            ...defaultOptions,
            origin: directions[i % directions.length],
            particleCount: Math.floor(80 + Math.random() * 40),
          });
        }, i * interval);
      }
    },
    []
  );

  const fireCannon = useCallback(() => {
    if (!confetti || !isLoadedRef.current) return;

    const duration = 2000;
    const animationEnd = Date.now() + duration;

    const randomInRange = (min: number, max: number) =>
      Math.random() * (max - min) + min;

    const interval = setInterval(() => {
      const timeLeft = animationEnd - Date.now();

      if (timeLeft <= 0) {
        clearInterval(interval);
        return;
      }

      const particleCount = 50 * (timeLeft / duration);

      // Fire from both sides
      confetti({
        ...defaultOptions,
        particleCount,
        origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
      });
      confetti({
        ...defaultOptions,
        particleCount,
        origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
      });
    }, 250);
  }, []);

  const fireStars = useCallback(() => {
    if (!confetti || !isLoadedRef.current) return;

    const defaults = {
      spread: 360,
      ticks: 50,
      gravity: 0,
      decay: 0.94,
      startVelocity: 30,
      colors: ["#FFE400", "#FFBD00", "#E89400", "#FFCA6C", "#FDFFB8"],
    };

    function shoot() {
      confetti!({
        ...defaults,
        particleCount: 40,
        scalar: 1.2,
        shapes: ["star"],
      });

      confetti!({
        ...defaults,
        particleCount: 10,
        scalar: 0.75,
        shapes: ["circle"],
      });
    }

    setTimeout(shoot, 0);
    setTimeout(shoot, 100);
    setTimeout(shoot, 200);
  }, []);

  return {
    fire,
    fireMultiple,
    fireCannon,
    fireStars,
    isLoaded: isLoadedRef.current,
  };
}

/**
 * Component wrapper that fires confetti when rendered
 */
interface ConfettiTriggerProps {
  trigger: boolean;
  type?: "default" | "multiple" | "cannon" | "stars";
  children?: React.ReactNode;
}

export function ConfettiTrigger({
  trigger,
  type = "multiple",
  children,
}: ConfettiTriggerProps) {
  const { fire, fireMultiple, fireCannon, fireStars } = useConfetti();
  const hasFiredRef = useRef(false);

  useEffect(() => {
    if (trigger && !hasFiredRef.current) {
      hasFiredRef.current = true;

      // Small delay for visual impact
      setTimeout(() => {
        switch (type) {
          case "multiple":
            fireMultiple();
            break;
          case "cannon":
            fireCannon();
            break;
          case "stars":
            fireStars();
            break;
          default:
            fire();
        }
      }, 300);
    }
  }, [trigger, type, fire, fireMultiple, fireCannon, fireStars]);

  return <>{children}</>;
}
