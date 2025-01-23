// @ts-check
//
/** @type {Map<string, TTodoTable>} */
export const TodoTableInstances = new Map()

/** 
 * @typedef TTodoTable
 *
 * @property {HTMLElement|Element} elem - outermost element
 * @property {HTMLElement[]} tables - All tables within `elem`
 * @property {HTMLElement[]} rows - All rows with `elem`.
 * @property {(row: HTMLElement) => void} highlightRow - Highlight a row.
 * @property {() => void} initialize - Initializer.
  *
  */


/** Highlight the rows in table to indicate completion status.
 *
 * Check that the table is well formed.
 * Since quarto is silly about giving ids to tables (and cross references are
 * broken in the version that I am currently using) wrap tables in a div with
 * the id.
 *
 * @param {HTMLElement|Element} elem - The table element wrapped in a table group. This must
 *   have an ``id`` that starts with ``tbl-``.
 * @throws {Error} if the identifier is malformed or missing.
 * @returns {TTodoTable}
 *
 */
export function TodoTable(elem) {
  console.log(elem, elem.id)
  if (!elem.id) throw Error("`TodoTable` requires that `elem` has an `id`.")
  else if (!elem.id.startsWith("tbl-")) throw Error(`\`TodoTable\` requires that element \`id=${elem.id}\` starts with \`tbl-\`.`)

  const tables = Array.from(elem.querySelectorAll("table")) // Because may be a table group
  const rows = Array.from(elem.getElementsByTagName("tr"))

  /** @param {HTMLElement} row */
  function highlightRow(row) {
    let completionColumn = Array.from(row.getElementsByTagName("td"))[1]
    if (!completionColumn?.innerHTML) return
    else if (completionColumn.innerText === "In Progress") row.classList.add("text-yellow")
    else if (completionColumn.innerText === "Canceled") row.classList.add("text-red")
    else if (completionColumn.innerText === "Delayed") row.classList.add("text-pink")
    else row.classList.add("text-green")
  }

  function initialize() {
    tables.map(table => table.classList.add("table-borderless", "table-striped", "text-start"))
    rows.map(highlightRow)
  }

  initialize()

  /** @type TTodoTable */
  const closure = { elem, tables, rows, highlightRow, initialize }
  TodoTableInstances.set(elem.id, closure)

  return closure
}


export function hydrate() {
  const figs = Array.from(document.querySelectorAll(".todo-table.quarto-figure"))
  /** @type {(elem: Element) => TTodoTable} */
  const callback = (elem) => TodoTable(elem)
  figs.map(callback)
}

