/**
 * src/motion.js — Central motion configuration
 * Single source of truth for springs, ease curves, timing, and animation variants.
 * Exported for use throughout the app; imported from "motion/react".
 */

import React from 'react';

// ─────────────────────────────────────────────────────────────────────────
// SPRING DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────

export const springs = {
  // Large surfaces, page transitions, big panels — smooth, weighted settle
  soft: {
    type: 'spring',
    stiffness: 260,
    damping: 30,
    mass: 1,
  },

  // Buttons, toggles, tabs, pills — responsive, snappy feedback
  snappy: {
    type: 'spring',
    stiffness: 420,
    damping: 34,
    mass: 0.9,
  },

  // Modals, popovers, sheets — medium responsiveness
  sheet: {
    type: 'spring',
    stiffness: 300,
    damping: 32,
  },
};

// ─────────────────────────────────────────────────────────────────────────
// EASING & TIMING
// ─────────────────────────────────────────────────────────────────────────

// Apple ease fallback for opacity and color (no spring needed)
export const appleEase = [0.22, 1, 0.36, 1];

// Stagger config for list items
export const staggerConfig = {
  delayChildren: 0.08, // Delay before first child starts
  staggerChildren: 0.05, // Delay between each child (cap: 0.08 + 12×0.05 ≈ 0.68s)
};

// Scroll reveal config
export const scrollRevealConfig = {
  once: true,
  viewport: { margin: '-40px' },
};

// ─────────────────────────────────────────────────────────────────────────
// ANIMATION VARIANTS
// ─────────────────────────────────────────────────────────────────────────

export const variants = {
  // Fade in + slight scale + blur — used for cards, list items, content blocks
  fadeUp: {
    hidden: {
      opacity: 0,
      y: 14,
      scale: 0.98,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        ...springs.soft,
        duration: 0.34,
      },
    },
    exit: {
      opacity: 0,
      y: -8,
      scale: 0.96,
      transition: {
        duration: 0.2,
        ease: appleEase,
      },
    },
  },

  // Page / section transition: opacity + y displacement + blur
  pageTransition: {
    hidden: {
      opacity: 0,
      y: 16,
      filter: 'blur(6px)',
    },
    visible: {
      opacity: 1,
      y: 0,
      filter: 'blur(0px)',
      transition: {
        ...springs.soft,
        duration: 0.34,
      },
    },
    exit: {
      opacity: 0,
      y: -8,
      filter: 'blur(4px)',
      transition: {
        duration: 0.2,
        ease: appleEase,
      },
    },
  },

  // Detail view slide in from right (for modal/panel detail views)
  slideInRight: {
    hidden: {
      opacity: 0,
      x: 24,
    },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        ...springs.soft,
        duration: 0.34,
      },
    },
    exit: {
      opacity: 0,
      x: 24,
      transition: {
        duration: 0.2,
        ease: appleEase,
      },
    },
  },

  // List container: staggers all children
  listContainer: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        ...staggerConfig,
      },
    },
    exit: {
      opacity: 0,
      transition: {
        duration: 0.2,
      },
    },
  },

  // List item: individual row animation
  // NOTE: never animate height on exit — it triggers layout thrashing.
  // Use opacity + scale only; rows collapse naturally via layout prop.
  listItem: {
    hidden: {
      opacity: 0,
      y: -10,
      scale: 0.98,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        ...springs.snappy,
      },
    },
    exit: {
      opacity: 0,
      scale: 0.96,
      transition: {
        duration: 0.18,
        ease: appleEase,
      },
    },
  },

  // Modal / drawer / popover
  modalScale: {
    hidden: {
      opacity: 0,
      scale: 0.96,
    },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        ...springs.sheet,
        duration: 0.34,
      },
    },
    exit: {
      opacity: 0,
      scale: 0.92,
      transition: {
        duration: 0.2,
        ease: appleEase,
      },
    },
  },

  // Backdrop / dimmer
  backdropFade: {
    hidden: {
      opacity: 0,
    },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.26,
        ease: appleEase,
      },
    },
    exit: {
      opacity: 0,
      transition: {
        duration: 0.16,
      },
    },
  },

  // Sidebar nav items stagger
  navItemContainer: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delayChildren: 0.08,
        staggerChildren: 0.04,
      },
    },
  },

  navItem: {
    hidden: {
      opacity: 0,
      x: -12,
    },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        ...springs.snappy,
      },
    },
  },
};

// ─────────────────────────────────────────────────────────────────────────
// ACCESSIBILITY: useMotionPrefs Hook
// ─────────────────────────────────────────────────────────────────────────

/**
 * useMotionPrefs hook: Detect prefers-reduced-motion and return appropriate config.
 * If motion is reduced, return simple 150ms fade instead of springs.
 * 
 * Avoids linter warning: Initializes state from media query check before effect
 * to prevent synchronous setState in effect.
 */
export function useMotionPrefs() {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(() => {
    // Initialize from media query on mount
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleChange = (e) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // If motion reduced, return simple 150ms fade config for all variants
  if (prefersReducedMotion) {
    return {
      fadeUp: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15, ease: 'easeInOut' } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      pageTransition: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      slideInRight: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      listItem: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      listContainer: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      modalScale: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      backdropFade: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      navItemContainer: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
      },
      navItem: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
      },
    };
  }

  // Normal motion: return full variants
  return variants;
}

// ─────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────

/**
 * AnimatedNumber placeholder
 * For animated counters, wrap the value in a motion.div and use motion's animate feature
 */
export const AnimatedNumber = null;

/**
 * calculateDashOffset helper: Convert score percentage to SVG stroke-dashoffset
 * Used for RiskGauge arc animation
 */
export function calculateDashOffset(score, circumference = 252) {
  // score is 0-100 percentage
  const ratio = (100 - score) / 100;
  return ratio * circumference;
}

/**
 * useMotionConfig hook: Convenience wrapper that returns all motion config
 * Respects prefers-reduced-motion
 */
export function useMotionConfig() {
  const motionPrefs = useMotionPrefs();
  return {
    springs,
    appleEase,
    staggerConfig,
    variants: motionPrefs,
  };
}

export default {
  springs,
  variants,
  appleEase,
  staggerConfig,
  scrollRevealConfig,
  useMotionPrefs,
  useMotionConfig,
  AnimatedNumber,
  calculateDashOffset,
};
