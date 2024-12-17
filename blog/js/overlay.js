const params = new URLSearchParams(window.location.search)
const params_overlay = params.get("overlay") // Identifier for the overlay
const params_overlay_content_item = params.get("overlay-content-item") // key for the overlay content item

// If an overlay is found, add controls.
function Overlay(overlay, { paramsColorize } = { paramsColorize: {} }) {
  if (!overlay.id) throw Error("Overlay missing required `id`.")

  const overlayContent = overlay.querySelector(".overlay-content")
  if (!overlayContent) throw Error("Could not find overlay content.")

  // Create ordered keys and map to keys.
  const state = { length: 0, currentIndex: null, currentKey: null, overlayIsOpen: null }
  const keysToIndices = {}
  const indicesToKeys = {}
  const overlayContentChildren = {}

  Array
    .from(overlayContent.getElementsByClassName("overlay-content-item"))
    .map(addContent)

  /* ----------------------------------------------------------------------- */
  /* Functions that modify state directly */


  function addContent(elem) {
    const key = elem.dataset.key
    if (!key) throw Error(`No key for \`${elem}\`.`)

    indicesToKeys[state.length] = key
    keysToIndices[key] = state.length
    overlayContentChildren[key] = elem

    state.length = state.length + 1
  }

  // Hide the overlay, its content, and all of the content items.
  function hideOverlay(isNotAnimated) {
    overlay.style.opacity = 0
    setTimeout(() => {
      overlay.style.display = "none";
      overlayContent.style.display = "none"
    }, isNotAnimated ? 0 : 300)

    hideOverlayContentItems()

    // Update state.
    state.overlayIsOpen = false
  }

  // Show the overlay without setting content.
  function showOverlay() {
    overlay.style.opacity = 0
    overlay.style.display = "flex";
    overlayContent.style.display = "block";
    setTimeout(() => { overlay.style.opacity = 1 }, 10)

    // Update state.
    state.overlayIsOpen = true
  }

  /* When the page has been refreshed, use params to show the overlay again. */
  function restoreOverlay() {

  }

  // Hide all overlay content.
  function hideOverlayContentItems() {
    Object
      .values(overlayContentChildren)
      .map(child => { child.style.display = 'none' })
  }


  // Hide or display an ``overlay-content-item`` by key.
  function showOverlayContentItem(key) {
    key = key || indicesToKeys[0]
    if (!key) throw Error("Could not determine key.")

    // Hide all.
    hideOverlayContentItems()

    // Show content.
    const content = overlayContentChildren[key]
    if (!content) throw Error(`Could not find content for \`${key}\`.`)
    content.style.display = 'block'

    // Update state.
    state.currentKey = key
    state.currentIndex = keysToIndices[key]

    return content

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

    function nextOverlayContentItem(incr) {
      let nextIndex = (state.currentIndex + incr) % state.length
      if (nextIndex < 0) nextIndex = state.length + nextIndex
      const nextKey = indicesToKeys[nextIndex]

      const contentItem = showOverlayContentItem(nextKey)
      const colorizeParams = {
        color: contentItem.dataset.colorizeColor,
        colorText: contentItem.dataset.colorizeColorText,
        colorTextHover: contentItem.dataset.colorizeColorTextHover,
      }

      colorize(colorizeParams)
    }

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

  function Colorize({ color, colorText, colorTextHover }) {

    const state = {
      // Colors
      color: null, colorPrev: null,
      colorText: null, colorTextPrev: null,
      colorTextHover: null, colorTextHoverPrev: null,

      // Classes
      classBackground: null, classBackgroundPrev: null,
      classBorder: null, classBorderPrev: null,
      classText: null, classTextPrev: null,
      classTextHover: null, classTextHoverPrev: null
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
      controls.classList.remove(state.classBackgroundPrev)
      overlayContent.classList.remove(state.classBorderPrev)
    }

    /* Add current classes */
    function up() {
      navIcons.map(item => item.classList.add(state.classBackground, state.classText))
      controls.classList.add(state.classBackground)
      overlayContent.classList.add(state.classBorder, "border", "border-5")
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

    function mouseOver(event) {
      event.target.classList.remove(state.classText)
      event.target.classList.add(state.classTextHover)
    }
    function mouseOut(event) {
      event.target.classList.remove(state.classTextHover)
      event.target.classList.add(state.classText)
    }

    const navIcons = Array.from(controls.getElementsByTagName("i"))
    initialize()
    restart({ color, colorText, colorTextHover })

    return {
      mouseOut, mouseOver, setColorText, setColor, restart,
      initialize, down, up, setColorTextHover, revert, state
    }
  }

  function colorize({ color, colorText, colorTextHover }) {
    if (!state.colorize) state.colorize = Colorize({ color, colorText, colorTextHover })
    else state.colorize.restart({ color, colorText, colorTextHover })
  }


  colorize(paramsColorize)
  const overlayClosure = { elem: overlay, nav: controls, colorize, hideOverlay, hideOverlayContentItems, showOverlay, showOverlayContentItem, addContent, state }
  hideOverlay(true)
  overlayParamsHook(overlay, overlayClosure)

  return overlayClosure
}


function overlayParamsHook(overlay, overlayClosure) {
  const id = overlay.id
  if (id != params_overlay) return

  overlayClosure.showOverlay()
  overlayClosure.showOverlayContentItem(params_overlay_content_item)
}


// Set up floaty with ``id=name``.
function Floaty(name, { liMargin, kind }) {
  const parent = document.getElementById(name)
  if (!parent) throw Error(`Could not find element with name \`${name}\`.`)

  const floatyContainer = parent.querySelector(".floaty-container")
  if (!floatyContainer) throw Error(`Could not find element with name \`${floatyContainer}\`.`)

  const overlay = parent.querySelector(".overlay")
  const overlayControls = !overlay ? null : Overlay(overlay)
  if (overlay) overlayControls.colorize({ color: "light" })

  function setUpListItem(iconInLi) {
    const size = parseInt(iconInLi.style['font-size'])

    // NOTE: This makes it so that size should always be specified in pixels.
    const li = iconInLi.closest("li")
    if (li) {
      li.style["min-height"] = `${size}px`
      li.style["min-width"] = `${size}px`
      li.style.margin = liMargin || `${(size / 4)}px`
    }

    // NOTE: Icon and its list item should be clickable.
    if (overlay) li.addEventListener("click", onClick(iconInLi))

    // NOTE: Look for a header. If a header is found, wrap the content in a link or div.
    const head = li.querySelector("h3")
    if (!head) return

    head.classList.remove("anchored")
    let wrapper
    if (head.dataset.url) {
      wrapper = document.createElement("a")
      wrapper.href = head.dataset.url
      wrapper.setAttribute('target', '_blank');
      wrapper.setAttribute('rel', 'noopener noreferrer');
    } else {
      wrapper = document.createElement("div")
    }

    wrapper.classList.add("floaty-item-wrapper")
    Array.from(li.children).map((child) => wrapper.append(child))
    li.append(wrapper)
  }

  function onClick(iconOrRow) {
    const key = iconOrRow.dataset.key

    return function() {
      overlayControls.showOverlay()
      overlayControls.showOverlayContentItem(key)
    }
  }

  function setOnClick(icons) {
    // NOTE: It is important that nested does not go beyond its floaty.
    //       Table gets found when nested inside.
    if (kind === "table") {
      const table = parent.querySelector(".floaty-container table")
      if (!table) {
        console.error("No `table` found.")
        return
      }
      icons.map(icon => {
        if (overlay) {
          tr = icon.closest("tr")
          if (!tr) {
            console.error("Expected table row for icon.", icon)
            return
          }
          tr.addEventListener("click", onClick(icon))
        }
      })
    }
    else {
      const ul = parent.querySelector(".floaty-container ul")
      if (!ul) console.error("No `ul` found.")
      icons.map(icon => setUpListItem(icon))
    }
  }


  // NOTE: For now, clicking anywhere on the overlay should hide it.
  const icons = Array.from(floatyContainer.getElementsByTagName("iconify-icon"))
  setOnClick(icons)


  return { icons, overlayControls }
}



