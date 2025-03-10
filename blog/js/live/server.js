// @ts-check


/* ------------------------------------------------------------------------- */
/* TYPES */

/**
 * @module
 *
 * The live logs server.
 * Each ``Server`` instance will listen to the server for new logs using a 
 * websocket and push them to a table.
 *
 * While this can be used on its own, it is recommended that you check out 
 * the pandoc filter ``live.py`` which will generate this for any page provided
 * some basic ``YAML`` settings.
 *
 *
 * @typedef {Object} TLogItem
 * @property {number} [created] - Created timestamp (must be greater than 0).
 * @property {string} filename - Filename.
 * @property {string} funcName - Function name.
 * @property {string} levelname - Logging level name.
 * @property {number} levelno - Logging level number.
 * @property {number} lineno - Line number in the file.
 * @property {string} module - Module name.
 * @property {string} msg - Log message.
 * @property {string} name - Logger name.
 * @property {string} pathname - Full path to the file.
 * @property {string} threadName - Thread name.
 * @property {string} created_time
 *
 *
 * @typedef {object} TServerOptions
 * @property {HTMLTableElement} table - The table containing all of the server logs.
 * @property {HTMLElement} container - A parent element of the table. This
 *   makes it such that when new logs are pushed the bottom of the page is
 *   scrolled to. In the initial version, this was the tab content div.
 *
 *
 * @typedef {object} TServer
 * @property {WebSocket} ws -
 * @property {HTMLTableElement} table - Table into which the logs should be inserted.
 * @property {HTMLElement} container - Container for logs.
 * @property {(event: MessageEvent) => void} handleWsMessage - Handle an event 
 *   emited by the websocket. Should push new logs to `table tbody`.
 *
 */

/* ------------------------------------------------------------------------- */
/* CODE */

import * as util from "./util.js"

/** @type Map<string, TServer> */
export const ServerInstances = new Map()
export const LIVE_SERVER_VERBOSE = false

const UvicornLogPattern = /(?<ip>[\d.]+):(?<port>\d+)\s+-\s+"(?<method>[A-Z]+)\s+(?<path>[^\s]+)\s+(?<protocol>HTTP\/\d+\.\d+)"\s+(?<status>\d+)/;
const PatternLogRender = /(Starting render of `.*`)|(Copying `.*` to `.*`)|(Rendered `.*`)./
const PatternRenderFailed = /Failed to render `.*`./
const PatternRenderDefered = /Dispatching render of `.*` from changes in `.*`./
const PatternLogWebSocket = /^\('(?<ip>[\d.]+)', (?<port>\d+)\) - "WebSocket (?<path>[^"]+)" \[(?<detail>([^\]]+))\]$/

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
 * @param {TLogItem} item - The current item.
 * @param {Array<TLogItem>} array - All items.
 * @returns {HTMLTableRowElement} A table row for the log item.
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

  if (UvicornLogPattern.test(item.msg)) {
    // @ts-ignore
    const { ip, port, method, path, protocol, status } = item.msg.match(UvicornLogPattern)?.groups

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
  else if (PatternLogWebSocket.test(item.msg)) {
    // @ts-ignore
    const { ip, port, detail, path } = item.msg.match(PatternLogWebSocket)?.groups

    const uvicornIp = document.createElement("span")
    const uvicornPort = document.createElement("span")
    const uvicornMethod = document.createElement("span")
    const uvicornPath = document.createElement("span")
    // const uvicornStatus = document.createElement("span")
    const uvicornProtocol = document.createElement("span")

    uvicornIp.textContent = ip
    uvicornPort.textContent = ":" + port
    uvicornMethod.textContent = " " + detail.toUpperCase()
    uvicornPath.textContent = " " + path
    uvicornProtocol.textContent = " WEBSOCKET"

    uvicornIp.classList.add("uvicorn-ip")
    uvicornPort.classList.add("uvicorn-port")
    uvicornMethod.classList.add("uvicorn-method")
    uvicornPath.classList.add("uvicorn-path")
    // uvicornStatus.classList.add("uvicorn-status")
    uvicornProtocol.classList.add("uvicorn-protocol")

    itemMsg.appendChild(uvicornIp)
    itemMsg.appendChild(uvicornPort)
    itemMsg.appendChild(uvicornMethod)
    itemMsg.appendChild(uvicornPath)
    // itemMsg.appendChild(uvicornStatus)
    itemMsg.appendChild(uvicornProtocol)

  }
  else {
    itemMsg.textContent = item.msg
  }

  if (PatternLogRender.test(item.msg)) {
    itemMsg.style.color = "var(--bs-green)"
  }
  else if (PatternRenderDefered.test(item.msg)) {
    itemMsg.style.color = "var(--bs-blue)"
  }
  else if (PatternRenderFailed.test(item.msg)) {
    itemMsg.style.color = "var(--bs-red)";
  }
  else if (item.msg.startsWith("connection")) {
    itemMsg.style.color = "var(--bs-gray-600)"
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
    state.highlight ? elem.classList.remove(...highlightClasses) : elem.classList.add(...highlightClasses)
    state.highlight = !state.highlight
  })

  return elem
}


/** Add reactivity to ``ServerLog``. Generates new rows when logs are pushed
 * to the websocket.
 *
 * @param {TServerOptions} options
 * @returns {TServer}
 *
 */
export function Server({
  table,
  container,
}) {
  if (!table) throw Error("`table` is required.")
  if (!container) throw Error("`container` is required.")

  const tableBody = table.querySelector("tbody")
  if (!tableBody) throw Error("Could not find table body.")
  const ws = new WebSocket("/api/dev/log")

  /** @param {MessageEvent} event */
  function handleWsMessage(event) {
    const data = JSON.parse(event.data)
    if (!data) return

    data.items.map(
      /**
       * @param {TLogItem} item -
       * @param {number} index -
       * @param {Array<TLogItem>} array -
       */
      (item, index, array) => {
        const elem = hydrateServerLogItem(item, index, array)

        // @ts-ignore
        tableBody.appendChild(elem)
        container.scrollTop = container.scrollHeight
      }

    )
  }

  ws.addEventListener("message", handleWsMessage)
  util.createWebsocketTimer(ws)

  if (LIVE_SERVER_VERBOSE) {
    ws.addEventListener("close", (event) => console.log(event))
    ws.addEventListener("open", () => console.log("Websocket connection opened for logs."))
  }

  const closure = { ws, table, container, handleWsMessage }
  ServerInstances.set("it", closure)
  return closure
}




