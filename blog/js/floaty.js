// @ts-check
import { Overlay } from "./overlay.js"
import { getBreakpoint, BREAKPOINTS } from "./util.js"

/** @type {Map<string, TFloaty>} */
export const FloatyInstances = new Map()

/** @typedef {import("./util.js").EnumBSBreakpoint} EnumBSBreakpoint */
/** @typedef {import("./overlay.js").TOverlay} TOverlay */
/** @typedef {Map<EnumBSBreakpoint, number>} TBreakpointColumns */

/** @type {TBreakpointColumns} */
const BREAKPOINTS_RESIZE = new Map()
BREAKPOINTS_RESIZE.set('xs', 1)
BREAKPOINTS_RESIZE.set('sm', 1)
BREAKPOINTS_RESIZE.set('md', 2)
BREAKPOINTS_RESIZE.set('lg', 3)
BREAKPOINTS_RESIZE.set('xl', 5)
BREAKPOINTS_RESIZE.set('xxl', 5)

/** @type {EnumBSBreakpoint} */
const BREAKPOINT_TOOLTIPS_TRANSFORM = 'xl'

/** @typedef {object} TFloatyOptions 
 *
 * @property {TOverlay|null} [overlayControls] - Output of ``Overlay`` *(from ``overlay.js``)*.
 * @property {object} [resize] - Enable resizing.
 * @property {TBreakpointColumns} [resizeBreakpoints] - Breakpoint names mapping to the number of columns for the range. By default `BREAKPOINTS_RESIZE`.
 * @property {boolean} [tooltipsToggle] - Toggle tooltips.
 * @property {EnumBSBreakpoint} [tooltipsToggleBreakpoint] - Breakpoint for toggleing tooltips into card descriptions. By default, ``BREAKPOINT_TOOLTIPS_TRANSFORM``.
 */

/**
 * @typedef {object} TFloaty
 *
 * @property {HTMLElement} elem
 * @property {Element} container
 * @property {Element[]} cards
 * @property {TOverlay|null} overlayControls - Controls for the included overlay.
 * @property {(countColumns: number) => void} resizeForColumns - Resize to a specified number of columns.
 * @property {(width?: number) => void} resizeForWidth - Resize the columns for the current window width or specified width.
 * @property {(width?: number) => void} toggleTooltip - Toggle tooltips into card descriptions and
 *   vice versa around some breakpoint.
 * @property {() => void} initialize
 *
 */

/** Add responsiveness to a `floaty` element.
 *
 * Ideally, these are styled with `floaty` as in `floaty.scss`.
 *
 * Responsiveness includes:
 *
 * - opening overlays and links when clicking on ``floaty-items``,
 * - moving tooltips to descriptions and vice versa at certain breakpoints,
 * - resizing the grid while keeping cards of equal width using fillers,
 *
 * @param {HTMLElement} elem - The target to add responsiveness to.
 * @param {TFloatyOptions} options - Configuration options.
 * @throws {Error} if ``element`` is not passed, or when the floaty does not contain a `floaty-container` element.
 * @returns {TFloaty}
 *
 * */
export function Floaty(elem, { overlayControls, resize, tooltipsToggle, resizeBreakpoints, tooltipsToggleBreakpoint }) {

  resizeBreakpoints = resizeBreakpoints || BREAKPOINTS_RESIZE
  tooltipsToggleBreakpoint = tooltipsToggleBreakpoint || BREAKPOINT_TOOLTIPS_TRANSFORM
  if (!elem) throw Error("Missing required element.")

  const container = elem.querySelector(".floaty-container")
  if (!container) throw Error("Missing container.")

  const cards = Array.from(container.getElementsByClassName("card"))

  // @ts-ignore
  const tooltips = [...elem.querySelectorAll(".floaty-item .card[data-bs-toggle='tooltip']")].map(card => new bootstrap.Tooltip(card))

  /** Make an empty (invisible) floaty item.
   *
   * These are the placeholds used to make sure that `flex-grow` does not
   * result in a card taking up an uneven amount of space when resizing *(for
   * instance if a card was put into a single row)*.
   *
   * @throws {Error} when a `floaty-item` or card cannot be found.
  */
  function createEmptyItem() {
    if (!cards.length) {
      console.log("No cards.")
      return
    }

    const floatyItemFirst = elem.querySelector(".floaty-item")
    if (!floatyItemFirst) throw Error(`No \`floaty-item\` found in \`elem\` with \`id=${elem.id}\`.`)

    const floatyItemFirstCard = elem.querySelector(".card")
    if (!floatyItemFirstCard) throw Error(`No \`card\` found in \`elem\` with \`id=${elem.id}\`.`)

    const floatyItemEmpty = document.createElement("div")

    // @ts-ignore
    floatyItemEmpty.classList.add("floaty-item", ...floatyItemFirst.classList)
    const floatyItemEmptyCard = document.createElement("div")

    // @ts-ignore
    floatyItemEmptyCard.classList.add("card", "hidden", ...floatyItemFirstCard.classList)
    floatyItemEmptyCard.ariaLabel = "empty"
    floatyItemEmptyCard.ariaDescription = "This is a placeholder."
    floatyItemEmptyCard.innerHTML = `
          <div class="card-img-top">
            <i class="bi bi-bug text-red bg-black"></i>
          </div>
          <div class="card-boDy">
            <div class="card-title">
              Empty
            </div>
            <div class="card-text">
              This card should not be visible.
            </div>
          </div>
        </div>
      `

    floatyItemEmpty.appendChild(floatyItemEmptyCard)
    return floatyItemEmpty
  }

  function createRow() {
    const floatyRowFirst = elem.querySelector(".floaty-row")
    if (!floatyRowFirst) throw Error("No row.")

    const floatyRow = document.createElement("div")

    // @ts-ignore
    floatyRow.classList.add("floaty-row", ...floatyRowFirst.classList)
    return floatyRow
  }

  /**
   * Divide the cards into ``countColumns`` columns.
   *
   * This function calculates the required rows and evenly distributes items
   * across the specified number of columns. Empty placeholder items are added
   * if needed to ensure all rows are balanced. The container is updated with
   * new rows and their corresponding items.
   *
   * @param {number} [countColumns] - The number of columns to devide the floaty into.
   * @throws {Error} when no items are found and when `options.countColumns` is
   *   not negative or indeterminable.
   *
   * @example
   *
   * // Resize the floaty container to 3 columns
   * resizeForColumns({ countColumns: 3 });
   *
   * @example
   *
   * // Resize the floaty container to 5 columns
   * resizeForColumns({ countColumns: 5 });
   *
   * */
  function resizeForColumns(countColumns) {
    if (!cards.length) {
      console.log("No cards.")
      return
    }

    // NOTE: Assume all rows have the same classes.
    const items = elem.querySelectorAll(".floaty-item")
    if (!items) throw Error("Missing items.")

    if (!countColumns) {
      const rowFirst = elem.querySelector(".floaty-row")
      if (!rowFirst) throw Error("Missing row.")
      countColumns = rowFirst.querySelectorAll(".floaty-item").length
      // console.log("countColumns", countColumns, elem.id)
      // console.log(items)
    }
    if (countColumns <= 0) throw Error("`countColumns` must be a positive number.")

    let countRows = Math.floor(items.length / countColumns)
    const countIncomplete = items.length % countColumns
    const countEmptyRequired = countColumns - countIncomplete

    if (countIncomplete) countRows++

    const emptyItem = createEmptyItem()
    if (!emptyItem) return

    const empty = Array.from(Array(countEmptyRequired).keys()).map(
      (index) => {
        const emptyItemCurrent = emptyItem.cloneNode(true)

        // @ts-ignore
        emptyItemCurrent.dataset.key = `empty-from-js-${index}`
        return emptyItemCurrent
      }
    )

    // NOTE: Replace Old Content, make template row.
    const row = createRow()

    // @ts-ignore
    container.innerHTML = ''

    // NOTE: Make and Add Rows
    // @ts-ignore
    const allItems = [...items, ...empty]
    Array.from(Array(countRows).keys()).map(rowIndex => {
      const rowCurrent = row.cloneNode(true)
      allItems.slice(
        countColumns * rowIndex,
        countColumns * (rowIndex + 1),
      ).map(card => rowCurrent.appendChild(card))

      // @ts-ignore
      container.append(rowCurrent)
    })
  }


  /** Resize using current or privided width.
   *
   * Resizing is determined by `resizeBreakpoints` provided to the closure or `BREAKPOINTS_RESIZE`.
   *
   * @param {number} [width] - Number of pixels that the resize is for.
  */
  function resizeForWidth(width) {
    if (!resizeBreakpoints) throw Error()

    const breakpoint = getBreakpoint(width)
    const countColumns = resizeBreakpoints.get(breakpoint)
    if (!countColumns) {
      console.error(`No specification for breakpoint \`${breakpoint}\`.`)
      return
    }

    return resizeForColumns(countColumns)
  }

  /** Toggle the boostrap tooltip into a card description (on the card, this
   * should match the selector ``.card .card-body .card-text``).
   *
   * Additionally, this will disable the bootstrap tool tip.
   *
   * @param {any} item - Ideally ``floaty-item``.
   */
  function toggleTooltipToCardDescription(item) {
    const elem = item._element
    // NOTE: Does not disable tooltip.
    item.disable()

    // NOTE: Check if card text has been added.
    const textFromResize = Array.from(elem.getElementsByClassName("card-text")).filter(item => item.dataset.cardTextFromResize != null)
    if (textFromResize.length) return

    // NOTE: Look for a card  body. If there isn't one, make it.
    let body = elem.querySelector(".card-body")
    if (!body) {
      body = document.createElement("div")
      body.classList.add("card-body")
      body.dataset.cardTextFromResize = true
      elem.appendChild(body)
    }

    // NOTE: Add tooltip as card-text.
    const description = document.createElement("div")
    description.classList.add("card-text")
    description.innerText = elem.dataset.bsTitle
    description.dataset.cardTextFromResize = 'true'

    body.appendChild(description)
  }

  /** Toggle card description into a bootstrap tooltip.
   *
   * @param {any} item - Ideally a ``floaty-item``.
   */
  function toggleCardDescriptionToTooltip(item) {
    const elem = item._element
    item.enable()

    // NOTE: Find all ``card-text`` children marked with ``cardTextFromResize`` and remove.
    const textFromResize = Array.from(elem.getElementsByClassName("card-text")).filter(item => item.dataset.cardTextFromResize != null)
    textFromResize.map(item => item.remove())

    // NOTE: If a card body is marked with ``cardTextFromResize``, then it should 
    //       be removed.
    const bodyFromResize = Array.from(elem.getElementsByClassName("card-body")).filter(item => item.dataset.cardTextFromResize != null)
    bodyFromResize.map(item => item.remove())
  }

  /** @param {number} [width] - width at which to toggle. */
  function toggleTooltip(width) {
    width = width || BREAKPOINTS.get(tooltipsToggleBreakpoint || BREAKPOINT_TOOLTIPS_TRANSFORM)?.start || undefined
    if (!width) throw Error("Failed to determine `width`.")

    tooltips.map(item => (
      window.innerWidth < width
        ? toggleTooltipToCardDescription(item)
        : toggleCardDescriptionToTooltip(item)
    ))
  }


  /** Initialization steps. */
  function initialize() {
    // Add resizing on window size change if it is desired.
    if (resize) {
      console.log(`Resizing for \`${elem.id}\`.`, resize)
      window.addEventListener("resize", () => resizeForWidth())
      window.addEventListener("load", () => resizeForWidth())
    }

    // Add toggle on window resize if it is desired.
    if (tooltipsToggle) {
      window.addEventListener("resize", () => toggleTooltip())
      window.addEventListener("load", () => toggleTooltip())
      toggleTooltip()
    }

    // Add links.
    cards.map(card => {
      // @ts-ignore
      if (!card.dataset.floatyUrl) return
      card.addEventListener("click", () => {
        // @ts-ignore
        window.open(card.dataset.floatyUrl, "_blank").focus()
      })
    })

    // Add overlay.
    if (overlayControls) cards.map(card => {
      card.addEventListener("click", () => {
        overlayControls.showOverlay()
        // @ts-ignore
        overlayControls.showOverlayContentItem(card.dataset.key)
      })
    })


    // NOTE: Add fillers.
    resizeForColumns()

  }

  initialize()

  /** @type {TFloaty} */
  return {
    elem,
    container,
    cards,
    overlayControls: (overlayControls || null),
    resizeForColumns,
    resizeForWidth,
    toggleTooltip,
    initialize,
    // _tooltips: tooltips,
    // _toggleTooltipToCardDescription: toggleTooltipToCardDescription,
    // _toggleCardDescriptionToTooltip: toggleCardDescriptionToTooltip,
    // _createRow: createRow,
    // _createEmptyItem: createEmptyItem,
  }
}

/** Wrapper for ``Floaty`` to minimize amount of js the ``floaty`` filter
 * includes.
 *
 * @param {string} elemId - The target element to add `Floaty` functionality to.
 * @param {object} options - Configuration options.
 * @param {string} options.overlayId - Identifier for the associated overlay.
 * @param {TOverlay|null} options.overlayControls - Pass already existing ``overlayControls``
 *   to ``Floaty`` *(instead of creating them from ``overlayId``)*.
 * @throws {Error} when an element with identifier ``elemId`` or ``options.overlayId``
 *   cannot be found.
 *
 */
export function lazyFloaty(elemId, { overlayId, overlayControls, ...rest }) {
  const elem = document.getElementById(elemId)
  if (!elem) throw Error(`Could not find element with id \`${elemId}\`.`)

  if (overlayId && !overlayControls) {
    const overlay = document.getElementById(overlayId)
    overlayControls = overlay ? Overlay(overlay) : null
  }

  const floaty = Floaty(elem, { overlayControls, ...rest })
  FloatyInstances.set(elem.id, floaty)
  return floaty
}
