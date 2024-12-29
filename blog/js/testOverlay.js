
const COLORS = [
  "blue",
  "indigo",
  "purple",
  "pink",
  "red",
  "orange",
  "yellow",
  "green",
  "teal",
  "cyan"
]


function OverlayColorizeTestContent({ color }) {
  const elem = document.createElement("div")
  elem.classList.add("overlay-content-item")
  elem.dataset.colorizeColor = color
  elem.dataset.key = color

  elem.innerHTML = `
    <div class="p-5">
      <h3 class="text-${color}">${color}</h3>
    </div>
  `

  return elem
}

function OverlayColorizeTestButton({ color }) {
  const elem = document.createElement("div")
  elem.type = "button"
  elem.dataset.key = color
  elem.innerText = `Show \`${color}\` Overlay.`

  const colorClass = `text-${color}`
  elem.classList.add(colorClass, "p-3",)

  elem.addEventListener("mouseover", () => {
    elem.classList.remove(colorClass)
    elem.classList.add("text-white")
  })
  elem.addEventListener("mouseout", () => {
    elem.classList.remove("text-white")
    elem.classList.add(colorClass)
  })

  return elem
}


function OverlayColorizeTest({ overlay, controls }) {
  COLORS.map(
    color => {
      const contentItem = OverlayColorizeTestContent({ color })
      overlay.addContent(contentItem)
      overlay.contentItems.appendChild(contentItem)

      const button = OverlayColorizeTestButton({ color })
      controls.appendChild(button)
      button.addEventListener("click", () => {
        overlay.showOverlay()
        overlay.showOverlayContentItem(color)
      })
    }
  )

  return {
    overlay,
    controls
  }
}

