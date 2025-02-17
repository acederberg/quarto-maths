// @ts-check
/** @module
 *
 * Used to put raw ascii art into divs and ensure that the grid is properly 
 * set.
 *
 * Thank you to https://patorjk.com/software/taag
 */

/** @typedef {object} T_AsciiCharacterOptions
 *
 * @property {boolean} linesKeepEmpty - Keep empty lines.
 * @property {number} whitespaceSize - Ammount of (hopefull) front whitespace characters to strip from front.
 * @property {number} whitespaceKeep - Strip front whitespace or not?
 * @property {number} whitespaceSizeAppend - Number of whitespace to put at the end of each line.
 *
 */

/** @typedef {object} T_AsciiCharacterStringItem
 *
 * @property {Partial<T_AsciiCharacterOptions>} options? - Options for parsing a character.
 * @property {string} character - Text for the character.
 *
 */

/**
 * @typedef {object} T_AsciiCharacterStringOptions
 *
 * @property {HTMLElement} elem?
 * @property {Partial<T_AsciiCharacterOptions>} charOptions? - Default options.
 *
 */


/** @param {string[]} lines 
 * @returns {number} 
 */
function getWhiteSpace(lines) {
  const reWhitespace = /^(?<whitespace> *)/
  const whitespaceSizes = lines.map(
    line => line.match(reWhitespace)?.groups?.whitespace.length || 0
  )
  // console.log("whitespaceSizes", whitespaceSizes)
  return Math.min(...whitespaceSizes.filter(count => count > 0))
}

/** @param {string} char - Ascii art character as a string. This might come 
 *  with some preceeding white space, which should be stripped. This is because
 *  often this input will be written in a backticks string which will be 
 *  indented propertly.
 *  @param {Partial<T_AsciiCharacterOptions>} options
 *  @returns {HTMLSpanElement}
 */
export function AsciiCharacter(char, { linesKeepEmpty, whitespaceSize, whitespaceKeep, whitespaceSizeAppend } = {}) {
  const asciiText = char
  let asciiLines = asciiText.split("\n")

  // Remove preceeding whitespace. Filter out empty lines.
  if (!whitespaceKeep) {
    whitespaceSize = whitespaceSize || getWhiteSpace(asciiLines)
    asciiLines = asciiLines.map(line => line.slice(whitespaceSize))
  }

  if (linesKeepEmpty) asciiLines = asciiLines.filter(line => line.length > 0)

  const asciiCols = Math.max(...asciiLines.map(item => item.length)) + (whitespaceSizeAppend || 0)
  const elemOut = document.createElement("span")
  elemOut.classList.add("ascii-art-letter")
  elemOut.style.gridTemplateColumns = `repeat(${asciiCols}, 1ch)`


  asciiLines.forEach(line => {
    line = line.padEnd(asciiCols, " ")
    line.split("").forEach((char) => {
      const charDiv = document.createElement("span");
      charDiv.textContent = char === " " ? "\u00A0" : char; // Preserve spaces
      elemOut.appendChild(charDiv);
    })
  })

  return elemOut
}

/** 
 * @param {Array<T_AsciiCharacterStringItem|string>} items
 * @param {Partial<T_AsciiCharacterStringOptions>} options
 */
export function AsciiCharacterString(items, options = {}) {

  let elem = options.elem
  if (!elem) {
    elem = document.createElement("span")
    elem.classList.add("ascii-art")
  }

  const characters = items.map(item => {
    const char = (
      typeof (item) == 'string'
        ? AsciiCharacter(item, options.charOptions)
        : AsciiCharacter(item.character, item.options || options)
    )
    elem.appendChild(char)
    return char
  })

  return { characters, elem }
}


export function forLandingPage() {
  const landingPageBannerTitle = document.getElementById("acederberg-io")
  if (!landingPageBannerTitle) throw Error("Could not find `acederberg-io`.")

  /** @returns {Partial<T_AsciiCharacterStringOptions>} */
  const create_opts = () => {
    const elem = document.createElement("span")
    elem.classList.add("ascii-flex")
    return { charOptions: { whitespaceSizeAppend: 1 }, elem: elem }
  }

  /** @type {T_AsciiCharacterStringItem} */
  const langleFinal = { character: langle, options: { whitespaceSizeAppend: 8 } }

  const langles = AsciiCharacterString([langleFinal])
  langles.elem.classList.add("ascii-art-green")

  // Primary Grouping.
  const AA = AsciiCharacterString([A], create_opts())
  AA.elem.classList.add("ascii-art-teal")

  const CED = AsciiCharacterString([C, E, D, E, R], create_opts())
  const ERB = AsciiCharacterString([B], create_opts())
  const ERG = AsciiCharacterString([E, R, G], create_opts())

  CED.elem.classList.add("ascii-art-yellow")
  ERB.elem.classList.add("ascii-art-yellow")
  ERG.elem.classList.add("ascii-art-yellow")

  const IO = AsciiCharacterString([dot, I, O,], create_opts())
  IO.elem.classList.add("ascii-art-red")

  const _ = AsciiCharacterString([underscore], create_opts())
  _.elem.classList.add("ascii-art-blinks", "ascii-art-green")

  // Secondary Grouping.
  const row_1 = document.createElement("span")
  row_1.classList.add("ascii-flex")
  row_1.appendChild(AA.elem)
  row_1.appendChild(CED.elem)


  const row_2 = document.createElement("span")
  row_2.classList.add("ascii-flex")
  row_2.appendChild(ERB.elem)
  row_2.appendChild(ERG.elem)

  const row_3 = document.createElement("span")
  row_3.classList.add("ascii-flex")
  row_3.appendChild(IO.elem)
  row_3.appendChild(_.elem)


  // Tertiary Grouping.
  const right = document.createElement("span")
  right.classList.add("ascii-art")
  right.id = "landing-page-banner-title-right"
  right.appendChild(row_1)
  right.appendChild(row_2)
  right.appendChild(row_3)

  landingPageBannerTitle.replaceChildren(right)

  // const left = document.getElementById("landing-page-banner-title-left")
  // const leftContent = document.createElement("span")
  // leftContent.classList.add("assii-art")
  // leftContent.id = "landing-page-banner-title-left"
  // leftContent.appendChild(langles.elem)
  // left?.appendChild(leftContent)
  //

  /*
  /// Posts
  const posts = document.getElementById("landing-page-navigation-posts")
  if (!posts) throw new Error()

  const POSTS = AsciiCharacterString([B, L, O, G, underscore, P, O, S, T, S])
  posts.replaceChildren(POSTS.elem)

  /// Projects
  const projects = document.getElementById("landing-page-navigation-projects")
  if (!projects) throw new Error()

  const PROJECTS = AsciiCharacterString([P, R, O, J, E, C, T, S])
  projects.replaceChildren(PROJECTS.elem)


  const resume = document.getElementById("landing-page-navigation-resume")
  if (!resume) throw new Error()

  const RESUME = AsciiCharacterString([R, E, S, U, M, E])
  resume.replaceChildren(RESUME.elem)
  */

}


export const dot = `






  $$\\
  \\__|`

export const A = `
   $$$$$$\\
  $$  __$$\\
  $$ /  $$ |
  $$$$$$$$ |
  $$  __$$ |
  $$ |  $$ |
  $$ |  $$ |
  \\__|  \\__|`
export const B = `
  $$$$$$$\\
  $$  __$$\\
  $$ |  $$ |
  $$$$$$$\\ |
  $$  __$$\\
  $$ |  $$ |
  $$$$$$$  |
  \\_______/`

export const C = `
   $$$$$$\\
  $$  __$$\\
  $$ /  \\__|
  $$ |
  $$ |
  $$ |  $$\\
  \\$$$$$$  |
   \\______/`

export const D = `
  $$$$$$$\\
  $$  __$$\\
  $$ |  $$ |
  $$ |  $$ |
  $$ |  $$ |
  $$ |  $$ |
  $$$$$$$  |
  \\_______/`

export const E = `
  $$$$$$$$\\
  $$  _____|
  $$ |
  $$$$$\\
  $$  __|
  $$ |
  $$$$$$$$\\
  \\________|`

export const F = `
  $$$$$$$$\\
  $$  _____|
  $$ |
  $$$$$\\
  $$  __|
  $$ |
  $$ |
  \\__|`

export const G = `
   $$$$$$\\
  $$  __$$\\
  $$ /  \\__|
  $$ |$$$$\\
  $$ |\\_$$ |
  $$ |  $$ |
  \\$$$$$$  |
   \\______/`

export const H = `
  $$\\   $$\\
  $$ |  $$ |
  $$ |  $$ |
  $$$$$$$$ |
  $$  __$$ |
  $$ |  $$ |
  $$ |  $$ |
  \\__|  \\__|`

export const I = `
  $$$$$$\\
  \\_$$  _|
    $$ |
    $$ |
    $$ |
    $$ |
  $$$$$$\\
  \\______|`

export const J = `
     $$$$$\\
     \\__$$ |
        $$ |
        $$ |
  $$\\   $$ |
  $$ |  $$ |
  \\$$$$$$  |
   \\______/`

export const K = `
  $$\\   $$\\
  $$ | $$  |
  $$ |$$  /
  $$$$$  /
  $$  $$<
  $$ |\\$$\\
  $$ | \\$$\\
  \\__|  \\__|`


export const L = `
  $$\\
  $$ |
  $$ |
  $$ |
  $$ |
  $$ |
  $$$$$$$$\\
  \\________|`

export const M = `
  $$\\      $$\\
  $$$\\    $$$ |
  $$$$\\  $$$$ |
  $$\\$$\\$$ $$ |
  $$ \\$$$  $$ |
  $$ |\\$  /$$ |
  $$ | \\_/ $$ |
  \\__|     \\__|`

export const N = `
  $$\\   $$\\
  $$$\\  $$ |
  $$$$\\ $$ |
  $$ $$\\$$ |
  $$ \\$$$$ |
  $$ |\\$$$ |
  $$ | \\$$ |
  \\__|  \\__|`

export const O = `
   $$$$$$\\
  $$  __$$\\
  $$ /  $$ |
  $$ |  $$ |
  $$ |  $$ |
  $$ |  $$ |
   $$$$$$  |
   \\______/`

export const P = `
  $$$$$$$\\
  $$  __$$\\
  $$ |  $$ |
  $$$$$$$  |
  $$  ____/
  $$ |
  $$ |
  \\__|`

export const Q = `
   $$$$$$\\
  $$  __$$\\
  $$ /  $$ |
  $$ |  $$ |
  $$ |  $$ |
  $$ $$\\$$ |
  \\$$$$$$ /
   \\___$$$\\
       \\___|`

export const R = `
  $$$$$$$\\
  $$  __$$\\
  $$ |  $$ |
  $$$$$$$  |
  $$  __$$<
  $$ |  $$ |
  $$ |  $$ |
  \\__|  \\__|`

export const S = `
   $$$$$$\\
  $$  __$$\\
  $$ /  \\__|
  \\$$$$$$\\
   \\____$$\\
  $$\\   $$ |
  \\$$$$$$  |
   \\______/`

export const T = `
  $$$$$$$$\\
  \\__$$  __|
     $$ |
     $$ |
     $$ |
     $$ |
     $$ |
     \\__|`

export const U = `
  $$\\   $$\\
  $$ |  $$ |
  $$ |  $$ |
  $$ |  $$ |
  $$ |  $$ |
  $$ |  $$ |
  \\$$$$$$  |
   \\______/`

export const V = `
  $$\\    $$\\
  $$ |   $$ |
  $$ |   $$ |
  \\$$\\  $$  |
   \\$$\\$$  /
    \\$$$  /
     \\$  /
      \\_/`

export const W = `
  $$\\      $$\\
  $$ | $\\  $$ |
  $$ |$$$\\ $$ |
  $$ $$ $$\\$$ |
  $$$$  _$$$$ |
  $$$  / \\$$$ |
  $$  /   \\$$ |
  \\__/     \\__|`

export const X = `
  $$\\   $$\\
  $$ |  $$ |
  \\$$\\ $$  |
   \\$$$$  /
   $$  $$<
  $$  /\\$$\\
  $$ /  $$ |
  \\__|  \\__|`

export const Y = `
  $$\\     $$\\
  \\$$\\   $$  |
   \\$$\\ $$  /
    \\$$$$  /
     \\$$  /
      $$ |
      $$ |
      \\__|`

export const Z = `
  $$$$$$$$\\
  \\____$$  |
      $$  /
     $$  /
    $$  /
   $$  /
  $$$$$$$$\\
  \\________|`


export const langle = `
  $$\\
  \\$$\\
   \\$$\\
    \\$$\\
    $$  |
   $$  /
  $$  /
  \\__/`


export const underscore = `






  $$$$$$$$$$$\\ 
  \\___________|`



