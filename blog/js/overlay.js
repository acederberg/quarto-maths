// @ts-check
/** @module overlay */

/** @type {Map<string, TOverlay>} */
export const OverlayInstances = new Map()
const COLORIZE_VERBOSE = false
const OVERLAY_VERBOSE = false
const OVERLAY_ITEM_TRANSFORMATION_DELAY = 10
const OVERLAY_ITEM_TRANSFORMATION_TIME = 500

// ------------------------------------------------------------------------- //
// TYPES

/** @namespace overlay */
/** 
 * @typedef {object} TOverlay
 *
 * @property {HTMLElement} elem - Outmost overlay element.
 * @property {Element} overlayContent - Overlay content element, should contain content items and navbar.
 * @property {Element} overlayContentItems - Container for content.
 * @property {HTMLElement} controls -
 *
 * @property {Map<string, number>} keysToIndices
 * @property {Map<number, string>} indicesToKeys
 *
 * @property {THideOverlay} hideOverlay - Hide the overlay, its content, and all of the content items.
 * @property {THideOverlayContentItems} hideOverlayContentItems - Hide all overlay content items.
 * @property {TShowOverlay} showOverlay - Show the overlay (but not a content item).
 * @property {TShowOverlayContentItem} showOverlayContentItem - Show a content item by key.
 * @property {TAddContent} addContent - Add a page to the overlay.
 * @property {TRestoreOverlay} restoreOverlay - When the page has been refreshed, use session storage to show the overlay again. 
 * @property {TNextOverlayContentItem} nextOverlayContentItem - Show overlay content items.
 * @property {(contentItem: HTMLElement) => void} colorizeContentItem
 * @property {(colorize: Partial<TColorizeOptions>) => void} colorize
 *
 * @property {TOverlayState} state
 */

/**
 * @callback TShowOverlayContentItem
 *
 * @param {string} key - `data-key` for the content item.
 * @param {Partial<TShowOverlayContentItemOptions>} [options]
 *
 * @returns {HTMLElement|null}
 *
 */
/**
 * @typedef {object} TShowOverlayContentItemOptions
 *
 * @property {boolean} [keepLocalStorage]
 * @property {boolean} [isAnimated]
 * @property {boolean} [animationToRight]
 */

/**
 * @callback THideOverlayContentItems
 *
 * @param {Partial<THideOverlayContentItemsOptions>} [options]
 * @returns {void}
 */
/**
 * @typedef THideOverlayContentItemsOptions
 *
 * @property {boolean} [keepLocalStorage]
 */

/**
 * @callback TAddContent
 *
 * @param {HTMLElement} elem - Element to add to overlay.
 * @returns {void}
 *
 */

/**
 *
 * @callback THideOverlay
 *
 * @param {Partial<THideOverlayOptions>} [options]
 * @returns {void}
 */
/**
 * @typedef THideOverlayOptions
 *
 * @property {boolean} [isNotAnimated]
 * @property {boolean} [keepLocalStorage]
 *
 */

/**
 *
 * @callback TRestoreOverlay
 *
 * @returns {void}
 */

/**
 * @callback TShowOverlay
 *
 * @returns {void}
 */

/** 
 *
 * @callback TNextOverlayContentItem
 *
 * @param {number} incr - Number of pages to move over.
 * @returns {void}
 */


/** State for the `Overlay` closure.
 *
 * @typedef TOverlayState
 *
 * @property {number} length - The total number of content items.
 * @property {number|null} currentIndex - The current index of the item displayed in the overlay.
 * @property {string|null} currentKey - The current key of the item display in the overlay.
 * @property {boolean|null} overlayIsOpen - Is the overlay open or not.
 * @property {TColorize|null} colorize - Colorize tool.
 */


/** @namespace colorize */

/**
 * @typedef TColorizeState
 *
 * @property {string|null} color
 * @property {string|null} colorPrev
 * @property {string|null} colorText
 * @property {string|null} colorTextPrev
 * @property {string|null} colorTextHover
 * @property {string|null} colorTextHoverPrev
 * @property {string|null} classBackground
 * @property {string|null} classBackgroundPrev
 * @property {string|null} classBorder
 * @property {string|null} classBorderPrev
 * @property {string|null} classText
 * @property {string|null} classTextPrev
 * @property {string|null} classTextHover
 * @property {string|null} classTextHoverPrev
*/

/**
 * @typedef TColorizeOptions
 *
 * @property {string|null} color
 * @property {string|null} colorText
 * @property {string|null} colorTextHover
 *
 */

/**
 * @callback TColorizeSetter
 *
 * @param {string} color
 * @returns void
 */

/**
 * @namespace colorize
 * @callback TUpdateElement
 *
 * @param {HTMLElement} elem
 * @param {(color: string|null) => string[]} mkClasses
 *
 */

/**
 * @typedef TColorize
 *
 * @property {TColorizeSetter} setColorText - Update text classes for a new color.
 * @property {TColorizeSetter} setColor - Update background and border classes for a new color.
 * @property {TColorizeSetter} setColorTextHover - Update the color of text when hovered.
 * @property {(options: Partial<TColorizeOptions>) => void} restart - Start again with provided options.
 * @property {() => void} initialize
 * @property {() => void} down - Remove previous classes.
 * @property {() => void} up - Add current classes.
 * @property {() => void} revert
 * @property {TUpdateElement} updateElem
 * @property {(event: Event) => void} mouseOut
 * @property {(event: Event) => void} mouseOver
 * @property {TColorizeState} state
 */


/**
 * Tool for setting overlay color.
 * This should be simplified later using ``scss``.
 *
 * @param {TOverlay} overlay - Overlay instance on which colorization will take effect.
 * @param {Partial<TColorizeOptions>} options - Options for colorize.
 *
 * @returns {TColorize}
 */
export function Colorize(overlay, { color, colorText, colorTextHover }) {

  COLORIZE_VERBOSE && console.log(`Creating colorize for overlay with id \`${overlay.elem.id}\`.`)

  /** @type {TColorizeState} */
  const state = {
    // Colors
    color: null, colorPrev: null,
    colorText: null, colorTextPrev: null,
    colorTextHover: null, colorTextHoverPrev: null,

    // Classes
    classBackground: null, classBackgroundPrev: null,
    classBorder: null, classBorderPrev: null,
    classText: null, classTextPrev: null,
    classTextHover: null, classTextHoverPrev: null,
  }


  /** @type {TColorizeSetter} */
  function setColor(color) {
    state.colorPrev = state.color
    state.classBackgroundPrev = state.classBackground
    state.classBorderPrev = state.classBorder

    state.color = color
    state.classBackground = `bg-${color}`
    state.classBorder = `border-${color}`
  }

  /** @type {TColorizeSetter} */
  function setColorText(color) {
    state.colorTextPrev = state.colorText
    state.classTextPrev = state.classText

    state.colorText = color
    state.classText = `text-${color}`
  }

  /** @type {TColorizeSetter} */
  function setColorTextHover(color) {
    state.colorTextHoverPrev = state.colorTextHover
    state.classTextHover = state.classTextHoverPrev

    state.colorTextHover = color
    state.classTextHover = `text-${color}`
  }

  function down() {
    COLORIZE_VERBOSE && console.log(`Removing colorize classes for \`${overlay.elem.id}\`.`)

    navIcons.map(item => {
      state.classBackgroundPrev && item.classList.remove(state.classBackgroundPrev)
      state.classTextPrev && item.classList.remove(state.classTextPrev)
    })
    state.classBackgroundPrev && overlay.controls.classList.remove(state.classBackgroundPrev)
    state.classBorderPrev && overlay.overlayContent.classList.remove(state.classBorderPrev)
  }

  function up() {
    COLORIZE_VERBOSE && console.log(`Setting colorize classes for \`${overlay.elem.id}\`.`)

    navIcons.map(item => {
      state.classBackground && item.classList.add(state.classBackground)
      state.classText && item.classList.add(state.classText)
    })
    state.classBackground && overlay.controls.classList.add(state.classBackground)
    state.classBorder && overlay.overlayContent.classList.add(state.classBorder, "border", "border-5")
  }

  function initialize() {
    navIcons.map(item => {
      item.addEventListener("mouseover", mouseOver)
      item.addEventListener("mouseout", mouseOut)
    })
  }

  /** @type {(options: Partial<TColorizeOptions>) => void} */
  function restart({ color, colorText, colorTextHover }) {
    if (color) setColor(color)
    if (colorText) setColorText(colorText)
    if (colorTextHover) setColorTextHover(colorTextHover)

    down()
    up()
  }

  function revert() {
    if (state.colorPrev) setColor(state.colorPrev)
    if (state.colorTextPrev) setColorText(state.colorTextPrev)
    if (state.colorTextHoverPrev) setColorTextHover(state.colorTextHoverPrev)

    down()
    up()
  }

  /*
    ``elem`` should be the element to update.
    ``mkClass`` should take ``state` and create an array of classes.

    Problem is that this will update every registered item.

    function registerElem(elem, mkClass) {
      state.registered.append({ elem, mkClass })
    }
  */

  /** @type TUpdateElement */
  function updateElem(elem, mkClasses) {
    return () => {
      const classes = mkClasses(state.color)
      const classesPrev = mkClasses(state.colorPrev)

      elem.classList.remove(...classesPrev)
      elem.classList.add(...classes)
    }
  }


  /** @param {Event} event */
  function mouseOver(event) {
    if (!event.target) return

    // @ts-ignore
    event.target.classList.remove(state.classText)

    // @ts-ignore
    event.target.classList.add(state.classTextHover)
  }

  /** @param {Event} event */
  function mouseOut(event) {
    if (!event.target) return

    // @ts-ignore
    event.target.classList.remove(state.classTextHover)

    // @ts-ignore
    event.target.classList.add(state.classText)
  }


  const navIcons = Array.from(overlay.controls.getElementsByTagName("i"))
  initialize()
  restart({ color, colorText, colorTextHover })

  return {
    mouseOut, mouseOver,
    setColorText, setColor, setColorTextHover,
    restart, initialize, down,
    up, revert, state, updateElem,
  }
}


/**
 * @param {HTMLElement} overlay
 * @param {object} options
 * @param {Partial<TColorizeOptions>} options.colorizeOptions
 * @returns {TOverlay}
 */
export function Overlay(overlay, { colorizeOptions } = { colorizeOptions: {} }) {
  if (!overlay.id) throw Error("Overlay missing required `id`.")

  const overlayContent = overlay.querySelector(".overlay-content")
  if (!overlayContent) throw Error(`Could not find overlay content for \`${overlay.id}\`.`)

  const overlayContentItems = overlayContent.querySelector(".overlay-content-items")
  if (!overlayContentItems) throw Error(`Could not find overlay content items for \`${overlay.id}\`.`)

  // NOTE: Create ordered keys and map to keys.

  /** @type {TOverlayState} */
  const state = { length: 0, currentIndex: null, currentKey: null, overlayIsOpen: null, colorize: null }

  /** @type {Map<string, number>} */
  const keysToIndices = new Map()

  /** @type {Map<number, string>} */
  const indicesToKeys = new Map()

  /** @type {Map<string, HTMLElement>} */
  const overlayContentChildren = new Map()

  // @ts-ignore
  Array.from(overlayContent.getElementsByClassName("overlay-content-item")).map(addContent)


  /** @type {TAddContent} */
  function addContent(elem) {
    const key = elem.dataset.key
    if (!key) throw Error(`No key for \`${elem}\`.`)

    indicesToKeys.set(state.length, key)
    keysToIndices.set(key, state.length)
    overlayContentChildren.set(key, elem)

    state.length = state.length + 1
  }


  /** @type {THideOverlay} */
  function hideOverlay({ isNotAnimated, keepLocalStorage } = {}) {
    OVERLAY_VERBOSE && console.log(`Hiding overlay \`${overlay.id}\`.`)
    overlay.style.opacity = '0'
    setTimeout(() => {
      overlay.classList.add("hidden")
      // @ts-ignore
      overlayContent.classList.add("hidden")
    }, isNotAnimated ? 0 : 300)

    hideOverlayContentItems({ keepLocalStorage })

    // Update state.
    state.overlayIsOpen = false
    state.currentKey = null
    state.currentIndex = null

    if (!keepLocalStorage) {
      OVERLAY_VERBOSE && console.log("`hideOverlay` removing `overlayId`.")
      window.localStorage.removeItem("overlayId")
    }
  }


  /** @type {TShowOverlay} */
  function showOverlay() {
    OVERLAY_VERBOSE && console.log(`Showing overlay \`${overlay.id}\`.`)

    overlay.style.opacity = '0'
    overlay.style.display = "flex";
    overlay.classList.remove("hidden")
    // @ts-ignore
    overlayContent.classList.remove("hidden")
    setTimeout(() => { overlay.style.opacity = '1' }, 10)

    // Update state.
    state.overlayIsOpen = true
    window.localStorage.setItem("overlayId", overlay.id)
  }


  /** @type {TRestoreOverlay} */
  function restoreOverlay() {
    if (!window.localStorage.getItem("overlayKey") || (window.localStorage.getItem("overlayId") != overlay.id)) { return }

    const key = window.localStorage.getItem("overlayKey")
    if (!key) return
    let overlayContentItem = null
    try { overlayContentItem = showOverlayContentItem(key, { isAnimated: false, keepLocalStorage: true }) }
    catch {
      console.error(`Failed to find content item \`${key}\` of \`${overlay.id}\` while restoring overlay.`)
      return
    }
    finally {
      if (overlayContentItem) showOverlay()
    }
  }


  /** @type {THideOverlayContentItems} */
  function hideOverlayContentItems({ keepLocalStorage } = { keepLocalStorage: false }) {

    Array.from(overlayContentChildren.values()).map(child => {
      child.classList.add("hidden")
    })



    if (!keepLocalStorage) {
      OVERLAY_VERBOSE && console.log(`Removing \`overlayKey\` \`hideOverlayContentItems\`.`)
      window.localStorage.removeItem("overlayKey")
    }
  }


  /** @type {TShowOverlayContentItem} */
  function showOverlayContentItem(key, { keepLocalStorage, isAnimated, animationToRight } = {
    isAnimated: true,
    animationToRight: true,
  }) {
    // NOTE: Defaults and verify that anything actually needs to change.
    isAnimated = isAnimated === null ? true : isAnimated
    animationToRight = animationToRight === null ? true : animationToRight

    const slideyClasses = ["slide-a", "slide-b", "slide-c"]
    const slideyClassesReverse = ["slide-c", "slide-b", "slide-a"]

    // @ts-ignore
    key = key || indicesToKeys.get(0)
    if (!key) throw Error("Could not determine key.")

    const oldKey = state.currentKey
    const content = overlayContentChildren.get(key)

    if (!content) {
      console.error(`Could not find content for \`key=${key}\` and \`id=${overlay.id}\`.`)
      return null
    }

    if (key == oldKey) {
      state.colorize && colorizeContentItem(content)
      return null
    }

    OVERLAY_VERBOSE && console.log(`Showing overlay \`${overlay.id}\` content item \`${key}\`.`)

    // NOTE: Hide all content items. Find the content item to display.
    hideOverlayContentItems({ keepLocalStorage: keepLocalStorage })

    // NOTE: Do slidey transition if the overlay is already open (and there is more than one item, and the overlay is already open).
    const oldContent = oldKey ? overlayContentChildren.get(oldKey) : null
    if (oldContent && (oldKey != key) && isAnimated) {

      const [slideRight, slideCenter, slideLeft] = animationToRight ? slideyClasses : slideyClassesReverse

      // NOTE: Put old in middle and new on left of it.
      oldContent.classList.add(slideCenter)
      oldContent.classList.remove("hidden")

      content.classList.add(slideLeft)
      content.classList.remove("hidden")
      // @ts-ignore
      overlayContentItems.insertBefore(content, oldContent)

      // NOTE: Wait for content to be shown, then remove the classes.
      // NOTE: Put middle to right and left to middle
      setTimeout(() => {
        oldContent.classList.add(slideRight)
        oldContent.classList.remove(slideCenter)

        content.classList.add(slideCenter)
        content.classList.remove(slideLeft)
        if (state.colorize) colorizeContentItem(content)

        // NOTE: When transition is over, remove all classes.
        setTimeout(() => {
          oldContent.classList.remove(slideRight)
          oldContent.classList.add("hidden")
          content.classList.remove(slideCenter)
        }, OVERLAY_ITEM_TRANSFORMATION_TIME)

      }, OVERLAY_ITEM_TRANSFORMATION_DELAY)


    } else {
      content.classList.remove("hidden")
      if (state.colorize) colorizeContentItem(content)
    }

    // Update state.
    state.currentKey = key
    state.currentIndex = keysToIndices.get(key) || null

    OVERLAY_VERBOSE && console.log(`Setting \`overlayKey\` to \`${key}\` in \`showOverlayContentItec\`.`)
    window.localStorage.setItem("overlayKey", key)

    return content

  }

  /** @type {TNextOverlayContentItem} */
  function nextOverlayContentItem(incr) {
    const currentIndex = state.currentIndex || 0
    let nextIndex = (currentIndex + incr) % state.length
    if (nextIndex < 0) nextIndex = state.length + nextIndex
    const nextKey = indicesToKeys.get(nextIndex)

    if (nextKey && currentIndex != nextIndex) showOverlayContentItem(nextKey, { isAnimated: true, animationToRight: incr > 0 })
  }

  /** @param {Partial<TColorizeOptions>} options */
  function colorize({ color, colorText, colorTextHover } = {}) {
    if (!state.colorize) state.colorize = Colorize(overlayClosure, { color, colorText, colorTextHover })
    else state.colorize.restart({ color, colorText, colorTextHover })
  }


  /** @param {HTMLElement} contentItem */
  function colorizeContentItem(contentItem) {
    COLORIZE_VERBOSE && console.log("Colorize overlay from contentitem dataet.")
    const colorizeParams = {
      color: contentItem.dataset.colorizeColor,
      colorText: contentItem.dataset.colorizeColorText,
      colorTextHover: contentItem.dataset.colorizeColorTextHover,
    }

    colorize(colorizeParams)
  }

  /* ----------------------------------------------------------------------- */
  /* Add listeners in a navbar. */

  // NOTE: In some cases (e.g. the dev page) this is called twice.
  const controlsId = `${overlay.id}-controls`
  let controls = document.getElementById(controlsId)

  if (!controls) {
    controls = document.createElement("nav");
    controls.id = controlsId

    const exit = document.createElement('i'); const left = document.createElement('i'); const right = document.createElement('i')
    controls.appendChild(left); controls.appendChild(right);
    controls.appendChild(exit);

    controls.classList.add('overlay-controls', 'p-1')
    left.classList.add('bi-chevron-left', 'overlay-controls-item', 'px-1', 'overlay-controls-left')
    right.classList.add('bi-chevron-right', 'overlay-controls-item', 'px-1', 'overlay-controls-right')
    exit.classList.add('bi-x-lg', 'overlay-controls-item', 'overlay-controls-exit', 'px-1')

    overlayContent.insertBefore(controls, overlayContent.children[0])

    hideOverlay()
    exit.addEventListener("click", () => hideOverlay())
    left.addEventListener("click", () => nextOverlayContentItem(-1))
    right.addEventListener("click", () => nextOverlayContentItem(1))
    overlay.addEventListener("click", (event) => {
      // @ts-ignore
      if (event.target.id !== overlay.id) return
      hideOverlay()
    })
  }

  /** @type {TOverlay} */
  const overlayClosure = {
    elem: overlay, overlayContent: overlayContent, overlayContentItems,
    controls: controls, colorize, hideOverlay, hideOverlayContentItems, showOverlay,
    colorizeContentItem,
    showOverlayContentItem, addContent, state, restoreOverlay, nextOverlayContentItem,
    keysToIndices, indicesToKeys,

  }


  colorize(colorizeOptions)
  restoreOverlay()

  OverlayInstances.set(overlay.id, overlayClosure)
  return overlayClosure
}


