from typing import Annotated, Generic, TypeVar

import panflute as pf
import pydantic

from scripts.filters import util


class ConfigFloatyItemIconify(pydantic.BaseModel):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str
    label: str
    size: Annotated[int | None, pydantic.Field(default=None)]


class ConfigFloatyItemImage(pydantic.BaseModel):
    iconify: ConfigFloatyItemIconify


class ConfigFloatyItem(pydantic.BaseModel):
    image: ConfigFloatyItemImage
    # name: str
    title: str
    description: Annotated[
        str,
        pydantic.Field(description="Description to be displayed in the overlay."),
    ]

    def hydrate_iconify_li(self, *args, **kwargs):
        res = self.hydrate_iconify(*args, **kwargs)
        return pf.ListItem(pf.Para(res))

    def hydrate_iconify_tr(self, *args, **kwargs):
        return

    def hydrate_iconify(
        self,
        size: int,
        key: int,
        *,
        inline: bool = True,
    ):
        """Should make the iconify icon."""

        # NOTE: Font size MUST be in pixels for JS to ensure list item resize.
        attrs = (
            f'icon="{self.image.iconify.set_}:{self.image.iconify.name}"',
            f"aria-label={self.image.iconify.label}",
            f"title={self.title}",
            f"style='font-size: {self.image.iconify.size or size}px;'",
            f"data-key={key}",
        )
        raw = f'<iconify-icon {" ".join(attrs)}></iconify-icon>'

        if inline:
            el = pf.RawInline(raw, format="html")
        else:
            el = pf.RawBlock(raw, format="html")

        return el

    def hydrate_overlay_content_item(
        self,
        size: int,
        key: int,
    ):
        """Should make content to put in overlay-content"""

        # NOTE: Hidden by js.
        overlay_text = pf.RawBlock(
            pf.convert_text(self.description, "markdown", "html")
        )

        return pf.Div(
            pf.Div(
                self.hydrate_iconify(size, key, inline=False),
            ),
            pf.Div(pf.Header(pf.Str(self.title)), classes=["p-1"]),
            pf.Div(overlay_text, classes=["p-1"]),
            classes=["overlay-content-item", "p-5"],
            attributes={"data-key": str(key)},
        )


T_ConfigFloatySection = TypeVar("T_ConfigFloatySection", bound=ConfigFloatyItem)


class ConfigFloatySection(pydantic.BaseModel, Generic[T_ConfigFloatySection]):
    size: int
    size_margin: Annotated[int | None, pydantic.Field(default=None)]
    include_overlay: Annotated[bool, pydantic.Field(default=True)]
    include_titles: Annotated[bool, pydantic.Field(default=False)]

    content: list[T_ConfigFloatySection]

    def hydrate_html_overlay(self, element: pf.Element):
        closure_name = "overlay_" + element.identifier.lower().replace("-", "_")
        size_margin = (
            f"'{self.size_margin}px'" if self.size_margin is not None else "null"
        )
        js = f"let {closure_name} = Overlay('{ element.identifier }', {size_margin})"

        element.content = (
            *element.content,
            pf.Div(
                pf.Div(
                    *(
                        item.hydrate_overlay_content_item(self.size, key)
                        for key, item in enumerate(self.content)
                    ),
                    classes=["overlay-content"],
                ),
                classes=["overlay"],
            ),
            pf.RawBlock(f"<script>{js}</script>"),
        )
        return element

    def hydrate_html(self, element: pf.Element):
        config = self
        list_content = (
            config_image.hydrate_iconify_li(config.size, key)
            for key, config_image in enumerate(config.content)
        )

        element.content = (
            pf.Div(
                pf.BulletList(*list_content),
                classes=["floaty-container"],
            ),
            *element.content,
        )

        if self.include_overlay:
            element = config.hydrate_html_overlay(element)

        return element


class ConfigFloaty(pydantic.BaseModel):
    floaty: dict[str, ConfigFloatySection[ConfigFloatyItem]]


class FilterFloaty(util.BaseFilter):
    filter_name = "floaty"
    filter_config_cls = ConfigFloaty

    doc: pf.Doc
    config: ConfigFloaty

    def __init__(self, doc: pf.Doc):
        super().__init__(doc)
        self.config = ConfigFloaty.model_validate(
            {"floaty": doc.get_metadata("floaty")}  # type: ignore
        )

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        if element.identifier not in self.config.floaty:
            return element

        config = self.config.floaty[element.identifier]
        if self.doc.format == "html" and "floaty-wrapper" in element.classes:
            element = config.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterFloaty)
