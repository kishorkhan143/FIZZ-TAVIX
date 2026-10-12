# TAVIX GUARD — Premium Motion Architecture

This document defines the reusable motion system for TAVIX GUARD, a cybersecurity React + Vite dashboard. All animations and transitions are GPU-accelerated, accessibility-compliant, and designed for premium iOS-style fluidity.

---

## 1. Animation Token System

All timing, easing, and shadow values are defined as CSS custom properties in `src/styles/ios-motion.css` and `src/index.css`. These tokens ensure consistency across the entire application.

### 1.1 Duration Tokens

| Token | Value | Use Case |
|-------|-------|----------|
| `--ios-duration-micro` | 130ms | Icon toggles, checkboxes, badge updates, micro-interactions |
| `--ios-duration-fast` | 180ms | Button taps, nav items, pills, form focus, tap feedback |
| `--ios-duration-normal` | 260ms | Dropdowns, tabs, popovers, modals, select menus |
| `--ios-duration-smooth` | 340ms | Cards, panels, drawer slides, modal entrance |
| `--ios-duration-page` | 300ms | Full view transitions, page route changes |
| `--ios-duration-skeleton` | 1500ms | Shimmer loop for skeleton loading |

### 1.2 Easing Curves

All easing curves use cubic-bezier functions for precise, natural-feeling motion:

| Token | Curve | Characteristics | Use Case |
|-------|-------|-----------------|----------|
| `--ios-ease` | `cubic-bezier(0.22, 1, 0.36, 1)` | Snappy deceleration, rapid start with silky gentle landing | Standard transitions, button feedback |
| `--ios-spring` | `cubic-bezier(0.175, 0.885, 0.32, 1.15)` | Lively spring with refined responsiveness, no exaggerated wobble | Icon scales, interactive feedback |
| `--ios-spring-soft` | `cubic-bezier(0.16, 1, 0.3, 1)` | Smooth organic velocity, fluid spring motion | Card entrances, modal opens, page transitions |
| `--ios-ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Standard ease-in-out rhythm | Fallback for compatibility |

### 1.3 Shadow Tokens

Shadows provide depth and hierarchy in animations:

| Token | Value |
|-------|-------|
| `--ios-shadow-subtle` | `0 2px 6px -1px rgba(0, 0, 0, 0.05), 0 1px 3px -1px rgba(0, 0, 0, 0.03)` |
| `--ios-shadow-card` | `0 4px 16px -2px rgba(0, 0, 0, 0.06), 0 2px 6px -1px rgba(0, 0, 0, 0.03)` |
| `--ios-shadow-card-hover` | `0 12px 28px -4px rgba(0, 102, 255, 0.12), 0 4px 12px -2px rgba(0, 0, 0, 0.06)` |
| `--ios-shadow-popover` | `0 16px 36px -6px rgba(0, 0, 0, 0.15), 0 4px 12px -2px rgba(0, 0, 0, 0.08)` |
| `--ios-shadow-modal` | `0 24px 60px -12px rgba(0, 0, 0, 0.25), 0 8px 24px -4px rgba(0, 0, 0, 0.1)` |

---

## 2. Reusable CSS Animation Classes

All keyframe animations and utility classes are defined in `src/styles/ios-motion.css` for global reuse.

### 2.1 Keyframe Animations

#### Page & View Entrances
- **`iosPageEntrance`**: Fade-in with subtle upward translation (10px). Duration: `--ios-duration-page`, Easing: `--ios-spring-soft`.
- **`iosTabFadeIn`**: Gentle fade with small Y-translate for tab content. Duration: `--ios-duration-normal`, Easing: `--ios-ease`.

#### Card & Element Reveals
- **`iosFadeInUp`**: Opacity fade + translateY(14px) → 0. Duration: `--ios-duration-smooth`, Easing: `--ios-spring-soft`.
- **`iosScaleIn`**: Scale entrance from 0.95 to 1 with fade. Duration: `--ios-duration-smooth`, Easing: `--ios-spring-soft`.

#### Modal & Overlay Transitions
- **`iosModalEntrance`**: Scale-in from 0.92 with 16px downward Y-translate + fade. Duration: `--ios-duration-smooth`, Easing: `--ios-spring-soft`.
- **`iosBackdropBlur`**: Backdrop opacity fade + blur(0px) → blur(14px). Duration: `--ios-duration-normal`, Easing: `--ios-ease`.

#### Dropdown & Popover
- **`iosDropdownEntrance`**: Scale-in from 0.96, Y-translate -8px → 0. Duration: `--ios-duration-normal`, Easing: `--ios-spring-soft`.

#### Notifications & Toast
- **`iosToastSlideIn`**: Upward slide with scale-in and fade. Duration: `--ios-duration-fast`, Easing: `--ios-spring-soft`.

#### Micro-animations
- **`iosPulseSubtle`**: Gentle pulse scale (1 → 1.08 → 1) with opacity shift (1 → 0.85 → 1). Duration: 2.2s infinite. Used for live status indicators.
- **`iosShimmer`**: Background gradient slide for skeleton loading placeholders. Duration: `--ios-skeleton`.

### 2.2 Utility Classes

#### Scroll-Triggered Reveals (see ScrollReveal component)
```css
.ios-reveal {
  opacity: 0;
  transform: translateY(14px);
  transition: opacity var(--ios-duration-smooth) var(--ios-ease),
              transform var(--ios-duration-smooth) var(--ios-spring-soft);
  will-change: opacity, transform;
}

.ios-reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}
```

#### Stagger Delays (for list reveals, staggered card entrance)
```css
.ios-stagger-1 { animation-delay: 30ms; }
.ios-stagger-2 { animation-delay: 60ms; }
.ios-stagger-3 { animation-delay: 90ms; }
/* ... up to .ios-stagger-10 (300ms) */
```

Apply stagger classes alongside animation classes:
```jsx
<div className="some-animation ios-stagger-2">Content</div>
```

#### Page Container
```css
.ios-page-container {
  animation: iosPageEntrance var(--ios-duration-page) var(--ios-spring-soft) forwards;
  will-change: transform, opacity;
}
```

#### Tap Feedback & Press Feedback
```css
/* All interactive buttons/cards scale to 0.972 on active */
button:active:not(:disabled),
.nav-item:active,
.stat-card:active {
  transform: scale(0.972);
}

/* Modal close button: scale + rotate */
.modal-close-btn:active {
  transform: scale(0.9) rotate(90deg);
}
```

#### Loading States
```css
.ios-skeleton {
  background: linear-gradient(90deg, rgba(229, 231, 235, 0.7) 0%,
    rgba(243, 244, 246, 0.9) 50%, rgba(229, 231, 235, 0.7) 100%);
  background-size: 200% 100%;
  animation: iosShimmer var(--ios-skeleton) infinite linear;
  border-radius: var(--radius-md);
}
```

---

## 3. React Hook API

### 3.1 useReducedMotion Hook

**Location:** `src/utils/useReducedMotion.js` (to be created during implementation)

**Purpose:** Detects the user's `prefers-reduced-motion` setting and disables or reduces animations globally.

**Usage:**
```jsx
import { useReducedMotion } from '../utils/useReducedMotion';

export default function MyComponent() {
  const prefersReducedMotion = useReducedMotion();
  
  return (
    <div
      className={prefersReducedMotion ? '' : 'some-animation'}
      style={{
        transitionDuration: prefersReducedMotion ? '0.01ms' : '0.26s',
      }}
    >
      Content
    </div>
  );
}
```

**Implementation:** Returns a boolean that reflects `window.matchMedia('(prefers-reduced-motion: reduce)').matches`. Hook also listens for changes.

### 3.2 useIntersectionObserver Hook

**Location:** `src/components/ScrollReveal.jsx` (already implemented)

**Purpose:** Triggers animations when an element scrolls into the viewport without repeated replay on minor scrolls.

**Behavior:**
- Observes element visibility using IntersectionObserver
- Fires animation once when `threshold` (default: 0.08) is reached
- Unobserves after first trigger
- Respects `rootMargin: '0px 0px -20px 0px'` to avoid triggering animations too early

**Props:**
- `threshold` (optional): IntersectionObserver threshold. Default: 0.08
- `stagger` (optional): Multiplies by 45ms for animation delay. Example: `stagger={2}` = 90ms delay
- `className` (optional): Additional CSS classes to apply
- `as` (optional): Component type to render. Default: 'div'

---

## 4. Page Transition Strategy

### 4.1 PageTransition Wrapper Component

**Location:** `src/components/PageTransition.jsx`

**Purpose:** Wraps each route view/page to provide smooth fade-in + subtle Y-translate entrance animations without remounting business logic.

**Implementation:**
```jsx
export default function PageTransition({ children, transitionKey, className = '' }) {
  return (
    <div
      key={transitionKey}
      className={`ios-page-container ${className}`}
      style={{ width: '100%', minHeight: '100%' }}
    >
      {children}
    </div>
  );
}
```

**Integration in React Router:**

All major views (pages) must be wrapped by `PageTransition` with a unique `transitionKey`:

```jsx
import PageTransition from './components/PageTransition';
import LiveDashboardView from './components/live/LiveDashboardView';

<PageTransition transitionKey="dashboard">
  <LiveDashboardView />
</PageTransition>

<PageTransition transitionKey="laboratories">
  <LaboratoriesView />
</PageTransition>
```

**How it works:**
- Each route change receives a new `transitionKey` prop
- React remounts the PageTransition container (which has the key), triggering the `iosPageEntrance` animation
- Child component state is preserved by React's reconciliation if it doesn't depend on the key
- Browser back/forward works correctly without forced state loss

---

## 5. Component-by-Component Motion Spec

### 5.1 Global Layout

| Component | Animation | Trigger | Duration | Easing | Notes |
|-----------|-----------|---------|----------|--------|-------|
| `.sidebar` | `slide-in-left` | Page load | `--ios-duration-page` | `--ios-spring-soft` | Initial entrance from left |
| `.header` | `slide-in-up` | Page load | `--ios-duration-page` | `--ios-spring-soft` | Subtle upward entrance |
| `.main-content` | `fade-in` | Page load | `--ios-duration-page` | `--ios-spring-soft` | Smooth content fade |
| `.body` | `fade-in` (0.4s, 0.1s delay) | Page load | `--ios-duration-smooth` | `--ios-spring-soft` | Staggered entrance |

### 5.2 Sidebar Navigation

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.nav-item` | All transitions | Hover/Active/Focus | `--ios-duration-fast` | Color, background, transform (3px translateX on hover) |
| `.nav-item:active` | Scale press | Mouse/Touch active | `--ios-duration-fast` | Scale 0.975 |
| `.nav-icon` | Transform + scale | Hover/Active | `--ios-duration-fast` | Scale 1.06 on hover, 1.12 when active |
| `.admin-btn` | Hover elevation | Hover | `--ios-duration-base` | TranslateY(-2px), shadow elevation |

### 5.3 Buttons & Interactive Controls

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `button` (all) | Transition all properties | Hover/Focus/Active | `--ios-duration-fast` | See `ios-motion.css` tap feedback |
| `:active` state | Scale 0.972 | Mouse/Touch down | `--ios-duration-fast` | Tactile press feedback |
| `.date-filter-pill` | Hover elevation + Y-translate | Hover | `--ios-duration-base` | TranslateY(-1px), subtle shadow |

### 5.4 Status Badges & Cards

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.status-badge` | Scale-in entrance | Initial render | `--ios-duration-normal` | Scale 0.95 → 1 with fade |
| `.status-badge:hover` | Elevation + Y-translate | Hover | `--ios-duration-base` | TranslateY(-2px), shadow upgrade |
| `.stat-card` | Scale-in entrance, hover elevation | Initial render / Hover | `--ios-duration-smooth` / `--ios-duration-normal` | Primary entrance; Hover: translateY(-4px) scale(1.008) |
| `.stat-card .stat-icon` | Rotate + scale on hover | Hover | `--ios-duration-normal` | Scale 1.1, rotate -3deg |

### 5.5 Panels & Card Containers

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.events-panel, .alerts-panel, .telemetry-panel` | Scale-in entrance | Initial render | `--ios-duration-normal` | Scale 0.95 → 1 with opacity fade |
| `.settings-card` | Scale-in entrance | Initial render | `--ios-duration-normal` | Scale entrance |
| Row hover (`.event-row, .alert-row`) | Translate + background shift | Hover | `--ios-duration-fast` | TranslateX(4px), background color change |

### 5.6 Tables & Lists

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.event-row, .alert-row` | Hover highlight + slide | Hover | `--ios-duration-fast` | Background tertiary, translateX(4px) |
| `.event-row:active` | Press scale | Active | `--ios-duration-fast` | Scale 0.995 |

### 5.7 Modals & Overlays

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.modal-backdrop` | Blur + opacity | Modal open | `--ios-duration-normal` | iosBackdropBlur: blur(0) → blur(14px), opacity fade |
| `.modal-dialog` | Scale + Y-translate + fade | Modal open | `--ios-duration-smooth` | iosModalEntrance: scale(0.92) → 1, translateY(16px) → 0 |
| `.modal-close-btn` | Rotate + scale on hover/active | Hover/Active | `--ios-duration-fast` | Hover: rotate(90deg) scale(1.1); Active: rotate(90deg) scale(0.9) |

### 5.8 Dropdowns, Menus & Selects

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.custom-select-menu, .export-dropdown-menu` | Scale-in with backdrop blur | Open | `--ios-duration-normal` | iosDropdownEntrance: translateY(-8px) scale(0.96) → identity |
| `.custom-select-option, .export-dropdown-item` | Color + transform on hover | Hover | `--ios-duration-fast` | Background change, translateX(3px) |

### 5.9 Form Inputs & Search

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `input[type="text"], input[type="date"], textarea, select` | Border + glow on focus | Focus | `--ios-duration-fast` | Border color + box-shadow with accent color |
| `:focus` state | Slight Y-translate | Focus | `--ios-duration-fast` | TranslateY(-1px) for tactile rise |

### 5.10 Badges, Indicators & Pulses

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.status-badge.online .dot, .live-pulse-dot` | Pulse animation | Always (live status) | 2.2s infinite | iosPulseSubtle: scale(1 → 1.08 → 1), opacity shift |
| `.badge` | Scale micro-interaction | Panel header hover | `--ios-duration-micro` | Scale 1 → 1.08 |

### 5.11 Loading States & Skeletons

| Component | Animation | Trigger | Duration | Notes |
|-----------|-----------|---------|----------|-------|
| `.ios-skeleton` | Shimmer gradient slide | Skeleton visible | 1500ms infinite | iosShimmer: background gradient sweep left-to-right |

### 5.12 Scroll-Triggered Reveals

All card panels and list sections that enter the viewport use the `ScrollReveal` wrapper component:

| Component | Animation | Trigger | Duration | Threshold |
|-----------|-----------|---------|----------|-----------|
| `.ios-reveal` | Fade-up on scroll | Content enters viewport | `--ios-duration-smooth` | 0.08 (8% visible) |
| Staggered reveals | Reveal with incremental delay | Multiple reveal children | `--ios-duration-smooth` | 45ms per child |

**Example:**
```jsx
import ScrollReveal from './components/ScrollReveal';

<ScrollReveal stagger={0}><Card1 /></ScrollReveal>
<ScrollReveal stagger={1}><Card2 /></ScrollReveal>
<ScrollReveal stagger={2}><Card3 /></ScrollReveal>
```

---

## 6. Performance Guidelines

### 6.1 GPU-Accelerated Properties

Only animate properties that trigger GPU compositing to ensure 60 FPS:

- **`transform`** (translate, scale, rotate, skew) — Always GPU-accelerated
- **`opacity`** — GPU-accelerated
- **`filter`** and **`backdrop-filter`** — GPU-accelerated (use cautiously)

**Never animate:**
- `width`, `height`, `padding`, `margin` — Triggers layout recalculation
- `top`, `left`, `bottom`, `right` — Triggers reflow
- `background-color` — CPU-rendered, but acceptable for short transitions
- `border`, `box-shadow` (except in modals/popovers) — CPU-intensive

### 6.2 will-change Usage

Apply `will-change: transform, opacity;` to elements that animate frequently:

```css
.stat-card {
  will-change: transform;
  transition: transform var(--ios-duration-normal) var(--ios-spring-soft);
}
```

**Rules:**
- Apply only to elements that will actually animate
- Remove or clear after animation ends if applied dynamically
- Never apply `will-change: all;`

### 6.3 Animation Limits

- **Simultaneous animations**: Limit to 8-10 DOM elements animating at once on a single view
- **Stagger delays**: Use increments of 30-45ms for list reveals (10-12 items max with stagger)
- **Scroll-triggered animations**: Use viewport threshold to fire once, then cleanup with `unobserve()`
- **Data table rows**: Do not animate entrance for virtualized tables with hundreds of rows; animate only visible rows

### 6.4 GPU Hints

Ensure hardware acceleration with:
```css
element {
  transform: translateZ(0);
  backface-visibility: hidden;
  -webkit-tap-highlight-color: transparent;
}
```

---

## 7. Accessibility & Reduced Motion

### 7.1 prefers-reduced-motion Media Query

All animations respect the system accessibility preference via `@media (prefers-reduced-motion: reduce)`:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  .ios-page-container,
  .modal-dialog,
  .custom-select-menu {
    transform: none !important;
    animation: none !important;
    opacity: 1 !important;
  }
}
```

**Implementation:**
- All CSS animations are automatically reduced to 0.01ms duration
- JavaScript scroll behavior reverts to instant
- Page transitions and modals appear instantly without animations
- No visual glitches or opacity changes occur

### 7.2 useReducedMotion Hook (React)

In React components, detect reduced motion and conditionally apply animations:

```jsx
const prefersReducedMotion = useReducedMotion();

return (
  <div
    style={{
      transition: prefersReducedMotion ? 'none' : 'opacity 0.26s ease',
    }}
  >
    Content
  </div>
);
```

### 7.3 Keyboard Navigation

Ensure all interactive elements have visible focus indicators. Focus animations use the same easing as hover:

```css
button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  animation: focusGlow var(--ios-duration-fast) var(--ios-ease) forwards;
}
```

---

## 8. Mobile & Responsive Strategy

### 8.1 Touch Feedback

On mobile/touch devices, ensure tactile feedback is clear:
- Active scale: 0.97 (similar to desktop but more pronounced)
- Duration: `--ios-duration-fast` (180ms) for snappy feedback
- No hover states on touch; rely on focus and active states

**Implementation:**
```css
@media (hover: none) {
  /* Remove hover-specific animations on touch devices */
  button:hover {
    transform: none;
  }
}
```

### 8.2 Reduced Animation on Small Screens

On devices with low-power CPUs, reduce animation complexity:
- Keep stagger count under 6 items
- Use shorter durations (180ms instead of 260ms) where acceptable
- Avoid parallax effects entirely
- Simplify shadows (reduce blur radius on modals)

```css
@media (max-width: 768px) {
  .ios-page-container {
    --ios-duration-page: 250ms;
  }
  
  .stat-card {
    animation-duration: 200ms;
  }
}
```

### 8.3 Scrollbar & Scroll Behavior

- Smooth scrolling is enabled globally but disabled on low-motion preference
- Custom scrollbars use subtle colors that match the theme
- Scroll-triggered reveals fire at 0.08 threshold to avoid delayed perception on mobile

### 8.4 Layout & Overflow

- No horizontal overflow caused by animations
- All transforms use `translateX()` within safe bounds
- Modals and popovers position correctly on small screens
- Sidebar remains hidden on mobile; use fixed positioning, not animations, to show/hide

---

## 9. Scroll Behavior & Parallax

### 9.1 Smooth Scrolling

Global smooth scroll is enabled via CSS:

```css
html {
  scroll-behavior: smooth;
}
```

**Scope:**
- Applied to window/document scrolling for anchor navigation
- Applied within scrollable containers (e.g., event lists, table panels)
- Disabled on low-motion preference

### 9.2 Scroll-Triggered Animations (ScrollReveal)

Use the `ScrollReveal` component to trigger animations when content enters the viewport:

```jsx
import ScrollReveal from './components/ScrollReveal';

<ScrollReveal threshold={0.08} stagger={0}>
  <StatCard />
</ScrollReveal>

<ScrollReveal threshold={0.08} stagger={1}>
  <EventRow />
</ScrollReveal>
```

**Behavior:**
- Fires once when element reaches 8% visibility
- Does not replay on minor back-and-forth scrolling
- Uses 45ms stagger multiplier between items
- Unobserves after first trigger to prevent repeated animation

### 9.3 No Parallax

Parallax effects are avoided to maintain performance and accessibility. If parallax is desired in future, it should:
- Only apply on desktop with sufficient GPU
- Disable on mobile and low-motion preference
- Use `transform: translateZ()` for GPU acceleration

---

## 10. Backward Compatibility & Fallbacks

### 10.1 Graceful Degradation

- All animations fall back to instant transitions in older browsers
- CSS custom properties have fallback values: `var(--token, fallback-value)`
- IntersectionObserver is detected; if unavailable, elements reveal immediately
- Transforms and filter effects are progressive enhancements

### 10.2 Browser Support

- Chrome/Edge 60+
- Firefox 55+
- Safari 12+
- Mobile Safari 12+

All target browsers support:
- CSS custom properties
- `transform` and `opacity`
- IntersectionObserver
- `prefers-reduced-motion`
- `backdrop-filter` (with -webkit prefix)

---

## 11. Implementation Checklist

During the implementation phase, ensure:

1. ✅ All CSS tokens are imported in `index.css` and used consistently
2. ✅ PageTransition wrapper is applied to every major view/page
3. ✅ ScrollReveal component wraps card/panel/row elements that should fade-up on scroll
4. ✅ Stagger classes applied to list items (max 10 items)
5. ✅ All buttons and interactive elements use unified tap feedback (0.972 scale)
6. ✅ Modals use `iosModalEntrance` + `iosBackdropBlur` keyframes
7. ✅ Dropdowns/selects use `iosDropdownEntrance` keyframe
8. ✅ Hover states use `--ios-duration-fast` or `--ios-duration-normal`
9. ✅ Loading skeletons use `ios-skeleton` class with shimmer animation
10. ✅ Forms use focus highlight animation and glow effect
11. ✅ Table/list rows animate on hover (translateX, background transition)
12. ✅ Live status indicators use `iosPulseSubtle` animation
13. ✅ `prefers-reduced-motion` media query is respected globally
14. ✅ All GPU-accelerated properties use `will-change` where necessary
15. ✅ No animations exceed 400ms on main thread
16. ✅ Mobile breakpoints reduce animation complexity
17. ✅ Accessibility focus rings are visible and smooth

---

## 12. Future Extensions

Potential enhancements (out of scope for v1):
- **Gesture-based animations**: Swipe-to-dismiss for cards
- **Rive animations**: For complex dashboard intro sequences
- **Lottie integrations**: For loading states or success celebrations
- **Haptic feedback**: Vibration on tap (mobile)
- **Voice-driven animations**: Respond to voice commands with micro-interactions
- **3D transforms**: Perspective-based card flip effects for detail views

---

**Document Version**: 1.0  
**Last Updated**: Implementation Phase  
**Maintained By**: Frontend Team
