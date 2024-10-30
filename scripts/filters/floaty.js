function Overlay(name) {
  let parent = document.getElementById(name)
  let overlay = Array.from(parent.getElementsByClassName("overlay"))[0]
  let overlay_content = Array.from(parent.getElementsByClassName("overlay-content"))[0]

  if (!overlay) { console.error(`Could not find overlay for \`${name}\`.`) }
  if (!overlay_content) { console.error(`Could not find overlay_content for \`${name}\`.`) }

  function hideOverlay(name) {
    overlay.style.display = "none";
    overlay_content.style.display = "none"
  }

  function showOverlay(name) {
    overlay.style.display = "flex";
    overlay_content.style.display = "block";
  }

  // NOTE: For now, clicking anywhere on the overlay should hide it.
  hideOverlay(name)
  parent.addEventListener("click", hideOverlay)

  return { hideOverlay, showOverlay, overlay, overlay_content }
}

let overlay = Overlay("thank-you-tools")

