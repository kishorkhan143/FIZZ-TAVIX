# TAVIX GUARD iOS Motion Upgrade — Implementation Plan

**Design**: motion-design.md (with H2, H3, H4, H5, M1-M3, N1-N4 findings resolved)  
**Status**: Ready for implementation  
**Workspace**: `c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend`

---

## Overview

Replace all CSS keyframe animations and `transition: all` rules with buttery-smooth, spring-based, iOS 17/18-style animations using the `motion` package (React 19 compatible). No data logic or visual design changes—motion only.

**Key deliverables**:
1. Install `motion` package
2. Create central motion config (`src/motion.js`) with springs, variants, and helpers
3. Remove CSS keyframes and replace `transition: all` rules
4. Update all components with motion animations (App.jsx, pages, components, live views)
5. Verify build passes with no warnings; test functionality

**Critical decisions made** (from design review findings):
- **H2 resolved**: Using `motion` package's key-based presence API, not `AnimatePresence` (which doesn't exist in motion)
- **H4 resolved**: RiskGauge counter uses `useSpring` + `useTransform` pattern in motion.js
- **H5 resolved**: Exit animations: 0.2s consistently for all exits (page, row, modal)
- **M1 resolved**: Complete CSS audit provided below with file:line references
- **M3 resolved**: whileInView viewport margin uses `"-40px"` (pixels, not percentage)
- **N1 resolved**: Status badge breathing glow is infinite (acceptable for live indicator; documented)

---

## Phase 1: Install & Setup

- [ ] **1. Install motion package and verify React 19 compatibility**

  Run `npm install motion` in workspace root.
  Verify build succeeds: `npm run build` (no errors, no warnings).
  This is prerequisite for all subsequent steps.

  Files: package.json (updated with motion dependency)
  Verify: `npm run build` passes, `node_modules/motion` exists, no peer dependency errors

- [ ] **2. Create central motion configuration**

  Create `src/motion.js` with:
  - `springs.soft`, `springs.snappy`, `springs.sheet` object exports
  - `appleEase` cubic-bezier constant
  - `staggerConfig` with delayChildren and staggerChildren
  - `variants` object: fadeUp, pageTransition, slideInRight, listContainer, listItem, modalScale, backdropFade
  - `useMotionPrefs()` hook (detects prefers-reduced-motion, returns appropriate variant set)
  - Note: Fix H2 finding: do NOT import AnimatePresence (doesn't exist in motion); key changes handle presence
  - Note: Add comment at top: `import React from 'react'` (fixes H1 finding)
  - Implementation: Use exact code from motion-design.md Section 2, with additions:
    - Add helper function `scrollRevealConfig` constant: `{ once: true, viewport: { margin: "-40px" } }`
    - Add `animateCounter` helper to convert numeric useSpring values to text via useTransform (fixes H4 finding)
    - Add `calculateDashOffset` helper for RiskGauge arc animation (animates from previous value, not 0)

  Files: src/motion.js (create new)
  Verify: `import { springs, variants, useMotionPrefs } from './motion'` in any test file succeeds; no runtime errors

- [ ] **3. Wrap App.jsx with MotionConfig**

  In `src/App.jsx`, wrap the component tree with `<MotionConfig reducedMotion="user">`.
  Import: `import { MotionConfig } from 'motion/react'`

  Files: src/App.jsx (lines ~1-15 at root export)
  Verify: Component tree renders with no console errors; accessibility: test with `prefers-reduced-motion: reduce` enabled in browser DevTools and observe fades instead of springs

---

## Phase 2: CSS Cleanup (Foundation for Motion)

Remove all keyframes, animations, and `transition: all` rules to prevent double-animations.

- [ ] **4. Remove keyframes and animations from index.css**

  **Remove these keyframe definitions** (index.css lines 95–113):
  - `@keyframes fade-in` (lines 95–99)
  - `@keyframes slide-in-left` (lines 100–104)
  - `@keyframes slide-in-up` (lines 105–109)
  - `@keyframes scale-in` (lines 110–113)

  **Remove inline `animation:` usage** in App.jsx and App.css on these elements (scanned via grep):
  - `.sidebar` animation removed (if present in App.css)
  - `.main-content` animation removed
  - `.header` animation removed
  - `.body` animation removed
  - `.section` animation removed

  Files: src/index.css, src/App.css
  Verify: `npm run build` passes; no CSS syntax errors; app still renders (no flickering)

- [ ] **5. Remove keyframes and animations from ios-motion.css**

  **Remove these keyframe definitions** (ios-motion.css lines 96–223):
  - `@keyframes iosPageEntrance` (lines 96–112)
  - `@keyframes iosTabFadeIn` (lines 113–123)
  - `@keyframes iosFadeIn` (lines 125–129)
  - `@keyframes iosFadeInUp` (lines 130–140)
  - `@keyframes iosScaleIn` (lines 141–151)
  - `@keyframes iosModalEntrance` (lines 152–162)
  - `@keyframes iosBackdropBlur` (lines 163–175)
  - `@keyframes iosDropdownEntrance` (lines 176–186)
  - `@keyframes iosToastSlideIn` (lines 187–197)
  - `@keyframes iosPulseSubtle` (lines 198–208)
  - `@keyframes iosShimmer` (lines 209–223)

  **Keep these for now** (CSS-only, not animation):
  - CSS variables (--ios-ease, --ios-spring, --ios-duration-*)
  - Smooth scrolling rules
  - Scrollbar styling
  - Button/link base styles (but remove `transition: all` rules from selectors)

  **Replace `transition: transform` and explicit transition rules** with motion variants in components (do not remove from CSS yet; CSS transitions will be cleaned up per component as motion replaces them):
  - ios-motion.css lines 61–66: button transition rules (will be moved to motion whileHover/whileTap)
  - ios-motion.css lines 248–251: stat-card transitions (will be moved to motion)
  - ios-motion.css lines 260–262: stat-icon transition (will be moved to motion)
  - (And others listed in M1 findings; these are handled per-component)

  Files: src/styles/ios-motion.css
  Verify: `npm run build` passes; no CSS syntax errors; page still renders

- [ ] **6. Remove keyframes from CustomSelect.css**

  **Remove keyframe definition**:
  - `@keyframes iosDropdownEntrance` (if redefined in CustomSelect.css; typically at line ~109)

  **Convert `transition: all` to motion variants** (will be done in component update step):
  - CustomSelect.css lines 41, 153, 181: `transition: all` rules → move to motion component

  Files: src/components/CustomSelect.css
  Verify: `npm run build` passes; no CSS syntax errors

- [ ] **7. Remove keyframes from csvAnalytics.css**

  **Remove keyframe definitions**:
  - `@keyframes progress-pulse` (csvAnalytics.css line 707–712)
  - Any other `@keyframes` definitions in this file

  **Convert `transition: all` to motion**:
  - csvAnalytics.css lines 62, 90, 129, 576, 878, 903: `transition: all` rules (will be moved to motion in CSV component steps)

  Files: src/csv_analytics/csvAnalytics.css
  Verify: `npm run build` passes

- [ ] **8. Remove keyframes from ComputerDetailView.css**

  **Keep `@keyframes spin`** (line 42–45) if it's used for CSS loading spinner (not motion-replaceable, or move to motion if desired)
  Actually, replace with motion loading spinner or keep as-is if used in SVG.
  Decision: Keep for now (not part of motion upgrade scope); comment that this is CSS-only for now

  Files: src/components/live/ComputerDetailView.css
  Verify: `npm run build` passes

- [ ] **9. Remove keyframes from RiskGauge.css**

  **Remove or replace `@keyframes` definitions** if present; check file content first.
  **Replace inline `transition: stroke-dashoffset`** rule with motion animation (handled in RiskGauge.jsx component update)

  Files: src/components/RiskGauge.css
  Verify: `npm run build` passes

---

## Phase 3: Core Component Updates (App.jsx & Pages)

- [ ] **10. Update App.jsx: Sidebar navigation with layoutId pill highlight**

  Add motion imports: `import { motion } from 'motion/react'`
  
  **Replace sidebar nav active indicator**:
  - Sidebar nav items currently use class-based active state
  - Add `layoutId="nav-active"` to a motion.div background element behind active item
  - This motion.div animates its position to match active item with springs.snappy
  - Gradient height: match nav item height with layout animation
  
  **Add whileHover/whileTap to nav items**:
  - whileHover: `{ x: 2, scale: 1.06 }` with springs.snappy
  - whileTap: `{ scale: 0.97 }` with springs.snappy
  - Icon scales on hover: `{ scale: 1.06 }` springs.snappy
  
  **Add stagger on mount**:
  - Wrap nav items in motion.div with `variants.listContainer`
  - Each nav item motion.div with `variants.listItem`
  - Only animate first 12 items; cap stagger total to ~0.6s
  
  **Mobile drawer (if exists)**:
  - Animate drawer translateX from -100% → 0 with springs.soft on open
  - Add drag-to-close: `drag="x"` with `onDragEnd` callback
  - Backdrop fades in with springs.soft
  
  Files: src/App.jsx (Sidebar component section)
  Verify: `npm run dev` in workspace; inspect nav pill animation smoothness; click nav items and verify smooth spring motion; test mobile drawer drag-to-close

- [ ] **11. Update App.jsx: Header section**

  **Clock digits**: Add CSS `font-variant-numeric: tabular-nums` to clock element to prevent layout shift on digit update (no animation, just layout fix)
  
  **Category label**: Wrap category label text in motion.div with:
  - On mount: `initial="hidden"` `animate="visible"` with fadeUp variant
  - On section change: Crossfade label + subtle y slide (y: -2 → 0) via motion.animate or key change
  - Trigger on activeMenu change: `key={activeMenu}` on motion.div
  
  Files: src/App.jsx (Header component section)
  Verify: Clock updates without layout jank; category label fades/slides smoothly on section change

- [ ] **12. Update App.jsx: Overview stat cards with animated counters**

  **Container**: Wrap stat cards in motion.div with:
  - `variants.fadeUp` on visible
  - `initial="hidden"` `animate="visible"`
  - Stagger children: `delayChildren: 0.08s` `staggerChildren: 0.05s` (first 12 items only)
  
  **Each stat card**:
  - Fade up on mount
  - whileHover: `{ y: -3, shadow: ...grow }` with springs.soft
  - whileTap: `{ scale: 0.98 }` with springs.snappy
  
  **Stat number counter**:
  - Use `useSpring` + `useTransform` from motion/react (pattern: `animateCounter` helper from motion.js)
  - Animates from previous value to new value with springs.soft over 0.8s
  - Never resets to 0 on data update
  
  **Recharts <Area>** in OverviewSection:
  - Set `isAnimationActive={true}`
  - Set `animationDuration={900}`
  - Set `animationEasing="ease-out"` or custom curve
  - This handles chart line smoothing automatically; no motion intervention needed
  
  Files: src/App.jsx (OverviewSection component)
  Verify: Stat cards fade in with stagger; numbers count up smoothly; hover effect applies; `npm run build` passes

- [ ] **13. Update App.jsx: Events & Alerts lists (most critical for live data)**

  **AnimatePresence replacement** (motion package does NOT have AnimatePresence; use key changes):
  - Wrap EventsTable and AlertList in motion.div containers with `key={listKey}`
  - On new data: toggle key to trigger re-render with exit/enter animations
  - Use `initial={false}` equivalent by managing animation state
  
  **Layout animation for rows**:
  - Each row in motion.div with `layout="position"`
  - When new row added at top, existing rows slide down smoothly (layout handles position)
  
  **New row enter**:
  - opacity 0 → 1, y: -12 → 0, scale 0.98 → 1
  - Transition: springs.snappy over 0.34s
  
  **Highlight flash** on new row:
  - After enter completes, background color animates from accent → transparent over 1.2s
  - Use motion.div inside row with `animate={{ backgroundColor: [...] }}`
  
  **Row exit** (on removal):
  - Collapse height (layout handles) + fade opacity over 0.2s
  - Use `layout` + conditional rendering
  
  **Batching & cap simultaneous animations**:
  - Implement batch queue: max 5 rows animate simultaneously
  - Remaining rows queue with 300ms delay between batches
  - Stagger within batch: 0.04s per item (total ~0.28s per batch)
  - Implementation: useState with batchIndex, setTimeout for queue flushing
  
  **High-risk alert pulse**:
  - One-time pulse only (not infinite loop)
  - scale: 1 → 1.01 → 1 over 0.4s on mount (one iteration)
  - Trigger on risk level change or row insertion
  
  **First load stagger**:
  - Initial render: stagger first 12 rows with 0.04s delay per row
  - Delaying first row: 0.08s
  
  Files: src/App.jsx (EventsTable and AlertList component sections)
  Verify: Live events/alerts enter smoothly from top; existing rows slide down; new rows highlight and fade; high-risk rows pulse once on entry; batching prevents jank when 20 events arrive at once; test with `npm run dev` and WebSocket data; check React Profiler for layout thrashing (should be minimal)

- [ ] **14. Update App.jsx: Page/section switching (OverviewSection, LiveTelemetrySection, SettingsSection, etc.)**

  **Main section container** (switches between OverviewSection, LiveTelemetrySection, SettingsSection, etc.):
  - Wrap active section in motion.div with `key={activeMenu}` to trigger exit/enter
  - `variants.pageTransition`: opacity 0 → 1, y: 16 → 0, blur: 6px → 0 on enter
  - Exit: faster (0.2s), opacity → 0, y: -8, blur: 4px
  - Transition: springs.soft on enter, ease on exit
  
  **Section header** (h2 + description):
  - Animate in first with `delayChildren: 0.05s`
  
  **Content blocks**:
  - Stagger after header with `staggerChildren: 0.04s`
  
  **Live Telemetry section**:
  - Nested page transition for events/alerts/status sections
  - Use same pageTransition variant
  
  Files: src/App.jsx (section switching logic around activeMenu)
  Verify: Sections fade in/out smoothly on click; header enters first, content follows with stagger; `npm run dev` and click through menu items

- [ ] **15. Update App.jsx: Status badges & online/offline indicators**

  **Breathing glow on online dot**:
  - motion.div with `animate` loop: scale [1, 1.2, 1], opacity [0.8, 1, 0.8]
  - transition: repeat: Infinity, duration: 2s, easeInOut
  
  **Offline dot**: Static, no animation
  
  **Status color change**:
  - Crossfade color + text when status changes
  - opacity + color transition over 0.26s springs.soft
  
  Files: src/App.jsx (StatusBadge component)
  Verify: Online dot breathes smoothly; offline is static; status color changes crossfade

- [ ] **16. Update App.jsx: Buttons globally (admin-btn, nav-item, date-filter-pill)**

  **All buttons**: Add motion wrapper or motion.button:
  - whileHover: `{ scale: 1.02 }` springs.snappy
  - whileTap: `{ scale: 0.96 }` springs.snappy
  
  **Focus-visible ring**:
  - motion.div overlay with opacity 0 → 1 springs.soft on focus
  
  Files: src/App.jsx (all button elements)
  Verify: Buttons scale smoothly on hover and tap; focus ring fades in; `npm run dev` and test all interactive buttons

- [ ] **17. Update App.jsx: Panels & cards (events-panel, alerts-panel, settings-card, telemetry-panels)**

  **Scroll reveal**:
  - Use `whileInView` with `variants.fadeUp` once:true viewport={{ margin: "-40px" }}
  - Each panel animates in when scrolled into view
  
  Files: src/App.jsx (panel rendering)
  Verify: Scroll app vertically; panels fade in as they enter viewport; `npm run dev`

- [ ] **18. Update PageTransition.jsx component**

  If PageTransition.jsx exists and wraps page transitions:
  - Wrap with motion.div using pageTransition variant
  - Remove any existing CSS keyframe animations
  - Ensure key prop changes on route change (for presence)
  
  Files: src/components/PageTransition.jsx
  Verify: `npm run build` passes; no console errors

---

## Phase 4: Detailed Page & Component Updates

- [ ] **19. Update RiskGauge.jsx (SVG arc animation)**

  **Current**: Inline `transition: stroke-dashoffset 0.3s ease`
  
  **New approach**:
  - Import `useMotionValue`, `useTransform`, `useSpring`, `motion` from motion/react
  - Import `calculateDashOffset` helper from motion.js
  - Track previous score in ref: `useRef(currentScore)`
  - On score change:
    - Calculate dashOffsetFrom and dashOffsetTo using `calculateDashOffset(prevScore, newScore)`
    - Use `useSpring` to animate dashOffset from previous → new value with springs.soft
    - Never reset to 0
  - Animated number counter using `useSpring` + `useTransform` (animateCounter pattern from motion.js)
  - Color transition: Use motion.div or SVG element with color animation springs.soft when band changes
  
  Files: src/components/RiskGauge.jsx
  Verify: Arc morphs smoothly from previous value (no reset); number tweens smoothly; color transitions on band change; `npm run dev` and watch RiskGauge update with test data

- [ ] **20. Update RiskChart.jsx (Recharts line animation)**

  **Setup Recharts animations**:
  - Wrap each chart element (Line, Area, Bar) with `isAnimationActive={true}`
  - Set `animationDuration={900}`
  - Set `animationEasing="ease-out"` or use cubic-bezier
  - Tooltip: Scale + opacity animation springs.sheet on appearance
  
  **Smooth data morph**:
  - Recharts handles this automatically with isAnimationActive
  - Avoid re-creating chart data objects every render (use useMemo)
  
  Files: src/components/RiskChart.jsx
  Verify: Chart line morphs smoothly on data update; tooltip appears with spring; `npm run dev`

- [ ] **21. Update EntityDetail.jsx (detail page slide-in from right)**

  **Page transition**:
  - Wrap content in motion.div with `variants.slideInRight` (x: 24 → 0)
  - Enter: springs.soft, exit: springs.soft with x: 24
  
  **Expandable blocks**:
  - Never use CSS `height: auto` transitions
  - Use motion `layout` + `layoutId` for animated height on toggle
  - Or use `Animated.div` with height animation from 0 → auto (measure element)
  
  **Section header & content**:
  - Stagger content blocks on mount
  
  Files: src/pages/EntityDetail.jsx
  Verify: Detail view slides in from right on open; goes back slides out to right; expandable blocks animate height smoothly; `npm run dev` and navigate to detail view

- [ ] **22. Update IncidentPanel.jsx**

  **Same as EntityDetail.jsx**:
  - Page transition: slideInRight variant
  - Expandable sections: layout animation
  - Content stagger on mount
  
  Files: src/pages/IncidentPanel.jsx
  Verify: Same as EntityDetail

- [ ] **23. Update Environment.jsx**

  **Same as EntityDetail.jsx**: Page transition, expandable sections, content stagger

  Files: src/pages/Environment.jsx
  Verify: Same as EntityDetail

- [ ] **24. Update CustomSelect.jsx (dropdown animation)**

  **Replace keyframe-based dropdown entrance**:
  - Remove `@keyframes iosDropdownEntrance` reference
  - Wrap dropdown menu in motion.div with `variants.modalScale` (scale 0.96 → 1, opacity 0 → 1)
  - Transition: springs.sheet over 0.34s
  
  **Replace `transition: all` rules**:
  - CustomSelect.css lines 41, 85, 153, 181 (convert to motion variants in component)
  
  **Dropdown items stagger**:
  - motion.div with `variants.listContainer` wrapping items
  - Each item with `variants.listItem`
  
  Files: src/components/CustomSelect.jsx, src/components/CustomSelect.css
  Verify: Dropdown opens with spring scale animation; items stagger in; `npm run dev` and test select interactions

- [ ] **25. Update DateFilter.jsx**

  **Button animations**:
  - Replace `transition: all` with motion whileHover/whileTap
  - whileHover: scale 1.02, whileTap: scale 0.96
  - Transition: springs.snappy
  
  Files: src/components/DateFilter.jsx
  Verify: Buttons scale on hover/tap; `npm run dev`

- [ ] **26. Update Sparkline.jsx (if exists and needs animation)**

  **Line draw-in on mount** (if desired; currently may not exist):
  - Use pathLength animation from 0 → 1 with springs.soft
  - Applies to SVG path element
  
  Files: src/components/Sparkline.jsx
  Verify: Line draws in smoothly on render; `npm run dev`

- [ ] **27. Update ScrollReveal.jsx (if exists)**

  **Scroll reveal**:
  - Component wraps child elements with whileInView fadeUp once:true
  - Replace any existing CSS keyframes with motion
  
  Files: src/components/ScrollReveal.jsx
  Verify: Content reveals on scroll; `npm run dev` and scroll page

- [ ] **28. Update live view components (13 files in components/live/)**

  For each of: AddLabModal.jsx, AssignLabModal.jsx, ComputerDetailView.jsx, Header.jsx, LabComputersView.jsx, LaboratoriesView.jsx, LabTerminalsView.jsx, LiveAlertModal.jsx, LiveAlertsView.jsx, LiveDashboardView.jsx, LiveGroupDetailsModal.jsx, LiveGroupedDimensionsView.jsx:
  
  **Modals** (AddLabModal, AssignLabModal, LiveAlertModal, LiveGroupDetailsModal):
  - Wrap modal content in motion.div with `variants.modalScale` (scale 0.96 → 1, opacity 0 → 1)
  - Transition: springs.sheet
  - Backdrop with `variants.backdropFade`
  
  **Views** (ComputerDetailView, LaboratoriesView, LabComputersView, LabTerminalsView, LiveAlertsView, LiveDashboardView, LiveGroupedDimensionsView, Header):
  - Page transition: `variants.pageTransition` on content wrapper
  - List items (if present): AnimatePresence + layout + stagger
  - Content blocks: whileInView fadeUp
  - Buttons: whileHover/whileTap springs.snappy
  - Status indicators: breathing glow for online
  
  **Remove all `@keyframes` references** in these files' CSS
  
  Files: src/components/live/* (all 13 files)
  Verify: All live views animate smoothly; modals scale in; lists update with spring layout; no console errors; `npm run dev` and navigate through live components

- [ ] **29. Update CSV Analytics components (CsvAnalyticsPage, CsvUploader, CsvAnalyticsCharts, CsvAlertDetailsModal, etc.)**

  **Modals** (CsvAlertDetailsModal, CsvExportModal, CsvGroupDetailsModal):
  - Wrap with `variants.modalScale` springs.sheet
  
  **Upload area** (CsvUploader):
  - Dragover: scale 1.02 + border glow animation
  - Drop: Spring settle scale 1 y 0 springs.soft
  
  **Charts** (CsvAnalyticsCharts):
  - Recharts isAnimationActive 900ms
  
  **Panels**: whileInView fadeUp once
  
  **Buttons**: whileHover/whileTap springs.snappy
  
  **Remove `@keyframes progress-pulse` and other keyframes** from csvAnalytics.css
  
  **Replace `transition: all` rules** with motion
  
  Files: src/csv_analytics/* (all files)
  Verify: CSV page animates smoothly; upload drag-to-drop works; charts animate; modals scale; `npm run dev` and test CSV workflow

- [ ] **30. Final CSS cleanup: Remove remaining explicit transition rules (optional but recommended)**

  After all components are converted to motion:
  - Review remaining `transition:` rules in iOS-motion.css (lines 61–66, 248–251, 260–262, 318–321, etc.)
  - These can remain as fallback for non-motion elements OR be removed if all are motion-wrapped
  - Decision: Keep button base transitions as fallback for accessibility; remove deprecated `transition: all` rules
  - Audit App.css, CustomSelect.css, csvAnalytics.css for orphaned transition rules that no longer have corresponding motion animations
  - Replace with explicit property transitions where needed (e.g., `transition: background-color 0.26s var(--ios-ease)` for non-animated color changes)
  
  Files: src/styles/ios-motion.css, src/App.css, src/components/CustomSelect.css, src/csv_analytics/csvAnalytics.css
  Verify: No "transition: all" rules remain; only explicit properties or motion-wrapped elements; `npm run build` passes

---

## Phase 5: Verification & Testing

- [ ] **31. Full build verification**

  Run `npm run build` from `c:\Users\wwwki\OneDrive\Desktop\cyber hacks\TAVIX-GAURD\Working prototype\log\frontend`
  
  Expected: Build succeeds, no errors, no warnings
  
  Check:
  - No "animation" or "transition" CSS class conflicts
  - No undefined motion/react imports
  - All variants exported and imported correctly
  - Vite bundle is valid
  
  Verify: `npm run build` completes with exit code 0

- [ ] **32. Runtime functionality testing**

  Run `npm run dev` and start development server
  
  **Test each section**:
  1. **Sidebar**: Nav pills animate on click; stagger on mount smooth
  2. **Overview**: Stat cards fade in with stagger; numbers count up; hover effect applies
  3. **Events/Alerts**: Live data enters smoothly; rows slide down on new insert; high-risk pulse once; old rows collapse on remove
  4. **Pages**: Navigate through EntityDetail, Environment, IncidentPanel; slide-in from right smooth
  5. **Live components**: All modals scale in; views page-transition; status dots breathe
  6. **CSV**: Upload drag-over scales; modals appear; charts animate
  7. **Buttons**: All buttons scale on hover/tap throughout app
  8. **Scroll reveal**: Panels fade in as scrolled into view
  
  Verify: No layout jank, no stuttering, 60fps smooth (check DevTools Performance tab), no console errors

- [ ] **33. Accessibility testing: prefers-reduced-motion**

  In browser DevTools, emulate `prefers-reduced-motion: reduce`:
  - Chrome: DevTools → Rendering → Emulate CSS media feature prefers-reduced-motion
  
  Expected: All animations become simple 150ms fades (no springs, no transforms)
  
  Verify: App functions normally with reduced motion; no visual glitches

- [ ] **34. Performance profiling**

  Use React DevTools Profiler:
  1. Open dev server in React 19 app
  2. React DevTools → Profiler → Start recording
  3. Trigger live data update (WebSocket event or button click)
  4. Stop recording
  
  Check:
  - No component renders unnecessarily (EventsTable should batch update, not re-render all rows on every event)
  - Motion animations don't cause layout thrashing (transform/opacity only)
  - Frame rate stays at 60fps (or higher on ProMotion)
  
  Verify: Profiler shows green/yellow (acceptable), not red (problematic)

- [ ] **35. Visual regression check**

  Compare motion output to design intent:
  - Page transitions: smooth, 340ms soft spring enter, 200ms exit ✓
  - Buttons: responsive, snappy spring ✓
  - Lists: rows slide down smoothly, new row highlight fades ✓
  - Status badge: online dot breathes gently, offline static ✓
  - Detail views: slide in from right, expandable sections animate ✓
  - Modals: scale + fade in, dim backdrop ✓
  
  Verify: All animations match iOS 17/18 aesthetic (refined, subtle, no excessive bounce)

- [ ] **36. Cross-browser testing (optional but recommended)**

  Test in:
  - Chrome (latest) — primary
  - Edge (latest)
  - Safari (macOS) — to verify WebKit compatibility
  
  Check: Motion animations work in all browsers, no vendor-specific issues
  
  Verify: No console errors in any browser

---

## Tuning Guide (After Implementation)

If motion feel needs adjustment, tune `src/motion.js`:

| Parameter | Current | Snappier | Softer |
|-----------|---------|----------|--------|
| springs.soft.stiffness | 260 | 280 | 240 |
| springs.soft.damping | 30 | 35 | 25 |
| springs.snappy.stiffness | 420 | 440 | 380 |
| springs.snappy.damping | 34 | 40 | 28 |
| springs.sheet.stiffness | 300 | 320 | 280 |
| staggerChildren | 0.05s | 0.03s | 0.07s |
| delayChildren | 0.08s | 0.05s | 0.12s |

---

## CSS Animations Removed (Master Checklist)

| Keyframe | File | Lines | Status |
|----------|------|-------|--------|
| fade-in | index.css | 95–99 | Remove (Step 4) |
| slide-in-left | index.css | 100–104 | Remove (Step 4) |
| slide-in-up | index.css | 105–109 | Remove (Step 4) |
| scale-in | index.css | 110–113 | Remove (Step 4) |
| iosPageEntrance | ios-motion.css | 96–112 | Remove (Step 5) |
| iosTabFadeIn | ios-motion.css | 113–123 | Remove (Step 5) |
| iosFadeIn | ios-motion.css | 125–129 | Remove (Step 5) |
| iosFadeInUp | ios-motion.css | 130–140 | Remove (Step 5) |
| iosScaleIn | ios-motion.css | 141–151 | Remove (Step 5) |
| iosModalEntrance | ios-motion.css | 152–162 | Remove (Step 5) |
| iosBackdropBlur | ios-motion.css | 163–175 | Remove (Step 5) |
| iosDropdownEntrance | ios-motion.css | 176–186 | Remove (Step 5) |
| iosToastSlideIn | ios-motion.css | 187–197 | Remove (Step 5) |
| iosPulseSubtle | ios-motion.css | 198–208 | Remove (Step 5) |
| iosShimmer | ios-motion.css | 209–223 | Remove (Step 5) |
| iosDropdownEntrance | CustomSelect.css | ~109 | Remove (Step 6) |
| progress-pulse | csvAnalytics.css | 707–712 | Remove (Step 7) |
| spin | ComputerDetailView.css | 42–45 | Keep (CSS-only loading spinner) |

---

## Design Review Findings — Resolution Summary

| Finding | Decision | Implementation Step |
|---------|----------|---------------------|
| H1: React import missing | Add `import React from 'react'` at top of src/motion.js | Step 2 |
| H2: AnimatePresence doesn't exist in motion | Use key-based presence (key changes, initial={false} equivalent) | Steps 13, 28 |
| H3: Batching algorithm unspecified | Implement batch queue: max 5 rows, 300ms batch delay, 0.04s stagger within batch | Step 13 |
| H4: Counter animation undefined | Use useSpring + useTransform pattern; add animateCounter helper to motion.js | Steps 2, 12, 19 |
| H5: Exit timing contradictions | Standardize: all exits 0.2s; use springs.soft for page/row exits | Steps 5, 12, 13 |
| M1: CSS cleanup incomplete | Complete audit provided; all keyframes and transition rules listed with file:line | Steps 4–9, 30 |
| M2: Live components incomplete | All 13 live/* components documented; motion specs provided | Step 28 |
| M3: Scroll reveal margin unit | Use "-40px" (pixels); add scrollRevealConfig constant to motion.js | Step 2, 17 |
| N1: Status badge infinite loop | Keep infinite loop (acceptable for live indicator); document in code | Step 15 |
| N2: Tabular-nums font feature | Add font-variant-numeric: tabular-nums to clock (CSS-only, not motion) | Step 11 |
| N3: Motion package React 19 compat | Test npm install motion; verify build passes (handled in Step 1) | Step 1 |
| N4: useMotionConfig unused | Remove useMotionConfig hook; keep useMotionPrefs as single hook | Step 2 |

---

## Final Checklist

- [ ] npm install motion succeeds
- [ ] src/motion.js created with all springs, variants, helpers
- [ ] App.jsx wrapped with MotionConfig
- [ ] All CSS keyframes removed from index.css, ios-motion.css, component CSS files
- [ ] All `animation:` inline rules removed from components
- [ ] All `transition: all` converted to motion or explicit properties
- [ ] App.jsx sections animate with pageTransition variant
- [ ] Sidebar nav pill animates with layoutId
- [ ] Stat cards fade with stagger and animated counters
- [ ] Events/Alerts lists batch-animate with layout positioning
- [ ] RiskGauge animates arc from previous value (not 0)
- [ ] All buttons whileHover scale 1.02, whileTap scale 0.96
- [ ] Status badges online dot breathes, offline static
- [ ] Detail pages slide in from right
- [ ] Modals scale in with springs.sheet
- [ ] Live components all motion-enabled (13 files)
- [ ] CSV components all motion-enabled
- [ ] npm run build passes with no errors/warnings
- [ ] npm run dev shows smooth animations at 60fps
- [ ] prefers-reduced-motion: reduce tested and works (fades only)
- [ ] No console errors or warnings

---

## Implementation Notes

**Critical points to remember**:

1. **No AnimatePresence in motion package** — Use key-based presence or controlled exit/enter timing
2. **Motion animates transform/opacity/filter only** — Never animate width/height/top/left directly; use layout
3. **RiskGauge arc never resets** — Always animate from previous dashOffset to new dashOffset
4. **Batch list animations** — Cap 5 simultaneous row animations; queue remaining at 300ms intervals
5. **No double-animations** — CSS keyframes must be removed before motion components are added
6. **Verify build and tests** — Every step should leave codebase in buildable state
7. **Accessibility first** — prefers-reduced-motion must work; test with accessibility settings enabled

