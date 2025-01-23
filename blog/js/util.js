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
* @param {number|null} [width] - Width in pixels.
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



/** Make quarto page fullpage. */
export function FullPage() {
  document.getElementById("title-block-header")?.remove()
  document.getElementById("quarto-document-content")?.classList.add("px-1")
  document.getElementById("quarto-content")?.classList.remove("page-columns")
}


/** 
 * @returns {HTMLDivElement}
 */
export function Spinner() {

  const spinner = document.createElement("div")
  spinner.classList.add("spinner-border", "spinner-border-sm", "hidden")
  return spinner
}


/** 
 * @typedef {object} TButton
 *
 * @property {HTMLButtonElement} elem
 * @property {HTMLElement} icon
 * @property {HTMLDivElement} spinner
 * @property {() => void} toggleSpinner - Turn the spinner on and off.
 * @property {TButtonState} state
 *
 */

/**
 * @typedef {object} TButtonOptions
 *
 * @property {string} id -
 * @property {string} tooltip -
 * @property {string[]} [iconClasses] -
 * @property {Array<string>} [classesButton] -
 * @property {string} [dataKey] -
 * @property {string} [icon] -
 * @property {string} [text] -
 */

/**
 * @typedef {object} TButtonState
 *
 * @property {boolean} spinner - When ``true``, spinner is visible.
 */

/**
 * @param {TButtonOptions} options
 * @returns {TButton}
 */
export function Button({ id, classesButton, dataKey, tooltip, icon, iconClasses, text }) {

  if (!icon) throw Error("An icon is required.")

  const button = document.createElement('button');
  if (id) button.id = id;
  button.type = 'button';
  button.classList.add("btn", ...(classesButton || []))

  if (dataKey) button.dataset.key = dataKey;
  if (tooltip) {
    button.setAttribute('data-bs-toggle', 'tooltip');
    button.setAttribute('data-bs-placement', 'top');
    button.setAttribute('title', tooltip);
    button.setAttribute('data-bs-custom-class', 'banner-tooltip')
  }

  const buttonSpinner = Spinner()
  button.appendChild(buttonSpinner)

  const buttonIcon = document.createElement('i');
  buttonIcon.classList.add("bi", `bi-${icon}`);
  iconClasses && buttonIcon.classList.add(...iconClasses)
  button.appendChild(buttonIcon);

  if (text) {
    const textNode = document.createElement('text');
    textNode.textContent = text;
    button.appendChild(textNode);
  }

  /** @type {TButtonState} */
  const state = { spinner: false }

  function toggleSpinner() {

    if (!state.spinner) {
      buttonSpinner.classList.remove("hidden")
      buttonIcon.classList.add("hidden")
      button.classList.add("disabled")
    }
    else {
      buttonSpinner.classList.add("hidden")
      buttonIcon.classList.remove("hidden")
      button.classList.remove("disabled")
    }

    state.spinner = !state.spinner
  }

  return { elem: button, icon: buttonIcon, spinner: buttonSpinner, toggleSpinner, state };
}



