// @ts-check


/**
 * @see https://prettier.io/docs/en/configuration.html
 * @see https://prettier.io/docs/en/options
 * @type {import("prettier").Config}
 */
const config = {
  tabWidth: 2,
  semi: false,
  useTabs: false,
  trailingComma: "all",
  bracketSpacing: true,
  plugins: [
    "prettier-plugin-toml",
    "prettier-plugin-jinja-template",
  ],
  overrides: [
    {
      files: ["acederbergio/templates/*.html.j2"],
      options: {
        parser: "jinja-template"
      }
    },
    {
      files: ["blog/**/*.qmd"],
      options: {
        parser: "markdown",
      },
    },


  ]
}


export default config
