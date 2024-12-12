
const UvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;

function hydrateServerLogItem(item, index, array) {

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

  const matched = item.msg.match(UvicornLogPattern)

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

  return elem
}

function ServerLog({
  serverLogContainer,
  serverLogParent,
}) {

  // const parent = document.querySelector("#tab-content-1")
  // const container = document.querySelector("#live-logs-server tbody")
  if (!serverLogContainer) throw Error("`serverLogContainer` is required.")
  if (!serverLogParent) throw Error("`serverLogParent` is required.")

  const ws = new WebSocket("/api/dev/log")

  ws.addEventListener(
    "open",
    () => console.log("Websocket connection opened for logs."),
  )
  ws.addEventListener(
    "message",
    (event) => {
      const data = JSON.parse(event.data)
      data.items.map((item, index, array) => {
        const elem = hydrateServerLogItem(item, index, array)
        serverLogContainer.appendChild(elem)
        serverLogParent.scrollTop = serverLogParent.scrollHeight
      })
    },
  )

  return { ws }
}

// ------------------------------------------------------------------------- //
// Quarto 

function hydrateQuartoOverlayItem(item) {
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


/* Create quarto table table row for a log item. */
function hydrateQuartoLogItem(item) {
  const elem = document.createElement("tr")
  elem.classList.add(!item.status_code ? "quarto-success" : "quarto-failure")
  elem.classList.add("quarto-row")
  if (item.kind === "static") elem.classList.add("quarto-static")

  const kind = document.createElement("td")
  const time = document.createElement("td")
  const target = document.createElement("td")
  const origin = document.createElement("td")

  kind.textContent = item.kind
  kind.classList.add("quarto-log-kind")

  time.textContent = item.time
  time.classList.add("quarto-log-time")

  target.textContent = item.target
  target.classList.add("quarto-log-target")

  origin.textContent = item.origin
  origin.classList.add("quarto-log-origin")

  elem.appendChild(kind)
  elem.appendChild(time)
  elem.appendChild(target)
  elem.appendChild(origin)

  elem.dataset.key = item.timestamp

  return elem
}

/*
  Add content to overlay.
  If overlay exists, add new page to overlay content.
  Define a callback for any subsequent actions callbacks (e.g. clicking on any log items.
*/
function QuartoOverlayItem(item, { quartoOverlayControls, quartoOverlayContent }) {
  if (!quartoOverlayControls || !quartoOverlayContent) return

  const elem = hydrateQuartoOverlayItem(item)
  quartoOverlayControls.addContent(elem)
  quartoOverlayContent.appendChild(elem)

  function show() {
    quartoOverlayControls.showOverlay()
    quartoOverlayControls.showOverlayContentItem(item.timestamp)
    setTimeout(() => quartoOverlayContent.scrollTop = quartoOverlayContent.scrollHeight, 100)
  }

  return { show, elem }
}



/*
  Create a log item and items actions.
*/
function QuartoLogItem(item, { quartoLogs }) {
  if (!quartoLogs) return

  const elem = hydrateQuartoLogItem(item)
  quartoLogs.appendChild(elem)

  function show() {
    const classNew = item.status_code ? "quarto-failure-new" : "quarto-success-new"
    elem.classList.add(classNew)
    setTimeout(() => elem.classList.remove(classNew), 1000)
  }

  return { elem, show }
}


/*
  Add overlay content (if possible).
  Add log item (if possible).
*/
function QuartoItem(item, { quartoLogs, quartoOverlayControls, quartoOverlayContent }) {

  const overlay = QuartoOverlayItem(item, { quartoOverlayControls, quartoOverlayContent })
  const log = QuartoLogItem(item, { quartoLogs })

  console.log(quartoOverlayControls, quartoOverlayContent)
  console.log(overlay, log)
  if (log && quartoOverlayControls) log.elem.addEventListener("click", overlay.show)

  return { overlay, log }
}


/*
  When a message arrives, ensure that a row is added to the display.
  When the message is an error, show the overlay with the page scrolled down to the bottom of the content.
*/
function Quarto({ filters, all, quartoLogsParent, quartoLogs, quartoOverlayControls, quartoOverlayContent }) {

  /*
    Show an overlay if there is an item.
  */
  function handleMessage(event) {
    const data = JSON.parse(event.data)
    console.log(JSON.stringify(data, null, 2))
    data.items.map(
      item => {
        const quartoItem = QuartoItem(item, { quartoLogs, quartoOverlayControls, quartoOverlayContent })
        console.log(
          !state.count, quartoItem.overlay, item.status_code
        )
        if (!state.count && quartoItem.overlay && item.status_code) quartoItem.overlay.show()
        if (state.count && quartoItem.log) quartoItem.log.show()
      }
    )

    state.count++
    if (quartoLogsParent) quartoLogsParent.scrollTop = quartoLogsParent.scrollHeight
  }

  const state = { count: 0 }

  // NOTE: Send in filters for listener so it will start listening.
  const ws = new WebSocket(`/api/dev/quarto?all=${all || false}`)
  ws.addEventListener("open", () => {
    console.log("Sending filters to quarto watch websocket.")
    ws.send(JSON.stringify(filters || null))
  })
  ws.addEventListener("close", (event) => { console.log(event.code, event.reason) })
  ws.addEventListener("message", handleMessage)

  return { ws, state, handleMessage }
}


// ------------------------------------------------------------------------- //
// Controls


async function hydrateServerResponse(response) {
  const container = document.querySelector("#quarto-controls-response")

  const url = document.createElement("span")
  url.textContent = `URL: ${response.url}`
  url.classList.add("terminal-row")

  const status = document.createElement("span")
  status.textContent = `Status Code: ${response.status} ${response.statusText}`
  status.classList.add("terminal-row")

  const content = document.createElement("span")
  content.textContent = `Response: ${await response.text()}`
  content.classList.add("terminal-row")

  container.innerHTML = ''
  container.appendChild(url)
  container.appendChild(status)
  container.appendChild(content)

  container.classList.remove("hidden")
}


function addIcon(btn, iconName) {
  const icon = document.createElement("i")
  const text = btn.querySelector("text")
  icon.classList.add("bi", `bi-${iconName}`)
  btn.insertBefore(icon, text)
}


function hydrateRender() {
  const btnOne = document.querySelector("#quarto-controls-render-one")
  const btnMany = document.querySelector("#quarto-controls-render-many")
  addIcon(btnOne, "hammer")
  addIcon(btnMany, "hammer")
}


function hydrateClearLogs() {
  const btn = document.querySelector("#quarto-controls-clear-logs")
  addIcon(btn, "trash")

  btn.addEventListener("click", async function() {
    const response = await fetch("/api/dev/log", { method: "DELETE" })
    await hydrateServerResponse(response)
  })
}


function hydrateClearRenders() {
  const btn = document.querySelector("#quarto-controls-clear-renders")
  addIcon(btn, "trash")

  btn.addEventListener("click", async function() {
    const response = await fetch("/api/dev/quarto", { method: "DELETE" })
    await hydrateServerResponse(response)
  })
}
