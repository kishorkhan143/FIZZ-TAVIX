# Implementation Plan: TAVIX GUARD Premium iOS-Style Animations

**Project**: TAVIX GUARD React + Vite Cybersecurity Dashboard  
**Frontend Root**: `c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend`  
**Build Command**: `npm run build`  
**Lint Command**: `npm run lint`  
**Package Manager**: npm (with React 19.2.8, Vite 8.3.0)

---

## Architecture Overview

The animation system is already **50% implemented** with a solid foundation:
- ✅ `ios-motion.css` defines all tokens, easing curves, and keyframes
- ✅ `PageTransition.jsx` wraps route changes with smooth page entrance animations
- ✅ `ScrollReveal.jsx` provides viewport-triggered fade-up reveals with stagger support
- ✅ `prefers-reduced-motion` media query handles accessibility

**Gaps to close**:
1. ❌ `useReducedMotion` hook does not exist (required by design spec Section 3.1)
2. ❌ `--ios-duration-base` token is referenced but not defined (Finding #3 from design review)
3. ❌ Scroll-triggered reveals not yet applied to all list/card components
4. ❌ Some modal and dropdown CSS classes not verified in actual components

This plan addresses all gaps and applies animations component-by-component, prioritized by user impact.

---

## Step 0 — Setup: CSS Tokens & Foundation Audit

**Objective**: Verify all CSS tokens exist, define missing token, and confirm ios-motion.css is complete.

**Changes**:
- Audit `src/index.css` — Confirm all fallback tokens are defined
- Audit `src/styles/ios-motion.css` — Verify all keyframes and easing tokens match motion-design.md Section 1
- **Add missing token** to `src/styles/ios-motion.css` root:
  - `--ios-duration-base: 180ms;` (equivalent to `--ios-duration-fast` for backward compatibility)

**Files to modify**:
- `src/styles/ios-motion.css` (add `--ios-duration-base` token)

**Expected result**:
- All 6 duration tokens defined: micro, fast, **base**, normal, smooth, page, skeleton
- All 4 easing tokens defined: ease, spring, spring-soft, ease-in-out
- All 5 shadow tokens defined: subtle, card, card-hover, popover, modal
- All 11 keyframes present and valid: iosPageEntrance, iosFadeInUp, iosScaleIn, iosModalEntrance, iosBackdropBlur, iosDropdownEntrance, iosToastSlideIn, iosPulseSubtle, iosShimmer, and legacy fade-in, slide-in-left, slide-in-up, scale-in

**Verification**:
```bash
cd "c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend"
npm run build
# Expected: Build succeeds with no CSS errors
```

---

## Step 1 — Create useReducedMotion Hook

**Objective**: Implement the accessibility hook specified in motion-design.md Section 3.1.

**New file**: `src/utils/useReducedMotion.js`

**Purpose**: Detect system preference for reduced motion and provide hook for React components to conditionally apply animations.

**Implementation**:
```javascript
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
```

**Files**:
- Create `src/utils/useReducedMotion.js`

**Verification**:
```bash
cd "c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend"
npm run build
# Expected: Build succeeds; lint passes
# Manual test: Open browser DevTools > Rendering > Emulate CSS media feature prefers-reduced-motion: reduce
#   — Page should render with instant animations (0.01ms duration)
```

---

## Step 2 — Verify & Align iOS Motion CSS Classes

**Objective**: Ensure all CSS class names used in ios-motion.css match actual component implementations.

**Classes to verify exist in component JSX files**:
- `.custom-select-menu` in `src/components/CustomSelect.jsx` ✓ Confirmed
- `.custom-select-button` ✓ Confirmed
- `.custom-select-option` ✓ Confirmed
- `.export-dropdown-menu` in `src/components/ExportAnalysisDropdown.jsx` (verify)
- `.modal-dialog` in modal implementations (AddLabModal, LiveAlertModal, etc.) (verify)
- `.modal-backdrop` (verify)
- `.modal-close-btn` (verify)
- `.event-row` in live views (verify)
- `.alert-row` in alert views (verify)
- `.stat-card` in dashboard (verify)
- `.status-badge` (verify)
- `.nav-item` in sidebar (verify)

**Files to verify**:
- `src/components/AddLabModal.jsx`
- `src/components/AssignLabModal.jsx`
- `src/components/LiveAlertModal.jsx`
- `src/components/ExportAnalysisDropdown.jsx`
- `src/components/live/LiveDashboardView.jsx`
- `src/components/live/LiveAlertsView.jsx`
- `src/App.css` (where .nav-item, .stat-card are defined)

**Expected result**: All CSS selectors in ios-motion.css match actual rendered class names, or update ios-motion.css to correct selectors if classes differ.

**Verification**:
```bash
cd "c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend"
npm run build && npm run lint
# Expected: Build succeeds; no console errors about undefined classes
# Manual: Open DevTools > Elements; search for .custom-select-menu, .modal-dialog, confirm they exist and receive animations
```

---

## Step 3 — Wrap All Main Pages with PageTransition (Already Done)

**Status**: PageTransition is already integrated in `App.jsx` for all major route changes.

**Verification**: Confirm in `App.jsx` that these views are wrapped:
- LiveDashboardView (transitionKey="dashboard")
- LaboratoriesView (transitionKey="laboratories")
- LabComputersView (transitionKey="computers")
- LabTerminalsView (transitionKey="terminals")
- ComputerDetailView (transitionKey="computer-detail")
- LiveAlertsView (transitionKey="alerts")
- LiveGroupedDimensionsView (transitionKey="groups")
- CsvAnalyticsPage (transitionKey="analytics")
- etc.

**Expected result**: Each route change fades in smoothly with subtle upward translation.

**Verification**:
```bash
# Manual: Navigate between pages in the app; observe smooth fade-in entrance animation
# DevTools > Performance: Record 3 seconds while changing pages; confirm animations use GPU (transform, opacity)
```

---

## Step 4 — Apply ScrollReveal to Dashboard & Overview Cards

**Objective**: Add fade-up animation to stat cards, panels, and chart containers as they scroll into view.

**Changes**:
- Wrap stat card/metric containers in `ScrollReveal` with incrementing stagger
- Wrap event panels with `ScrollReveal`
- Wrap alerts panel with `ScrollReveal`
- Ensure each has stagger={0}, {1}, {2}, etc. for cascading reveals

**Files to modify**:
- `src/components/live/LiveDashboardView.jsx` — Wrap .stat-card (or grid container) and panels
- `src/csv_analytics/CsvAnalyticsCharts.jsx` — Wrap chart containers with ScrollReveal, stagger per chart
- `src/csv_analytics/CsvAlertsExplorer.jsx` — Wrap table rows or row containers with ScrollReveal

**Example pattern** (for LiveDashboardView):
```jsx
import ScrollReveal from './ScrollReveal';

// Existing code renders stat cards in a grid
// Change to:
{stats.map((stat, idx) => (
  <ScrollReveal key={stat.id} stagger={idx % 3}>
    <StatCard data={stat} />
  </ScrollReveal>
))}
```

**Expected result**:
- Dashboard cards fade-up with smooth cascading stagger (45ms intervals) as page scrolls
- Charts and explorers in CSV page reveal with staggered animation
- No animations replay when scrolling back/forth (unobserve after first trigger)

**Verification**:
```bash
cd "c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend"
npm run build
# Manual:
# 1. Navigate to dashboard; scroll down slowly
#    — Observe cards fade-up in sequence as they enter viewport
# 2. Scroll up then down again over same cards
#    — Confirm animations do NOT replay; cards remain visible
# 3. DevTools > Rendering > Framerate monitor
#    — Confirm 60 FPS during scroll (no jank)
```

---

## Step 5 — Apply ScrollReveal to Laboratories & Lab Computers Views

**Objective**: Add scroll-triggered reveals to lab cards, computer rows, and terminals lists.

**Files to modify**:
- `src/components/live/LaboratoriesView.jsx` — Wrap lab card containers with ScrollReveal
- `src/components/live/LabComputersView.jsx` — Wrap computer rows in table or list with ScrollReveal
- `src/components/live/LabTerminalsView.jsx` — Wrap terminal containers with ScrollReveal

**Pattern**: Each list item or row wraps with unique `stagger={index}`:
```jsx
<ScrollReveal stagger={idx} key={computer.id}>
  <ComputerRow data={computer} />
</ScrollReveal>
```

**Expected result**:
- Lab cards fade-up smoothly as viewport reaches each card
- Computer rows and terminals animate with staggered entry
- No horizontal overflow from animations

**Verification**:
```bash
npm run build
# Manual:
# 1. Navigate to Laboratories; scroll down
#    — Confirm cards appear with fade-up animation
# 2. Navigate to Lab Computers; observe row animations
# 3. Open DevTools > Elements > Inspect .ios-reveal class
#    — Confirm .is-visible class toggles when content enters viewport
```

---

## Step 6 — Apply ScrollReveal to Live Alerts View

**Objective**: Add scroll-triggered reveals to alert table rows and details.

**Files to modify**:
- `src/components/live/LiveAlertsView.jsx` — Wrap alert rows or row containers with ScrollReveal

**Expected result**:
- Alert table rows fade-up in sequence as user scrolls through alerts
- Initial load shows staggered reveals for first visible batch

**Verification**:
```bash
npm run build
# Manual: Navigate to Alerts; scroll down
#   — Confirm alert rows fade-up in sequence with smooth stagger
```

---

## Step 7 — Apply ScrollReveal to CSV Analytics Explorers

**Objective**: Add scroll reveals to CSV analytics charts, alert explorer, and groups explorer.

**Files to modify**:
- `src/csv_analytics/CsvAnalyticsCharts.jsx` — Wrap chart containers with ScrollReveal stagger
- `src/csv_analytics/CsvAlertsExplorer.jsx` — Wrap table rows or row containers with ScrollReveal
- `src/csv_analytics/CsvGroupsExplorer.jsx` — Wrap group cards with ScrollReveal stagger

**Pattern**: Stagger per visible item:
```jsx
{charts.map((chart, idx) => (
  <ScrollReveal key={chart.id} stagger={idx}>
    <ChartContainer data={chart} />
  </ScrollReveal>
))}
```

**Expected result**:
- CSV page charts appear with cascading fade-up animations
- Alert and group explorers show smooth staggered reveals
- Performance remains smooth with virtualized/paginated data

**Verification**:
```bash
npm run build
# Manual:
# 1. Navigate to Analytics page
# 2. Scroll down to view charts and explorers
#    — Confirm smooth cascading animations
# 3. DevTools > Performance > Record during scroll
#    — Confirm 60 FPS; no layout thrashing
```

---

## Step 8 — Enhance Modal Entrance Animations

**Objective**: Ensure all modals use the `iosModalEntrance` + `iosBackdropBlur` keyframes with correct CSS class names.

**Files to verify & update if needed**:
- `src/components/live/AddLabModal.jsx` — Confirm uses `.modal-dialog` and `.modal-backdrop`
- `src/components/live/AssignLabModal.jsx`
- `src/components/live/LiveAlertModal.jsx`
- `src/components/live/LiveGroupDetailsModal.jsx`
- `src/csv_analytics/CsvAlertDetailsModal.jsx`
- `src/csv_analytics/CsvExportModal.jsx`
- `src/csv_analytics/CsvGroupDetailsModal.jsx`

**Expected CSS classes**:
```jsx
<div className="modal-backdrop">
  <div className="modal-dialog">
    <button className="modal-close-btn">×</button>
    {/* modal content */}
  </div>
</div>
```

**Expected result**:
- All modals appear with smooth scale-in + fade + subtle Y-translate entrance
- Backdrop fades in with blur effect
- Close button rotates smoothly on hover (90deg scale 1.1) and active state (90deg scale 0.9)

**Verification**:
```bash
npm run build
# Manual:
# 1. Click "Add Lab" button; observe modal entrance animation
# 2. Hover close button; confirm rotate + scale effect
# 3. Close modal; confirm fade-out with backdrop unblur
# 4. DevTools > Elements > Inspect modal-dialog
#    — Confirm iosModalEntrance animation is applied
```

---

## Step 9 — Enhance Dropdown & Custom Select Animations

**Objective**: Verify CustomSelect and ExportAnalysisDropdown use `iosDropdownEntrance` with correct CSS classes.

**Files to verify**:
- `src/components/CustomSelect.jsx` — Confirm `.custom-select-menu` class on dropdown container
- `src/components/CustomSelect.css` — Verify animations are applied
- `src/components/ExportAnalysisDropdown.jsx` — Confirm `.export-dropdown-menu` class
- All component CSS files where selectors are used

**Expected CSS classes**:
```jsx
{isOpen && (
  <div className="custom-select-menu">
    {/* options */}
  </div>
)}
```

**Expected result**:
- Dropdowns appear with smooth scale-in + upward Y-translate entrance
- Options highlight with smooth color transition + subtle X-translate on hover
- Dropdown entrance uses `iosDropdownEntrance` keyframe (340ms spring-soft easing)

**Verification**:
```bash
npm run build
# Manual:
# 1. Click dropdown to open; observe entrance animation
# 2. Hover over options; confirm translateX(3px) + color transition
# 3. DevTools > Elements > Inspect .custom-select-menu
#    — Confirm iosDropdownEntrance animation applied
```

---

## Step 10 — Enhance Form Focus & Input Animations

**Objective**: Ensure all form inputs have smooth focus animations with glow and Y-translate.

**Files to verify**:
- `src/App.css` — Confirm input[type="text"]:focus has border-color + box-shadow + translateY(-1px)
- `src/components/CustomSelect.css` — Custom select button focus state
- All form-related CSS files

**Expected result**:
- Input focus: Smooth border-color + box-shadow glow with accent color, translateY(-1px) for tactile rise
- Duration: `--ios-duration-fast` (180ms)
- Easing: `--ios-ease`

**Verification**:
```bash
npm run build
# Manual:
# 1. Click on text input field; observe smooth focus glow
# 2. Tab through form fields; confirm focus ring is visible
# 3. DevTools > Elements > Inspect input:focus-visible
#    — Confirm border-color and box-shadow animate smoothly
```

---

## Step 11 — Verify Table & List Row Hover Animations

**Objective**: Ensure event rows, alert rows, and data table rows animate on hover with translateX + background color.

**Files to verify**:
- `src/App.css` — Confirm `.event-row:hover`, `.alert-row:hover` apply `transform: translateX(4px)`
- Any data table CSS files where row hover is defined

**Expected result**:
- Rows slide right 4px on hover with smooth background color transition
- Duration: `--ios-duration-fast` (180ms)
- Background change: to `var(--bg-tertiary)`

**Verification**:
```bash
npm run build
# Manual:
# 1. Navigate to events or alerts view
# 2. Hover over table row; confirm smooth slide-right + background change
# 3. DevTools > Elements > Inspect row:hover
#    — Confirm transform and background-color transitions applied
```

---

## Step 12 — Verify Status Badge & Pulse Animations

**Objective**: Confirm status badges, live indicators, and pulse dots animate with `iosPulseSubtle` keyframe.

**Files to verify**:
- `src/App.css` — Confirm `.status-badge.online .dot` and `.live-pulse-dot` apply `iosPulseSubtle` animation
- Any component rendering live status indicators

**Expected result**:
- Live status dots pulse smoothly (scale 1 → 1.08 → 1, opacity shift)
- Infinite animation with 2.2s duration
- No jarring or distracting motion

**Verification**:
```bash
npm run build
# Manual:
# 1. Look for online status badge or live indicator
# 2. Observe gentle pulse animation (should feel subtle, not distracting)
# 3. DevTools > Animations panel > Inspect iosPulseSubtle
#    — Confirm animation runs infinitely
```

---

## Step 13 — Verify Button & Control Tap Feedback

**Objective**: Ensure all buttons and interactive controls have unified tap feedback (scale 0.972) with smooth transitions.

**Files to verify**:
- `src/App.css` — Confirm `button:active`, `.nav-item:active`, `.stat-card:active` apply `transform: scale(0.972)`
- All button-related CSS

**Expected result**:
- All buttons scale to 0.972 on active state with smooth `--ios-duration-fast` transition
- Hover states use appropriate easing (ios-ease or ios-spring)
- Active states feel responsive and tactile

**Verification**:
```bash
npm run build
# Manual:
# 1. Click any button; observe scale press effect
# 2. Hover over navigation items; confirm smooth color + transform transition
# 3. DevTools > Elements > Inspect button:active
#    — Confirm scale(0.972) applied
```

---

## Step 14 — Apply Reduced Motion Conditionally in Critical Components

**Objective**: Use `useReducedMotion` hook in components where conditional animation is beneficial.

**Files to update** (priority: high-motion components):
- `src/components/live/LiveDashboardView.jsx` — Conditionally apply ScrollReveal delays
- `src/components/live/LiveAlertsView.jsx` — Reduce stagger on low-motion preference
- `src/csv_analytics/CsvAnalyticsCharts.jsx` — Reduce animation complexity

**Pattern**:
```jsx
import { useReducedMotion } from '../utils/useReducedMotion';

export default function MyView() {
  const prefersReducedMotion = useReducedMotion();
  
  return (
    <div>
      {items.map((item, idx) => (
        <ScrollReveal 
          key={item.id} 
          stagger={prefersReducedMotion ? 0 : idx}
        >
          <Card data={item} />
        </ScrollReveal>
      ))}
    </div>
  );
}
```

**Expected result**:
- Users with reduced motion preference see instant reveals (no stagger delay)
- Normal users see cascading staggered animations
- Accessibility requirement met per WCAG guidelines

**Verification**:
```bash
npm run build
# Manual:
# 1. DevTools > Rendering > Emulate CSS media feature prefers-reduced-motion: reduce
# 2. Reload page; navigate to dashboard
#    — Confirm cards appear instantly (no stagger delay)
# 3. Remove emulation; reload
#    — Confirm staggered cascading animations return
```

---

## Step 15 — Full Build & Accessibility Testing

**Objective**: Run full build, linter, and manual accessibility verification.

**Commands**:
```bash
cd "c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend"

# Build the project
npm run build
# Expected: ✓ Build succeeds; no errors

# Run linter
npm run lint
# Expected: ✓ All files pass linting

# Manual Testing Checklist:
# [ ] Navigate between pages; observe smooth transitions
# [ ] Scroll on each view; confirm ScrollReveal fires once, doesn't replay
# [ ] Open modals; confirm entrance animations
# [ ] Hover buttons, rows, cards; confirm smooth hover feedback
# [ ] Click buttons; confirm 0.972 scale press effect
# [ ] Open DevTools > Performance > Record 5 seconds of scrolling
#     Confirm 60 FPS (green bar), no dropped frames
# [ ] DevTools > Rendering > Paint flashing; scroll and confirm minimal repaints
# [ ] Enable "Reduce motion" in DevTools; reload and test
#     Confirm animations are instant (0.01ms)
# [ ] Test on mobile viewport (DevTools > Device toolbar, iPhone 12)
#     Confirm animations still smooth, no horizontal overflow
# [ ] Test keyboard navigation (Tab through all interactive elements)
#     Confirm focus rings are visible and smooth
# [ ] Test in Safari, Firefox, Chrome (if possible)
#     Confirm animations render smoothly on all browsers
```

**Files verified in build**:
- `src/styles/ios-motion.css` — All tokens, keyframes, and classes
- `src/index.css` — All fallback values, design tokens
- `src/App.css` — All animations and transitions
- `src/components/PageTransition.jsx` — Page entrance animations working
- `src/components/ScrollReveal.jsx` — Viewport-triggered reveals working
- `src/utils/useReducedMotion.js` — Hook detects preference and updates
- All component files — ScrollReveal wrapping applied, animations integrated

**Expected result**:
- Build succeeds with no errors or warnings
- Linter passes all checks
- Manual testing confirms smooth 60 FPS animations across all views
- Accessibility testing confirms `prefers-reduced-motion` works correctly
- Mobile viewport shows no overflow, smooth touch feedback

**Verification**:
```bash
npm run build && npm run lint
# Expected output:
# ✓ vite v8.3.0 building for production...
# ✓ N modules transformed
# ✓ dist/index.html 0.XX kB
# ✓ dist/... built in Xs
# ✓ oxlint completed successfully
```

---

## Summary

**Total Steps**: 15 (8 implementation + 7 verification)

**Critical Path**:
1. Step 0 — Add `--ios-duration-base` token
2. Step 1 — Create `useReducedMotion` hook
3. Step 2 — Verify CSS class names in components
4. Steps 3-12 — Apply ScrollReveal and verify animations per component
5. Step 14 — Integrate `useReducedMotion` into key components
6. Step 15 — Full build and testing

**Risk Mitigation**:
- All animations use GPU-composited properties (transform, opacity) only
- Stagger delays limited to 45ms increments, max 12 items per list
- Reduced motion media query ensures accessibility compliance
- No breaking changes to existing routing, state, or API calls
- All verification steps use the project's actual build tools

**Expected Outcome**:
- TAVIX GUARD dashboard feels buttery smooth with iOS-inspired motion
- All page transitions, scrolls, modals, buttons, and interactive elements animate smoothly
- 60 FPS performance on desktop and mobile
- Full accessibility compliance with reduced motion support
- No user functionality affected; only visual polish and motion quality improved

