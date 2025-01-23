// @ts-check

/** @type {Partial<import("typedoc").TypeDocOptions>} */
const config = {
  plugin: ['typedoc-plugin-missing-exports'],
  entryPoints: ["blog/js/index.js"],
  out: "blog/build/projects/blog/typedoc",
};

export default config;
