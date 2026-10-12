# TAVIX GUARD — Component Motion Inventory

This document lists every file that requires motion animation enhancements, grouped by category. Each entry specifies the component, its motion spec from the architecture, and implementation priority.

---

## Global Foundation

### Tokens & Motion System

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/styles/ios-motion.css` | Motion tokens & keyframes | Global system | **CRITICAL** | Already exists; verify all tokens and keyframes match architecture doc. All keyframes documented in section 2.1 |
| `src/index.css` | Color & spacing tokens | Duration & easing fallbacks | **CRITICAL** | Already exists; ensure `--transition-fast`, `--transition-base`, `--transition-slow` and iOS tokens are present |
| `src/App.css` | Layout & component animations | Foundation animations | **CRITICAL** | Already has basic animations; audit and align with iOS-motion.css token usage |

### Utility Hooks & Components

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/PageTransition.jsx` | Page route wrapper | Page transitions (section 4.1) | **CRITICAL** | Already exists; ensure `.ios-page-container` animation is applied with `transitionKey` prop |
| `src/components/ScrollReveal.jsx` | Scroll-triggered reveal | Scroll reveals (section 5.12) | **CRITICAL** | Already exists; verify IntersectionObserver threshold (0.08), stagger calculation, and `.ios-reveal.is-visible` class toggle |
| `src/utils/useReducedMotion.js` | Accessibility hook | Reduced motion detection | **HIGH** | **NEEDS CREATION**: Hook to detect `prefers-reduced-motion` media query and expose boolean. Return updated value on media query change. |

---

## Global Layout Components

### Sidebar Navigation

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `.sidebar` | Sidebar container | Slide-in-left entrance (section 5.1) | **HIGH** | Already has `animation: slide-in-left`; verify uses `--ios-duration-page` and `--ios-spring-soft` easing |
| `src/App.css` - `.nav-item` | Navigation buttons | Hover/active transitions (section 5.2) | **HIGH** | Has transitions; ensure all properties (color, background, transform) use `--ios-duration-fast` and spring easing |
| `src/App.css` - `.nav-item:hover` | Nav hover state | Transform translateX(3px) | **HIGH** | Already has 3px translate; verify easing and duration align with `--ios-duration-fast` |
| `src/App.css` - `.nav-item:active` | Nav press feedback | Scale 0.975 on active | **MEDIUM** | Add active state press feedback if not present |
| `src/App.css` - `.nav-icon` | Icon in nav items | Scale transform on hover/active | **MEDIUM** | Has scale(1.06) on hover, 1.12 when active; verify duration uses `--ios-duration-fast` with spring easing |

### Header

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `.header` | Header container | Slide-in-up entrance | **HIGH** | Has `animation: slide-in-up`; verify timing and easing tokens |
| `src/App.css` - `.date-filter-pill` | Date filter button | Hover elevation + translateY(-1px) | **MEDIUM** | Add hover state with `--ios-duration-base` and subtle shadow upgrade if missing |

### Main Content & Body

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `.main-content` | Main content wrapper | Fade-in entrance | **MEDIUM** | Has `animation: fade-in`; verify timing |
| `src/App.css` - `.body` | Page content container | Fade-in with staggered delay | **MEDIUM** | Has animation with 0.1s delay; verify uses `--ios-duration-smooth` |

---

## Pages & Main Views

### Dashboard & Home Page

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/LiveDashboardView.jsx` | Main dashboard view | Scroll-triggered reveals for charts/stats | **HIGH** | Wrap chart/stat sections with `ScrollReveal` component with stagger |
| `src/components/live/Header.jsx` | Dashboard header | Subtly fade-in with page | **MEDIUM** | Verify part of PageTransition wrapper |

### Laboratories View

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/LaboratoriesView.jsx` | Labs list page | Scroll-triggered card reveals | **HIGH** | Wrap lab cards with `ScrollReveal`; stagger=0,1,2... for each card |

### Lab Computers View

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/LabComputersView.jsx` | Computer list page | Scroll-triggered table reveals, row hover animations | **HIGH** | Wrap initial layout with PageTransition; apply row hover animations (translateX, background); add SearchInput focus animation |

### Computer Detail View

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/ComputerDetailView.jsx` | Detail view page | Page entrance + section scrolls | **HIGH** | Wrap with PageTransition; apply ScrollReveal to info sections |
| `src/components/live/ComputerDetailView.css` | Detail view styles | Ensure animations defined | **MEDIUM** | Review existing styles; add any missing animations |

### Terminals View

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/LabTerminalsView.jsx` | Terminals page | Page entrance + list animations | **MEDIUM** | Wrap with PageTransition; apply row hover animations |

### Live Alerts View

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/LiveAlertsView.jsx` | Alerts page | Page entrance + alert table reveals | **HIGH** | Wrap with PageTransition; add ScrollReveal to alert rows; apply hover animations |

### Grouped Dimensions View

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/LiveGroupedDimensionsView.jsx` | Grouped view page | Page entrance + group card reveals | **MEDIUM** | Wrap with PageTransition; apply ScrollReveal to dimension groups |

### CSV Analytics Page

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/csv_analytics/CsvAnalyticsPage.jsx` | Analytics main page | Page entrance + chart animations | **HIGH** | Wrap with PageTransition; add ScrollReveal to charts and tables |

### Other Pages

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/pages/IncidentPanel.jsx` | Incident management | Page entrance + incident table | **MEDIUM** | Wrap with PageTransition; apply table row hover animations |
| `src/pages/EntityDetail.jsx` | Entity detail page | Page entrance + info sections | **MEDIUM** | Wrap with PageTransition; apply ScrollReveal to detail sections |
| `src/pages/Environment.jsx` | Environment page | Page entrance + content reveals | **MEDIUM** | Wrap with PageTransition; apply ScrollReveal to environment items |

---

## Shared Components

### Cards & Panels

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `.status-badge` | Status badge | Scale-in entrance + hover elevation (section 5.3) | **MEDIUM** | Apply `scale-in` animation on render; add hover state with `--ios-duration-base` |
| `src/App.css` - `.stat-card` | Stat/metric card | Scale-in + hover elevation + icon rotate (section 5.4) | **HIGH** | Has animations; verify `iosFadeInUp` and hover transform use correct durations/easing |
| `src/App.css` - `.events-panel, .alerts-panel` | Panel containers | Scale-in entrance + hover shadow (section 5.5) | **HIGH** | Apply `scale-in` animation on render; add hover box-shadow transition |
| `src/App.css` - `.settings-card` | Settings card | Scale-in entrance (section 5.5) | **MEDIUM** | Apply `scale-in` animation; verify uses `--ios-duration-normal` |
| `src/App.css` - `.telemetry-panel` | Telemetry panel | Scale-in entrance (section 5.5) | **MEDIUM** | Apply `scale-in` animation if not present |
| `src/App.css` - `.info-item` | Info item card | Subtle fade-in | **LOW** | Light reveal animation; use ScrollReveal if in scrollable list |

### Tables & Lists

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `.event-row, .alert-row` | Table rows | Hover highlight + slide (section 5.6) | **HIGH** | Has transitions; verify translateX(4px) and background change use `--ios-duration-fast` |
| `src/App.css` - `.event-row:active` | Row press | Scale 0.995 | **MEDIUM** | Ensure active state works on touch; add scale transform |

### Buttons & Controls

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `button` (all) | Button elements | Tap feedback + transitions (section 5.3) | **CRITICAL** | Ensure all buttons apply `.ios-duration-fast` for all properties |
| `src/App.css` - `.admin-btn` | Admin button | Hover elevation + color transition (section 5.2) | **MEDIUM** | Add hover state with translateY(-2px) and shadow upgrade |
| `src/App.css` - `.date-filter-pill` | Date filter | Hover state transitions | **MEDIUM** | Verify hover uses `--ios-duration-fast` easing |

### Modals & Overlays

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/live/AddLabModal.jsx` | Add lab modal | Modal entrance + backdrop blur (section 5.7) | **HIGH** | Ensure `.modal-dialog` uses `iosModalEntrance` keyframe; `.modal-backdrop` uses `iosBackdropBlur` |
| `src/components/live/AssignLabModal.jsx` | Assign lab modal | Modal entrance + backdrop blur | **HIGH** | Apply modal entrance animations |
| `src/components/live/LiveAlertModal.jsx` | Alert detail modal | Modal entrance + backdrop blur | **HIGH** | Apply modal entrance animations |
| `src/components/live/LiveGroupDetailsModal.jsx` | Group details modal | Modal entrance + backdrop blur | **HIGH** | Apply modal entrance animations |
| `src/csv_analytics/CsvAlertDetailsModal.jsx` | CSV alert modal | Modal entrance + backdrop blur | **HIGH** | Apply modal entrance animations |
| `src/csv_analytics/CsvExportModal.jsx` | Export modal | Modal entrance + backdrop blur | **MEDIUM** | Apply modal entrance animations |
| `src/csv_analytics/CsvGroupDetailsModal.jsx` | CSV group modal | Modal entrance + backdrop blur | **MEDIUM** | Apply modal entrance animations |
| Modal close button `.modal-close-btn` | Close button | Rotate + scale on hover/active (section 5.7) | **MEDIUM** | Hover: rotate(90deg) scale(1.1); Active: rotate(90deg) scale(0.9) |

### Dropdowns & Menus

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/CustomSelect.jsx` | Custom select dropdown | Dropdown entrance + option hover (section 5.8) | **HIGH** | Ensure `.custom-select-menu` uses `iosDropdownEntrance` keyframe; options animate on hover with `--ios-duration-fast` |
| `src/components/CustomSelect.css` | Custom select styles | Dropdown & option animations | **HIGH** | Add `iosDropdownEntrance` animation to menu; ensure option hover uses translateX(3px) and `--ios-duration-fast` |
| `src/components/ExportAnalysisDropdown.jsx` | Export dropdown | Dropdown entrance + item hover (section 5.8) | **HIGH** | Apply dropdown entrance and item hover animations |

### Forms & Inputs

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `input[type="text"], input[type="date"], textarea, select` | Form inputs | Focus glow animation (section 5.9) | **MEDIUM** | Ensure focus state uses border color + box-shadow transition with `--ios-duration-fast` |
| `src/App.css` - `input:focus` | Input focus state | Y-translate + glow | **MEDIUM** | Add translateY(-1px) on focus for tactile rise |

### Indicators & Badges

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/App.css` - `.status-badge.online .dot` | Live status dot | Pulse animation (section 5.10) | **MEDIUM** | Apply `iosPulseSubtle` animation; verify 2.2s infinite duration |
| `src/App.css` - `.live-pulse-dot` | Live pulse indicator | Pulse animation | **MEDIUM** | Apply `iosPulseSubtle` animation |
| `src/App.css` - `.badge` | Badge element | Subtle scale on hover | **LOW** | Scale 1 → 1.08 on parent hover; apply to badge within |

### Data Visualization Components

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/components/RiskChart.jsx` | Risk chart component | Scroll-triggered reveal | **MEDIUM** | Wrap with ScrollReveal if used in scrollable view |
| `src/components/RiskGauge.jsx` | Risk gauge component | Scroll-triggered reveal + gentle entrance | **MEDIUM** | Wrap with ScrollReveal |
| `src/components/RiskGauge.css` | Gauge styles | Gauge animation entrance | **MEDIUM** | Add fade-in + subtle entrance animation if not present |
| `src/components/Sparkline.jsx` | Sparkline mini-chart | Chart render animation | **LOW** | Light fade-in on render; no complex animations needed |

### CSV Analytics Components

| File Path | Component | Motion Spec | Priority | Implementation Notes |
|-----------|-----------|-------------|----------|----------------------|
| `src/csv_analytics/CsvAnalyticsCharts.jsx` | Charts page | Chart reveals + animations | **HIGH** | Wrap chart containers with ScrollReveal; stagger multiple charts |
| `src/csv_analytics/CsvAlertsExplorer.jsx` | Alerts explorer | Table row reveals | **HIGH** | Apply ScrollReveal to alert rows; animate on hover |
| `src/csv_analytics/CsvGroupsExplorer.jsx` | Groups explorer | Group card reveals | **HIGH** | Apply ScrollReveal to group cards; stagger reveals |
| `src/csv_analytics/CsvUploader.jsx` | CSV uploader | Upload form animations | **MEDIUM** | Smooth form focus animations; file input hover states |

---

## Style Files Summary

| File Path | Purpose | Animation Status | Priority |
|-----------|---------|------------------|----------|
| `src/styles/ios-motion.css` | Global animation tokens & keyframes | **COMPLETE** | N/A - Reference |
| `src/index.css` | Design system tokens | **NEEDS AUDIT** | **HIGH** - Verify all tokens present |
| `src/App.css` | Layout & main component animations | **NEEDS ENHANCEMENT** | **HIGH** - Add missing animations, unify easing |
| `src/components/CustomSelect.css` | Dropdown styles | **NEEDS ENHANCEMENT** | **HIGH** - Add dropdown entrance animation, option hover |
| `src/components/RiskGauge.css` | Gauge styles | **NEEDS AUDIT** | **MEDIUM** - Add entrance animation |
| `src/csv_analytics/csvAnalytics.css` | CSV analytics styles | **NEEDS AUDIT** | **HIGH** - Audit and enhance animations |

---

## Implementation Priority Matrix

### CRITICAL (Do First)
- `src/styles/ios-motion.css` — Verify all tokens, keyframes match architecture
- `src/index.css` — Audit CSS custom properties, fallback values
- `src/App.css` — Unify all animations to use iOS tokens, fix easing inconsistencies
- `src/components/PageTransition.jsx` — Ensure `transitionKey` integration with router
- `src/components/ScrollReveal.jsx` — Verify threshold (0.08) and stagger calculation

### HIGH (Do Second)
- All stat/status cards (StatCard, StatusBadge, StatusGrid)
- All modals (AddLabModal, AssignLabModal, etc.)
- Main views (LiveDashboardView, LabComputersView, LiveAlertsView)
- Tables & rows (.event-row, .alert-row)
- Custom select & dropdowns
- Form inputs with focus animations
- CSV Analytics charts and explorers

### MEDIUM (Do Third)
- Nav items refinement
- Panel hover animations
- Individual page wrap with PageTransition
- ScrollReveal stagger application
- Button active states refinement
- Sidebar animations

### LOW (Optional)
- Sparkline animations
- Info item cards
- Badges/indicator refinements
- Other non-critical micro-interactions

---

## Implementation Strategy

### Phase 1: Foundation (Days 1-2)
1. Verify `ios-motion.css` tokens and keyframes are complete and correct
2. Audit `index.css` for all CSS custom property definitions
3. Consolidate `App.css` animations to use centralized tokens
4. Create `src/utils/useReducedMotion.js` hook

### Phase 2: Global Components (Days 3-4)
5. Wrap all main pages/views with `PageTransition` component
6. Apply `ScrollReveal` to card/panel elements across views
7. Enhance button/control animations (tap feedback, hover states)
8. Modal entrance animations (iosModalEntrance, iosBackdropBlur)

### Phase 3: Specific Components (Days 5-6)
9. Dropdown/custom select animations (iosDropdownEntrance, option hover)
10. Table row hover animations (translateX, background)
11. Form input focus animations (glow, Y-translate)
12. Status indicators & badge animations (pulse, scale)

### Phase 4: Polish & Refinement (Days 7-8)
13. CSV analytics page animations
14. Incident panel animations
15. Detail view animations (EntityDetail, ComputerDetail, Environment)
16. Testing on mobile breakpoints
17. Accessibility testing with prefers-reduced-motion

---

## Testing & Verification

After implementation of each category, verify:

- [ ] Animations play smoothly at 60 FPS (use Chrome DevTools > Performance)
- [ ] All animations respect `prefers-reduced-motion` setting
- [ ] Keyboard navigation still works; focus indicators visible
- [ ] Mobile touch feedback feels responsive (no lag)
- [ ] No horizontal overflow from translate animations
- [ ] Page transitions don't break browser back/forward
- [ ] Scroll-triggered animations fire once, not repeatedly
- [ ] Modals don't interfere with body scroll behavior
- [ ] All `will-change` properties are applied to animated elements
- [ ] No layout thrashing or recalculation (check DevTools)

---

**Document Version**: 1.0  
**Last Updated**: Design Phase  
**Total Components**: 40+ files  
**Total Priority Items**: 50+  
**Estimated Implementation**: 1-2 weeks with attention to performance
