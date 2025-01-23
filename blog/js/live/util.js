// @ts-check

export const LIVE_VERBOSE = true

/** @typedef {Map<string, string[]>}  */
const EXT_TO_ICON = new Map()
EXT_TO_ICON.set("py", ["bi-filetype-py", "text-yellow"])
EXT_TO_ICON.set("qmd", ["bi-filetype-md", "text-teal"])
EXT_TO_ICON.set("html", ["bi-filetype-html", "text-orange"])
EXT_TO_ICON.set("js", ["bi-filetype-js", "text-green"])
EXT_TO_ICON.set("scss", ["bi-filetype-scss", "text-pink"])
EXT_TO_ICON.set("yaml", ["bi-filetype-yml", "text-yellow"])
EXT_TO_ICON.set("pdf", ["bi-filetype-pdf", "text-red"])


/** Create the listener timer.
 *
 * @param {WebSocket} ws -
 */
export function createWebsocketTimer(ws) {
  /**
   * @memberof live
   * @typedef {object} WebsocketTimerState
   * @property {number|undefined} id
   * @property {() => Promise<void>} start
   * @property {() => void} stop
   *
   */

  /** @type WebsocketTimerState */
  const state = {
    start: async () => {
      LIVE_VERBOSE && console.log("Waiting...")
      const id = setInterval(() => {
        LIVE_VERBOSE && console.log("Waiting...")
        ws.send("null")
      }, 1000)
      // @ts-ignore
      state.id = id
    },
    id: undefined,
    stop: () => {
      clearInterval(state.id)
    }
  }

  ws.addEventListener("open", state.start)
  ws.addEventListener("close", state.stop)
  return state
}

/** Options for ``handlePathlike``
 *
 * @typedef {object} PathlikeOptions - Additional options for output.
 *
 * @property {string|null} wrapperTag - Tag for the output `HTMLElement`.
 * @property {Array<string>|null} textClasses - Additional classes for the text. Text is usually ``pathlike``.
 * @property {string|null} textTag - ``HTML`` tag to wrap ``pathlike`` in. By default it is ``text``.
 * @property {Array<string>|null} iconClasses - Additional classes to apply to the icon.
 */


/** Get and style bootstrap icon for a path.
 *
 * @param {string} pathlike -
 * @param {Partial<PathlikeOptions>} options -
 *
 * @returns a stylized ``HTML`` element with ``pathlike`` and an appropriate
 *   bootstrap file icon.
 */
export function handlePathlike(pathlike, { wrapperTag, textClasses, textTag, iconClasses }) {

  if (!pathlike) throw Error("Missing required argument `pathlike`.")

  const text = document.createElement(textTag || "text")
  textClasses && text.classList.add(...textClasses)
  text.innerText = pathlike

  const ext = pathlike.split(".").pop()
  if (!ext) throw Error(`Could not determine extension of \`${pathlike}\`.`)

  const icon = document.createElement("i")
  icon.classList.add("bi", ... (EXT_TO_ICON.get(ext) || ["bi-file"]), ...(iconClasses || ["px-3"]))

  const output = document.createElement(wrapperTag || 'p')
  if (wrapperTag === 'a') {
    // @ts-ignore
    output.href = pathlike
  }

  output.appendChild(icon)
  output.appendChild(text)

  return output
}

/**
 * @param {object} options - Request body.
 * @param {Array<string|object> | null} [options.items] - Items to render.
 */
export async function requestRender({ items }) {
  LIVE_VERBOSE && console.log("Requesting quarto render.")

  const res = await fetch("/api/dev/quarto/render", {
    body: JSON.stringify({ items: items || [window.location.pathname] }),
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
    method: "POST",
  })
  return res
}


/**
 * @param {object} filter - Filtering parameters.
 */
export async function requestRenderHistory(filter) {
  LIVE_VERBOSE && console.log("Requesting quarto render history.")

  const res = await fetch("/api/dev/quarto", {
    body: JSON.stringify(filter),
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', },
    method: "POST",
  })
  return res
}

/**
 * @param {object} filter - Filtering parameters.
 */
export async function requestLast(filter) {
  LIVE_VERBOSE && console.log("Requesting last item rendered.")

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
//
