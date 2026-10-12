# iOS Motion Tuning Guide for TAVIX GUARD

## Motion Configuration (src/motion.js)

### Spring Tuning

```javascript
// Soft spring - large surfaces, page transitions
soft: {
  type: 'spring',
  stiffness: 260,    // Lower = softer, more floaty
  damping: 30,       // Lower = more bounce, higher = faster settle
  mass: 1,           // Weight of the element (1 = normal)
}

// Snappy spring - buttons, toggles, interactive elements  
snappy: {
  type: 'spring',
  stiffness: 420,    // Higher = more responsive
  damping: 34,       // Controls overshoot (34 = slight overshoot)
  mass: 0.9,         // Slightly lighter than normal
}

// Sheet spring - modals, panels, overlays
sheet: {
  type: 'spring',
  stiffness: 300,    // Medium responsiveness
  damping: 32,       // Smooth settle with minimal bounce
}
```

### Quick Adjustments

**Want snappier feel?**
- Increase stiffness (420 → 500)
- Slightly decrease damping (34 → 30)

**Want softer, floatier feel?**
- Decrease stiffness (260 → 200)
- Increase damping (30 → 35)

**Want more bounce?**
- Decrease damping (30 → 24)
- Keep stiffness moderate

### Stagger Timing
- `delayChildren: 0.08s` - Wait before first child animates
- `staggerChildren: 0.05s` - Delay between each child
- Max total stagger: ~0.68s (0.08 + 12×0.05)

### Easing Curves
- **Apple ease**: `[0.22, 1, 0.36, 1]` - Fast start, smooth deceleration
- Use for: opacity, color, non-spring animations

## Component-Specific Motion

### Sidebar Navigation
```javascript
// Active pill glides between items
<motion.div layoutId="nav-active" />

// Nav items stagger on load
variants.navItemContainer // Contains stagger
```

### Status Badge
- Online: Breathing glow (2s infinite loop, scale + opacity)
- Offline: Static
- Status change: Color crossfade via React key change

### Risk Gauge
- Arc animates via `stroke-dashoffset` with spring
- Number tweens with spring
- Color transitions with ease curve (400ms)

### Risk Chart
- Tooltip fades in with scale (0.96 → 1)
- Empty state fades in
- Chart data: Recharts built-in animationDuration (900ms)

### Lists (Events, Alerts)
- `layout="position"` for smooth row reordering
- New rows: opacity 0 → 1, y -12 → 0
- Removed rows: collapse + fade
- Stagger capped at first 12 rows for performance

## Performance Rules

1. **Animate only**: transform, opacity, filter
2. **Never animate**: width, height, top, left, box-shadow
3. **Replace**: `transition: all` → `transition: transform, opacity`
4. **Use**: `will-change: transform` on actively animating elements
5. **Avoid**: Inline variant objects (reuse from motion.js)

## Accessibility

- `prefers-reduced-motion` handled by `useMotionPrefs()` hook
- Reduced motion: 150ms fades instead of springs
- Test with Chrome DevTools: Rendering → Emulate CSS media feature

## Common Issues

**Animation not working?**
1. Check motion imports: `import { motion } from 'motion/react'`
2. Ensure variants imported: `import { variants } from './motion'`
3. Check for double-animation (CSS + motion)

**Janky performance?**
1. Verify only transform/opacity are animated
2. Check for `transition: all` in CSS
3. Ensure large lists use virtualization or capping

**Spring feels wrong?**
1. Adjust stiffness/damping in motion.js
2. Check mass values (default = 1)
3. Verify no competing CSS transitions