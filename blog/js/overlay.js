const params = new URLSearchParams(window.location.search)
const params_overlay = params.get("overlay")
const params_overlay_content_item = params.get("overlay-content-item")

// If an overlay is found, add controls.
function Overlay(overlay) {
  if (!overlay.id) throw Error("Overlay missing required `id`.")

  const overlayContent = overlay.querySelector(".overlay-content")
  if (!overlayContent) throw Error("Could not find overlay content.")

  // Create ordered keys and map to keys.
  const keysToIndices = {}
  const indicesToKeys = {}
  const overlayContentChildren = {}

  let length = 0
  Array
    .from(overlayContent.getElementsByClassName("overlay-content-item"))
    .map(function(elem, index) {
      const key = elem.dataset.key

      indicesToKeys[index] = key
      keysToIndices[key] = index
      overlayContentChildren[key] = elem

      length = length + 1
    })

  /* ----------------------------------------------------------------------- */
  /* Functions that modify state directly */

  const state = { currentIndex: null, currentKey: null, overlayIsOpen: null }

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

  // Hide all overlay content.
  function hideOverlayContentItems() {
    Object
      .values(overlayContentChildren)
      .map(child => { child.style.display = 'none' })
  }


  // Hide or display an ``overlay-content-item`` by key.
  function showOverlayContentItem(key) {
    key = key || indicesToKeys[0]

    // Hide all.
    hideOverlayContentItems()

    // Show content.
    const content = overlayContentChildren[key]
    if (!content) throw Error(`Could not find content for \`${key}\`.`)
    content.style.display = 'block'

    // Update state.
    state.currentKey = key
    state.currentIndex = keysToIndices[key]

  }

  /* ----------------------------------------------------------------------- */
  /* Add listeners in a navbar. */

  const controls = document.createElement("nav");
  const exit = document.createElement('i'); const left = document.createElement('i'); const right = document.createElement('i')
  // const next_overlay = document.createElement("i")
  // const prev_overlay = document.createElement("i")

  controls.appendChild(left); controls.appendChild(right);
  // controls.appendChild(prev_overlay); controls.appendChild(next_overlay);
  controls.appendChild(exit)

  controls.classList.add('overlay-controls', 'p-1')
  // prev_overlay.classList.add("bi-chevron-bar-left", 'overlay-controls-item', 'px-1', 'overlay-controls-left')
  left.classList.add('bi-chevron-left', 'overlay-controls-item', 'px-1', 'overlay-controls-left')
  right.classList.add('bi-chevron-right', 'overlay-controls-item', 'px-1', 'overlay-controls-right')
  // next_overlay.classList.add("bi-chevron-bar-right", 'overlay-controls-item', 'px-1', 'overlay-controls-left')
  exit.classList.add('bi-x-lg', 'overlay-controls-item', 'overlay-controls-exit', 'px-1')

  overlayContent.insertBefore(controls, overlayContent.children[0])

  function nextOverlayContentItem(incr) {
    let nextIndex = (state.currentIndex + incr) % length
    if (nextIndex < 0) nextIndex = length + nextIndex
    const nextKey = indicesToKeys[nextIndex]

    showOverlayContentItem(nextKey)
  }

  exit.addEventListener("click", () => hideOverlay(0))
  left.addEventListener("click", () => nextOverlayContentItem(-1))
  right.addEventListener("click", () => nextOverlayContentItem(1))
  overlay.addEventListener("click", (event) => {
    if (event.target.id !== overlay.id) return
    hideOverlay()
  })

  const overlayClosure = { hideOverlay, hideOverlayContentItems, showOverlay, showOverlayContentItem }
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

    // NOTE: Look for a header. If a header is found, 
    const head = li.querySelector("h3")
    if (!head) return

    head.classList.remove("anchored")
    console.log(head.dataset.url)

    let wrapper
    if (head.dataset.url) {
      wrapper = document.createElement("a")
      wrapper.href = head.dataset.url
    }
    else {
      wrapper = document.createElement("div")
    }

    wrapper.classList.add("floaty-item-wrapper")

    Array.from(li.children).map((child) => {
      wrapper.append(child)
    })

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



