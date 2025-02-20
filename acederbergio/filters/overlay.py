"""Pandoc filter for the overlay component.

## Demo and Browser Functionality

See [the demo and examples](/components/overlay/index.html) to learn more about 
filter configuration and the intended functionality and the 
[javascript documentation](/projects/blog/typedoc/overlay.html)
to learn more about how it works in the browser.

Use
-------------------------------------------------------------------------------

The object is to hydrate overlays and add the necessary javascript
(because writing many nested div fences is a garbage pattern and can become quite cumbersome).

Ideally, this filter should turn


```md
::: { #my-overlay }

::: { .overlay-content-item }

It works!

:::

:::
```


into

```html
<div>
    <div id="my-overlay" class="overlay">
        <div class="overlay-content">
            <div class="overlay-content-items">
                <div class="overlay-content-item">
                    It works!
                </div>
            </div>
        </div>
    </div>
    <script>
        Overlay(...)
    </script>
</div>
```
"""

from typing import Annotated, Literal

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import util

logger = env.create_logger(__name__)

BSColor = Annotated[
    # fmt: off
    Literal[
        "indigo", "purple", "pink", "red", "orange", "yellow", "green", "teal", 
        "cyan", "primary", "info", "warning", "danger", "light", "dark", "success",
        "black", "white",
    ] | None,
    # fmt: on
    pydantic.Field(None),
]


class Colorize(pydantic.BaseModel):
    """Colorize configuration for the overlay.

    :ivar color: Background color for the overlay navbar and border.
    :ivar color_text: Color of the navbar text and icons.
    :ivar color_text_hover: Color of the navbar text when hovered.
    """

    color: BSColor
    color_text: BSColor
    color_text_hover: BSColor


class ConfigOverlay(util.BaseHasIdentifier):
    """Overlay filter config.

    :ivar identifier: Unique identifier for the configuration instance. This
      tells the filter which pandoc markdown div to hydrate.
    :ivar colorize: Optional colorize settings.
    :ivar classes: Classes for the overlay element (e.g. ``overlay-blur``).
    :ivar classes_items_wrapper: Classes to add to the overlay items wrapper.
    :ivar classes_items: Classes to add to each overlay item.
    """

    colorize: Annotated[Colorize | None, pydantic.Field(None)]
    classes: util.FieldClasses
    classes_items_wrapper: util.FieldClasses
    classes_items: util.FieldClasses

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def js_name(self) -> str:
        name_segments = list(map(str.title, self.identifier.split("-")))
        return "overlay" + "".join(name_segments)

    def hydrate_html_js(self, element: pf.Div):

        tpl = util.JINJA_ENV.get_template("overlay.js.j2")
        js = tpl.render(element=element, overlay=self)
        js = f"<script type='module' id='{self.identifier + 'script'}'>{ js }</script>"

        return pf.RawBlock(js, format="html")

    def hydrate_html(self, element: pf.Div):

        items = pf.Div(classes=["overlay-content-items"])
        classes_wrap = util.update_classes(list(), self.classes_items_wrapper)

        def hydrate_item(item):
            if not isinstance(item, pf.Div):
                logger.warning(
                    "Encountered non-div in overlay-hydration, `%s`.", item.to_json()
                )
                return item

            util.update_classes(item.classes, self.classes_items)
            wrapped = pf.Div(*item.content, classes=classes_wrap)
            item.content = (wrapped,)
            return item

        items.content = list(map(hydrate_item, element.content))

        content = pf.Div(items, classes=["overlay-content"])

        element.content = [content]
        util.update_classes(element.classes, ["overlay"], self.classes)

        return pf.Div(element, self.hydrate_html_js(element))


class Config(pydantic.BaseModel):
    """Schema used to validate quarto metadata.

    :ivar overlay: An optional list of overlay schemas.
    """

    overlay: Annotated[
        dict[str, ConfigOverlay] | None,
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterOverlay(util.BaseFilter):
    """Overlay filter."""

    filter_name = "overlay"

    _config: Config | None

    def __init__(self, doc: pf.Doc | None = None):
        super().__init__(doc=doc)
        self._config = None

    @property
    def config(self) -> Config | None:
        if self._config is not None:
            return self._config

        data = self.doc.get_metadata("overlay")  # type: ignore
        if data is None:
            self._config = None
            return None

        self._config = Config.model_validate({"overlay": data})
        return self._config

    def __call__(self, element: pf.Element):
        if self.doc.format != "html":
            return element

        if (
            not isinstance(element, pf.Div)
            or self.config is None
            or (config := self.config.overlay) is None
        ):
            return element

        if (
            config_overlay := config.get(element.identifier)
        ) is None or self.doc.format != "html":
            return element

        element = config_overlay.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterOverlay)
