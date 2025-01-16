import { Overlay } from "./overlay.js"

const UvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;
const LIVE_VERBOSE = false
const LIVE_QUARTO_VERBOSE = false
const LIVE_SERVER_VERBOSE = false
const EXT_TO_ICON = {
  "py": ["bi-filetype-py", "text-yellow"],
  "qmd": ["bi-filetype-md", "text-teal"],
  "html": ["bi-filetype-html", "text-orange"],
  "js": ["bi-filetype-js", "text-green"],
  "scss": ["bi-filetype-scss", "text-pink"],
  "yaml": ["bi-filetype-yml", "text-yellow"],
  "pdf": ["bi-filetype-pdf", "text-red"],
}

/** Turn a websocket log item into a table row for display.
 *
 * Uvicorn server logs get special highlighting to make them easier to read.
 * Time should not be added unless it does not equal the time in the previous
 * row.
 *
 * The parameters are derived from ``Array.map``.
 * These parameters are used to inspect the previous row to omit repeated
 * information (and eventually repeated logs).
 *
 * @param {number} index - The index of the current item.
 * @param {object} item - The current item.
 * @param {Array} array - All items.
 */
function hydrateServerLogItem(item, index, array) {

  const itemPrevious = index > 0 ? array[index - 1] : null

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
    uvicornPort.textContent = ":" + port
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

  const state = { highlight: false }
  const highlightClasses = ["border", "border-1", "border-yellow"]

  elem.addEventListener("click", () => {
    console.log(elem)
    state.highlight ? elem.classList.remove(...highlightClasses) : elem.classList.add(...highlightClasses)
    state.highlight = !state.highlight
  })

  return elem
}



function createWebsocketTimer(ws) {
  const state = {
    start: async () => {
      LIVE_VERBOSE && console.log("Waiting...")
      const id = setInterval(() => {
        LIVE_VERBOSE && console.log("Waiting...")
        ws.send("null")
      }, 1000)
      state.id = id
    },
    id: null,
    stop: () => {
      clearInterval(state.id)
    }
  }

  ws.addEventListener("open", state.start)
  ws.addEventListener("close", state.stop)
  return state
}


/** Add reactivity to ``ServerLog``. Generates new rows when logs are pushed
 * to the websocket.
 *
 * @param {HTMLElement} serverLogContainer - The table containing all of the
 *   server logs.
 * @param {HTMLElement} serverLogParent - A parent element of the table. This
 *   makes it such that when new logs are pushed the bottom of the page is
 *   scrolled to.
 *
 */
export function ServerLog({
  serverLogContainer,
  serverLogParent,
}) {
  if (!serverLogContainer) throw Error("`serverLogContainer` is required.")
  if (!serverLogParent) throw Error("`serverLogParent` is required.")

  const ws = new WebSocket("/api/dev/log")

  ws.addEventListener(
    "message",
    (event) => {
      const data = JSON.parse(event.data)
      if (!data) return

      data.items.map((item, index, array) => {
        const elem = hydrateServerLogItem(item, index, array)
        serverLogContainer.appendChild(elem)
        serverLogParent.scrollTop = serverLogParent.scrollHeight
      })
    },
  )

  createWebsocketTimer(ws)

  if (LIVE_SERVER_VERBOSE) {
    ws.addEventListener("close", (event) => console.log(event))
    ws.addEventListener("open", () => console.log("Websocket connection opened for logs."))
  }

  return { ws }
}

// ------------------------------------------------------------------------- //
// Quarto
// TODO: Write these like a closure as was done for ``Floaty`` and ``Overlay``.

/** Create overlay content for a quarto render.
 *
 * All errors will be highlighted in red and the overlay content will be colorized to red.
 * Successful renders of ``qmd`` documents will be colorized to blue.
 * Successful updates of static assets will be colorized in teal.
 *
 * @param {object} item - an item pushed from ``quarto`` logs websocket.
 *
 */
function hydrateQuartoOverlayItem(item) {

  const contentItem = document.createElement("div")
  contentItem.classList.add("overlay-content-item", "hidden")
  contentItem.dataset.key = item.timestamp
  contentItem.dataset.colorizeColor = item.status_code ? "danger" : (
    item.kind === "state" ?
      "primary" : "teal")

  const terminal = document.createElement('code')
  terminal.classList.add('terminal', 'p-3')
  contentItem.appendChild(terminal)

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

  terminal.appendChild(timestamp)
  terminal.appendChild(command)
  terminal.appendChild(origin)
  terminal.appendChild(target)
  terminal.appendChild(status)
  terminal.appendChild(spacer)
  item.stdout.map(item => {
    const elem = document.createElement("span")
    elem.textContent = item
    elem.classList.add("terminal-row", colorClass)
    terminal.appendChild(elem)
  })

  return contentItem
}


/** Get and style bootstrap icon for a path.
 *
 * @param {string} pathlike - 
 * @param {object} options - Additional options for output.
 * @param {string} options.wrapperTag - Tag for the output `HTMLElement`.
 * @param {array<string>} textClasses - Additional classes for the text. Text
 *   is usually ``pathlike``.
 * @param {string} textTag - ``HTML`` tag to wrap ``pathlike`` in. By default it is ``text``.
 * @param {array<string} iconClasses - Additional classes to apply to the icon.
 * @returns a stylized ``HTML`` element with ``pathlike`` and an appropriate
 *   bootstrap file icon.
 *
 */
function handlePathlike(pathlike, { wrapperTag, textClasses, textTag, iconClasses } = {}) {

  const text = document.createElement(textTag || "text")
  textClasses && text.classList.add(...textClasses)
  text.innerText = pathlike

  const ext = pathlike.split(".").pop()
  const icon = document.createElement("i")
  icon.classList.add("bi", ... (EXT_TO_ICON[ext] || ["bi-file"]), ...(iconClasses || ["px-3"]))

  const output = document.createElement(wrapperTag || 'p')
  if (wrapperTag === 'a') {
    output.href = pathlike
  }

  output.appendChild(icon)
  output.appendChild(text)

  return output
}

/** Create quarto table table row for a log item.
 *
 * Includes buttons to active the overlay and re-render, kind, origin, time,
 * target, and origin.
 * Highlights depending on success or failure of render.
 *
 * @param {object} item - Log item pushed from websocket.
 * @returns a hydrated table row.
 *
 */
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
  const targetUrlPath = document.createElement("td")
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

  targetUrlPath.appendChild(handlePathlike(item.target_url_path, { wrapperTag: 'a' }))
  targetUrlPath.classList.add("quarto-log-target-url-path")

  target.appendChild(handlePathlike(item.target))
  target.classList.add("quarto-log-target")

  origin.appendChild(handlePathlike(item.origin))
  origin.classList.add("quarto-log-origin")


  elem.appendChild(info)
  elem.appendChild(render)
  elem.appendChild(kind)
  elem.appendChild(from)
  elem.appendChild(time)
  elem.appendChild(targetUrlPath)
  elem.appendChild(target)
  elem.appendChild(origin)

  // NOTE: Eventually statusCode should tell the overlay how to be colored.
  //       For now, overlay does not colorize until it is opened.
  elem.dataset.key = item.timestamp

  const state = { highlight: false }
  const highlightClasses = ["highlight"]

  elem.addEventListener("click", () => {
    console.log(elem)
    state.highlight ? elem.classList.remove(...highlightClasses) : elem.classList.add(...highlightClasses)
    state.highlight = !state.highlight
  })

  return { elem, renderAction, info, render }
}

/** Add quarto render data content to overlay (if the overlay exists).
 *
 * @param {object} item - Render log item from the websocket.
 * @param {object} options - Additional options.
 * @param {object} options.quartoOverlayControls - Overlay controls. This is 
 *   the overlay in which the content will be added.
*/
function QuartoOverlayItem(item, { quartoOverlayControls }) {
  if (!quartoOverlayControls) return

  const elem = hydrateQuartoOverlayItem(item)
  quartoOverlayControls.addContent(elem)
  quartoOverlayControls.contentItems.appendChild(elem)

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
    setTimeout(() => quartoOverlayControls.contentItems.scrollTop = quartoOverlayControls.contentItem, 100)
  }

  return { colorize, show, elem }
}



/** Create a log item and items actions.
 *
 * @param {object} item - Render log item from the websocket.
 * @param {object} options - Additional options.
 * @param {HTMLElement} quartoLogs - The table containing the render logs.
 * @returns the output of ``hydrateQuartoLogItem`` and an additional function
 *   to highlight the row when it is rendered.
*/
export function QuartoLogItem(item, { quartoLogs }) {
  if (!quartoLogs) return

  const logItem = hydrateQuartoLogItem(item)
  quartoLogs.appendChild(logItem.elem)

  function show() {
    const classNew = item.status_code ? "border-red" : "border-teal"
    logItem.elem.classList.add(classNew, "border", "boder-3")

    // Add a border to indicate that the item is new.
    setTimeout(() => {
      logItem.elem.classList.remove(classNew)
      logItem.elem.classList.add("border-black")
    }, 1000)

    setTimeout(() => {
      logItem.elem.classList.remove("border-black", "border", "border-3")
    }, 30000)

  }

  return { ...logItem, show }
}


/** Add overlay content (if possible) and log item (if possible).
 *
 * @param {object} item - Render  log item from the websocket.
 * @param {object} options - 
 * @param {object} options.quartoOverlayControls - controls for the overlay 
 *   that will contain render log details.
 * @param {HTMLElement} options.quartoLogs - The table containing quarto logs.
*/
function QuartoItem(item, { quartoLogs, quartoOverlayControls }) {

  const overlay = QuartoOverlayItem(item, { quartoOverlayControls })
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
export function Quarto({ filters, last, quartoLogsParent, quartoLogs, quartoOverlayControls, quartoBannerInclude, reload }) {

  /*
    If there is an overlay, show an overlay if there is an error.
    If there is a log, put the log item in and call `show` to make it obvious that it is new.
    If there is not a log, add a banner at the bottom of the page and call `show` to make it obvious that it is new.

    When there is data (when ``GET /api/dev/quarto`` would return ``HTTP 204``, do nothing.
  */
  function handleMessage(event) {
    const data = JSON.parse(event.data)
    if (!data) return

    LIVE_QUARTO_VERBOSE && data.target && console.log(`Recieved event for \`${data.target}\`.`)
    LIVE_QUARTO_VERBOSE && console.log(data)

    console.log(data.items)
    data.items.map(
      (item, index) => {
        const quartoItem = QuartoItem(item, { quartoLogs, quartoOverlayControls })
        if (!state.isInitial) {
          if (quartoItem.overlay && item.status_code) quartoItem.overlay.show()
          if (quartoItem.log) quartoItem.log.show()
        }

        if (reload && item.status_code && index + 1 === data.items.length) quartoItem.overlay.show()

        if (reload && !state.isInitial && (item.target_url_path == window.location.pathname || item.target_url_path == window.location.pathname + "index.html")) {
          ws.close(1000)
          window.location.reload()
          console.log(content, oldContent)
          return
        }

        if (!quartoItem.log || quartoBannerInclude) {
          const banner = QuartoRenderBanner(item, {})

          document.body.appendChild(banner.elem)
          if (!state.isInitial || reload) {
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
  createWebsocketTimer(ws)

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
  LIVE_QUARTO_VERBOSE && console.log("Requesting quarto render.")

  const res = await fetch("/api/dev/quarto/render", {
    body: JSON.stringify({ items: items || [window.location.pathname] }),
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
    method: "POST",
  })
  return res
}

async function requestRenderHistory(filter) {
  LIVE_QUARTO_VERBOSE && console.log("Requesting quarto render history.")

  const res = await fetch("/api/dev/quarto", {
    body: JSON.stringify(filter),
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
    method: "POST",
  })
  return res
}

async function requestLast(filter) {
  LIVE_QUARTO_VERBOSE && console.log("Requesting last item rendered.")

  const res = await fetch(
    "/api/dev/quarto/last",
    {
      method: "POST",
      body: JSON.stringify(filter),
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      }
    }
  )

  return res
}

export function QuartoRenderBanner(item, { bannerTextInnerHTML } = {}) {
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
    banner.classList.add("new")

    setTimeout(() => {
      banner.classList.remove("new")
    }, 1500)
  }

  function initialize() {
    // NOTE: Remove the banner if it already exists.
    const bannerOg = document.getElementById(identifier)
    if (bannerOg) bannerOg.remove()

    // NOTE: Make code elements and banner the right color.
    const classResult = !item.status_code ? "success" : "failure"
    banner.classList.add(successClass, classResult)
  }

  const identifier = "quarto-render-notification"

  // NOTE: Create the banner
  const successClass = !item.status_code ? "success" : "failure"
  const banner = document.createElement("div")
  banner.id = identifier
  banner.classList.add("position-fixed", "bottom-0", "w-100", "text-white", "text-center", "bg-black")

  // NOTE: Add info and render icons on the left hand side.
  const left = document.createElement("div")
  left.classList.add("start-0", "position-absolute")
  left.style.marginTop = '2px'

  // NOTE: Add close button
  const closeButton = document.createElement("i");
  closeButton.style.marginTop = '2px'
  closeButton.classList.add("bi", "bi-x-lg", "px-2", "banner-control")
  closeButton.addEventListener("click", () => banner.remove())
  left.appendChild(closeButton);

  const info = document.createElement("i");
  info.classList.add("bi", !item.status_code ? "bi-info-circle" : "bi-bug", "px-2", "banner-control")
  left.appendChild(info)

  const render = document.createElement("i")
  render.classList.add("bi", "bi-arrow-repeat", "px-2", "banner-control")
  left.appendChild(render)
  render.addEventListener("click", renderAction)
  banner.appendChild(left)

  // NOTE: Add banner text.
  const bannerText = document.createElement("div")
  // bannerText.classList.add("bg-black")

  if (!bannerTextInnerHTML) {
    bannerText.innerHTML = `
      <text>Last rendered </text>
      <span></span>
      <text>at </text>
      <code>${item.time}</code>
      <text>from changes in </text>
      <span></span>
      <text>.</text>
    `

    const [target_mt, origin_mt] = bannerText.getElementsByTagName("span")

    const target = handlePathlike(item.target, { textTag: 'code', wrapperTag: 'span', iconClasses: ["px-1"] })
    target.classList.add("bg-black")
    target_mt.replaceWith(target)

    const origin = handlePathlike(item.origin, { textTag: 'code', wrapperTag: 'span', iconClasses: ["px-1"] })
    origin.classList.add("bg-black")
    origin_mt.replaceWith(origin)



  } else { bannerText.innerHTML = bannerTextInnerHTML }
  banner.appendChild(bannerText)

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
    const responseBody = JSON.stringify(json, null, 2); // Pretty print with 2 spaces

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


/** Create input group for enum and helpers.
 *
 * @param {string} baseId - 
 * @param {object} options - Additional configuration options.
 * @param {string} innerHTML - Select options
 *
 */
function hydrateInputKind(baseId, { selectInnerHTML } = {}) {
  const inputGroup = document.createElement("div")
  inputGroup.classList.add("input-group", "bg-black", "my-4", "flex-wrap")

  // Create the input.
  const input = document.createElement("select")
  input.classList.add("form-select", "w-100")
  input.id = `api-params-${baseId}-kind`
  input.innerHTML = selectInnerHTML || `
    <option value="none" selected>Select Render Kind</option>
    <option value="direct">Direct</option>
    <option value="defered">Defered</option>
    <option value="static">Static</option>
  `
  inputGroup.append(input)

  // NOTE: Create the error message.
  const inputErrorMsg = document.createElement("div")
  inputErrorMsg.classList.add("form-text", "text-warning", "hidden")
  inputErrorMsg.id = `api-params-${baseId}-err`
  inputErrorMsg.innerHTML = `
    <i class="bi bi-info-circle"></i>
    <text>At least one kind must be selected.</text>
  `
  inputGroup.append(inputErrorMsg)

  function onInvalid() {
    inputErrorMsg.classList.remove("hidden")
    input.classList.add("border", "border-warning", "border-3")
  }

  function onValid() {
    inputErrorMsg.classList.add("hidden")
    input.classList.remove("border", "border-warning", "border-3")
  }

  return { elem: inputGroup, input, errorMsg: inputErrorMsg, onInvalid, onValid }
}


function hydrateInputItems(baseId) {
  const inputGroup = document.createElement("div")
  inputGroup.classList.add("input-group", "my-4", "flex-wrap")

  const input = document.createElement("input")
  input.type = "text"
  input.classList.add("form-control", "w-100")
  input.id = `api-params-${baseId}-item`
  inputGroup.append(input)

  const inputText = document.createElement("div")
  inputText.classList.add("form-text")
  inputText.id = `api-params-${baseId}-desc`
  inputText.innerHTML = `
      <i class="bi bi-file-earmark"></i>
      <text>Enter the absolute url to the file to re-render.</text>
    `
  inputGroup.append(inputText)

  const inputErrorMsg = document.createElement("div")
  inputErrorMsg.classList.add("form-text", "text-warning", "hidden")
  inputErrorMsg.id = "api-params-render-err"
  inputErrorMsg.innerHTML = `
      <i class="bi bi-info-circle"></i>
      <text>The provided value must be a valid path.</text>
    `
  inputGroup.append(inputErrorMsg)

  function onInvalid() {
    inputErrorMsg.classList.remove("hidden")
    inputText.classList.add("hidden")
    input.classList.add("border", "border-warning", "border-3")
  }

  function onValid() {
    inputErrorMsg.classList.add("hidden")
    inputText.classList.remove("hidden")
    input.classList.remove("border", "border-warning", "border-3")
  }


  return { elem: inputGroup, input, text: inputText, errorMsg: inputErrorMsg, onValid, onInvalid }
}

function hydrateForm(baseId, { overlay, title, submitText, inputs }) {
  // NOTE: Create the overlay content item.
  const elem = document.createElement("div")
  elem.classList.add("overlay-content-item")
  elem.dataset.key = baseId

  // NOTE: Create the header.
  elem.innerHTML = `<h4 class="my-5">${title}</h4>`

  // NOTE: Create the form container.
  const form = document.createElement("div")
  form.id = `api-params-${baseId}`
  form.classList.add("m-3")
  elem.appendChild(form)
  if (inputs) inputs.map(item => form.appendChild(item.elem))

  // NOTE: Create the button.
  const button = document.createElement("button")
  button.id = `api-params-${baseId}-button`
  button.type = "button"
  button.classList.add("btn", "my-5")

  const spinner = document.createElement("span")
  spinner.classList.add("spinner-border", "spinner-border-sm", "hidden")
  spinner.role = "status"

  const text = document.createElement("text")
  text.innerText = " " + (submitText || "Submit")

  button.appendChild(spinner)
  button.appendChild(text)
  elem.appendChild(button)

  const updateButtonColor = overlay.state.colorize.updateElem(button, (color) => [`btn-outline-${color}`])
  updateButtonColor()

  /* Button is no longer disabled, hide spinner, hide overlay, revert error color */
  function onRequestOver() {
    overlay.hideOverlay()

    button.classList.remove("disabled")
    spinner.classList.add("hidden")
    updateButtonColor()
  }

  /* Disable button and make spinner visible */
  function onRequestSent() {
    elem.dataset.colorizeColor = "primary"
    overlay.state.colorize.restart({ color: "primary" })
    spinner.classList.remove("hidden")
    button.classList.add("disabled")
    updateButtonColor()
  }


  /* Does not update form elements. */
  function onInvalid() {
    elem.dataset.colorizeColor = "warning"
    overlay.colorize({ color: "warning" })
    updateButtonColor()
  }

  overlay.contentItems.appendChild(elem)
  overlay.addContent(elem)
  elem.dataset.colorizeColor = "primary"

  return { elem, form, button, updateButtonColor, onRequestOver, onRequestSent, onInvalid }
}

function hydrateGetAll(overlay) {
  async function action() {
    overlay.showOverlay()
    overlay.showOverlayContentItem("get-all")
  }

  const elem = document.querySelector("#quarto-controls-get-all")
  elem.addEventListener("click", action)
  const baseId = "get-all"

  // NOTE: Spawn the form.
  const inputKind = hydrateInputKind(baseId)
  const formContentItem = hydrateForm(baseId, {
    title: "Get All",
    overlay: overlay,
    inputs: [inputKind]
  })


  // NOTE: Add form listeners.
  formContentItem.button.addEventListener("click", async () => {
    formContentItem.onRequestSent()
    hydrateServerResponse(
      await requestRenderHistory({ kind: inputKind.input.value === 'none' ? null : [inputKind.input.value] })
    )
    formContentItem.onRequestOver()
  })

  formContentItem.updateButtonColor()
}


function hydrateRender(overlay) {
  async function action() {
    overlay.showOverlay()
    overlay.showOverlayContentItem(elem.dataset.key)
  }

  const elem = document.querySelector("#quarto-controls-render")
  elem.addEventListener("click", action)

  const baseId = "render"
  const inputItems = hydrateInputItems(baseId)
  const inputKind = hydrateInputKind(
    baseId,
    {
      selectInnerHTML: `
        <option value="file" selected>File</option>
        <option value="directory">Directory</option>
      `
    }
  )

  const formContentItem = hydrateForm(baseId, { title: "Render By URL", overlay, inputs: [inputItems, inputKind] })

  formContentItem.button.addEventListener("click", async () => {
    if (!inputItems.input.value) {
      inputItems.onInvalid()
      formContentItem.onInvalid()
      inputKind.onInvalid()
      return
    }
    else {
      inputItems.onValid()
      inputKind.onValid()
    }

    formContentItem.onRequestSent()
    const items = [{ path: inputItems.input.value, kind: inputKind.input.value }]
    console.log(items)
    hydrateServerResponse(await requestRender({ items: items }))
    formContentItem.onRequestOver()
  })

  return { elem, formContentItem, inputItems }
}


function hydrateClearLogs() {
  async function action() {
    const response = await fetch("/api/dev/log", { method: "DELETE" })
    await hydrateServerResponse(response)
  }

  const elem = document.querySelector("#server-controls-clear-logs")
  elem.addEventListener("click", action)

  return { elem, action }
}


function hydrateClearRenders() {
  async function action() {
    const response = await fetch("/api/dev/quarto", { method: "DELETE" })
    await hydrateServerResponse(response)
  }


  const elem = document.querySelector("#quarto-controls-clear-renders")
  elem.addEventListener("click", action)

  return { elem, action }
}




function hydrateGetLast(overlay) {
  async function action() {
    overlay.showOverlay()
    overlay.showOverlayContentItem("get-last")
  }

  const elem = document.querySelector("#quarto-controls-get-last")
  elem.addEventListener("click", action)

  const baseId = "get-last"
  const inputKind = hydrateInputKind(baseId, {})
  const formContentItem = hydrateForm(baseId, { overlay, inputs: [inputKind], title: "Render by URL" })

  formContentItem.button.addEventListener("click", async () => {

    if (inputKind.input.value === 'none') {
      formContentItem.onInvalid()
      inputKind.onInvalid()
      return
    }
    else inputKind.onValid()

    formContentItem.onRequestSent()
    hydrateServerResponse(await requestLast({ kind: [inputKind.input.value] }))
    formContentItem.onRequestOver()
  })


  return { elem }
}


export function QuartoControls() {
  const overlay = Overlay(document.getElementById("api-params"))
  overlay.colorize({ color: "primary", colorText: "white", colorTextHover: "black" })

  const render = hydrateRender(overlay)
  const clearLogs = hydrateClearLogs()
  const clearQuarto = hydrateClearRenders()
  const getLast = hydrateGetLast(overlay)
  const getAll = hydrateGetAll(overlay)

  return { overlay, render, clearLogs, clearQuarto, getLast, getAll }
}
