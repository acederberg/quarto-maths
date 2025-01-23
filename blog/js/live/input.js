// @ts-check

/** @typedef {import("../overlay.js").Overlay} TOverlay */
/** @typedef {import("../util.js").TButton} TButton */
/** @typedef {import("../util.js").TButtonOptions} TButtonOptions */

import { Button } from "../util.js"

/**
 * @typedef {object} TInput
 *
 * @property {HTMLElement} elem
 * @property {HTMLInputElement|HTMLSelectElement} input
 * @property {HTMLElement} errorMsg
 * @property {HTMLElement} [text]
 * @property {() => void } onInvalid
 * @property {() => void } onValid
 *
 */

/**
 * @typedef TFormOptions
 *
 * @property {string} baseId - Identifier prefix for form and form elements.
 * @property {TInput[]} inputs - Inputs to be put into the form.
 * @property {TOverlay} overlayInputs - Overlay into which the form will go.
 * @property {() => void} onSubmit
 * @property {string} [title] - Form title.
 * @property {Partial<TButtonOptions>} [buttonOptions={}] - Options for the button.
 *
 */

/**
 * @typedef TForm
  *
  * @property {HTMLDivElement} elem
  * @property {HTMLDivElement} form
  * @property {TButton} button
  * @property {TInput[]} inputs
  * @property {() => void} updateButtonColor
  * @property {() => void} onRequestOver - Button is no longer disabled, hide spinner, hide overlay, revert error color.
  * @property {() => void} onRequestSent - Disable button and make spinner visible.
  * @property {() => void} onInvalid - Turn overlay orange
  */


/* ------------------------------------------------------------------------- */
/* INPUTS */

/** Create input group for enum and helpers.
 *
 * @param {object} options - Additional configuration options.
 * @param {string} options.baseId
 * @param {string} [options.selectInnerHTML] - Select options
 * @returns {TInput}
 *
 */
export function InputKind({ baseId, selectInnerHTML }) {
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


/**
 * @param {object} options
 * @param {string} options.baseId
 * @returns {TInput}
 */
export function InputItems({ baseId }) {
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


/**
 * @param {TFormOptions} options
 * @returns {TForm}
 */
export function Form({ baseId, overlayInputs, title, buttonOptions, inputs, onSubmit }) {
  if (!overlayInputs) throw Error("Missing `overlayInputs`.")
  buttonOptions = buttonOptions || {}

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
  const button = Button({
    id: `${baseId}-button`,
    tooltip: buttonOptions.text || "Submit",
    icon: buttonOptions.icon || "chevron-right",
    iconClasses: ['px-2'],
    text: buttonOptions.text || "Submit",
    classesButton: buttonOptions.classesButton
  })
  elem.appendChild(button.elem)

  const updateButtonColor = overlayInputs.state.colorize?.updateElem(button.elem, (color) => [`btn-outline-${color}`])

  function onRequestOver() {
    overlayInputs.hideOverlay()
    button.toggleSpinner()
    updateButtonColor()
  }

  function onRequestSent() {
    elem.dataset.colorizeColor = "primary"

    // @ts-ignore
    overlayInputs.state.colorize.restart({ color: "primary" })
    button.toggleSpinner()
    updateButtonColor()
  }


  function onInvalid() {
    elem.dataset.colorizeColor = "warning"
    overlayInputs.colorize({ color: "warning" })
    updateButtonColor()
  }

  button.elem.addEventListener("click", onSubmit)
  overlayInputs.overlayContentItems.appendChild(elem)
  overlayInputs.addContent(elem)

  elem.dataset.colorizeColor = "primary"
  updateButtonColor()

  /** @type {TForm} */
  return {
    elem, form, button, updateButtonColor, onRequestOver, onRequestSent, onInvalid,
    inputs
  }

}


