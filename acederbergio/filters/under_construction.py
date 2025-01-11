import secrets
from typing import Annotated

import panflute as pf
import pydantic
from pydantic.v1.utils import deep_update

from acederbergio import env
from acederbergio.filters import floaty, util

logger = env.create_logger(__name__)

CLASSES = {f"under-construction-{key}": key for key in range(1, 7)}
MSG_HEAD_PAGE = "This Page is Currently Under Construction."
MSG_HEAD_SECTION = "This Section is Currently Under Construction."
MSG_DONOTPANIC = (
    "Do not panic, you (the user) have done nothing wrong. There will be "
    "something here soon but changes are yet to be deployed."
)


def create_config(v: dict):
    if not isinstance(v, dict):
        raise ValueError

    if "content" in v and not isinstance(v["content"], dict):
        raise ValueError

    defaults = dict(
        identifier=f"under-construction-{secrets.token_urlsafe(16)}",
        content=dict(
            key="under-construction",
            title=MSG_HEAD_PAGE,
            description=MSG_HEAD_SECTION,
            label="under-construction",
            image=dict(
                iconify=dict(set="misc", name="construction"),
                bootstrap=dict(name="hammer"),
            ),
        ),
        container=dict(
            mode="iconify",
            include_titles=True,
            include_descriptions=True,
            columns=1,
            size=1,
        ),
    )

    defaults = deep_update(defaults, v)
    defaults["content"] = {defaults["content"]["key"]: defaults["content"]}

    return ConfigUnderConstruction.model_validate(defaults)


def validate_configs(v):
    if v is None:
        return v
    v = util.content_from_list_identifier(v)
    v = {k: create_config(w) for k, w in v.items()}
    return v


class ConfigContainer(floaty.ConfigFloatyContainer):

    @pydantic.computed_field
    @property
    def classes_always(self) -> list[str]:
        return ["under-construction", f"under-construction-{self.size}", "floaty"]


class ConfigUnderConstruction(
    floaty.ConfigFloaty[floaty.ConfigFloatyItem, ConfigContainer]
):

    def hydrate(
        self,
        element: pf.Element,
    ):
        element = super().hydrate_html(element)
        element.classes.append("under-construction")

        return element


class Config(util.BaseConfig):
    under_construction: Annotated[
        dict[str, ConfigUnderConstruction] | None,
        pydantic.Field(
            default=None,
            description=(
                "Map from element id's to their custom configuration. Custom "
                "configuration will be merged into the defaults"
            ),
        ),
        pydantic.BeforeValidator(validate_configs),
    ]


class FilterUnderConstruction(util.BaseFilterHasConfig[Config]):
    filter_name = "under_construction"
    filter_config_cls = Config

    def is_under_construction(self, element: pf.Element) -> floaty.FieldSize | None:
        if "under-construction" == element.identifier:
            return 1

        # NOTE: Probably should just use hash.
        item = next(
            (
                item
                for item in element.classes
                if item.startswith("under-construction-")
            ),
            None,
        )

        if item is not None:
            if item not in CLASSES:
                raise ValueError(
                    f"Invalid size `{item}`, must be one of `{set(CLASSES)}`."
                )

            return CLASSES[item]  # type: ignore

        return None

    def __call__(self, element: pf.Element):
        if self.config is None or not isinstance(element, pf.Div):
            return element

        # NOTE: Generally use `#under-construction` for pages and
        #       `#under-construction-{size}` for sections.
        if element.identifier in self.config.under_construction:
            logger.debug(
                "Found target with id ``%s`` for ``under_construction``.",
                element.identifier,
            )
            config = self.config.under_construction[element.identifier]
            return config.hydrate(element)

        if size := self.is_under_construction(element):
            logger.debug("Found ``under_construction`` div for for `%s`.", size)
            config = create_config(dict(container=dict(size=size)))
            element = config.hydrate(element)

            return element

        return element


filter = util.create_run_filter(FilterUnderConstruction)
