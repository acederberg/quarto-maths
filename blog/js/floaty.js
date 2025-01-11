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

  cards.map(card => {

    if (!card.dataset.floatyUrl) {
      return
    }

    card.addEventListener("click", () => {
      window.open(
        card.dataset.floatyUrl,
        "_blank"
      ).focus()
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



function handleTooltipOnResize() {
  function addDescription(item) {
    const elem = item._element
    item.disable()

    if (!elem.dataset.cardTooltipToggle) return

    // NOTE: Check if card text has been added.
    const textFromResize = Array.from(elem.getElementsByClassName("card-text")).filter(item => item.dataset.cardFromResize != null)
    if (textFromResize.length) return

    // NOTE: Look for a card  body. If there isn't one, make it.
    let body = elem.querySelector(".card-body")
    if (!body) {
      body = document.createElement("div")
      body.classList.add("card-body")
      body.dataset.cardFromResize = true
      elem.appendChild(body)
    }

    // NOTE: Add tooltip as card-text.
    const description = document.createElement("div")
    description.classList.add("card-text")
    description.innerText = elem.dataset.bsTitle
    description.dataset.cardFromResize = true

    body.appendChild(description)
  }

  function removeDescription(item) {
    item.enable()
    const elem = item._element
    if (!elem.dataset.cardTooltipToggle) return

    // NOTE: Find all ``card-text`` children marked with ``cardFromResize`` and remove.
    const textFromResize = Array.from(elem.getElementsByClassName("card-text")).filter(item => item.dataset.cardFromResize != null)
    textFromResize.map(item => item.remove())

    // NOTE: If a card body is marked with ``cardFromResize``, then it should 
    //       be removed.
    const bodyFromResize = Array.from(elem.getElementsByClassName("card-body")).filter(item => item.dataset.cardFromResize != null)
    bodyFromResize.map(item => item.remove())
  }


  function onResize() {
    tooltipList.map(item => {
      window.innerWidth > 1200 ? removeDescription(item) : addDescription(item)
    })
  }

  return { addDescription, removeDescription, onResize }
}
