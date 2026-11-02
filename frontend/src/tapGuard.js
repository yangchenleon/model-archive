/**
 * Tell a real tap apart from a scroll, drag or text-selection gesture.
 *
 * A plain `@click` on a whole card fires even when the pointer moved 50px while
 * the user was selecting text, which is how "滑动复制" ends up opening a drawer.
 * Bind the pointer handlers to the element and gate the click handler with
 * `shouldActivate()`.
 */
export function createTapGuard({ moveThreshold = 10, maxPressMs = 700 } = {}) {
  let startX = 0
  let startY = 0
  let pressedAt = 0
  let moved = false
  let sawPointer = false

  return {
    pointerdown(event) {
      if (event.pointerType === 'mouse' && event.button !== 0) return
      sawPointer = true
      moved = false
      startX = event.clientX
      startY = event.clientY
      pressedAt = performance.now()
    },
    pointermove(event) {
      if (!sawPointer) return
      if (Math.hypot(event.clientX - startX, event.clientY - startY) > moveThreshold) {
        moved = true
      }
    },
    pointercancel() {
      // The browser took over the gesture (usually a touch scroll).
      moved = true
    },
    shouldActivate() {
      // Keyboard / assistive-technology clicks never fire pointer events.
      if (!sawPointer) return true
      const pressedFor = performance.now() - pressedAt
      sawPointer = false
      if (moved || pressedFor > maxPressMs) return false
      const selection = window.getSelection?.()
      if (selection && selection.toString().trim()) return false
      return true
    },
  }
}
