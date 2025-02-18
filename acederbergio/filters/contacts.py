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


class ConfigContactsContainer(floaty.ConfigFloatyContainer):
    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def classes_always(self) -> list[str]:
        return [*super().classes_always, "contacts"]


class ConfigContacts(
    floaty.ConfigFloaty[ConfigContactItem, ConfigContactsContainer]
): ...


# NOTE: Only expects one config.
class Config(util.BaseConfig):

    include_descriptions: Annotated[bool, pydantic.Field(default=True)]

    contacts: Annotated[
        dict[str, ConfigContacts | None],
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterContacts(util.BaseFilterHasConfig):
    filter_name = "contacts"
    filter_config_cls = Config

    def __call__(self, element: pf.Element) -> pf.Element:
        if not isinstance(element, pf.Div) or self.config is None:
            return element

        if element.identifier in self.config.contacts:
            config = self.config.contacts[element.identifier]
            if self.doc.format == "latex":
                element = config.hydrate_tex(element)
            elif self.doc.format == "html":
                element = config.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterContacts)
