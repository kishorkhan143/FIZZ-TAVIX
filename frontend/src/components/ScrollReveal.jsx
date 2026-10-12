import React, { useEffect, useRef, useState } from 'react';

/**
 * ScrollReveal — Viewport Intersection Reveal Wrapper
 * Triggers silky iOS fade-up when an element scrolls into view.
 * Complies with Apple motion principles:
 * - Fires once when content becomes visible.
 * - Does not re-animate repeatedly on minor scrolling back and forth.
 * - Lightweight, non-intrusive IntersectionObserver implementation.
 */
export default function ScrollReveal({
  children,
  stagger = 0,
  threshold = 0.08,
  className = '',
  style = {},
  as: Component = 'div',
}) {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // If IntersectionObserver is not supported, reveal immediately
    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(node);
        }
      },
      {
        threshold,
        rootMargin: '0px 0px -20px 0px',
      }
    );

    observer.observe(node);

    return () => {
      observer.disconnect();
    };
  }, [threshold]);

  const staggerDelay = stagger ? `${stagger * 45}ms` : undefined;

  return (
    <Component
      ref={ref}
      className={`ios-reveal ${isVisible ? 'is-visible' : ''} ${className}`}
      style={{
        ...style,
        ...(staggerDelay ? { transitionDelay: staggerDelay } : {}),
      }}
    >
      {children}
    </Component>
  );
}
