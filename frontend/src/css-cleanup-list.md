# CSS Animation Cleanup List
## What was replaced by Motion animations

### Keyframes Removed (from ios-motion.css)

**These CSS keyframes were replaced with motion spring animations:**

1. `@keyframes iosPageEntrance` - Page/section transitions (now: `variants.pageTransition`)
2. `@keyframes iosTabFadeIn` - Tab switching (now: motion variants)
3. `@keyframes iosFadeIn` - Simple fades (now: `animate={{ opacity: 1 }}`)
4. `@keyframes iosFadeInUp` - Fade + upward movement (now: `variants.fadeUp`)
5. `@keyframes iosScaleIn` - Scale + fade (now: `variants.modalScale`)
6. `@keyframes iosModalEntrance` - Modal animations (now: motion sheet spring)
7. `@keyframes iosBackdropBlur` - Backdrop fades (now: `variants.backdropFade`)
8. `@keyframes iosDropdownEntrance` - Dropdowns (now: motion variants)
9. `@keyframes iosToastSlideIn` - Toasts (now: motion variants)
10. `@keyframes iosPulseSubtle` - Pulsing effects (now: motion `repeat` animations)
11. `@keyframes iosShimmer` - Shimmer effects (motion can handle if needed)

### CSS Transitions to Update

**Replace these in App.css:**

1. **Line 144**: `transition: all var(--ios-duration-fast, 0.18s)`  
   → Should be: `transition: transform var(--ios-duration-fast), opacity var(--ios-duration-fast)`

2. **Line 209**: `transition: all var(--transition-base)`  
   → Should be explicit properties based on what changes (likely: `transform, opacity, background-color`)

3. **Line 298**: `transition: all var(--transition-base)`  
   → Same as above

4. **Line 346**: `transition: all var(--transition-fast, 0.15s)`  
   → Should be explicit properties

5. **Line 411**: `transition: all 0.15s`  
   → Should be explicit properties

6. **Line 478**: `transition: all var(--transition-base)`  
   → Should be explicit properties

7. **Line 667**: `transition: all var(--transition-base)`  
   → Should be explicit properties

8. **Line 680**: `transition: all var(--transition-base)`  
   → Should be explicit properties

### Performance Optimizations Applied

✅ **Completed:**
- All interactive elements use `transform` and `opacity` only
- Layout animations use `layout="position"` for smooth reordering
- `will-change: transform` applied to actively animating elements
- Large lists capped at 12 simultaneous animations
- WebSocket updates batched for smooth performance

⚠️ **Remaining:**
- Some `transition: all` still need explicit property specification
- Old keyframes could be removed from ios-motion.css (safe to delete)

### Verification Checklist

- [x] `npm run build` passes
- [x] `npm run lint` passes (warnings only, no errors)
- [x] Application runs at http://localhost:5173
- [x] Sidebar active pill glides smoothly
- [x] Status badges have breathing glow
- [x] RiskGauge arcs animate with springs
- [x] Lists have smooth entry/exit animations
- [x] `prefers-reduced-motion` respected
- [ ] All `transition: all` replaced with explicit properties
- [ ] Old keyframes removed from CSS files

### Notes

**Why keep ios-motion.css?**
- Contains useful timing tokens (`--ios-duration-fast`, etc.)
- Contains easing curves still used for non-spring animations
- Can be cleaned up by removing only the keyframes

**Migration Complete When:**
1. All animations feel "buttery smooth" (60 FPS)
2. No visible jank during WebSocket updates
3. Reduced motion mode works correctly
4. No competing CSS/motion animations