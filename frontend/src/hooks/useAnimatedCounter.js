import { useEffect, useRef, useState } from 'react'

/**
 * useAnimatedCounter
 * ------------------
 * Smoothly animates a numeric display value towards `target` using
 * requestAnimationFrame and an ease-out cubic curve. Respects the
 * user's reduced-motion preference by snapping instantly.
 *
 * @param {number} target   final value
 * @param {number} duration animation length in ms
 * @returns {number}        current animated value (already rounded)
 */
export default function useAnimatedCounter(target = 0, duration = 900) {
  const [value, setValue] = useState(0)
  const fromRef = useRef(0)
  const rafRef = useRef(null)

  useEffect(() => {
    const to = Number(target) || 0
    const from = fromRef.current

    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setValue(to)
      fromRef.current = to
      return undefined
    }

    if (from === to) {
      setValue(to)
      return undefined
    }

    const start = performance.now()
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(from + (to - from) * eased))
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        fromRef.current = to
      }
    }
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      fromRef.current = to
    }
  }, [target, duration])

  return value
}
