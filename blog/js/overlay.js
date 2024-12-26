const OVERLAY_VERBOSE = false
const FLOATY_VERBOSE = false

function Colorize(overlay, { color, colorText, colorTextHover }) {

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

    // Registry, should be a list of elements and maps to classList
    // registered: []
  }

  /* Update background and border classes for a new color. */
  function setColor(color) {
    state.colorPrev = state.color
    state.classBackgroundPrev = state.classBackground
    state.classBorderPrev = state.classBorder

    state.color = color
    state.classBackground = `bg-${color}`
    state.classBorder = `border-${color}`
  }

  /* Update text classes for a new color */
  function setColorText(color) {
    state.colorTextPrev = state.colorText
    state.classTextPrev = state.classText

    state.colorText = color
    state.classText = `text-${color}`
  }

  function setColorTextHover(color) {
    state.colorTextHoverPrev = state.colorTextHover
    state.classTextHover = state.classTextHoverPrev

    state.colorTextHover = color
    state.classTextHover = `text-${color}`
  }

  /* Remove previous classes */
  function down() {
    navIcons.map(item => item.classList.remove(state.classBackgroundPrev, state.classTextPrev))
    overlay.nav.classList.remove(state.classBackgroundPrev)
    overlay.content.classList.remove(state.classBorderPrev)
  }

  /* Add current classes */
  function up() {
    navIcons.map(item => item.classList.add(state.classBackground, state.classText))
    overlay.nav.classList.add(state.classBackground)
    overlay.content.classList.add(state.classBorder, "border", "border-5")

    // state.registered.map(registeredItem => updateElem(registeredItem))
  }

  /* Only call this once. */
  function initialize() {
    navIcons.map(item => {
      item.addEventListener("mouseover", mouseOver)
      item.addEventListener("mouseout", mouseOut)
    })
  }

  /* Like revert, but with parameters. */
  function restart({ color, colorText, colorTextHover }) {
    if (color) setColor(color)
    if (colorText) setColorText(colorText)
    if (colorTextHover) setColorTextHover(colorTextHover)

    down()
    up()
  }

  /* Should toggle between current state and last state. */
  function revert() {
    if (state.colorPrev) setColor(state.colorPrev)
    if (state.colorTextPrev) setColorText(state.colorTextPrev, state.colorText)
    if (state.colorTextHoverPrev) setColorTextHover(state.colorTextHoverPrev, state.colorTextHover)

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

  /*
    This should be executed against registed elements in state.
  */
  function updateElem(elem, mkClasses) {
    return () => {
      const classes = mkClasses(state.color)
      const classesPrev = mkClasses(state.colorPrev)

      elem.classList.remove(...classesPrev)
      elem.classList.add(...classes)
    }
  }

  function mouseOver(event) {
    event.target.classList.remove(state.classText)
    event.target.classList.add(state.classTextHover)
  }
  function mouseOut(event) {
    event.target.classList.remove(state.classTextHover)
    event.target.classList.add(state.classText)
  }

  const navIcons = Array.from(overlay.nav.getElementsByTagName("i"))
  initialize()
  restart({ color, colorText, colorTextHover })

  return {
    mouseOut, mouseOver, setColorText, setColor, restart, initialize, down,
    up, setColorTextHover, revert, state, updateElem,
  }
}

function Overlay(overlay, { paramsColorize } = { paramsColorize: {} }) {
  // NOTE: Veryify structure of overlay. It should require an id and seequence
  //       of children ``.overlay-content`` and ``.overlay-content-items``.
  if (!overlay.id) throw Error("Overlay missing required `id`.")

  const overlayContent = overlay.querySelector(".overlay-content")
  const overlayContentItems = overlayContent.querySelector(".overlay-content-items")

  if (!overlayContent) throw Error(`Could not find overlay content for \`${overlay.id}\`.`)
  if (!overlayContentItems) throw Error(`Could not find overlay content items for \`${overlay.id}\`.`)

  // NOTE: Create ordered keys and map to keys.
  const state = { length: 0, currentIndex: null, currentKey: null, overlayIsOpen: null }
  const keysToIndices = {}
  const indicesToKeys = {}
  const overlayContentChildren = {}

  Array
    .from(overlayContent.getElementsByClassName("overlay-content-item"))
    .map(addContent)

  /* ----------------------------------------------------------------------- */
  /* Functions that modify state directly */


  /* Because changing heights is ugly as hell */
  function fixIconSizes(contentItem) {
    Array.from(contentItem.getElementsByTagName("iconify-icon")).map(
      item => {
        if (!item.style.fontSize) return

        item.style.height = item.style.fontSize
        item.style.width = item.style.fontSize
      }
    )
  }

  /* Assumes that `elem`  has been appended independently. */
  function addContent(elem) {
    const key = elem.dataset.key
    if (!key) throw Error(`No key for \`${elem}\`.`)

    indicesToKeys[state.length] = key
    keysToIndices[key] = state.length
    overlayContentChildren[key] = elem
    fixIconSizes(elem)

    state.length = state.length + 1
  }

  // Hide the overlay, its content, and all of the content items.
  function hideOverlay({ isNotAnimated, keepLocalStorage } = {}) {
    OVERLAY_VERBOSE && console.log(`Hiding overlay \`${overlay.id}\`.`)
    overlay.style.opacity = 0
    setTimeout(() => {
      overlay.classList.add("hidden")
      overlayContent.classList.add("hidden")
    }, isNotAnimated ? 0 : 300)

    hideOverlayContentItems({ keepLocalStorage: keepLocalStorage })

    // Update state.
    state.overlayIsOpen = false
    state.currentKey = null
    state.currentIndex = null

    if (!keepLocalStorage) {
      OVERLAY_VERBOSE && console.log("`hideOverlay` Removing")
      window.localStorage.removeItem("overlayId")
    }
  }

  // Show the overlay without setting content.
  function showOverlay() {
    OVERLAY_VERBOSE && console.log(`Showing overlay \`${overlay.id}\`.`)
    overlay.style.opacity = 0

    overlay.style.display = "flex";

    overlay.classList.remove("hidden")
    overlayContent.classList.remove("hidden")
    setTimeout(() => { overlay.style.opacity = 1 }, 10)

    // Update state.
    state.overlayIsOpen = true
    window.localStorage.setItem("overlayId", overlay.id)
  }

  /* When the page has been refreshed, use session storage to show the overlay again. */
  function restoreOverlay() {
    if (window.localStorage.getItem("overlayKey") && (window.localStorage.getItem("overlayId") != overlay.id)) { return }

    const key = window.localStorage.getItem("overlayKey")
    let overlayContentItem = null
    try { overlayContentItem = showOverlayContentItem(key, { isNotAnimated: true, keepLocalStorage: true }) }
    catch {
      console.error(`Failed to find content item \`${key}\` of \`${overlay.id}\` while restoring overlay.`)
      return
    }
    finally {
      if (overlayContentItem) showOverlay()
    }
  }

  // Hide all overlay content.
  function hideOverlayContentItems({ keepLocalStorage } = {}) {
    OVERLAY_VERBOSE && console.log(`Hiding overlay \`${overlay.id}\` content items.`)
    Object
      .values(overlayContentChildren)
      .map(child => { child.classList.add("hidden") })


    if (!keepLocalStorage) {
      OVERLAY_VERBOSE && console.log(`Removing \`overlayKey\` \`hideOverlayContentItems\`.`)
      window.localStorage.removeItem("overlayKey")
    }
  }


  // Hide or display an ``overlay-content-item`` by key.
  function showOverlayContentItem(key, { keepLocalStorage } = {}) {
    key = key || indicesToKeys[0]
    if (!key) throw Error("Could not determine key.")

    OVERLAY_VERBOSE && console.log(`Showing overlay \`${overlay.id}\` content item \`${key}\`.`)

    // Hide all.
    hideOverlayContentItems({ keepLocalStorage: keepLocalStorage })

    // Show content.
    const content = overlayContentChildren[key]
    if (!content) {
      console.error(`Could not find content for \`key=${key}\` and \`id=${overlay.id}\`.`)
      return
    }

    // NOTE: Do slidey transition if the overlay is already open (and there is more than one item, and the overlay is already open).
    const oldKey = state.currentKey
    const oldContent = overlayContentChildren[oldKey]

    console.log(JSON.stringify(state, null, 2))
    if (oldContent && (oldKey != key)) {

      // NOTE: Put old in middle and new on left of it.
      oldContent.classList.add("slide-b")
      oldContent.classList.remove("hidden")

      content.classList.add("slide-a")
      content.classList.remove("hidden")
      overlayContentItems.insertBefore(content, oldContent)



      // NOTE: Wait for content to be shown, then remove the classes.
      // NOTE: Put middle to right and left to middle
      setTimeout(() => {
        oldContent.classList.add("slide-c")
        oldContent.classList.remove("slide-b")

        content.classList.add("slide-b")
        content.classList.remove("slide-a")
      }, 100)

      // NOTE: When transition is over, remove all classes.
      setTimeout(() => {
        oldContent.classList.remove("slide-c")
        oldContent.classList.add("hidden")
        content.classList.remove("slide-b")
        if (state.colorize) colorizeContentItem(content)
      }, 100)

    } else {
      content.classList.remove("hidden")
      if (state.colorize) colorizeContentItem(content)
    }




    ////////////////////////////


    // Update state.
    state.currentKey = key
    state.currentIndex = keysToIndices[key]

    OVERLAY_VERBOSE && console.log(`Setting \`overlayKey\` to \`${key}\` in \`showOverlayContentItec\`.`)
    window.localStorage.setItem("overlayKey", key)

    return content

  }

  function nextOverlayContentItem(incr) {
    let nextIndex = (state.currentIndex + incr) % state.length
    if (nextIndex < 0) nextIndex = state.length + nextIndex
    const nextKey = indicesToKeys[nextIndex]

    showOverlayContentItem(nextKey)
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

    exit.addEventListener("click", () => hideOverlay(0))
    left.addEventListener("click", () => nextOverlayContentItem(-1))
    right.addEventListener("click", () => nextOverlayContentItem(1))
    overlay.addEventListener("click", (event) => {
      if (event.target.id !== overlay.id) return
      hideOverlay()
    })
  }

  /*
  if ( includeFullscreenControls ){
    const fullscreenControlsId = `${overlay.id}-controls-fullscreen`
    let fullscreenControls = document.getElementById(fullscreenControlsId)

    if (!fullscreenControls){
      fullscreenControls = document.createElement("nav")
      // const fullscreen = document.createElement("i"); const minimize = document.createElement("i")
      // fullscreen.classList.add("bi-arrows-fullscreen", "overlay-controls-item", "px-5")
      // minimize.classList.add("bi-fullscreen-exit", "overlay-controls-item", "px-5")
      // controls.appendChild(fullscreen); controls.appendChild(minimize);
    }
  }
  */


  function colorize({ color, colorText, colorTextHover }) {
    if (!state.colorize) state.colorize = Colorize(overlayClosure, { color, colorText, colorTextHover })
    else state.colorize.restart({ color, colorText, colorTextHover })
  }


  function colorizeContentItem(contentItem) {
    OVERLAY_VERBOSE && console.log("Colorize overlay from contentitem dataet.")
    const colorizeParams = {
      color: contentItem.dataset.colorizeColor,
      colorText: contentItem.dataset.colorizeColorText,
      colorTextHover: contentItem.dataset.colorizeColorTextHover,
    }

    colorize(colorizeParams)
  }

  const overlayClosure = { elem: overlay, content: overlayContent, contentItems: overlayContentItems, nav: controls, colorize, hideOverlay, hideOverlayContentItems, showOverlay, showOverlayContentItem, addContent, state, restoreOverlay, nextOverlayContentItem }

  colorize(paramsColorize)
  Array.from(overlayContentItems.getElementsByClassName(".overlay-content-item")).map(fixIconSizes)
  restoreOverlay()

  return overlayClosure
}
