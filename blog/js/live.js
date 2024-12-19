const UvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;

const LIVE_QUARTO_VERBOSE = true
const LIVE_SERVER_VERBOSE = false

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
  itemName.classList.add("terminal-row-name", "text-dark")
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
  if (LIVE_SERVER_VERBOSE) {
    ws.addEventListener("close", (event) => console.log(event))
    ws.addEventListener("open", () => console.log("Websocket connection opened for logs."))
  }

  return { ws }
}

// ------------------------------------------------------------------------- //
// Quarto 

function hydrateQuartoOverlayItem(item) {
  container = document.createElement('code')
  container.style.display = 'none'
  container.classList.add('terminal')
  container.dataset.key = item.timestamp

  const colorClass = !item.status_code ? "text-light" : "text-danger"

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

  container.dataset.colorizeColor = item.status_code ? "danger" : "primary"

  return container
}


/* Create quarto table table row for a log item. */
function hydrateQuartoLogItem(item) {
  const elem = document.createElement("tr")
  elem.classList.add(!item.status_code ? "quarto-success" : "quarto-failure")
  elem.classList.add("quarto-row")
  if (item.kind === "static") elem.classList.add("quarto-static")

  // RENDER CELL
  async function renderAction() {
    const renderIconSpinner = document.createElement("span")
    renderIconSpinner.classList.add("spinner-border")
    render.append(renderIconSpinner)
    renderIcon.classList.add("hidden")
    // NOTE: Since the row will show up with an error or not, do nothing with the 
    //       request response.
    await requestRender({ items: [item.target] })

    renderIconSpinner.remove()
    renderIcon.classList.remove("hidden")
  }

  const render = document.createElement("td")
  render.classList.add("quarto-log-render")

  const renderIcon = document.createElement("i")
  renderIcon.classList.add("bi", "bi-arrow-repeat")
  render.append(renderIcon)
  render.addEventListener("click", renderAction)


  // INFO CELL. This should be made to display the overlay later.
  const info = document.createElement("td")
  info.classList.add("quarto-log-info")

  const infoIcon = document.createElement("i")
  infoIcon.classList.add("bi", "bi-info-circle")

  info.append(infoIcon)

  // DATA CELLS
  const kind = document.createElement("td")
  const from = document.createElement("td")
  const time = document.createElement("td")
  const target = document.createElement("td")
  const origin = document.createElement("td")

  kind.textContent = item.kind
  kind.classList.add("quarto-log-kind")
  if (item.kind == "direct") kind.classList.add("text-warning")
  else if (item.kind == "defered") kind.classList.add("text-primary")
  // else kind.classList.add("text-white");

  from.textContent = item.item_from
  from.classList.add("quarto-log-from")
  if (item.item_from == "client") from.classList.add("text-warning")
  // else from.classList.add("text-white")

  time.textContent = item.time
  time.classList.add("quarto-log-time")

  target.textContent = item.target
  target.classList.add("quarto-log-target")

  origin.textContent = item.origin
  origin.classList.add("quarto-log-origin")


  elem.appendChild(info)
  elem.appendChild(render)
  elem.appendChild(kind)
  elem.appendChild(from)
  elem.appendChild(time)
  elem.appendChild(target)
  elem.appendChild(origin)

  // NOTE: Eventually statusCode should tell the overlay how to be colored.
  //       For now, overlay does not colorize until it is opened.
  elem.dataset.key = item.timestamp

  return { elem, renderAction, info, render }
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
      color: item.status_code ? "danger" : "primary",
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

  const logItem = hydrateQuartoLogItem(item)
  quartoLogs.appendChild(logItem.elem)

  function show() {
    const classNew = item.status_code ? "quarto-failure-new" : "quarto-success-new"
    logItem.elem.classList.add(classNew)
    setTimeout(() => logItem.elem.classList.remove(classNew), 1000)
  }

  return { ...logItem, show }
}


/*
  Add overlay content (if possible).
  Add log item (if possible).
*/
function QuartoItem(item, { quartoLogs, quartoOverlayControls, quartoOverlayContent }) {

  const overlay = QuartoOverlayItem(item, { quartoOverlayControls, quartoOverlayContent })
  const log = QuartoLogItem(item, { quartoLogs })

  LIVE_QUARTO_VERBOSE && console.debug("Adding quarto overlay item.", overlay)
  LIVE_QUARTO_VERBOSE && console.debug("Adding quarto log item.", log)

  if (log && quartoOverlayControls) log.info.addEventListener("click", overlay.show)

  return { overlay, log }
}


/*
  When a message arrives, ensure that a row is added to the display.
  When the message is an error, show the overlay with the page scrolled down to the bottom of the content.
*/
function Quarto({ filters, last, quartoLogsParent, quartoLogs, quartoOverlayControls, quartoOverlayContent, quartoBannerInclude }) {

  /*
    If there is an overlay, show an overlay if there is an error.
    If there is a log, put the log item in and call `show` to make it obvious that it is new.
    If there is not a log, add a banner at the bottom of the page and call `show` to make it obvious that it is new.
  */
  function handleMessage(event) {
    const data = JSON.parse(event.data)
    LIVE_QUARTO_VERBOSE && data.target && console.log(`Recieved event for \`${data.target}\`.`)
    console.log(data)

    data.items.map(
      item => {
        const quartoItem = QuartoItem(item, { quartoLogs, quartoOverlayControls, quartoOverlayContent })
        if (!state.isInitial) {
          if (quartoItem.overlay && item.status_code) quartoItem.overlay.show()
          if (quartoItem.log) quartoItem.log.show()
        }

        if (!quartoItem.log || quartoBannerInclude) {
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
    if (LIVE_QUARTO_VERBOSE) {
      console.log("Websocket connection opened for quarto renders.")
      console.log(`Websocket sent filters \`${JSON.stringify(filters || null, null, 2)}\`.`)
    }
  })
  ws.addEventListener("message", handleMessage)
  LIVE_QUARTO_VERBOSE && ws.addEventListener("close", (event) => console.log(event))

  return { ws, state, handleMessage, overlay: quartoOverlayControls, logs: quartoLogs, logsParent: quartoLogsParent }
}


async function requestRender({ items }) {
  res = await fetch("/api/dev/quarto", {
    body: JSON.stringify({ items: items || [window.location.pathname] }),
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
    method: "POST",
  })
  return res
}


function QuartoRenderBanner(item, { bannerTextInnerHTML } = {}) {
  /* Re-render this page. */
  async function renderAction() {
    render.remove()

    const spinnerContainer = document.createElement("i")
    spinnerContainer.classList.add("px-2")

    const spinner = document.createElement("div")
    spinner.classList.add("spinner-border")
    spinnerContainer.appendChild(spinner)
    left.appendChild(spinnerContainer)

    const res = await requestRender({})
    spinnerContainer.remove()
    left.appendChild(render)

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
  const colorClass = item.status_code ? "bg-warning" : "bg-primary"
  const banner = document.createElement("div")
  banner.id = identifier
  banner.classList.add("position-fixed", "bottom-0", "w-100", "text-white", "text-center", colorClass)

  // NOTE: Add info and render icons on the left hand side.
  const left = document.createElement("div")
  left.classList.add("start-0", "position-absolute")
  left.style.marginTop = '2px'

  const info = document.createElement("i");
  info.classList.add("bi", !item.status_code ? "bi-info-circle" : "bi-bug", "px-2")
  left.appendChild(info)

  const render = document.createElement("i")
  render.classList.add("bi", "bi-arrow-repeat", "px-2")
  left.appendChild(render)
  render.addEventListener("click", renderAction)
  banner.appendChild(left)

  // NOTE: Add banner text.
  const bannerText = document.createElement("text")
  if (!bannerTextInnerHTML) {
    bannerText.innerHTML = `
      <text>Last rendered </text>
      <code>${item.target}</code>
      <text>at </text>
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
