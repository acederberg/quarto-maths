from typing import Annotated, Literal

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import overlay, util

logger = env.create_logger(__name__)

FieldCount = Annotated[
    int,
    pydantic.Field(1, description="Initial number of logs to recieve from websocket."),
]


class LiveQuartoConfig(util.BaseConfig):
    renders: Annotated[
        overlay.ConfigOverlay,
        pydantic.Field(
            description="Overlay to put the render results into.",
            default_factory=lambda: {
                "identifier": "quarto-live-renders",
                "classes": ["live-overlay"],
            },
            validate_default=True,
        ),
    ]
    responses: Annotated[
        overlay.ConfigOverlay,
        pydantic.Field(
            description="Overlay to put results from API calls into.",
            default_factory=lambda: {
                "identifier": "quarto-live-responses",
                "classes": ["live-overlay"],
                "colorize": {
                    "color": "primary",
                    "color_text": "black",
                    "color_text_hover": "white",
                },
            },
            validate_default=True,
        ),
    ]
    inputs: Annotated[
        overlay.ConfigOverlay,
        pydantic.Field(
            description="Overlay for API request inputs.",
            default_factory=lambda: {
                "identifier": "quarto-live-inputs",
                "classes": ["live-overlay"],
            },
            validate_default=True,
        ),
    ]

    targets: Annotated[
        list[str],
        pydantic.Field(
            default=list(),
            description="Files to listen for changes in through the websocket (in addition to the page on which the filter is run.",
        ),
    ]
    # NOTE: When using a single listener for logs,
    reload: Annotated[bool, pydantic.Field(True)]

    count: FieldCount

    table: Annotated[
        util.BaseElemConfig,
        pydantic.Field(
            default_factory=lambda: dict(
                identifier="live-quarto-renders-table",
                classes=["table", "table-borderless", "quarto", "p-2"],
            ),
            validate_default=True,
            description="Table details. Table is where new logs are added as rows.",
        ),
    ]
    container: Annotated[
        util.BaseElemConfig,
        pydantic.Field(
            default_factory=lambda: dict(
                identifier="live-quarto-renders-container",
                classes=["tab-pane", "fade"],
            ),
            validate_default=True,
            description="Container details. Container is the element in which the table scroll is set to keep up with logs.",
        ),
    ]
    include_logs: Annotated[bool, pydantic.Field(False)]
    js: Annotated[list[str] | None, pydantic.Field(None)]

    @pydantic.computed_field
    @property
    def overlays(self) -> dict[str, overlay.ConfigOverlay]:
        return {
            overlay.identifier: overlay
            for overlay in (self.renders, self.responses, self.inputs)
        }

    def hydrate(self, element: pf.Div):
        logger.warning("%s", self.js)
        template = util.JINJA_ENV.get_template("live_quarto_renders.html.j2")
        innerHTML = pf.RawBlock(template.render(quarto=self, element=element))

        return innerHTML


class LiveServerConfig(pydantic.BaseModel):
    """Configuration for the server logs page."""

    count: FieldCount
    table: Annotated[
        util.BaseElemConfig,
        pydantic.Field(
            default_factory=lambda: dict(
                identifier="live-server-log-table",
                classes=["table", "table-borderless", "terminal", "p-2"],
            ),
            validate_default=True,
        ),
    ]
    container: Annotated[
        util.BaseElemConfig,
        pydantic.Field(
            default_factory=lambda: dict(
                identifier="live-server-log-container",
                classes=["tab-pane", "fade"],
            ),
            validate_default=True,
        ),
    ]

    def hydrate(self, element: pf.Div):
        template = util.JINJA_ENV.get_template("live_server_log.html.j2")
        innerHTML = pf.RawBlock(template.render(server=self, element=element))

        return innerHTML


class LiveConfig(pydantic.BaseModel):
    quarto: Annotated[
        LiveQuartoConfig | None,
        pydantic.Field(default_factory=dict, validate_default=True),
        util.ValidatorIgnoreFalsy,
    ]
    server: Annotated[
        LiveServerConfig | None,
        pydantic.Field(
            default_factory=dict,
            validate_default=True,
        ),
        util.ValidatorIgnoreFalsy,
    ]

    include_quarto: Annotated[bool, pydantic.Field(True)]
    include_server: Annotated[bool, pydantic.Field(False)]


class Config(pydantic.BaseModel):
    live: Annotated[
        LiveConfig | Literal[False],
        pydantic.Field(
            default_factory=dict,
            validate_default=True,
            description="Set to ``false`` to exclude this filter.",
        ),
    ]

    # @pydantic.field_validator("live", mode="before")
    # def validate_live(cls, v):
    #     logger.warning(v)
    #     if v == "":
    #         return dict()
    #     return v

    # # =self.doc.get_metadata("live_id_quarto_logs"),  # type: ignore
    # # quarto_logs_parent=self.doc.get_metadata("live_id_quarto_logs_parent"),  # type: ignore
    # quarto_banner_include = (self.doc.get_metadata("live_quarto_banner_include"),)  # type: ignore
    # last = (self.doc.get_metadata("live_quarto_logs_last"),)  # type: ignore
    # reload = (self.doc.get_metadata("live_reload"),)  # type: ignore
    # filters = ({"targets": targets},)


class FilterLive(util.BaseFilterHasConfig):
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
    filter_config_cls = Config
    filter_config_default = dict()

    def __call__(self, element: pf.Element) -> pf.Element:
        if (
            self.doc.format != "html"
            or not isinstance(element, pf.Div)
            or self.config is None
            or (live := self.config.live) is None
        ):
            return element

        # NOTE: Hydrate overlays for the banner.
        if (
            quarto := live.quarto
        ) is not None and element.identifier in quarto.overlays:
            config = quarto.overlays[element.identifier]
            element = config.hydrate_html(element)

            return element

        # NOTE: Hydrate server log / quarto render container with table.
        for item in (live.server, live.quarto):
            if item is not None and element.identifier == item.container.identifier:
                return item.hydrate(element)

        return element

    def prepare(self, doc: pf.Doc) -> None:
        super().prepare(doc)
        if (config := self.config) is None:
            raise ValueError()

        if config.live is False:
            logger.warning(
                "Ignoring `live` filter for `%s`.", doc.get_metadata("live_file_path")
            )
            return

        # NOTE: This is the only setting that does not go in the live config.
        file_path = self.doc.get_metadata("live_file_path")  # type:ignore
        if not file_path:
            logger.warning("Live could not find file path.")
            return

        if (live := config.live) is None:
            logger.warning("Live filter disabled for `%s`.")
            return
        elif not env.ENV_IS_DEV or self.doc.format != "html":
            logger.debug("Live filter ignoring `%s` for .")
            return

        # NOTE: Look for names of additional elements to populate.
        js = util.JINJA_ENV.get_template("live.js.j2").render(
            filters=(
                (
                    {"targets": [file_path, *live.quarto.targets]}
                    if "*" not in live.quarto.targets
                    else {}
                )
                if live.quarto is not None
                else None
            ),
            live=live,
        )

        out = pf.Div(
            pf.RawBlock(
                f"<script id='quarto-hydrate' type='module'>{ js }</script>",
                format="html",
            ),
            identifier="live",
        )

        if live.quarto:
            out.content.insert(
                -1,
                pf.Div(
                    pf.Div(identifier=live.quarto.renders.identifier),
                    pf.Div(identifier=live.quarto.responses.identifier),
                    pf.Div(identifier=live.quarto.inputs.identifier),
                    identifier="live-overlay",
                ),
            )

        # TODO: Simplify this JS, make this configurable using this live filter.
        # NOTE: Overlays will be hydrated by the overlay filter.
        doc.content.insert(-1, out)


filter = util.create_run_filter(FilterLive)
