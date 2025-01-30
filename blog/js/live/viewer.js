// @ts-check

/** @typedef {import('./quarto.js').TQuarto} TQuarto */
/** @typedef {import('./banner.js').TQuartoRender} TQuartoRender */

/**
 * @typedef {object} TViewerOptions
 *
 * @property {TQuarto} quarto - Quarto components instance. The websocket will tell
 *   the iframe when to reload.
 * @property {string} target
 *
 */

/**
 * This component should:
 *
 * - Display ``target`` within an IFrame,
 * - reload when the websocket recieves a message for the target,
 * - display that a render started (once the handler emits render jobs) by
 *   putting a spinner ontop of the iframe indicating that a reload has
 *   started,
 * - provide some means to to the page displayed in the iframe.
 *
 * @param {HTMLIFrameElement} iframe
 * @param {TViewerOptions} options
 */
export function Viewer(iframe, { quarto, target }) {
  const ws = quarto.ws

  /** @param {TQuartoRender} [item] */
  function reload(item) {
    if (!item || item.target == target) {
      const now = Date.now()

      const leftURL = new URL(iframe.src)
      leftURL.searchParams.set("timestamp", String(now))
      iframe.src = String(leftURL)
    }
  }

  /**
    * @param {MessageEvent} event
    */
  function handleMessage(event) {
    const data = JSON.parse(event.data)

    data.items.map(
      /** @param {TQuartoRender} item */
      item => reload(item)
    )
  }

  ws.addEventListener("message", handleMessage)
  return { elem: iframe, quarto, reload, handleMessage }
}

