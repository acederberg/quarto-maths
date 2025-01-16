import json

import panflute as pf

from acederbergio import env
from acederbergio.filters import util

logger = env.create_logger(__name__)


class FilterLive(util.BaseFilter):
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

    filter_name = "live"

    def __call__(self, element: pf.Element) -> pf.Element:
        return element

    def prepare(self, doc: pf.Doc) -> None:
        super().prepare(doc)

        logger.info(
            "This is a test to ensure that filter logs do not show up in stdout."
        )
        # data = doc.get_metadata("live")

        include_raw = doc.get_metadata("live_include")  # type: ignore
        include = include_raw if include_raw is not None else True
        if not env.ENV_IS_DEV or self.doc.format != "html" or not include:
            return

        if self.doc.get_metadata("live_disable"):  # type: ignore
            return

        file_path = self.doc.get_metadata("live_file_path")  # type:ignore
        if not file_path:
            logger.warning("Could not find file path.")
            return

        # NOTE: Depends on should be a list of paths relative to the project root.
        targets = [file_path]
        depends_on = self.doc.get_metadata("live_depends_on")  # type: ignore
        if depends_on and isinstance(depends_on, list):
            targets += depends_on

        # NOTE: Look for names of additional elements to populate.
        options = dict(
            quarto_logs=self.doc.get_metadata("live_id_quarto_logs"),  # type: ignore
            quarto_logs_parent=self.doc.get_metadata("live_id_quarto_logs_parent"),  # type: ignore
            quarto_banner_include=self.doc.get_metadata("live_quarto_banner_include"),  # type: ignore
            last=self.doc.get_metadata("live_quarto_logs_last"),  # type: ignore
            reload=self.doc.get_metadata("live_reload"),  # type: ignore
            filters={"targets": targets},
        )

        js = util.JINJA_ENV.get_template("live.j2").render(options=options)
        script = pf.RawBlock(
            f"<script id='quarto-hydrate' type='module'>{ js }</script> ",
            format="html",
        )

        # TODO: Simplify this JS, make this configurable using this live filter.
        overlay_and_script = pf.Div(
            pf.Div(
                pf.Div(
                    pf.Div(classes=["overlay-content-items"]),
                    classes=["overlay-content"],
                ),
                classes=["overlay", "when-navbar"],
                identifier="quarto-overlay",
            ),
            script,
        )
        doc.content.insert(0, overlay_and_script)


filter = util.create_run_filter(FilterLive)
