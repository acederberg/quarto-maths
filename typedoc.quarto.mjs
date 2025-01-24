// @ts-check
import * as fs from 'fs'
import { MarkdownPageEvent } from './node_modules/typedoc-plugin-markdown/dist/index.js';

const QUARTO_METADATA_PATH = "./blog/projects/blog/typedoc/_metadata.yaml"
const QUARTO_METADATA_CONTENT = `
---
format:
  html:
    page-layout: full
toc: true
`
const QUARTO_RENDER_INFO = `
::: { .callout-note }

**Documentation generated by \`typedoc\` on \`${Date()}\` with 
\`typedoc-plugin-markdown\` (and then rendered by \`quarto\`).**

:::
`


/** Add ``YAML`` metadata to the generated directory */
async function addMetadata() {
  console.log("Creating ``YAML`` metadata for quarto.")
  fs.writeFileSync(QUARTO_METADATA_PATH, QUARTO_METADATA_CONTENT)
}


/** Add individualized document frontmatter.
 *
 * @param {import('./node_modules/typedoc-plugin-markdown/dist/index.d.ts').MarkdownPageEvent} page 
 */
function addFrontMatter(page) {

  /** @type {string} */
  const name = page.model?.name

  page.frontmatter = {
    title: name.charAt(0).toUpperCase() + name.slice(1),
    ...page.frontmatter,
  };
}


/**
 * @param {import('./node_modules/typedoc-plugin-markdown/dist/index.d.ts').MarkdownApplication} app
 */
export function load(app) {
  app.renderer.preRenderAsyncJobs.push(addMetadata)
  app.renderer.markdownHooks.on("page.begin", () => QUARTO_RENDER_INFO)
  app.renderer.on(MarkdownPageEvent.BEGIN, addFrontMatter)
}
