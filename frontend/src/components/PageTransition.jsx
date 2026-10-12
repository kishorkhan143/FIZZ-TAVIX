import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { springs, useMotionPrefs } from '../motion';

/**
 * PageTransition — Premium iOS-inspired View Container
 * Provides silky smooth opacity + subtle vertical spring entrance
 * without disturbing business logic, routing, or state.
 * Uses useMotionPrefs to respect prefers-reduced-motion.
 */
export default function PageTransition({ children, transitionKey, className = '' }) {
  const motionPrefs = useMotionPrefs();
  const pageVariant = motionPrefs.pageTransition;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={transitionKey}
        className={`ios-page-container ${className}`}
        style={{ width: '100%', height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', flex: 1 }}
        variants={pageVariant}
        initial="hidden"
        animate="visible"
        exit="exit"
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}