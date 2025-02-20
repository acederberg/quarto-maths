
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

  elem.innerText = `
    <div class="p-5 text-${color}">
      <h3>This page should be colorized as <code>${color}</code></h3>
    </div>
  `

  return elem
}

function OverlayColorizeTestButton({ color }) {
  const elem = document.createElement("button")
  elem.classList.add("btn", `btn-outline`)
  elem.type = "button"
  elem.dataset.key = color
  elem.innerText = `Show \`${color}\` Overlay.`

  return elem
}


function OverlayColorizeTest({ overlay, controls }) {
  COLORS.map(
    color => {
      const contentItem = OverlayColorizeTestContent({ color })
      overlay.addContent(contentItem)
      overlay.elem.appendChild(contentItem)

      const button = OverlayColorizeTestButton({ color })
      controls.appendChild(button)
      button.addEventListener("click", overlay.onClick)
    }
  )
}

