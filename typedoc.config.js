// @ts-check

/**
 * These docs should be turned into pandoc compatible markdown (with ``YAML`` fontmatter).
 * This will make it so that `quarto` can then render these documents and match the rest of the site theming.
 * As a result, these files are ignored by git.
 *
 * @see https://typedoc-plugin-markdown.org/plugins/frontmatter
 * @see https://typedoc-plugin-markdown.org/docs/quick-start
 *
 * @type {import('typedoc').TypeDocOptions & import('./node_modules/typedoc-plugin-markdown/dist/index.d.ts').PluginOptions}
 */
const config = {
  plugin: [
    "typedoc-plugin-missing-exports",
    "typedoc-plugin-markdown",
    "typedoc-plugin-frontmatter",
    "./typedoc.quarto.js",
  ],
  excludeExternals: true,
  entryPoints: [
    "blog/js/live/index.js",
    "blog/js/overlay.js",
    "blog/js/todo.js",
    "blog/js/floaty.js",
  ],
  entryFileName: "index",
  mergeReadme: true,
  readme: "blog/js/_readme.md",
  out: "blog/projects/blog/typedoc",
  outputFileStrategy: "modules",
  formatWithPrettier: true,
  useCodeBlocks: true,
  /** @description Page title will be taken care of by quarto. Title is injected into metadata */
  hidePageTitle: true,
  /** @description So that quarto will recognize the documents. */
  fileExtension: ".qmd",
  /** @description Breadcrumbs will be generated by quarto. */
  hideBreadcrumbs: true,
  /**
   *
   * Eventually a `_metadata.yaml` should be placed in the directory before 
   * the watcher can render (probable using [hooks]()), which will make it no
   * longer necessary to add this to each document.
   *
   */
};

export default config;
