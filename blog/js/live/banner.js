// @ts-check

/** @typedef {import("../overlay.js").Overlay} TOverlay */
/** @typedef {import("./quarto.js").TQuartoRender} TQuartoRender */
/** @typedef {import("./input.js").TForm} TForm */
/** @typedef {import("../util.js").TButton} TButton */

/**
 * @typedef {object} TLiveControlsOptions
 *
 * @property {TOverlay} overlayInputs - TOverlay to put api request inputs into.
 * @property {TOverlay} overlayResponses - Overlay to display api responses in.
 * @property {TOverlay} overlayRenders - Overlay to show all renders so far.
 * @property {string|null} [bannerTextInnerHTML] - Banner text message.
 *
 */


/** @typedef {object} TServerResponseOptions
 *
 * @property {TOverlay} overlayResponses -
 * @property {boolean} [show=true] -
 */

/**
 * @typedef TLiveBannerButton
 *
 * @property {TButton} button
 * @property {() => void} action
 */

/**
 * @typedef {object} TLiveBannerButtonForm
 *
 * @property {TButton} button
 * @property {() => void} action
 * @property {TForm} form
 */

/** @typedef {object} TLiveBannerControls
 *
 * @property {HTMLElement} elem
 * @property {Map<string, TLiveBannerButton|TLiveBannerButtonForm>} buttons
 * @property {any[]} tooltips
 */

/**
 * @callback TLiveBannerShow
 *
 * @param {TQuartoRender} logItem -
 * @param {object} options -
 * @param {boolean} options.newItem -
 * @returns void
 */


/** @typedef {object} TLiveBanner
 *
 * @property {HTMLElement} elem
 * @property {TLiveBannerControls} bannerControls
 * @property {TLiveBannerShow} show
 * @property {() => void} initialize
 *
 */





/* ------------------------------------------------------------------------- */

import { Button } from "../util.js"
import * as util from "./util.js"
import * as input from "./input.js"

/** @type {Map<string, TLiveBanner>} */
export const LiveBannerInstances = new Map()

/* ------------------------------------------------------------------------- */
/* RESPONSES */

/** Add response to the responses overlay.
 *
 * Overlay color should match text color.
 *
 * @param {Response} response
 * @param {TServerResponseOptions} ServerResponseOptions
 * @returns {Promise<HTMLElement>}
 *
 */
export async function ServerResponse(response, { overlayResponses, show }) {
  show = show === false ? false : true

  const color = response.ok === null ? "yellow" : (!response.ok ? 'red' : 'primary')
  const colorClass = `text-${color}`

  const path = document.createElement("span")
  path.textContent = `${response.url}`

  const status = document.createElement("span")
  status.textContent = ` ${response.status} ${response.statusText}`

  const head = document.createElement("span")
  head.classList.add("terminal-row", "text-blue", "text-center")
  head.appendChild(path)
  head.appendChild(status)

  const spacer = document.createElement("span")
  spacer.classList.add("terminal-row", colorClass)
  spacer.textContent = " "

  const container = document.createElement("div")
  container.classList.add("terminal")
  container.appendChild(head)
  container.appendChild(spacer)

  const responseText = await response.text()
  try {
    const json = JSON.parse(responseText);
    const responseBody = JSON.stringify(json, null, 2); // Pretty print with 2 spaces

    responseBody.split("\n").map(
      line => {
        const elem = document.createElement("span")
        elem.classList.add("terminal-row", colorClass, "fw-light")
        elem.textContent = line
        container.appendChild(elem)
      }
    )

  } catch (e) {
    const content = document.createElement("span")
    content.classList.add(colorClass)
    content.textContent = `Response: ${responseText}`
  }

  const elem = document.createElement("div")
  elem.classList.add("overlay-content-item")
  elem.dataset.colorizeColor = color
  elem.appendChild(container)
  elem.dataset.key = Date.now().toString()

  overlayResponses.overlayContentItems.appendChild(elem)
  overlayResponses.addContent(elem)

  if (show) {
    overlayResponses.showOverlayContentItem(elem.dataset.key)
    overlayResponses.showOverlay()
  }

  return elem
}


/* ------------------------------------------------------------------------- */
/* Buttons */

/** Show the most recent render.
 *
 * @param {object} options
 * @param {TOverlay} options.overlayRenders
 * @returns {TLiveBannerButton}
 *
 */
export function ButtonShowLatestRender({ overlayRenders }) {

  function action() {
    overlayRenders.showOverlay()
    if (overlayRenders.state.length > 0) {
      const keyLatest = overlayRenders.indicesToKeys.get(overlayRenders.state.length - 1)
      keyLatest && overlayRenders.showOverlayContentItem(keyLatest)
    }
  }

  const button = Button({ icon: 'info-circle-fill', id: 'quarto-controls-banner-overlay', tooltip: 'Get ' })
  button.elem.addEventListener("click", action)

  return { action, button }
}


/**
 * @param {object} options
 * @param {TOverlay} options.overlayResponses
 * @param {TOverlay} options.overlayInputs
 * @returns {TLiveBannerButtonForm}
 */
export function ButtonGetAllRenders({ overlayResponses, overlayInputs }) {
  async function action() {
    overlayInputs.showOverlay()
    overlayInputs.showOverlayContentItem("get-all")
  }

  async function onSubmit() {
    button.toggleSpinner()
    form.onRequestSent()
    ServerResponse(
      await util.requestRenderHistory({ kind: inputKind.input.value === 'none' ? null : [inputKind.input.value] }),
      { overlayResponses }
    )
    form.onRequestOver()
    button.toggleSpinner()
  }

  const button = Button({ id: 'quarto-controls-get-all', dataKey: 'get-all', tooltip: 'Render History', icon: 'body-text' })
  button.elem.addEventListener("click", action)

  const inputKind = input.InputKind({ baseId: "get-all" })
  const form = input.Form({
    baseId: "get-all",
    title: "Get All",
    overlayInputs: overlayInputs,
    inputs: [inputKind],
    onSubmit: onSubmit
  })

  return { button, action, form }
}



/**
 * @param {object} options
 * @param {TOverlay} options.overlayResponses
 * @param {TOverlay} options.overlayInputs
 * @returns {TLiveBannerButtonForm}
 */
export function ButtonRender({ overlayInputs, overlayResponses }) {
  async function action() {
    overlayInputs.showOverlay()
    if (!button.elem.dataset.key) throw Error()
    overlayInputs.showOverlayContentItem(button.elem.dataset.key)
  }

  async function onSubmit() {
    if (!inputItems.input.value) {
      inputItems.onInvalid()
      form.onInvalid()
      inputKind.onInvalid()
      return
    }
    else {
      inputItems.onValid()
      inputKind.onValid()
    }

    button.toggleSpinner()
    form.onRequestSent()
    const items = [{ path: inputItems.input.value, kind: inputKind.input.value }]
    ServerResponse(await util.requestRender({ items: items }), { overlayResponses })
    form.onRequestOver()
    button.toggleSpinner()
  }

  const button = Button({ id: 'quarto-controls-render', dataKey: 'render', tooltip: 'Render', icon: 'hammer' })
  button.elem.addEventListener("click", action)

  const baseId = "render"
  const inputItems = input.InputItems({ baseId })
  const inputKind = input.InputKind(
    {
      baseId,
      selectInnerHTML: `
        <option value="file" selected>File</option>
        <option value="directory">Directory</option>
      `
    }
  )

  const form = input.Form({ onSubmit, baseId, title: "Render By URL", overlayInputs, inputs: [inputItems, inputKind] })
  return { button, action, form }
}




/**
 * @param {object} options
 * @param {TOverlay} options.overlayResponses
 * @returns {TLiveBannerButton}
 */
export function ButtonRenderCurrent({ overlayResponses }) {

  async function action() {
    button.toggleSpinner()
    ServerResponse(await util.requestRender({}), { overlayResponses })
    button.toggleSpinner()
  }

  const button = Button({ id: 'quarto-controls-render-current', icon: 'arrow-repeat', tooltip: 'Render This Page' })
  button.elem.addEventListener("click", action)

  return { button, action }
}


/**
 * @param {object} options
 * @param {TOverlay} options.overlayInputs
 * @param {TOverlay} options.overlayResponses
 * @returns {TLiveBannerButtonForm}
 */
export function ButtonShowLastRendered({ overlayInputs, overlayResponses }) {
  async function action() {
    overlayInputs.showOverlay()
    overlayInputs.showOverlayContentItem("get-last")
  }

  async function onSubmit() {
    if (inputKind.input.value === 'none') {
      form.onInvalid()
      inputKind.onInvalid()
      return
    }
    else inputKind.onValid()

    button.toggleSpinner()
    form.onRequestSent()
    ServerResponse(await util.requestLast({ kind: [inputKind.input.value] }), { overlayResponses })
    form.onRequestOver()
    button.toggleSpinner()
  }

  const button = Button({ icon: 'clock-fill', id: 'quarto-controls-banner-overlay', tooltip: 'Get Last Rendered.' })
  button.elem.addEventListener("click", action)

  const baseId = "get-last"
  const inputKind = input.InputKind({ baseId })
  const form = input.Form({ baseId, overlayInputs, inputs: [inputKind], title: "Get Last Render", onSubmit })

  return { button, action, form }
}


/**
 * @param {object} options
 * @param {TOverlay} options.overlayResponses
 * @returns {TLiveBannerButton}
 *
 */
export function ButtonShowServerResponses({ overlayResponses }) {
  async function action() {
    let keyLatest = overlayResponses.indicesToKeys.get(overlayResponses.state.length - 1)
    if (!keyLatest) {
      const contentItem = await ServerResponse({
        text: async () => '{"msg": "No responses yet.", "note": "Make a request to and you\'ll see responses here."}',
        // @ts-ignore
        ok: null,
        status: 200,
        statusText: "OK",
        url: "/dev/live.html",
      }, { overlayResponses })
      keyLatest = contentItem.dataset.key
      return
    }

    if (!keyLatest) throw Error("Could not determine `keyLatest`.")

    overlayResponses.showOverlay()
    overlayResponses.showOverlayContentItem(keyLatest)
  }

  const button = Button({ id: "server-responses", tooltip: "Show Server Responses.", icon: "server" })
  button.elem.addEventListener("click", action)

  return { button, action }
}




/**
 * @param {object} options
 * @param {TOverlay} options.overlayResponses
 * @returns {TLiveBannerButton}
 */
export function ButtonClearRenders({ overlayResponses }) {
  async function action() {
    const response = await fetch("/api/dev/quarto", { method: "DELETE" })
    await ServerResponse(response, { overlayResponses })
  }

  const button = Button({ id: 'quarto-controls-clear-renders', tooltip: 'Clear Renders', icon: 'trash-fill' })
  button.elem.addEventListener("click", action)

  return { button, action }
}


/**
 * @param {object} options
 * @param {TOverlay} options.overlayResponses
 * @returns {TLiveBannerButton}
 */
export function ButtonClearLogs({ overlayResponses }) {
  async function action() {
    button.toggleSpinner()
    const response = await fetch("/api/dev/log", { method: "DELETE" })
    await ServerResponse(response, { overlayResponses })
    button.toggleSpinner()
  }

  const button = Button({ id: "server-controls-clear-logs", tooltip: "Clear Logs", icon: "trash-fill", iconClasses: ["text-red"] })
  button.elem.addEventListener("click", action)

  return { button, action }
}


/** Create the render controls shown on the left hand side of the render banner.
 *
 * The following functionality should be achieved:
 *
 * 1. Tools should show up in their own overlay, where inputs are displayed
 *    and requests are sent to the API.
 * 2. Responses should be be shown in a separate overlay.
 * 3. Errors should be pushed to a separate overlay where they can be observed.
 *
 * @param {TLiveControlsOptions} options
 * @returns {TLiveBannerControls}
 */
export function LiveBannerControls(options) {

  /** @type Map<string, TLiveBannerButton|TLiveBannerButtonForm> */
  const buttons = new Map(Object.entries({
    showLatestRender: ButtonShowLatestRender(options),
    showServerResponses: ButtonShowServerResponses(options),
    renderCurrent: ButtonRenderCurrent(options),
    render: ButtonRender(options),
    getAllRenders: ButtonGetAllRenders(options),
    getLastRendered: ButtonShowLastRendered(options),
    clearLogs: ButtonClearLogs(options),
    clearRenders: ButtonClearRenders(options),
  }))

  const elementButtons = document.createElement("div")
  elementButtons.classList.add("banner-controls-container")
  Array.from(buttons.values()).map(button => {
    elementButtons.appendChild(button.button.elem)
  })

  const elem = document.createElement("div")
  elem.classList.add("banner-controls")
  elem.appendChild(elementButtons)

  // @ts-ignore
  const tooltips = [...elem.querySelectorAll("button.btn[data-bs-toggle='tooltip']")].map(button => new bootstrap.Tooltip(button))

  return { elem, buttons, tooltips }
}



/** Create the live banner.
 *
 * This should make it so that any module can easily dispatch renders, view
 * render data, etc.
 *
 * @param {TLiveControlsOptions} options -
 * @returns {TLiveBanner} 
 */
export function LiveBanner({ overlayInputs, overlayResponses, overlayRenders }) {
  /* Re-render this page. */

  if (!overlayInputs || !overlayResponses || !overlayRenders) {
    console.warn(overlayInputs, overlayRenders, overlayResponses)
    throw Error("Could not find all required overlays.")
  }

  function initialize() {
    document.body.appendChild(banner)
  }

  /** @type {TLiveBannerShow} */
  function show(logItem, { newItem }) {
    console.log("newItem", newItem, "|")
    bannerTextContainer.innerHTML = `
        <text>Last rendered </text>
        <span></span>
        <text>at </text>
        <code class="fw-bolder">${logItem?.time || 'none'}</code>
        <text>from changes in </text>
        <span></span>
        <text>.</text>
      `

    // @ts-ignore
    const [target_mt, origin_mt] = bannerTextContainer.getElementsByTagName("span")

    const target = util.handlePathlike(logItem?.target || 'none', { textTag: 'code', wrapperTag: 'span', iconClasses: ["px-1"] })
    target.classList.add("bg-black")
    target_mt.replaceWith(target)

    const origin = util.handlePathlike(logItem?.origin || 'none', { textTag: 'code', wrapperTag: 'span', iconClasses: ["px-1"] })
    origin.classList.add("bg-black")
    origin_mt.replaceWith(origin)

    bannerContent.appendChild(bannerText)

    // NOTE: Make code elements and banner the right color.
    const classResult = logItem ? (!logItem.status_code ? "success" : "failure") : null
    if (classResult) {
      banner.classList.add(classResult)
      banner.classList.add(classResult)
    }

    if (!newItem) return

    // NOTE: Ensure that the new banner text is obvious to the user.
    banner.classList.add("new")

    setTimeout(() => {
      banner.classList.remove("new")
    }, 1500)

  }

  const identifier = "quarto-render-notification"

  // NOTE: Create the banner
  const banner = document.createElement("div")
  banner.id = identifier

  const bannerContent = document.createElement("div")
  bannerContent.classList.add("banner-content")
  banner.appendChild(bannerContent)

  // NOTE: Create the banner controls.
  const bannerControls = LiveBannerControls({ overlayInputs, overlayResponses, overlayRenders })
  bannerControls.buttons.get('bannerClose')?.button.elem.addEventListener("click", () => banner.remove())
  bannerContent.appendChild(bannerControls.elem)

  // NOTE: Add banner text.
  const bannerTextContainer = document.createElement("div")
  bannerTextContainer.classList.add("banner-text-container")
  bannerTextContainer.innerText = "No renders for current application lifetime."

  const bannerText = document.createElement("div")
  bannerText.classList.add("banner-text")
  bannerText.appendChild(bannerTextContainer)


  initialize()

  const closure = { elem: banner, bannerControls, show, initialize }
  LiveBannerInstances.set("it", closure)
  return closure
}

