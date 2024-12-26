function Floaty(elem, { overlayControls, liMargin, kind }) {
  if (!elem) throw Error("Missing required element.")

  // NOTE: Look for the container of the floaty elements.
  const floatyContainer = elem.querySelector(".floaty-container")
  if (!floatyContainer) throw Error(`Could not find element with name \`${floatyContainer}\`.`)

  // NOTE: If ``overlayControls`` are not provided, try to find them.
  if (!overlayControls) {
    FLOATY_VERBOSE && console.log("Looking for overlay.")

    const overlay = elem.querySelector(".overlay")
    overlayControls = overlay ? Overlay(overlay) : null

    FLOATY_VERBOSE && overlayControls && console.log("Overlay controls found.")
  }
  else { FLOATY_VERBOSE && console.log("Not looking for overlay.") }


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
    if (overlayControls) li.addEventListener("click", onClick(iconInLi))

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
      const table = elem.querySelector(".floaty-container table")
      if (!table) {
        console.error("No `table` found.")
        return
      }
      icons.map(icon => {
        if (overlayControls) {
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
      const ul = elem.querySelector(".floaty-container ul")
      if (!ul) console.error("No `ul` found.")
      icons.map(icon => setUpListItem(icon))
    }
  }


  // NOTE: For now, clicking anywhere on the overlay should hide it.
  const icons = Array.from(floatyContainer.getElementsByTagName("iconify-icon"))
  setOnClick(icons)


  return { elem, icons, overlayControls, onClick }
}




