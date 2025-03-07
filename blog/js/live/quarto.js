// @ts-check
/** @typedef {import("../overlay.js").TOverlay} TOverlay */
/** @typedef {import("./banner.js").TBanner} TBanner */

/**
 *
 * @typedef {Object} TQuartoRender
 * @property {string} time - Time at which the log was generated.
 * @property {string} target_url_path - URL to the render target.
 * @property {number} timestamp - Timestamp (must be greater than 0).
 * @property {"client"|"lifespan"} item_from - Source of the render request.
 * @property {"defered"|"direct"|"static"} kind - Kind of render (default: "direct").
 * @property {string} origin - Origin of the render request.
 * @property {string} target - Target of the render operation.
 * @property {number} status_code - Status code of the render operation.
 * @property {string[]} command - Command executed during the render.
 * @property {string[]} stderr - Standard error output from the render.
 * @property {string[]} stdout - Standard output from the render.
 *
 *
 * @typedef {object} TQuartoOverlayItem
 * @property {() => void} show - Show the overlay for this particular item.
 * @property {HTMLElement} elem - The overlayContentItem
 *
 *
 * @typedef {object} TQuartoLogItem
 * @property {HTMLTableRowElement} elem -
 * @property {HTMLElement} render -
 * @property {HTMLElement} info -
 * @property {() => void} renderAction -
 * @property {() => void} show -
 *
 *
 * @typedef {object} TQuartoItem
 * @property {TQuartoLogItem | null} logItem
 * @property {TQuartoOverlayItem} overlayItem
 *
 *
 * @typedef {Object} TQuartoOptions
 * @property {object|null} [filters] - Filters for websocket messages.
 * @property {number|null} [last] - Number of initial logs to recieve.
 * @property {HTMLTableElement} table - The table containing quarto logs.
 * @property {HTMLElement} container - A div containing the renders container.
 * @property {TOverlay} overlayRenders - Output from ``Overlay`` for overlay to contain render datas.
 * @property {TBanner|null} banner - Banner settings. When ``null``, the banner is not included.
 * @property {boolean|null} [reload] - Do page hot reloads.
 *
 *
 * @typedef {object} TQuarto
 * @property {WebSocket} ws
 * @property {() => void} initialize
 * @property {object} state
 * @property {(event: MessageEvent) => void} handleMessage
 * @property {TOverlay} overlayRenders
 * @property {HTMLTableElement} table
 * @property {HTMLElement} container
 */


// ------------------------------------------------------------------------- //
// Quarto


import * as util from "./util.js"

/** @type {Map<string, TQuarto>} */
export const QuartoInstances = new Map()
export const LIVE_QUARTO_VERBOSE = false

/** Create overlay content for a quarto render.
 *
 * All errors will be highlighted in red and the overlay content will be colorized to red.
 * Successful renders of ``qmd`` documents will be colorized to blue.
 * Successful updates of static assets will be colorized in teal.
 *
 * @param {TQuartoRender} item - an item pushed from ``quarto`` logs websocket.
 * @param {object} options
 * @param {TOverlay} options.overlayRenders
 * @returns {TQuartoOverlayItem}
 *
 */
export function QuartoOverlayItem(item, { overlayRenders }) {

  const elem = document.createElement("div")
  elem.classList.add("overlay-content-item", "hidden")
  elem.dataset.key = String(item.timestamp)
  elem.dataset.colorizeColor = item.status_code ? "danger" : (
    item.kind === "static" ?
      "primary" : "teal")

  const terminal = document.createElement('code')
  terminal.classList.add('terminal', 'p-3')
  elem.appendChild(terminal)

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

  // function colorize() {
  //   overlayRenders.colorize({
  //     color: item.status_code ? "danger" : "primary",
  //     colorText: "white",
  //     colorTextHover: "black"
  //   })
  // }
  //
  function show() {
    LIVE_QUARTO_VERBOSE && console.log("Showing quarto renders overlay.")
    overlayRenders.showOverlay()
    overlayRenders.showOverlayContentItem(String(item.timestamp))
    // colorize()
    setTimeout(() => overlayRenders.overlayContentItems.scrollTop = elem.scrollHeight, 100)
  }

  return { elem, show }
}

/** Create quarto table table row for a log item.
 *
 * Includes buttons to active the overlay and re-render, kind, origin, time,
 * target, and origin.
 * Highlights depending on success or failure of render.
 *
 * @param {TQuartoRender} item - Log item pushed from websocket.
 * @returns {TQuartoLogItem}
 *
 */
export function QuartoLogItem(item) {
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
    await util.requestRender({ items: [item.target] })

    renderIconSpinner.remove()
    renderIcon.classList.remove("hidden")
  }

  function show() {
    const classNew = item.status_code ? "border-red" : "border-teal"
    elem.classList.add(classNew, "border", "boder-3")

    // Add a border to indicate that the item is new.
    setTimeout(() => {
      elem.classList.remove(classNew)
      elem.classList.add("border-black")
    }, 1000)

    setTimeout(() => {
      elem.classList.remove("border-black", "border", "border-3")
    }, 30000)

  }

  const renderIcon = document.createElement("i")
  renderIcon.classList.add("bi", "bi-arrow-repeat")

  const render = document.createElement("td")
  render.classList.add("quarto-log-render")
  render.append(renderIcon)
  render.addEventListener("click", renderAction)

  // INFO CELL. This should be made to display the overlay later.
  const infoIcon = document.createElement("i")
  infoIcon.classList.add("bi", "bi-info-circle")

  const info = document.createElement("td")
  info.classList.add("quarto-log-info")
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

  targetUrlPath.appendChild(util.handlePathlike(item.target_url_path, { wrapperTag: 'a' }))
  targetUrlPath.classList.add("quarto-log-target-url-path")

  target.appendChild(util.handlePathlike(item.target, {}))
  target.classList.add("quarto-log-target")

  origin.appendChild(util.handlePathlike(item.origin, {}))
  origin.classList.add("quarto-log-origin")


  elem.appendChild(info)
  elem.appendChild(render)
  elem.appendChild(kind)
  elem.appendChild(from)
  elem.appendChild(time)
  elem.appendChild(targetUrlPath)
  elem.appendChild(target)
  elem.appendChild(origin)
  elem.dataset.key = String(item.timestamp)

  const state = { highlight: false }
  const highlightClasses = ["highlight"]

  elem.addEventListener("click", () => {
    state.highlight ? elem.classList.remove(...highlightClasses) : elem.classList.add(...highlightClasses)
    state.highlight = !state.highlight
  })

  return { elem, renderAction, info, render, show }
}


/** Handles new log items for the logs table *(if exists)* and banner *(if included).
 * 
 * - When a message arrives, ensure that a row is added to the display.
 * - When the message is an error, show the overlay with the page scrolled down to the bottom of the content.
 *
 * @param {TQuartoOptions} options - 
*/
export function Quarto({ filters, last, table, container, overlayRenders, banner, reload }) {

  const tableContent = table ? table.querySelector("tbody") : null
  if (!overlayRenders) throw Error("Missing `overlayRenders`.")

  /** Add overlayRenders content (if possible) and log item (if possible).
   *
   * @param {TQuartoRender} item - Render log item from the websocket.
   * @returns {TQuartoItem}
  */
  function QuartoItem(item) {

    // NOTE: Add overlay item.
    const overlayItem = QuartoOverlayItem(item, { overlayRenders })
    LIVE_QUARTO_VERBOSE && console.debug("Adding quarto overlayRenders item.", overlayItem)
    overlayRenders.addContent(overlayItem.elem)
    overlayRenders.overlayContentItems.appendChild(overlayItem.elem)

    // NOTE: Add log item.
    const logItem = QuartoLogItem(item)
    LIVE_QUARTO_VERBOSE && console.debug("Adding quarto log item.", logItem)
    if (table && tableContent) {
      tableContent.appendChild(logItem.elem)
    }

    if (logItem && overlayItem) {
      logItem.info.addEventListener("click", () => {
        overlayItem.show()
      })
    }

    return { overlayItem, logItem }
  }


  /** Handle updates for a single log item.
   *
   * @param {TQuartoRender} logItem
   * @param {number} index
   * @param {TQuartoRender[]} data
   *
   */
  function handleQuartoRender(logItem, index, data) {
    const item = QuartoItem(logItem)

    if (!state.isInitial) {
      if (item.overlayItem && logItem.status_code) item.overlayItem.show()
      if (item.logItem) item.logItem.show()
    }

    if (reload && logItem.status_code && index + 1 === data.length) item.overlayItem.show()

    if (reload && !state.isInitial && (logItem.target_url_path == window.location.pathname || logItem.target_url_path == window.location.pathname + "index.html")) {
      ws.close(1000)
      window.location.reload()
      return
    }

    banner && banner.show(logItem, { newItem: !state.isInitial })
  }

  /**
    If there is an overlayRenders, show an overlayRenders if there is an error.
    If there is a log, put the log item in and call `show` to make it obvious that it is new.
    If there is not a log, add a banner at the bottom of the page and call `show` to make it obvious that it is new.

    When there is data (when ``GET /api/dev/quarto`` would return ``HTTP 204``, do nothing.

    @param {any} event
  */
  function handleMessage(event) {
    const data = JSON.parse(event.data)
    if (!data) return

    LIVE_QUARTO_VERBOSE && data.target && console.log(`Recieved event for \`${data.target}\`.`)
    LIVE_QUARTO_VERBOSE && console.log(data)

    data.items.map(handleQuartoRender)

    if (state.isInitial) state.isInitial = false
    if (container) container.scrollTop = container.scrollHeight
  }

  const state = { isInitial: true }

  let url = '/api/dev/quarto'
  if (last) { url = url + `?last=${last}` }
  const ws = new WebSocket(url)

  function initialize() {
    // NOTE: Send in filters for listener so it will start listening.

    util.createWebsocketTimer(ws)
    ws.addEventListener("open", () => {
      ws.send(JSON.stringify(filters || null))
      if (LIVE_QUARTO_VERBOSE) {
        console.log("Websocket connection opened for quarto renders.")
        console.log(`Websocket sent filters \`${JSON.stringify(filters || null, null, 2)}\`.`)
      }
    })

    ws.addEventListener("message", handleMessage)
    LIVE_QUARTO_VERBOSE && ws.addEventListener("close", (event) => console.log(event))
  }

  initialize()

  /** @type {TQuarto} */
  const closure = { ws, initialize, state, handleMessage, overlayRenders: overlayRenders, table: table, container: container }

  QuartoInstances.set("it", closure)
  return closure
}

