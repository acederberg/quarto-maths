
const uvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;

async function hydrateLiveLogLine(container, item, index, array) {

  itemPrevious = index > 0 ? array[index - 1] : null

  const elem = document.createElement("tr")
  const itemTime = document.createElement("td")
  const itemName = document.createElement("td")
  const itemMsg = document.createElement("td")
  const itemLevel = document.createElement("td")

  if (!itemPrevious || item.created_time != itemPrevious.created_time) {
    itemTime.textContent = '[' + item.created_time + ']'
  }
  itemLevel.textContent = item.levelname
  itemName.textContent = item.name + ":" + item.lineno

  const matched = item.msg.match(uvicornLogPattern)

  if (!matched) {
    itemMsg.textContent = item.msg
  }
  else {
    const { ip, port, method, path, protocol, status } = matched.groups

    const uvicornIp = document.createElement("span")
    const uvicornPort = document.createElement("span")
    const uvicornMethod = document.createElement("span")
    const uvicornPath = document.createElement("span")
    const uvicornStatus = document.createElement("span")
    const uvicornProtocol = document.createElement("span")

    uvicornIp.textContent = ip
    uvicornPort.textContent = " " + port
    uvicornMethod.textContent = " " + method
    uvicornPath.textContent = " " + path
    uvicornStatus.textContent = " " + status
    uvicornProtocol.textContent = " " + protocol

    uvicornIp.classList.add("uvicorn-ip")
    uvicornPort.classList.add("uvicorn-port")
    uvicornMethod.classList.add("uvicorn-method")
    uvicornPath.classList.add("uvicorn-path")
    uvicornStatus.classList.add("uvicorn-status")
    uvicornProtocol.classList.add("uvicorn-protocol")

    itemMsg.appendChild(uvicornIp)
    itemMsg.appendChild(uvicornPort)
    itemMsg.appendChild(uvicornMethod)
    itemMsg.appendChild(uvicornPath)
    itemMsg.appendChild(uvicornStatus)
    itemMsg.appendChild(uvicornProtocol)
  }



  itemTime.classList.add("terminal-row-time")
  itemLevel.classList.add("terminal-row-level")
  itemMsg.classList.add("terminal-row-msg")
  itemName.classList.add("terminal-row-name")

  itemLevel.classList.add(item.levelname.toLowerCase())

  elem.classList.add("terminal-row")
  elem.appendChild(itemTime)
  elem.appendChild(itemLevel)
  elem.appendChild(itemMsg)
  elem.appendChild(itemName)

  container.appendChild(elem)

}

async function hydrateLiveLog() {

  const parent = document.querySelector("#tab-content-1")
  const container = document.querySelector("#live-logs-server tbody")
  if (!container) throw Error("Could not find `live-logs-server`.")
  const ws = new WebSocket("/api/dev/log")

  ws.addEventListener(
    "open",
    () => console.log("Websocket connection opened for logs."),
  )
  ws.addEventListener(
    "message",
    (event) => {
      const data = JSON.parse(event.data)
      data.items.map((item, index, array) => hydrateLiveLogLine(container, item, index, array))

      parent.scrollTop = parent.scrollHeight
    },
  )


}


function hydrateQuartoPage(item) {
  container = document.createElement('code')
  container.style.display = 'none'
  container.classList.add('terminal')
  container.dataset.key = item.timestamp

  const timestamp = document.createElement("span")
  timestamp.textContent = "Timestamp: " + item.timestamp
  timestamp.classList.add("terminal-row", "quarto-exit-code")

  const command = document.createElement("span")
  command.textContent = "Command: " + item.command
  command.classList.add("terminal-row", "quarto-command")

  const origin = document.createElement("span")
  origin.textContent = "Origin: " + item.origin
  origin.classList.add("terminal-row", "quarto-origin")

  const target = document.createElement("span")
  target.textContent = "Target: " + item.target
  target.classList.add("terminal-row", "quarto-target")

  const status = document.createElement("span")
  status.textContent = "Status: " + item.status_code
  status.classList.add("terminal-row", "quarto-exit-code")

  const spacer = document.createElement("span")
  spacer.classList.add("terminal-row")

  container.appendChild(timestamp)
  container.appendChild(command)
  container.appendChild(origin)
  container.appendChild(target)
  container.appendChild(status)
  container.appendChild(spacer)
  item.stdout.map(item => {
    const elem = document.createElement("span")
    elem.textContent = item
    elem.classList.add("terminal-row")
    container.appendChild(elem)
  })

  return container
}


function hydrateLiveLogQuartoLine(item) {
  const elem = document.createElement("tr")
  elem.classList.add(!item.status_code ? "quarto-success" : "quarto-failure")
  elem.classList.add("quarto-row")

  const time = document.createElement("td")
  const target = document.createElement("td")
  const origin = document.createElement("td")

  time.textContent = item.time
  target.textContent = item.target
  origin.textContent = item.origin

  elem.appendChild(time)
  elem.appendChild(target)
  elem.appendChild(origin)

  elem.dataset.key = item.timestamp

  return elem
}

// Should generate a list of rows such that
// - Clicking on rows should show the full error,
// - Successful renders show up a blue row,
// - Failed renders show as a red row,
// - The latest render error shows up in an overlay.
async function hydrateLiveLogQuarto(overlay) {
  const state = { isFirst: true }
  const parent = document.querySelector("#tab-content-2")
  const overlayContent = document.querySelector('#quarto-overlay-content')

  const container = document.querySelector("#live-logs-quarto tbody")
  if (!container) throw Error("Missing container.")

  const ws = new WebSocket(`/api/dev/quarto`)
  ws.addEventListener(
    "open",
    () => console.log("Websocket connection opened for quarto logs."),
  )
  ws.addEventListener("message", (event) => {
    const data = JSON.parse(event.data)
    data.items.map(item => {
      // NOTE: Add a line to the log output and add page content. Make overlay
      //       controls aware of the page.
      const line = hydrateLiveLogQuartoLine(item)
      const overlayContentItem = hydrateQuartoPage(item)

      container.appendChild(line)
      overlay.addContent(overlayContentItem)
      overlayContent.appendChild(overlayContentItem)


      // Add a listener for clicks, open error.
      function callback() {
        overlay.showOverlay()
        overlay.showOverlayContentItem(item.timestamp)

        console.log(overlayContentItem)
        setTimeout(() => overlayContent.scrollTop = overlayContent.scrollHeight, 100)
      }
      line.addEventListener("click", callback)

      if (!state.isFirst) {
        if (item.status_code) callback()

        line.classList.add("new")
        setTimeout(() => line.classList.remove("new"), 1000)
      }

    })

    state.isFirst = false
    parent.scrollTop = parent.scrollHeight
  })
}
