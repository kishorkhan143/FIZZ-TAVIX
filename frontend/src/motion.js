/**
 * src/motion.js � Central motion configuration
 * Single source of truth for springs, ease curves, timing, and animation variants.
 * Exported for use throughout the app; imported from "motion/react".
 * Updated: iOS-like smoothness with delays
 */

import React from 'react';

// -------------------------------------------------------------------------
// SPRING DEFINITIONS
// -------------------------------------------------------------------------

export const springs = {
  // Large surfaces, page transitions, big panels � ultra smooth, weighted settle
  soft: {
    type: 'spring',
    stiffness: 220,
    damping: 28,
    mass: 1.2,
  },

  // Buttons, toggles, tabs, pills � responsive, snappy feedback
  snappy: {
    type: 'spring',
    stiffness: 380,
    damping: 32,
    mass: 0.8,
  },

  // Modals, popovers, sheets � medium responsiveness
  sheet: {
    type: 'spring',
    stiffness: 280,
    damping: 30,
    mass: 1.1,
  },
};

// -------------------------------------------------------------------------
// EASING & TIMING - Improved iOS-like smoothness
// -------------------------------------------------------------------------

// Apple ease fallback for opacity and color (no spring needed)
export const appleEase = [0.22, 1, 0.36, 1];

// iOS-like timing presets
export const iosTiming = {
  fast: 0.2,
  medium: 0.3,
  slow: 0.4,
};

// Stagger config for list items with delays
export const staggerConfig = {
  delayChildren: 0.1, // Slight delay before first child starts
  staggerChildren: 0.06, // Slightly longer between each child
};

// Scroll reveal config
export const scrollRevealConfig = {
  once: true,
  viewport: { margin: '-60px' },
};

// -------------------------------------------------------------------------
// ANIMATION VARIANTS - Updated for butter smoothness
// -------------------------------------------------------------------------

export const variants = {
  // Fade in + slight scale + blur � used for cards, list items, content blocks
  fadeUp: {
    hidden: {
      opacity: 0,
      y: 16,
      scale: 0.98,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        ...springs.soft,
        duration: 0.4,
        delay: 0.05, // Slight delay for smoother entry
      },
    },
    exit: {
      opacity: 0,
      y: -8,
      scale: 0.96,
      transition: {
        duration: 0.25,
        ease: appleEase,
      },
    },
  },

  // Page / section transition: opacity + y displacement + blur
  pageTransition: {
    hidden: {
      opacity: 0,
      y: 20,
      filter: 'blur(4px)',
    },
    visible: {
      opacity: 1,
      y: 0,
      filter: 'blur(0px)',
      transition: {
        ...springs.soft,
        duration: 0.4,
        delay: 0.1, // Longer delay for page transitions
      },
    },
    exit: {
      opacity: 0,
      y: -12,
      filter: 'blur(3px)',
      transition: {
        duration: 0.25,
        ease: appleEase,
      },
    },
  },

  // Detail view slide in from right (for modal/panel detail views)
  slideInRight: {
    hidden: {
      opacity: 0,
      x: 30,
    },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        ...springs.soft,
        duration: 0.35,
        delay: 0.08,
      },
    },
    exit: {
      opacity: 0,
      x: 30,
      transition: {
        duration: 0.25,
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
        delay: 0.1,
      },
    },
    exit: {
      opacity: 0,
      transition: {
        duration: 0.25,
      },
    },
  },

  // List item: individual row animation
  listItem: {
    hidden: {
      opacity: 0,
      y: -8,
      scale: 0.98,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        ...springs.snappy,
        delay: 0.05, // Small delay per item
      },
    },
    exit: {
      opacity: 0,
      scale: 0.96,
      transition: {
        duration: 0.2,
        ease: appleEase,
      },
    },
  },

  // Modal / drawer / popover
  modalScale: {
    hidden: {
      opacity: 0,
      scale: 0.94,
    },
    visible: {
      opacity: 1,
      scale: 1,
      transition: {
        ...springs.sheet,
        duration: 0.35,
        delay: 0.1,
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
        duration: 0.3,
        ease: appleEase,
        delay: 0.05,
      },
    },
    exit: {
      opacity: 0,
      transition: {
        duration: 0.2,
      },
    },
  },

  // Sidebar nav items stagger
  navItemContainer: {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        delayChildren: 0.12,
        staggerChildren: 0.05,
      },
    },
  },

  navItem: {
    hidden: {
      opacity: 0,
      x: -15,
    },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        ...springs.snappy,
        delay: 0.08,
      },
    },
  },
};

// -------------------------------------------------------------------------
// ACCESSIBILITY: useMotionPrefs Hook
// -------------------------------------------------------------------------

/**
 * useMotionPrefs hook: Detect prefers-reduced-motion and return appropriate config.
 * If motion is reduced, return simple 150ms fade instead of springs.
 */
export function useMotionPrefs() {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(() => {
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
        visible: { opacity: 1, transition: { duration: 0.18, ease: 'easeInOut' } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      pageTransition: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      slideInRight: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      listItem: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      listContainer: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      modalScale: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      backdropFade: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
      navItemContainer: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
      },
      navItem: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.18 } },
      },
    };
  }

  // Normal motion: return full variants
  return variants;
}

// -------------------------------------------------------------------------
// HELPER FUNCTIONS
// -------------------------------------------------------------------------

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
    iosTiming,
    staggerConfig,
    variants: motionPrefs,
  };
}

export default {
  springs,
  variants,
  appleEase,
  iosTiming,
  staggerConfig,
  scrollRevealConfig,
  useMotionPrefs,
  useMotionConfig,
  AnimatedNumber,
  calculateDashOffset,
};
