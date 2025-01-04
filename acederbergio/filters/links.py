from typing import Annotated

import panflute as pf
import pydantic

from acederbergio.filters import floaty, util


class ConfigLinkItem(floaty.ConfigFloatyItem["ConfigLinksContainer"]):
    def hydrate_tex(self) -> pf.Inline:

        out = pf.RawInline(
            r"\%s { %s } \label{%s}"
            % (
                self.image.tex.font_awesome,
                self.title,
                self.description,
            ),
            format="latex",
        )

        if self.href is None:
            return out

        return pf.Link(out, url=self.href, title=self.title)


class ConfigLinksContainer(floaty.ConfigFloatyContainer):

    @pydantic.computed_field
    @property
    def classes_always(self) -> list[str]:
        return [*super().classes_always, "links"]


class ConfigLinks(floaty.ConfigFloaty[ConfigLinkItem, ConfigLinksContainer]): ...


class Config(pydantic.BaseModel):
    floaty_links: Annotated[
        dict[str, ConfigLinks | None],
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterLinks(util.BaseFilterHasConfig):
    filter_name = "floaty_links"
    filter_config_cls = Config

    def __call__(self, element: pf.Element) -> pf.Element:
        assert self.config is not None
        if not isinstance(element, pf.Div) or self.config is None:
            return element

        if element.identifier in self.config.floaty_links:
            config = self.config.floaty_links[element.identifier]
            if self.doc.format == "latex":
                element = config.hydrate_tex(element)
            elif self.doc.format == "html":
                element = config.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterLinks)
