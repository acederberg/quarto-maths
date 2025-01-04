from typing import Annotated

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import floaty, util

logger = env.create_logger(__name__)


class ConfigContactItem(floaty.ConfigFloatyItem[floaty.ConfigFloatyContainer]):

    def hydrate_tex(self) -> pf.Inline:
        return pf.RawInline(
            r"\%s { %s } \label{%s}"
            % (self.image.tex.font_awesome, self.description, self.key),
            format="latex",
        )


class ConfigContacts(
    floaty.ConfigFloaty[ConfigContactItem, floaty.ConfigFloatyContainer]
): ...


# NOTE: Only expects one config.
class Config(pydantic.BaseModel):
    floaty_contacts: Annotated[
        dict[str, ConfigContacts | None],
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterContacts(util.BaseFilterHasConfig):
    filter_name = "floaty_contacts"
    filter_config_cls = Config

    def __call__(self, element: pf.Element) -> pf.Element:
        assert self.config is not None
        if not isinstance(element, pf.Div) or self.config is None:
            return element

        if element.identifier in self.config.floaty_contacts:
            config = self.config.floaty_contacts[element.identifier]
            if self.doc.format == "latex":
                element = config.hydrate_tex(element)
            elif self.doc.format == "html":
                element = config.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterContacts)
