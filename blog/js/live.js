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

  const colorClass = !item.status_code ? "text-success" : "text-danger"

  const timestamp = document.createElement("span")
  timestamp.textContent = "Timestamp: " + item.timestamp
  timestamp.classList.add("terminal-row", "quarto-exit-code", colorClass)

  const command = document.createElement("span")
  command.textContent = "Command: " + item.command
  command.classList.add("terminal-row", "quarto-command", colorClass)

  const origin = document.createElement("span")
  origin.textContent = "Origin: " + item.origin
  origin.classList.add("terminal-row", "quarto-origin", colorClass)

  const target = document.createElement("span")
  target.textContent = "Target: " + item.target
  target.classList.add("terminal-row", "quarto-target", colorClass)

  const status = document.createElement("span")
  status.textContent = "Status: " + item.status_code
  status.classList.add("terminal-row", "quarto-exit-code", colorClass)

  const spacer = document.createElement("span")
  spacer.classList.add("terminal-row", colorClass)

  container.appendChild(timestamp)
  container.appendChild(command)
  container.appendChild(origin)
  container.appendChild(target)
  container.appendChild(status)
  container.appendChild(spacer)
  item.stdout.map(item => {
    const elem = document.createElement("span")
    elem.textContent = item
    elem.classList.add("terminal-row", colorClass)
    container.appendChild(elem)
  })

  container.dataset.colorizeColor = item.status_code ? "danger" : "success"

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

  // NOTE: Eventually statusCode should tell the overlay how to be colored.
  //       For now, overlay does not colorize until it is opened.
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

  function colorize() {
    quartoOverlayControls.colorize({
      color: item.status_code ? "danger" : "success",
      colorText: "white",
      colorTextHover: "black"
    })
  }

  function show() {
    quartoOverlayControls.showOverlay()
    quartoOverlayControls.showOverlayContentItem(item.timestamp)
    colorize()
    setTimeout(() => quartoOverlayContent.scrollTop = quartoOverlayContent.scrollHeight, 100)
  }

  return { colorize, show, elem }
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

  if (log && quartoOverlayControls) log.elem.addEventListener("click", overlay.show)

  return { overlay, log }
}


/*
  When a message arrives, ensure that a row is added to the display.
  When the message is an error, show the overlay with the page scrolled down to the bottom of the content.
*/
function Quarto({ filters, last, quartoLogsParent, quartoLogs, quartoOverlayControls, quartoOverlayContent }) {

  /*
    If there is an overlay, show an overlay if there is an error.
    If there is a log, put the log item in and call `show` to make it obvious that it is new.
    If there is not a log, add a banner at the bottom of the page and call `show` to make it obvious that it is new.
  */
  function handleMessage(event) {
    const data = JSON.parse(event.data)
    data.items.map(
      item => {
        console.log(item.target)
        const quartoItem = QuartoItem(item, { quartoLogs, quartoOverlayControls, quartoOverlayContent })
        if (!state.isInitial) {
          if (quartoItem.overlay && item.status_code) quartoItem.overlay.show()
          if (quartoItem.log) quartoItem.log.show()
        }

        if (!quartoItem.log) {
          const banner = QuartoRenderBanner(item, {})

          document.body.appendChild(banner.elem)
          if (!state.isInitial) {
            banner.show()
          }
          quartoItem.overlay && banner.info.addEventListener("click", quartoItem.overlay.show)
        }
      }
    )

    if (state.isInitial) state.isInitial = false
    if (quartoLogsParent) quartoLogsParent.scrollTop = quartoLogsParent.scrollHeight
  }

  const state = { isInitial: true }

  // NOTE: Send in filters for listener so it will start listening.
  let url = '/api/dev/quarto'
  if (last) { url = url + `?last=${last}` }

  const ws = new WebSocket(url)
  ws.addEventListener("open", () => {
    ws.send(JSON.stringify(filters || null))
    console.log("Websocket connection opened for quarto renders.")
  })
  ws.addEventListener("message", handleMessage)

  return { ws, state, handleMessage, overlay: quartoOverlayControls }
}



function QuartoRenderBanner(item, { bannerTextInnerHTML } = {}) {
  /* Re-render this page. */
  async function render() {
    reload.remove()

    const spinnerContainer = document.createElement("i")
    spinnerContainer.classList.add("px-2")

    const spinner = document.createElement("div")
    spinner.classList.add("spinner-border")
    spinnerContainer.appendChild(spinner)
    left.appendChild(spinnerContainer)

    res = await fetch("/api/dev/quarto", {
      body: JSON.stringify({ items: [window.location.pathname] }),
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
      method: "POST",
    })

    spinnerContainer.remove()
    left.appendChild(reload)

    data = await res.json()
  }

  /* Ensure that the new banner is obvious to the user. */
  function show() {
    const code = Array.from(bannerText.getElementsByTagName("code"))
    code.map(elem => elem.classList.add("new"))
    banner.classList.add("new")

    setTimeout(() => {
      code.map((elem) => elem.classList.remove("new"))
      banner.classList.remove("new")
    }, 1500)
  }

  function initialize() {
    // NOTE: Remove the banner if it already exists.
    banner_og = document.getElementById(identifier)
    if (banner_og) banner_og.remove()

    // NOTE: Make code elements and banner the right color.
    const classResult = !item.status_code ? "success" : "failure"
    const code = Array.from(bannerText.getElementsByTagName("code"))

    code.map(elem => elem.classList.add(colorClass, classResult))
    banner.classList.add(colorClass, classResult)
  }

  const identifier = "quarto-render-notification"

  // NOTE: Create the banner
  const colorClass = item.status_code ? "bg-warning" : "bg-success"
  const banner = document.createElement("div")
  banner.id = identifier
  banner.classList.add("position-fixed", "bottom-0", "w-100", "text-white", "text-center", colorClass)

  // NOTE: Add info and reload icons on the left hand side.
  const left = document.createElement("div")
  left.classList.add("start-0", "position-absolute")
  left.style.marginTop = '2px'

  const info = document.createElement("i");
  info.classList.add("bi", !item.status_code ? "bi-info-circle" : "bi-bug", "px-2")
  left.appendChild(info)

  const reload = document.createElement("i")
  reload.classList.add("bi", "bi-arrow-repeat", "px-2")
  left.appendChild(reload)
  reload.addEventListener("click", render)

  banner.appendChild(left)

  // NOTE: Add banner text.
  const bannerText = document.createElement("text")
  if (!bannerTextInnerHTML) {
    bannerText.innerHTML = `
      <text>Last rendered at </text>
      <code>${item.time}</code>
      <text>from changes in </text>
      <code>${item.origin}</code>
      <text>.</text>
  `
  } else { bannerText.innerHTML = bannerTextInnerHTML }
  banner.appendChild(bannerText)

  // NOTE: Add close button
  const closeButton = document.createElement("i");
  closeButton.style.marginTop = '2px'
  closeButton.classList.add("bi", "bi-x-lg", "end-0", "position-absolute", "px-2")
  closeButton.addEventListener("click", () => banner.remove())
  banner.appendChild(closeButton);

  initialize()

  return { elem: banner, info, close, show, render, initialize }
}


// ------------------------------------------------------------------------- //
// Controls


async function hydrateServerResponse(response) {
  const colorClass = response.ok ? "text-green" : "text-red"

  const url = document.createElement("span")
  url.textContent = `URL: ${response.url}`
  url.classList.add("terminal-row", colorClass)

  const status = document.createElement("span")
  status.textContent = `Status Code: ${response.status} ${response.statusText}`
  status.classList.add("terminal-row", colorClass)

  const container = document.querySelector("#quarto-controls-response")
  container.innerHTML = ''
  container.appendChild(url)
  container.appendChild(status)

  const responseText = await response.text()
  try {
    const json = JSON.parse(responseText);
    responseBody = JSON.stringify(json, null, 2); // Pretty print with 2 spaces

    responseBody.split("\n").map(
      line => {
        const elem = document.createElement("span")
        elem.classList.add("terminal-row", colorClass)
        elem.textContent = line
        container.appendChild(elem)
      }
    )

  } catch (e) {
    const content = document.createElement("span")
    content.classList.add(colorClass)
    content.textContent = `Response: ${responseText}`
    container.appendChild(content)
  }



  container.classList.remove("hidden")
}


function addIcon(btn, iconName) {
  const icon = document.createElement("i")
  const text = btn.querySelector("text")
  icon.classList.add("bi", `bi-${iconName}`)
  btn.insertBefore(icon, text)
}


function hydrateRender(overlay) {
  function updateButtonColor() {
    buttonInOverlay.classList.remove(`btn-outline-${overlay.state.colorize.state.colorPrev}`)
    buttonInOverlay.classList.add(`btn-outline-${overlay.state.colorize.state.color}`)
  }

  const elem = document.querySelector("#quarto-controls-render-one")
  elem.addEventListener("click", () => {
    overlay.showOverlay()
    overlay.showOverlayContentItem(elem.dataset.key)
  })
  addIcon(elem, "hammer")

  const buttonInOverlay = document.getElementById("api-params-render-button")
  const buttonInOverlaySpinner = buttonInOverlay.querySelector("span")

  updateButtonColor()

  buttonInOverlay.addEventListener("click", async () => {
    const input = document.getElementById("api-params-render-item")
    const msgError = document.getElementById("api-params-render-err")
    const msgDesc = document.getElementById("api-params-render-desc")

    if (!input.value) {
      msgError.classList.remove("hidden")
      msgDesc.classList.add("hidden")
      input.classList.add("border", "border-warning", "border-3")

      overlay.colorize({ color: "warning" })
      updateButtonColor()

      return
    }


    buttonInOverlaySpinner.classList.remove("hidden")
    buttonInOverlay.classList.add("disabled")
    msgError.classList.add("hidden")
    msgDesc.classList.remove("hidden")
    const res = await fetch("/api/dev/quarto", {
      method: "POST",
      body: JSON.stringify({ items: [input.value] }),
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
    })

    hydrateServerResponse(res)
    overlay.hideOverlay()
    overlay.state.colorize.revert()

    updateButtonColor()
    buttonInOverlaySpinner.classList.add("hidden")
    buttonInOverlay.classList.remove("disabled")
  })

  return { elem, buttonInOverlay }
}


function hydrateClearLogs() {
  async function action() {
    const response = await fetch("/api/dev/log", { method: "DELETE" })
    await hydrateServerResponse(response)
  }

  const elem = document.querySelector("#quarto-controls-clear-logs")
  elem.addEventListener("click", action)
  addIcon(elem, "trash")

  return { elem, action }
}


function hydrateClearRenders() {
  async function action() {
    const response = await fetch("/api/dev/quarto", { method: "DELETE" })
    await hydrateServerResponse(response)
  }

  const elem = document.querySelector("#quarto-controls-clear-renders")
  elem.addEventListener("click", action)
  addIcon(elem, "trash")

  return { elem, action }
}


function hydrateGetLast(overlay) {
  async function action() {
    overlay.showOverlay()
    overlay.showOverlayContentItem("get-last")

  }

  function updateButtonColor() {
    buttonInOverlay.classList.remove(`btn-outline-${overlay.state.colorize.state.colorPrev}`)
    buttonInOverlay.classList.add(`btn-outline-${overlay.state.colorize.state.color}`)
  }

  const elem = document.querySelector("#quarto-controls-get-last")
  elem.addEventListener("click", action)
  addIcon(elem, "bookshelf")

  const buttonInOverlay = document.getElementById("api-params-get-last-button")
  const buttonInOverlaySpinner = buttonInOverlay.querySelector("span")
  updateButtonColor()

  buttonInOverlay.addEventListener("click", async () => {
    const input = document.getElementById("api-params-get-last-kind")
    const msgError = document.getElementById("api-params-get-last-err")

    if (input.value === 'none') {
      msgError.classList.remove("hidden")
      input.classList.add("border", "border-warning", "border-3")

      overlay.colorize({ color: "warning" })
      updateButtonColor()

      return
    }

    buttonInOverlaySpinner.classList.remove("hidden")
    buttonInOverlay.classList.add("disabled")
    msgError.classList.add("hidden")

    const res = await fetch(
      "/api/dev/quarto/last",
      {
        method: "POST",
        body: JSON.stringify({ kind: [input.value] }),
        headers: {
          "Accept": "application/json",
          "Content-Type": "application/json"
        }
      }
    )

    hydrateServerResponse(res)
    overlay.hideOverlay()
    overlay.state.colorize.revert()

    buttonInOverlay.classList.remove("disabled")
    buttonInOverlaySpinner.classList.add("hidden")
  })


  return { elem }
}


function QuartoControls() {
  const overlay = Overlay(document.getElementById("api-params"))
  overlay.colorize({ color: "primary", colorText: "white", colorTextHover: "black" })

  const render = hydrateRender(overlay)
  const clearLogs = hydrateClearLogs()
  const clearQuarto = hydrateClearRenders()
  const getLast = hydrateGetLast(overlay)

  return { overlay, render, clearLogs, clearQuarto, getLast }
}
