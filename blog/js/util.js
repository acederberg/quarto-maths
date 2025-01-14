
export const BREAKPOINTS = {
  xs: { stop: 576 },
  sm: { start: 576, stop: 768 },
  md: { start: 768, stop: 992 },
  lg: { start: 992, stop: 1200 },
  xl: { start: 1200, stop: 1400 },
  xxl: { start: 1400 },
}

export function isBreakpoint(width, specifier) {

  width = width || window.innerWidth
  const range = BREAKPOINTS[specifier]
  if (!range) throw Error(`No such speficier \`${specifier}\`.`)

  const geStart = !range.start || range.start < width
  const leStop = !range.stop || range.stop >= width

  return geStart && leStop

}

// NOTE: If start is not defined, then ``width`` only needs to be checked against upper bound.
//       If stop is not defined, then ``width`` only needs to be checked against lower bound.
//       All checks are on half open intervals to avoid intersections.
export function getBreakpoint(width) {
  width = width || window.innerWidth
  const item = Object.entries(BREAKPOINTS).filter(
    ([specifier]) => isBreakpoint(width, specifier)
  ).pop()

  if (!item) throw Error(`No breakpoint for \`${width}\`.`)
  return item[0]
}


export function FullPage() {
  document.getElementById("title-block-header").remove()
  document.getElementById("quarto-document-content").classList.add("px-1")
  const quartoContent = document.getElementById("quarto-content")
  quartoContent.classList.remove("page-columns")
}


