from typing import Annotated

import panflute as pf
import pydantic

from scripts.filters import util


class ConfigFloatyItemIconify(pydantic.BaseModel):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str
    label: str
    title: str
    size: Annotated[str | None, pydantic.Field(default=None)]

    def hydrate(self, size: int):
        attrs = (
            f'icon="{self.set_}:{self.name}"',
            f"aria-label={self.label}",
            f"title={self.title}",
            f"style='font-size: {self.size or size};'",
        )

        return pf.RawInline(
            f'<iconify-icon {" ".join(attrs)}></iconify-icon>',
            format="html",
        )


class ConfigFloatyItem(pydantic.BaseModel):
    iconify: ConfigFloatyItemIconify


class ConfigFloatyItemImage(pydantic.BaseModel):
    image: ConfigFloatyItem
    description: Annotated[
        str,
        pydantic.Field(description="Description to be displayed in the overlay."),
    ]


class ConfigFloatySection(pydantic.BaseModel):
    size: str
    content: list[ConfigFloatyItemImage]


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

    def floaty(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        if (
            "floaty-container" not in element.classes
            or "floaty-ignore" in element.classes
        ):
            return element

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
                    config_image.image.iconify.hydrate(config.size)
                    for config_image in config.content
                ),
            ),
        )

        element.content = (pf.BulletList(*list_content),)

        return element

    def __call__(self, element: pf.Element):
        return self.floaty(element)


filter = util.create_run_filter(FilterFloaty)
