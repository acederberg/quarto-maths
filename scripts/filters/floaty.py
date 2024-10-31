from typing import Annotated

import panflute as pf
import pydantic

from scripts.filters import util


class ConfigFloatyItemIconify(pydantic.BaseModel):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str
    label: str
    size: Annotated[str | None, pydantic.Field(default=None)]


class ConfigFloatyItem(pydantic.BaseModel):
    iconify: ConfigFloatyItemIconify


class ConfigFloatyItemImage(pydantic.BaseModel):
    image: ConfigFloatyItem
    # name: str
    title: str
    description: Annotated[
        str,
        pydantic.Field(description="Description to be displayed in the overlay."),
    ]

    def hydrate_iconify(self, size: str, key: int, *, inline: bool = True):
        """Should make the iconify icon."""
        attrs = (
            f'icon="{self.image.iconify.set_}:{self.image.iconify.name}"',
            f"aria-label={self.image.iconify.label}",
            f"title={self.title}",
            f"style='font-size: {self.image.iconify.size or size};'",
            f"data-key={key}",
        )
        raw = f'<iconify-icon {" ".join(attrs)}></iconify-icon>'

        if inline:
            return pf.RawInline(raw, format="html")
        else:
            return pf.RawBlock(raw, format="html")

    def hydrate_overlay_content_item(self, size: str, key: int):
        """Should make content to put in overlay-content"""

        # NOTE: Hidden by js.
        overlay_text = pf.RawBlock(
            pf.convert_text(self.description, "markdown", "html")
        )

        return pf.Div(
            pf.Div(
                self.hydrate_iconify(size, key, inline=False),
                classes=["p-1", "floaty"],
            ),
            pf.Div(pf.Header(pf.Str(self.title)), classes=["p-1"]),
            pf.Div(overlay_text, classes=["p-1"]),
            classes=["overlay-content-item", "p-5"],
            attributes={"data-key": str(key)},
        )


class ConfigFloatySection(pydantic.BaseModel):
    size: str
    content: list[ConfigFloatyItemImage]

    def create_overlay(self):
        return pf.Div(
            pf.Div(
                *(
                    item.hydrate_overlay_content_item(self.size, key)
                    for key, item in enumerate(self.content)
                ),
                classes=["overlay-content"],
            ),
            classes=["overlay"],
        )


class ConfigFloaty(pydantic.BaseModel):
    floaty: dict[str, ConfigFloatySection]


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

    def floaty_many(self, element: pf.Element):
        if element.identifier not in self.config.floaty:
            return element

        if self.doc.format != "html":
            return element

        config = self.config.floaty[element.identifier]
        list_content = map(
            pf.ListItem,
            map(
                pf.Para,
                (
                    config_image.hydrate_iconify(config.size, key)
                    for key, config_image in enumerate(config.content)
                ),
            ),
        )

        closure_name = "overlay_" + element.identifier.lower().replace("-", "_")
        element.content = (
            pf.Div(
                pf.BulletList(*list_content),
                classes=["floaty-container"],
            ),
            *element.content,
            config.create_overlay(),
            pf.RawBlock(
                f"<script> let {closure_name} = Overlay('{ element.identifier }')</script>"
            ),
        )

        return element

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        if "floaty-wrapper" in element.classes:
            return self.floaty_many(element)
        return element


filter = util.create_run_filter(FilterFloaty)
