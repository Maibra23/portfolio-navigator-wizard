import { useState, useEffect, useCallback } from "react";

interface OrientationState {
  isLandscape: boolean;
  isPortrait: boolean;
  angle: number;
}

export function useOrientation(): OrientationState {
  const getOrientation = useCallback((): OrientationState => {
    if (typeof window === "undefined") {
      return { isLandscape: true, isPortrait: false, angle: 0 };
    }

    const angle = window.screen?.orientation?.angle ?? 0;
    const isLandscape =
      window.matchMedia("(orientation: landscape)").matches ||
      window.innerWidth > window.innerHeight;

    return {
      isLandscape,
      isPortrait: !isLandscape,
      angle,
    };
  }, []);

  const [orientation, setOrientation] = useState<OrientationState>(getOrientation);

  useEffect(() => {
    const handleOrientationChange = () => {
      setOrientation(getOrientation());
    };

    const handleResize = () => {
      setOrientation(getOrientation());
    };

    window.addEventListener("orientationchange", handleOrientationChange);
    window.addEventListener("resize", handleResize);

    if (window.screen?.orientation) {
      window.screen.orientation.addEventListener("change", handleOrientationChange);
    }

    return () => {
      window.removeEventListener("orientationchange", handleOrientationChange);
      window.removeEventListener("resize", handleResize);
      if (window.screen?.orientation) {
        window.screen.orientation.removeEventListener("change", handleOrientationChange);
      }
    };
  }, [getOrientation]);

  return orientation;
}
