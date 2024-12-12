import json

import panflute as pf

from acederbergio import env
from acederbergio.filters import util

logger = env.create_logger(__name__)

# root_logger = logging.getLogger("root")
# root_logger.warning("Warning from root logger.")
# root_logger.critical("Critical from root logger.")
#
# logger.warning("Warning from dev filter logger.")
# logger.critical("Critical from dev filter logger.")


class DevFilter(util.BaseFilter):
    """Since intercepting ``main`` an modifying its content is not really
    possible (its parent does not contain the body, and it will be tricky
    to hunt that down), this filter looks for a div with `id=quarto-overlay`
    and replaces it with the full div and some scripts.

    Hydrated output should look something like

    ```html
        <div id='quarto-overlay' class='overlay'>
          <div class='overlay-content'>
            <div id='quarto-overlay-content' class='p-3' >
            </div>
          </div>
        </div>
        <script>...</script>
    ```

    A few importants notes are:

    - The script will only work if ``blog/js/live.js`` is included in the headers.
    - This filter should only modify the content when in dev mode.
    - Metadata providing the filepath should be injected on render from
      ``acederbergio/api/quarto.py:Handler.render_qmd``.
    - Additional files to watch can be specified in ``depends_on`` of the metadata.

    The desired functionality is that:

    - The error overlay shows up for failed renders.
    - A banner showing the last render is added for successful renders.
    - The page does not attempt websocket connections in production, since these
      websockets will not be available.
    """

    filter_name = "dev"

    def __call__(self, element: pf.Element) -> pf.Element:
        # util.record(__name__)
        # util.record(logger.handlers)
        if not env.ENV_IS_DEV or self.doc.format != "html":
            return element

        if (
            not isinstance(element, pf.Div)
            or not element.identifier == "quarto-overlay"
        ):
            return element

        file_path = self.doc.get_metadata("file_path")  # type:ignore
        if not file_path:
            logger.warning("Could not find file path.")
            return element

        # NOTE: Depends on should be a list of paths relative to the project root.
        targets = [file_path]
        depends_on = self.doc.get_metadata("depends_on")  # type: ignore
        if depends_on and isinstance(depends_on, list):
            targets += depends_on

        filters = json.dumps({"targets": targets})
        return pf.Div(
            pf.Div(
                pf.Div(
                    pf.Div(
                        identifier="quarto-overlay-content",
                        classes=["p-3"],
                    ),
                    classes=["overlay-content"],
                ),
                classes=["overlay"],
                identifier="quarto-overlay",
            ),
            pf.RawBlock(
                """
                <script>
                  globalThis.quartoDevOverlay = Overlay(document.getElementById("quarto-overlay"))
                  globalThis.quartoDev = Quarto({
                    filters: %s,
                    quartoOverlayControls: globalThis.quartoDevOverlay,
                    quartoOverlayContent: document.querySelector('#quarto-overlay-content'),
                  })
                </script>
                """
                % filters,
                format="html",
            ),
        )


filter = util.create_run_filter(DevFilter)
