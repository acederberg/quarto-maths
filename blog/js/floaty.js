function Floaty(elem, { overlayControls }) {
  if (!elem) throw Error("Missing required element.")

  // NOTE: Look for the container of the floaty elements.
  const floatyContainer = elem.querySelector(".floaty-container")
  if (!floatyContainer) throw Error(`Could not find element with name \`${floatyContainer}\`.`)

  // NOTE: For now, clicking anywhere on the overlay should hide it.
  const cards = Array.from(floatyContainer.getElementsByClassName("card"))
  if (overlayControls) cards.map(card => {
    card.addEventListener("click", () => {
      overlayControls.showOverlay()
      overlayControls.showOverlayContentItem(card.dataset.key)
    })
  })

  return { elem, cards, overlayControls }
}


function lazyFloaty(elemId, { overlayId, overlayControls }) {
  const elem = document.getElementById(elemId)
  if (!elem) console.error(`Could not find element with id \`${elemId}\`.`)

  if (overlayId && !overlayControls) {
    const overlay = document.getElementById(overlayId)
    overlayControls = overlay ? Overlay(overlay) : null
  }

  return Floaty(elem, { overlayControls })
}




