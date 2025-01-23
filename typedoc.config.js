// @ts-check

/**
 * These docs should be turned into pandoc compatible markdown (with ``YAML`` fontmatter).
 * This will make it so that `quarto` can then render these documents and match the rest of the site theming.
 * As a result, these files are ignored by git.
 *
 * @see https://typedoc-plugin-markdown.org/plugins/frontmatter
 * @see https://typedoc-plugin-markdown.org/docs/quick-start
 *
 * @type {import('typedoc').TypeDocOptions & import('typedoc-plugin-markdown').PluginOptions}
 */

const config = {
  plugin: [
    "typedoc-plugin-missing-exports",
    "typedoc-plugin-markdown",
    "typedoc-plugin-frontmatter",
  ],
  excludeExternals: true,
  entryPoints: [
    "blog/js/live/index.js",
    "blog/js/overlay.js",
    "blog/js/todo.js",
    "blog/js/floaty.js",
  ],
  out: "blog/projects/blog/typedoc",
  outputFileStrategy: "modules",
  fileExtension: ".qmd",
  entryFileName: "index",
  formatWithPrettier: true,
  // NOTE: This is not needed because ``_metadata.yaml``.
  frontmatterGlobals: {
    format: {
      html: {
        "page-layout": "full",
      },
    },
    toc: true,
  },
};

export default config;
