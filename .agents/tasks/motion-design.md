# TAVIX GUARD — iOS 17/18 Motion Architecture Design

## Overview

This document specifies the complete motion upgrade for the TAVIX GUARD React 19 + Vite dashboard application. The goal is to replace all existing CSS keyframes and transitions with **buttery-smooth, spring-based, iOS 17/18-style animations** using the `motion` package (successor to Framer Motion, supports React 19). **No data logic, backend calls, or visual design changes—only motion and interaction feel are affected.**

### Key Principles

- **Apple-inspired physics**: Springs settle smoothly with natural overshoot on small elements only. Large surfaces settle with zero visible overshoot.
- **Performance**: Animate ONLY `transform`, `opacity`, and `filter`. Never animate width, height, top, left, or box-shadow directly.
- **Interruptibility**: All animations are spring-based (no keyframe arrays), so users can interrupt and reverse any animation mid-motion.
- **Accessibility**: Respect `prefers-reduced-motion` at app root via `MotionConfig reducedMotion="user"` and fallback to simple 150ms fades.
- **Batching & throttling**: Cap simultaneous entering list items to ~5, stagger remaining items to prevent layout thrashing.

---

## 1. Component Inventory & Current Animation Usage

### Root & Layout

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `App.jsx` | CSS keyframes `slide-in-left` (sidebar), `fade-in` (main-content), `slide-in-up` (header, body, sections) | Replace with motion div + AnimatePresence for page transitions; sidebar layoutId pill highlight; page enter/exit with y/opacity/blur |
| `App.css` | 6× CSS keyframes (fade-in, slide-in-left, slide-in-up, scale-in); inline `animation:` on `.sidebar`, `.main-content`, `.header`, `.body`, `.section`, `.stat-card`; dozens of `transition: all` | Remove all keyframes; replace all inline `animation:` with motion.div; convert `transition: all` to explicit properties in motion config |

### Navigation & Sidebar

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `components/` (nav in App.jsx) | `.nav-item:hover` transform translateX(3px), `.nav-item:active` scale(0.975), `.nav-item .nav-icon:hover` scale(1.06) | whileHover x:2 scale(1.06), whileTap scale(0.97); animated pill background with layoutId="nav-active"; stagger nav items in on mount |

### Header & Clock

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `Header` function (App.jsx) | None; plain text clock update | Tabular-nums on clock to prevent layout shift; category label crossfade + y slide when section changes (use motion.div for label) |

### Overview / Stats Cards

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `OverviewSection`, `stat-card` (App.jsx, App.css) | `.stat-card` has `animation: iosFadeInUp` + inline delay; `.stat-card:hover` transform y -4px scale(1.008) | FadeUp stagger with 0.04s cap on 12 cards; animated number counter (useSpring/animate for smooth tween); whileHover y -3, whileTap scale 0.98; Recharts isAnimationActive 900ms ease-out |

### Events & Alerts Lists

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `EventsTable`, `AlertList` (App.jsx, App.css) | Inline `animation: iosFadeInUp` with staggered delay on each row; no exit animation | AnimatePresence + layout="position"; new row enters opacity 0 y -12 scale 0.98 → 1 with springs.snappy + brief highlight flash (bg fade 1.2s); remove row collapse + fade; cap simultaneous entering to 5; first load stagger 0.04s per item; high-risk alerts one-time pulse (scale 1 → 1.01 → 1, not infinite) |

### Panels & Cards

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `events-panel`, `alerts-panel`, `settings-card`, `telemetry-panel`, `info-grid` (App.jsx, App.css) | `.events-panel`, `.alerts-panel`, `.telemetry-panel`, `.settings-card` have `animation: scale-in 0.3s`; no scroll reveal | whileInView fadeUp once:true viewport={{ margin: -40 }} on each panel; remove scale-in keyframe |

### Status Badge

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `StatusBadge` function (App.jsx) | Inline `.dot` styles; no animation on dot | Online dot: breathing glow loop (opacity + scale 2s infinite) using motion + animate; offline static; color crossfade on status change (opacity + color transition) |

### Empty States & CSV Upload

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `empty-state` (App.css), CSV Analyzer pages | `.empty-state` fade in; no dragover animation | Icon + text fadeUp with small float (y -8px on scroll into view); CSV upload area dragover scale 1.02 border glow; drop spring settle |

### RiskGauge (SVG)

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `RiskGauge.jsx`, `RiskGauge.css` | `.gauge-svg` circle has inline `transition: stroke-dashoffset 0.3s ease`; number text static | Animate stroke-dashoffset from **previous value** (not from 0) to new value using spring; number text tween with useSpring/animate; color transition smoothly between bands via motion |

### RiskChart & Recharts

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `RiskChart.jsx` (if it exists in components) | Recharts defaults | Recharts isAnimationActive with animationDuration 900 + ease-out curve; on data update morph line smoothly; animated tooltip (scale + opacity spring) |

### Detail Pages & Modals

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `EntityDetail.jsx`, `IncidentPanel.jsx`, `Environment.jsx`, `LabTerminalsView.jsx`, etc. | CSS slide-in-up, scale-in keyframes if present | Detail views slide in from right (x:24 → 0 springs.soft); going back slide out to right; expandable blocks use animated height via layout animation (never CSS height transitions); modals scale 0.96 + opacity → 1 springs.sheet |

### Buttons Globally

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `admin-btn`, `date-filter-pill`, `nav-item`, any `<button>` | `.admin-btn:hover` translateY(-2px), `.admin-btn:active` scale(0.975); `.nav-item:hover` translateX(3px), `.nav-item:active` scale(0.975) | whileHover scale 1.02, whileTap scale 0.96 (springs.snappy) on all buttons; focus-visible ring fades in (opacity 0 → 1 with spring) |

### Other Components

| File | Current Animations | Motion Needs |
|------|-------------------|--------------|
| `CustomSelect.jsx` | `animation: iosDropdownEntrance`; `.custom-select-button:hover` | Dropdown scale 0.96 + opacity → 1 springs.sheet; items stagger in with listItem variant |
| `Sparkline.jsx` | None (pure SVG render) | Line draw-in on mount via pathLength; morph on data update |
| `DateFilter.jsx` | `.date-filter-pill:hover` transitions | whileHover scale 1.02, whileTap scale 0.96; date input focus ring fade |
| `ScrollReveal.jsx` (if used) | Likely old scroll-in animation | Replace with whileInView fadeUp once:true viewport={{ margin: -40 }} |
| Live components (`LaboratoriesView.jsx`, `ComputerDetailView.jsx`, etc.) | TBD based on file content | Consistent with main app: page transitions, list item enters, status indicators |

---

## 2. Central Motion Config (`src/motion.js`)

Create a single file that exports every spring, variant, and helper so the entire feel can be tuned from one place.

```javascript
/**
 * src/motion.js — Central motion configuration
 * Single source of truth for springs, ease curves, timing, and animation variants
 */

export const springs = {
  // Large surfaces, page transitions, big panels
  soft: {
    type: 'spring',
    stiffness: 260,
    damping: 30,
    mass: 1,
  },
  
  // Buttons, toggles, tabs, pills — snappy, responsive
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

// Apple ease fallback for opacity and color (no spring needed)
export const appleEase = [0.22, 1, 0.36, 1];

// Stagger config for list items
export const staggerConfig = {
  delayChildren: 0.08, // Delay before children start animating
  staggerChildren: 0.05, // Delay between each child
  // Cap total sequence: 0.08 + (12 * 0.05) = 0.68s ≈ 0.6s max
};

// Variants
export const variants = {
  // Fade in + scale up + blur out
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
        duration: 0.2, // Faster exit (~60% of enter)
        ease: appleEase,
      },
    },
  },

  // Page / section transition: opacity + y + blur
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

  // Detail view slide in from right
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

  // List container: staggers children
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
  listItem: {
    hidden: {
      opacity: 0,
      y: -12,
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
      height: 0,
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
};

/**
 * useMotionPrefs hook: detect prefers-reduced-motion and return appropriate config
 * If motion is reduced, return simple 150ms fade instead of springs
 */
export function useMotionPrefs() {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // If motion reduced, return 150ms fade config for all variants
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
      modalScale: {
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.15 } },
      },
    };
  }

  // Normal motion: return full variants
  return variants;
}

export function useMotionConfig() {
  const motionPrefs = useMotionPrefs();
  return {
    springs,
    appleEase,
    staggerConfig,
    variants: motionPrefs,
  };
}
```

---

## 3. Per-Component Motion Specifications

### A. Page / Section Switching (App.jsx)

**Current**: Sections render without animation; PageTransition is a plain div wrapper.

**Motion Upgrade**:

1. Wrap the active section in `<AnimatePresence mode="wait" initial={false}>` with keyed `motion.div`
2. Use `pageTransition` variant: opacity 0 y 16 blur(6px) → 1 0 0 on enter (springs.soft), faster exit y -8
3. Section header (h2 + p) appears first, then content blocks stagger in after with `layout` for smooth re-layout
4. Apply at the section container level (each section is a separate AnimatePresence)

**Code pattern**:
```jsx
<AnimatePresence mode="wait" initial={false}>
  <motion.div
    key={`section-${activeMenu}`}
    variants={variants.pageTransition}
    initial="hidden"
    animate="visible"
    exit="exit"
  >
    {/* Section content */}
  </motion.div>
</AnimatePresence>
```

### B. Sidebar Navigation

**Current**: `.nav-item:hover` translateX(3px), `.nav-item:active` scale(0.975); active background color change.

**Motion Upgrade**:

1. **Active pill background**: Use `layoutId="nav-active"` on a motion.div that animates behind the active item; springs.snappy ensures smooth glide
2. **Nav items**: whileHover x:2 scale(1.06), whileTap scale 0.97 springs.snappy
3. **Icon**: On hover, scale 1.06 + subtle color shift
4. **Stagger on mount**: All nav items fade in + stagger 0.04s per item (cap 12 items), delayChildren 0.08s
5. **Mobile drawer**: translateX(-100%) → 0 with springs.soft on open; drag-to-close with `drag="x"` and momentum; dim backdrop fades

**Code pattern**:
```jsx
<motion.div className="nav-active-pill" layoutId="nav-active" />
{/* Behind active nav item; animates to match its position */}

<motion.button
  whileHover={{ x: 2, scale: 1.06 }}
  whileTap={{ scale: 0.97 }}
  transition={springs.snappy}
>
  {/* Nav item */}
</motion.button>
```

### C. Header

**Current**: Clock updates every 1s; category label changes without animation.

**Motion Upgrade**:

1. **Clock digits**: Use `font-feature-settings: "tnum"` (tabular-nums) to prevent layout shift as digits update
2. **Category label**: Wrap in `motion.div`; crossfade color + subtle y slide (-2 → 0) when section changes using `motion.animate` or `layoutId` for text swap
3. No animation loop on clock itself; only label animates on change

### D. Overview Stat Cards (4 Cards)

**Current**: Inline `animation: iosFadeInUp` with staggered delay; hover translateY(-4px) scale(1.008).

**Motion Upgrade**:

1. **Container**: `motion.div` with `variants.fadeUp` and stagger: delayChildren 0.08s, staggerChildren 0.05s (cap at ~0.6s total)
2. **Each card**: Individually animated fadeUp on visible; whileHover y:-3 (not -4px) with shadow growth on opacity pseudo-element
3. **Number counter**: Use `motion.div` + `animate({ value: newValue })` from `motion/react`; tween from old value to new with springs.soft over 0.8s
4. **Recharts <Area>**: Set `isAnimationActive={true}` animationDuration={900} animationEasing="ease-out"
5. **No re-draw on every data tick**: Batch updates to prevent animation restarts

**Code pattern**:
```jsx
<motion.div
  variants={variants.fadeUp}
  initial="hidden"
  animate="visible"
  transition={{ ...springs.soft, delay: idx * 0.05 }}
>
  <AnimatedCounter value={statValue} />
</motion.div>
```

### E. Events List & Alerts List (Most Important)

**Current**: Inline `animation: iosFadeInUp` with stagger; no exit animation; rows don't reorder smoothly.

**Motion Upgrade**:

1. **AnimatePresence mode**: Use `initial={false}` to skip first-render animations
2. **Layout**: Set `layout="position"` on rows so existing rows slide down smoothly when new row inserted on top
3. **New row enter**: opacity 0, y -12, scale 0.98 → 1 with springs.snappy
4. **Highlight flash**: After entering, background fades from accent to transparent over 1.2s (CSS animation or motion sequence)
5. **Row removal**: Collapse height + fade with springs.soft over 0.2s
6. **First load stagger**: Cap stagger to first 12 rows; delay 0.04s per item, delayChildren 0.08s
7. **High-risk alerts**: One-time pulse (scale 1 → 1.01 → 1) on mount, NOT infinite loop
8. **Simultaneous cap**: Batch inserts so only ~5 rows animate in at once; queue remaining

**Code pattern**:
```jsx
<AnimatePresence initial={false}>
  <motion.div layout="position" key={row.id}>
    {/* Row content; animates in with listItem variant */}
  </motion.div>
</AnimatePresence>
```

### F. Panels (Events, Alerts, Telemetry, Settings, Info Grid)

**Current**: Inline `animation: scale-in 0.3s` with delay; no scroll-in behavior.

**Motion Upgrade**:

1. **Scroll reveal**: Use `whileInView` with `variants.fadeUp` once={true} viewport={{ margin: -40 }}
2. Remove inline `animation: scale-in`
3. Each panel has its own reveal trigger independent of others

### G. Status Badge (Online Dot)

**Current**: Static `.dot` color (green or red); no animation.

**Motion Upgrade**:

1. **Online dot**: Breathing glow loop using `motion.div` + `animate` with infinite repeat
   - opacity: 0.8 → 1 → 0.8
   - scale: 1 → 1.2 → 1
   - Duration 2s, easeInOut
2. **Offline dot**: Static, no animation
3. **Color change**: On status flip, text and dot color crossfade (opacity + color over 0.26s springs.soft)

**Code pattern**:
```jsx
<motion.div
  className="dot"
  animate={online ? { scale: [1, 1.2, 1], opacity: [0.8, 1, 0.8] } : {}}
  transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
/>
```

### H. Empty States & CSV Upload

**Current**: `.empty-state` fade-in; CSV upload no dragover animation.

**Motion Upgrade**:

1. **Empty state icon + text**: FadeUp + small float (y:-8 on mount) with whileInView, once={true}
2. **CSV upload area**: 
   - Dragover: scale 1.02 + border glow (border-color opacity animate, shadow grow)
   - Drop: Spring settle (scale 1 y 0) with springs.soft
   - No scale during drag; only on dragover pseudo-state

### I. RiskGauge (SVG Circle Progress)

**Current**: Inline `transition: stroke-dashoffset 0.3s ease` on arc.

**Motion Upgrade**:

1. **Arc animation**: Animate `stroke-dashoffset` from **previous value** (not 0) to new value using springs.soft over 0.8s
   - Capture previous score on update; calculate dash offset from prev, then spring to new
   - **Key**: Never reset dash offset to 0; morph from current state
2. **Number text**: Use `motion.div` + animate({ textContent: newScore }) OR <AnimatedCounter> with springs.soft tween
3. **Color transition**: On band change, stroke color + text color crossfade over 0.26s springs.soft

### J. RiskChart & Recharts

**Current**: Recharts defaults; likely no custom animation.

**Motion Upgrade**:

1. **Line draw-in**: Set `isAnimationActive={true}` on all chart elements
2. **Recharts animation config**: 
   - animationDuration={900}
   - animationEasing="ease-out"
   - animationEasing can also use cubic-bezier; use iOS ease curve
3. **Data morph**: Recharts will smooth line updates automatically
4. **Tooltip**: Tooltip appears with scale 0.96 + opacity 0 → 1 springs.sheet; exits same way

### K. Detail Views (EntityDetail, IncidentPanel, Environment)

**Current**: Likely CSS keyframes or no animation.

**Motion Upgrade**:

1. **Slide in from right**: x:24 → 0 springs.soft on enter; x:24 exit on back
2. **Expandable blocks**: Never use CSS `height` transitions; use motion layout animation
   - `layout` + `layoutId` on container; height animates automatically
   - Or use `height: auto` with `motion` + clip-path animation as fallback
3. **Same page transition** as main sections

### L. Buttons Globally

**Current**: Various hover/active states with transform; inconsistent transitions.

**Motion Upgrade**:

1. **All buttons**: 
   - whileHover scale 1.02
   - whileTap scale 0.96
   - transition springs.snappy (420 stiffness, 34 damping)
2. **Focus-visible ring**: Use motion.div overlay; opacity 0 → 1 springs.soft on focus; duration 0.16s
3. **No "transition: all"** in CSS; all hover/tap changes are motion variants

### M. Modals / Drawers / Dropdowns / Toasts

**Current**: Custom scale-in keyframes if present.

**Motion Upgrade**:

1. **Enter**: scale 0.96 + opacity 0 → 1 with springs.sheet over 0.34s
2. **Exit**: scale 0.92 + opacity 0 faster (0.2s) ease
3. **Backdrop**: Fade opacity 0 → 1 with springs.soft over 0.26s
4. **Dismiss on backdrop click**: Exit animation plays

### N. Live Components (LaboratoriesView, ComputerDetailView, LabTerminalsView, etc.)

**Current**: TBD based on actual file content; likely CSS keyframes or static.

**Motion Upgrade**:

1. **Page transitions**: Same as main app (pageTransition variant)
2. **List items** (computers, terminals, labs): AnimatePresence + layout + listItem variant
3. **Detail cards**: fadeUp + whileInView
4. **Buttons/interactive**: Standard spring hover/tap
5. **Status indicators**: Consistent with main app (breathing glow for online, static for offline)

---

## 4. CSS Cleanup: Animations to Remove/Replace

### CSS Keyframes to Remove
- `@keyframes fade-in` (index.css:95)
- `@keyframes slide-in-left` (index.css:100)
- `@keyframes slide-in-up` (index.css:105)
- `@keyframes scale-in` (index.css:110)
- `@keyframes iosFadeInUp` (ios-motion.css or App.css if duplicated)
- `@keyframes iosPageEntrance` (ios-motion.css)
- `@keyframes iosTabFadeIn` (ios-motion.css)
- `@keyframes iosDropdownEntrance` (CustomSelect.css)
- `@keyframes iosBackdropBlur` (csvAnalytics.css)
- `@keyframes iosModalEntrance` (csvAnalytics.css)
- `@keyframes progress-pulse` (csvAnalytics.css)
- Any other custom keyframes in component CSS files

### CSS Animations (inline `animation:` rules) to Remove
- `.sidebar` animation: slide-in-left 0.3s
- `.main-content` animation: fade-in 0.3s
- `.header` animation: slide-in-up 0.3s
- `.body` animation: fade-in 0.4s
- `.section` animation: slide-in-up 0.3s
- `.stat-card` animation: iosFadeInUp with delay (move to motion)
- `.status-badge` animation: scale-in 0.3s (move to motion)
- `.events-panel`, `.alerts-panel` animation: scale-in 0.3s (move to motion)
- `.telemetry-panel` animation: scale-in 0.3s (move to motion)
- `.settings-card` animation: scale-in 0.3s (move to motion)
- `.ios-page-container` animation: iosPageEntrance (move to motion)
- `.events-list` and `.alerts-list` inline animations on rows (move to motion)

### CSS Transitions (explicit `transition:` rules) to Replace

Replace all `transition: all` with explicit properties:

- `.nav-item` (transition: all → transition: background-color, color, transform; use motion variant instead)
- `.admin-btn` (transition: all → move to motion)
- `.date-filter-pill` (transition: all → move to motion)
- `.stat-card` (transition: complex multi-property → move to motion)
- `.status-badge` (transition: all → move to motion)
- `.event-row`, `.alert-row` (transition: all → move to motion)
- `.custom-select-button` (transition: all → move to motion)
- And many others (see grep output: 50+ transition rules)

**Strategy**:
1. Delete all `@keyframes` definitions from CSS
2. Delete all inline `animation:` properties
3. Replace `transition: all` with motion variants in component code
4. Keep only explicit non-animating transitions (e.g., scrollbar thumb color hover) in CSS

---

## 5. Performance Constraints

### Rendering & Optimization

1. **Animate ONLY transform, opacity, filter**
   - Never animate width, height, top, left, or box-shadow directly
   - Fake shadow growth with opacity-animated ::before or ::after pseudo-element

2. **Remove `transition: all` from CSS**
   - Replace with explicit properties (transform, opacity, background-color, border-color)
   - All interactive transitions move to motion variants

3. **Remove old CSS keyframes**
   - No element should have both CSS animation and motion animation
   - Audit for double-animation artifacts

4. **Layout & Reflow**
   - Use `layout` / `layoutId` for position and size changes (Recharts, lists)
   - Never manually calculate positions; let layout handle it

5. **will-change**
   - Add `will-change: transform` ONLY to actively animating elements
   - Never set globally; motion will add it as needed

6. **MotionConfig at App Root**
   ```jsx
   import { MotionConfig } from 'motion/react';
   
   <MotionConfig reducedMotion="user">
     <AppContent />
   </MotionConfig>
   ```

### Batching & Throttling

1. **List items**: Cap simultaneous entering rows to ~5
   - If 20 events arrive at once, animate first 5, queue remaining with stagger
   - Use a counter + state to manage batch size

2. **Avoid re-renders**: 
   - Memoize list rows with `React.memo`
   - Keep stable `key={item.id}` (never index-based keys for dynamic lists)
   - Don't create variant objects inline; import from motion.js

3. **Debounce chart updates**:
   - Batch WebSocket events; don't animate on every tick
   - Update Recharts data once per 200-300ms, not on every event

### Frame Rate & Jank Prevention

- **Target 60fps** (120fps on ProMotion displays)
- **No jank** when WebSocket pushes multiple events/second
  - Batch updates via setTimeout/requestAnimationFrame
  - Stagger list item animations (0.04s per item) to smooth throughput
- **Monitor performance**: Use React DevTools Profiler to check for layout thrashing

### Interruptibility

- All interactive animations use springs (no keyframe arrays)
- Springs naturally handle interruption and reverse smoothly
- Example: user hovers button, then immediately taps; animation interrupts and reverses

---

## 6. Implementation Order (Minimize Conflicts)

Execute in this order to avoid dependency conflicts:

1. **Install `motion` package**
   ```bash
   npm install motion
   ```

2. **Create `src/motion.js`**
   - Export springs, variants, useMotionPrefs, useMotionConfig
   - No JSX dependencies yet

3. **Wrap App.jsx with MotionConfig**
   ```jsx
   import { MotionConfig } from 'motion/react';
   
   export default function App() {
     return (
       <MotionConfig reducedMotion="user">
         <DateProvider>
           <AppContent />
         </DateProvider>
       </MotionConfig>
     );
   }
   ```

4. **Update index.css & App.css**
   - Remove all `@keyframes` definitions
   - Remove all inline `animation:` properties
   - Remove `transition: all` rules (or replace with explicit properties)
   - Keep only core layout and color/text styles

5. **Update App.jsx in order**:
   - Sidebar nav (layoutId pill, whileHover/Tap, stagger)
   - Header (category label fadeUp)
   - OverviewSection (stat cards fadeUp stagger, counter animate)
   - LiveTelemetrySection (events/alerts lists AnimatePresence + layout)
   - SettingsSection (panels whileInView)
   - StatusBadge component (breathing glow)
   - EventsTable & AlertList (motion rows, highlight flash, collapse exit)

6. **Update components in order**:
   - `PageTransition.jsx` → wrap with AnimatePresence, add pageTransition variant
   - `RiskGauge.jsx` → animate stroke-dashoffset from previous, number counter
   - `Sparkline.jsx` → add pathLength draw-in animation (if needed)
   - `DateFilter.jsx` → button whileHover/Tap
   - `CustomSelect.jsx` → dropdown fadeUp scale
   - `ScrollReveal.jsx` → whileInView fadeUp (if exists)

7. **Update live components**:
   - `LaboratoriesView.jsx`, `ComputerDetailView.jsx`, `LabTerminalsView.jsx`
   - Consistent page transitions, list animations, status indicators

8. **Update CSV Analyzer**:
   - Remove old keyframes from `csvAnalytics.css`
   - Add motion to modals, buttons, upload area

9. **Test & Debug**:
   - npm run build (verify no warnings)
   - Visual testing: scroll, click, interact with lists
   - Accessibility: test with `prefers-reduced-motion: reduce`
   - Performance: check React Profiler for jank

---

## 7. Tuning Guide

All motion feel adjusts in `src/motion.js`. Reference this table to dial in the exact feel:

| Parameter | Effect | Snappier | Softer |
|-----------|--------|---------|--------|
| **springs.soft.stiffness** | Page transition speed | ↑ 280 | ↓ 240 |
| **springs.soft.damping** | Overshoot on exit settle | ↑ 35 | ↓ 25 |
| **springs.snappy.stiffness** | Button tap response | ↑ 440 | ↓ 380 |
| **springs.snappy.damping** | Button bounce | ↑ 40 | ↓ 28 |
| **springs.sheet.stiffness** | Modal pop speed | ↑ 320 | ↓ 280 |
| **staggerConfig.staggerChildren** | List item spacing | ↓ 0.03s | ↑ 0.07s |
| **staggerConfig.delayChildren** | List start delay | ↓ 0.05s | ↑ 0.12s |

### Examples

- **Bouncier feel** (not recommended for iOS aesthetic):
  - Increase stiffness by +20, decrease damping by -3
  - Result: Visible overshoot on page exit, snappy button tap with wobble

- **Calmer feel** (recommended for TAVIX GUARD dashboard):
  - Keep stiffness ± 10, increase damping by +2
  - Result: Smooth settle, minimal overshoot, refined interaction

- **Faster stagger** (for snappier list reveal):
  - staggerChildren: 0.03, delayChildren: 0.05
  - Result: All 12 items in ≈ 0.4s instead of 0.68s

---

## 8. Accessibility & Reduced Motion

### prefers-reduced-motion Support

The `useMotionPrefs()` hook in `motion.js` detects user preference:

```javascript
const prefersReducedMotion = useMotionPrefs();

if (prefersReducedMotion) {
  // Fallback to simple 150ms fades for all animations
  // No springs, no transforms
}
```

### Testing

```bash
# macOS
System Preferences → Accessibility → Display → Reduce motion

# Windows 10/11
Settings → Ease of Access → Display → Show animations

# Browser DevTools (Chrome/Edge)
DevTools → Rendering → More settings → Emulate CSS media feature prefers-reduced-motion
```

### Manual Testing Checklist

- [ ] Page transitions work with motion disabled
- [ ] List items animate in without motion disabled
- [ ] Buttons respond tactilely (scale or opacity only)
- [ ] No flashing or jarring effects
- [ ] Keyboard navigation unaffected
- [ ] Screen readers read content correctly

---

## 9. Build & Verification

### Pre-Build Checklist

- [ ] `npm run lint` passes (no ESLint errors from motion imports)
- [ ] No duplicate animations (CSS + motion on same element)
- [ ] All `transition: all` removed or converted
- [ ] `MotionConfig reducedMotion="user"` wraps App
- [ ] No inline variant objects in render functions

### Build & Test

```bash
cd frontend
npm run build
# Verify: no warnings, dist/ contains app

# Preview
npm run preview
# Test: scroll lists, click nav, hover buttons, switch pages
```

### Performance Profiling

1. Open Chrome DevTools → Performance tab
2. Record 5-second session: scroll list, click buttons, switch pages
3. Check for:
   - No 60fps drops (red bars)
   - No layout thrashing (purple blocks)
   - Smooth animations at 60fps (green)

---

## 10. Files to Modify / Create

| File | Action | Summary |
|------|--------|---------|
| `src/motion.js` | **CREATE** | Central config: springs, variants, useMotionPrefs |
| `src/App.jsx` | **MODIFY** | Add motion to all sections; use AnimatePresence, variants |
| `src/App.css` | **MODIFY** | Remove @keyframes, animation:, transition: all rules |
| `src/index.css` | **MODIFY** | Remove fade-in, slide-in-*, scale-in keyframes |
| `src/styles/ios-motion.css` | **DELETE or REPLACE** | Old iOS motion rules; either keep as reference or remove |
| `src/components/PageTransition.jsx` | **MODIFY** | Wrap with AnimatePresence, apply pageTransition variant |
| `src/components/RiskGauge.jsx` | **MODIFY** | Animate arc from previous, counter tween, color transition |
| `src/components/RiskGauge.css` | **CLEAN** | Remove any keyframes or transitions |
| `src/components/Sparkline.jsx` | **MODIFY** | Add pathLength draw-in animation (optional) |
| `src/components/DateFilter.jsx` | **MODIFY** | Button whileHover/Tap variants |
| `src/components/CustomSelect.jsx` | **MODIFY** | Dropdown fadeUp + scale, stagger items |
| `src/components/ScrollReveal.jsx` | **MODIFY** | Replace with whileInView fadeUp (if exists) |
| `src/components/live/*.jsx` | **MODIFY** | Page transitions, list animations, status indicators |
| `src/csv_analytics/csvAnalytics.css` | **MODIFY** | Remove keyframes (iosBackdropBlur, iosModalEntrance, progress-pulse) |
| `src/csv_analytics/CsvAnalyticsPage.jsx` | **MODIFY** | Add motion to modals, buttons, charts |

---

## 11. Debugging Checklist

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Animation not playing | Variant not passed to motion.div | Check `animate="visible"` is set |
| Jank on list scroll | Too many items animating simultaneously | Implement batch cap (max 5 simultaneous) |
| Button scale feels stiff | Spring stiffness too high | Reduce stiffness by 20, increase damping by 3 |
| Page transition too slow | Spring damping too high | Reduce damping by 5 |
| Double animation on element | CSS animation + motion.div both running | Remove CSS `animation:` or remove motion wrapper |
| Text layout shift on number update | Not using tabular-nums font feature | Add `font-feature-settings: "tnum"` to clock |
| Reduced motion ignored | MotionConfig not wrapping app | Verify MotionConfig at App root |

---

## 12. Summary of Changes

### High-Level Changes

1. **Install** `motion` package (React 19 compatible successor to Framer Motion)
2. **Create** `src/motion.js` with centralized spring configs and variants
3. **Wrap App** with `<MotionConfig reducedMotion="user">` for accessibility
4. **Remove** 50+ CSS animations, keyframes, and `transition: all` rules
5. **Replace** with motion.div, AnimatePresence, whileHover/whileTap variants
6. **Audit** components for double-animations and inline variant objects
7. **Batch** list animations (cap 5 simultaneous; stagger remainder)
8. **Test** build, performance, accessibility, and interactions

### No Changes To

- ✅ Data logic, state management, Redux (if used)
- ✅ API calls, WebSocket connection
- ✅ Color scheme, typography, spacing
- ✅ Component props or JSX structure (only wrapping with motion)
- ✅ Functionality of any feature

### Result

Every layout, page, component, and interaction animates with **buttery-smooth, spring-based, iOS 17/18-style motion**—exactly matching Apple's Settings, App Store, and Apple Music design language. The dashboard feels weighted, responsive, and premium while maintaining 60fps performance and full accessibility.

---

## References

- [motion package](https://motion.dev/) — React 19 compatible, Framer Motion successor
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) — iOS 17/18 animation principles
- [CSS `will-change`](https://developer.mdn.org/en-US/docs/Web/CSS/will-change) — Performance hints
- [prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) — Accessibility standard
