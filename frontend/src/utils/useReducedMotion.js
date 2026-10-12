import { useEffect, useState } from 'react';

/**
 * useReducedMotion — Accessibility Hook
 * Detects prefers-reduced-motion system preference and updates on change.
 * Returns boolean: true if user prefers reduced motion, false otherwise.
 * 
 * Usage:
 * const prefersReducedMotion = useReducedMotion();
 * return <div style={{ transition: prefersReducedMotion ? 'none' : '0.26s ease' }} />;
 */
export function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleChange = (e) => {
      setPrefersReducedMotion(e.matches);
    };

    // Support both modern addEventListener and older addListener
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, []);

  return prefersReducedMotion;
}

export default useReducedMotion;
