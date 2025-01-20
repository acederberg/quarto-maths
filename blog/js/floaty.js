// @ts-nocheck
import { Overlay } from "./overlay.js"
import { getBreakpoint, BREAKPOINTS } from "./util.js"

// NOTE: Should persist over imports.
export const FloatyInstances = new Map()
const BREAKPOINTS_RESIZE = { xs: 1, sm: 1, md: 2, lg: 3, xl: 5, xxl: 5 }
const BREAKPOINT_TOOLTIPS_TRANSFORM = 'xl'

/** Add responsiveness to a `floaty` element.
 *
 * Ideally, these are styled with `floaty` as in `floaty.scss`.
 *
 * Responsiveness includes:
 *
 * - opening overlays and links when clicking on ``floaty-items``,
 * - moving tooltips to descriptions and vice versa at certain breakpoints,
 * - resizing the grid while keeping cards of equal width using fillers,
 * - 
 *
 * @param {HTMLElement} elem - The target to add responsiveness to.
 * @param {object} options - Configuration options.
 * @param {object} options.overlayControls - Output of ``Overlay`` *(from ``overlay.js``)*.
 * @param {object} options.resize - Enable resizing.
 * @param {object} options.resizeBreakpoints - Breakpoint names mapping to the number
 *   of columns for the range. By default `BREAKPOINTS_RESIZE`.
 * @param {option} options.tooltipsToggle - Toggle tooltips.
 * @param {string} options.tooltipsToggleBreakpoint - Breakpoint for toggleing
 *   tooltips into card descriptions. By default, ``BREAKPOINT_TOOLTIPS_TRANSFORM``.
 * @throws {Error} if ``element`` is not passed, or when the floaty does not
 *   contain a `floaty-container` element.
 *
 * */
export function Floaty(elem, { overlayControls, resize, tooltipsToggle, resizeBreakpoints, tooltipsToggleBreakpoint }) {

  resizeBreakpoints = resizeBreakpoints || BREAKPOINTS_RESIZE
  tooltipsToggleBreakpoint = tooltipsToggleBreakpoint || BREAKPOINT_TOOLTIPS_TRANSFORM
  if (!elem) throw Error("Missing required element.")

  const container = elem.querySelector(".floaty-container")
  if (!container) throw Error("Missing container.")

  const floatyItemContainers = Array.from(container.querySelectorAll("floaty-item-container"))
  const cards = Array.from(container.getElementsByClassName("card"))
  const tooltips = [...elem.querySelectorAll(".floaty-item .card[data-bs-toggle='tooltip']")].map(
    card => new bootstrap.Tooltip(card)
  )

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
    floatyItemEmpty.classList.add("floaty-item", ...floatyItemFirst.classList)

    const floatyItemEmptyCard = document.createElement("div")
    floatyItemEmptyCard.classList.add("card", "hidden", ...floatyItemFirstCard.classList)
    floatyItemEmptyCard.ariaLabel = "empty"
    floatyItemEmptyCard.ariaTitle = "empty"
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
   * @param {object} options - Options for resizing.
   * @param {number} options.countColumns - The number of columns to devide the
   *   floaty into.
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
  function resizeForColumns({ countColumns }) {
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
    const empty = Array.from(Array(countEmptyRequired).keys()).map(
      (index) => {
        const emptyItemCurrent = emptyItem.cloneNode(true)
        emptyItemCurrent.dataset.key = `empty-from-js-${index}`
        return emptyItemCurrent
      }
    )

    // NOTE: Replace Old Content, make template row.
    const row = createRow()
    container.innerHTML = ''

    // NOTE: Make and Add Rows
    const allItems = [...items, ...empty]
    Array.from(Array(countRows).keys()).map(rowIndex => {
      const rowCurrent = row.cloneNode(true)
      allItems.slice(
        countColumns * rowIndex,
        countColumns * (rowIndex + 1),
      ).map(card => rowCurrent.appendChild(card))

      container.append(rowCurrent)
    })
  }


  /** Resize using current or privided width.
   *
   * Resizing is determined by `resizeBreakpoints` provided to the closure or `BREAKPOINTS_RESIZE`.
   *
   * @param {number|null} width - Number of pixels that the resize is for.
  */
  function resizeForWidth(width) {
    const breakpoint = getBreakpoint(width)
    const countColumns = resizeBreakpoints[breakpoint]
    if (!countColumns) {
      console.error(`No specification for breakpoint \`${breakpoint}\`.`)
      return
    }

    return resizeForColumns({ countColumns })
  }

  /** Toggle the boostrap tooltip into a card description (on the card, this
   * should match the selector ``.card .card-body .card-text``).
   *
   * Additionally, this will disable the bootstrap tool tip.
   *
   * @param {HTMLElement} item - Ideally ``floaty-item``.
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
    description.dataset.cardTextFromResize = true

    body.appendChild(description)
  }

  /** Toggle card description into a bootstrap tooltip.
   *
   * @param {HTMLElement} item - Ideally a ``floaty-item``.
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

  /** Toggle tooltips into card descriptions and vice versa around some
   * breakpoint.
   *
   * @param {number|null} width - width at which to toggle.
   */
  function toggleTooltip(width) {
    width = width || BREAKPOINTS[tooltipsToggleBreakpoint].start
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
      if (!card.dataset.floatyUrl) return
      card.addEventListener("click", () => {
        window.open(
          card.dataset.floatyUrl,
          "_blank"
        ).focus()
      })
    })

    // Add overlay.
    if (overlayControls) cards.map(card => {
      card.addEventListener("click", () => {
        overlayControls.showOverlay()
        overlayControls.showOverlayContentItem(card.dataset.key)
      })
    })


    // NOTE: Add fillers.
    resizeForColumns({})

  }

  initialize()


  return {
    elem, container, cards, overlayControls,
    resizeForColumns,
    resizeForWidth,
    toggleTooltip,
    initialize,
    _tooltips: tooltips,
    _toggleTooltipToCardDescription: toggleTooltipToCardDescription,
    _toggleCardDescriptionToTooltip: toggleCardDescriptionToTooltip,
    _createRow: createRow,
    _createEmptyItem: createEmptyItem,
  }
}

/** Wrapper for ``Floaty`` to minimize amount of js the ``floaty`` filter
 * includes.
 *
 * @param {string} elemId - The target element to add `Floaty` functionality to.
 * @param {object} options - Configuration options.
 * @param {string} options.overlayId - Identifier for the associated overlay.
 * @param {string} options.overlayControls - Pass already existing ``overlayControls``
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
