/**
 * @typedef {object} Range
 *
 * @property {number|null} [start]
 * @property {number|null} [stop]
 *
 */

/**
 * @typedef {"xs" | "sm" | "md" | "lg" | "xl" | "xxl" } BSBreakpoint
 */

/** @type Map<BSBreakpoint, Range> */
export const BREAKPOINTS = new Map()
BREAKPOINTS.set('xs', { stop: 576 })
BREAKPOINTS.set('sm', { start: 576, stop: 768 })
BREAKPOINTS.set('md', { start: 768, stop: 992 })
BREAKPOINTS.set('lg', { start: 992, stop: 1200 })
BREAKPOINTS.set('xl', { start: 1200, stop: 1400 })
BREAKPOINTS.set('xxl', { start: 1400 })

/**
 * @param {number} width
 * @param {BSBreakpoint} specifier 
 * @returns {boolean}
 */
export function isBreakpoint(width, specifier) {

  width = width || window.innerWidth
  const range = BREAKPOINTS.get(specifier)
  if (!range) throw Error(`No such speficier \`${specifier}\`.`)

  const geStart = !range.start || range.start < width
  const leStop = !range.stop || range.stop >= width

  return geStart && leStop

}

/**
* @param {number} [width] - Width in pixels.
* @returns {BSBreakpoint} Breakpoint range in which the width falls.
*
* If start is not defined, then ``width`` only needs to be checked against upper bound.
* If stop is not defined, then ``width`` only needs to be checked against lower bound.
* All checks are on half open intervals to avoid intersections.
*/
export function getBreakpoint(width) {
  width = width || window.innerWidth
  const item = [...BREAKPOINTS.entries()].filter(
    ([specifier]) => isBreakpoint(width, specifier)
  ).pop()

  if (!item) throw Error(`No breakpoint for \`${width}\`.`)
  return item[0]
}


export function FullPage() {
  document.getElementById("title-block-header")?.remove()
  document.getElementById("quarto-document-content")?.classList.add("px-1")
  document.getElementById("quarto-content")?.classList.remove("page-columns")
}


