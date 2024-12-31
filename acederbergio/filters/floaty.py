"""Filters to generate floaty from configuration.

For exact detail on how to use, see `./blog/dev/componants/floaty.qmd`.
"""

import secrets
from typing import Annotated, Generic, Literal, TypeAlias, TypeVar

import panflute as pf
import pydantic
from pydantic.v1.utils import deep_update

from acederbergio import env
from acederbergio.filters import overlay, util

logger = env.create_logger(__name__)


FieldInclude = Annotated[bool, pydantic.Field(default=True)]
FieldKey = Annotated[
    str,
    pydantic.Field(default_factory=lambda: secrets.token_urlsafe(8)),
]
FieldMode = Annotated[
    Literal["bootstrap", "iconify"],
    pydantic.Field(default="iconify"),
]
FieldModeOptional = Annotated[FieldMode | None, pydantic.Field(None)]
FieldHref = Annotated[
    str | None,
    pydantic.Field(
        description=(
            "A link to go to when clicked on. Should open in a new tab."
            "Will be ignored when an overlay is included."
        ),
        default=None,
    ),
]
FieldLabel = Annotated[str | None, pydantic.Field(default=None)]
FieldAttributes = Annotated[dict[str, str] | None, pydantic.Field(None)]


class BaseConfigFloatyItemImageItem(pydantic.BaseModel):
    classes: util.FieldClasses
    attributes: FieldAttributes


class ConfigFloatyItemBootstrap(BaseConfigFloatyItemImageItem):
    name: str


class ConfigFloatyItemIconify(BaseConfigFloatyItemImageItem):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str


class ConfigFloatyItemImage(pydantic.BaseModel):
    iconify: Annotated[
        ConfigFloatyItemIconify,
        pydantic.Field(
            default_factory=lambda: dict(set="simple-icons", name="quarto"),
            validate_default=True,
        ),
    ]

    bootstrap: Annotated[
        ConfigFloatyItemBootstrap,
        pydantic.Field(
            default_factory=lambda: dict(name="bug"),
            validate_default=True,
        ),
    ]


# class IconifyKwargs(TypedDict):
#
#     inline: NotRequired[bool]
#     _parent: Required["ConfigFloaty"]


class ConfigFloatyItem(pydantic.BaseModel):
    key: FieldKey

    mode: FieldModeOptional
    image: ConfigFloatyItemImage
    href: FieldHref
    title: str
    label: FieldLabel

    tooltip: Annotated[str | None, pydantic.Field(default=None)]
    classes: Annotated[list[str] | None, pydantic.Field(default=None)]  # card classes.

    def get_attributes(
        self, *, _parent: "ConfigFloaty", mode: FieldMode | None = None
    ) -> dict[str, str]:

        mode = self.resolve_mode(_parent, mode)
        out = {
            "data-key": self.key,
            "aria-label": f"{self.label or self.title}",
            "title": self.title,
        }

        # NOTE: Tooltip section should be configured to include tooltips.
        if _parent.tooltip.include_item:
            out.update(
                {
                    "data-bs-toggle": "tooltip",
                    "data-bs-title": self.tooltip or self.title,
                    "data-bs-placement": "bottom",
                    "data-bs-custom-class": "floaty-tooltip",
                }
            )

        if mode == "iconify":
            out["icon"] = f"{self.image.iconify.set_}:{self.image.iconify.name}"

        return out

    def get_classes(self, *, _parent: "ConfigFloaty", mode: FieldMode | None = None):
        mode = self.resolve_mode(_parent, mode)
        if mode == "iconify":
            return self.image.iconify.classes or list()

        out = ["bi", f"bi-{self.image.bootstrap.name}"]
        if (extra := self.image.bootstrap.classes) is not None:
            out += extra

        return out

    def create_attrs(
        self, *, _parent: "ConfigFloaty", mode: FieldMode | None = None
    ) -> str:
        return " ".join(
            f"{key}='{value}'"
            for key, value in self.get_attributes(_parent=_parent, mode=mode).items()
        )

    def create_classes(
        self, *, _parent: "ConfigFloaty", mode: FieldMode | None = None
    ) -> str:
        classes = self.get_classes(_parent=_parent, mode=mode)
        if not classes:
            return ""

        classes = "class=" + "'" + " ".join(classes) + "'"
        return classes

    def resolve_mode(
        self, _parent: "ConfigFloaty", mode: FieldMode | None
    ) -> FieldMode:
        return mode or self.mode or _parent.mode

    def hydrate_image(
        self,
        *,
        _parent: "ConfigFloaty",
        inline: bool = False,
        mode: FieldMode | None = None,
    ) -> pf.RawBlock | pf.RawInline:
        """Should make the iconify icon."""

        mode = self.resolve_mode(_parent, mode)

        attrs = self.create_attrs(_parent=_parent, mode=mode)
        classes = self.create_classes(_parent=_parent, mode=mode)
        tag = "iconify-icon" if mode != "bootstrap" else "i"
        raw = f"<{tag} {attrs} {classes}></{tag}>"
        el = (pf.RawInline if inline else pf.RawBlock)(raw, format="html")

        return el

    def hydrate_card(self, *, _parent: "ConfigFloaty"):
        classes = ["card"]
        if _parent.container.classes_items is not None:
            classes = ["card", *_parent.container.classes_items]
        if self.classes:
            classes += self.classes

        return pf.Div(
            classes=classes,
            attributes={"data-key": self.key},
        )

    def hydrate_card_image(self, *, _parent: "ConfigFloaty"):
        return pf.Div(
            self.hydrate_image(_parent=_parent),
            classes=["card-img-top"],
        )

    def hydrate_card_body(self, *, _parent: "ConfigFloaty"):
        text = pf.Plain(pf.Str(self.title))
        if _parent.container.columns < 0:
            image = self.hydrate_image(_parent=_parent, inline=True)
            text.content.insert(0, pf.Str(" "))
            text.content.insert(0, image)

        return pf.Div(pf.Div(text, classes=["card-text"]), classes=["card-body"])

    def hydrate(
        self,
        *,
        _parent: "ConfigFloaty",
    ):
        el = self.hydrate_card(_parent=_parent)
        if _parent.container.columns < 0:

            body = self.hydrate_card_body(_parent=_parent)
            body.classes.append("text-start")

            el.content.append(body)
            return el

        el.content.append(self.hydrate_card_image(_parent=_parent))
        if _parent.container.include_titles:
            el.content.append(self.hydrate_card_body(_parent=_parent))

        return el

    def hydrate_overlay_content_item(
        self,
        element: pf.Element,
        *,
        _parent: "ConfigFloaty",
    ):
        """Should match ``.overlay-content``."""
        element.classes.append("overlay-content-item")
        element.content = (
            pf.Div(self.hydrate_image(_parent=_parent, inline=False)),
            *element.content,
        )

        return element


T_ConfigFloaty = TypeVar("T_ConfigFloaty", bound=ConfigFloatyItem)


class ConfigFloatyContainer(pydantic.BaseModel):
    include: FieldInclude
    include_titles: Annotated[bool, pydantic.Field(default=False)]

    classes: util.FieldClasses
    classes_items: util.FieldClasses
    classes_rows: util.FieldClasses

    columns: Annotated[int, pydantic.Field(3)]


class ConfigFloatyTip(pydantic.BaseModel):
    include: FieldInclude
    include_item: FieldInclude
    classes: util.FieldClasses

    text: Annotated[
        str,
        pydantic.Field(default="Click on any of the icons to see more."),
    ]


class ConfigFloaty(pydantic.BaseModel, Generic[T_ConfigFloaty]):

    identifier: str
    include: FieldInclude
    mode: FieldMode

    container: ConfigFloatyContainer
    content: dict[str, T_ConfigFloaty]
    overlay: Annotated[overlay.ConfigOverlay | None, pydantic.Field(None)]
    tooltip: Annotated[
        ConfigFloatyTip,
        pydantic.Field(default_factory=dict, validate_default=True),
    ]

    @classmethod
    def createNullContent(
        cls, index: str | int, *, data: dict | str | None = None
    ) -> dict:
        overwrites = {
            "image": {
                "iconify": {
                    "set": "empty",
                    "name": "empty",
                },
            },
            "key": f"empty-{index}",
            "title": "empty",
            "classes": ["hidden"],
        }

        match data:
            case dict():
                overwrites = deep_update(overwrites, data)
            case str() as css_class if css_class:
                overwrites["classes"] = [data]

        return overwrites

    @pydantic.field_validator("content", mode="before")
    def content_from_list(cls, v):

        if isinstance(v, list):
            v_as_dict = {
                x.get("key") or str(k): x
                for k, w in enumerate(v)
                if (
                    x := (
                        w
                        if isinstance(w, dict) and not w.get("custom", False)
                        else cls.createNullContent(k, data=w)
                    )
                )
                is not None
            }

            if len(v_as_dict) != len(v):
                raise ValueError("Key collisions found.")

            return v_as_dict

        return v

    @property
    def js_name(self) -> str:
        name_segments = tuple(map(str.title, self.identifier.lower().split("-")))
        return "floaty" + "".join(name_segments)

    def hydrate_html_js(self, element: pf.Element):
        if self.overlay is None:
            return element

        if not element.identifier:
            raise ValueError("Missing identifier for div.")

        # NOTE: Assumes that
        js_overlay_id = f"overlayControls: {self.overlay.js_name}"
        js = f"const {self.js_name} = lazyFloaty('{element.identifier}', {{ { js_overlay_id } }})\n"
        js += f"globalThis.{self.js_name} = {self.js_name}\n"
        js += f'console.log("overlay", {self.overlay.js_name})'

        element.content.append(
            pf.RawBlock(f"<script id={self.identifier + '-script' }>{js}</script>")
        )

        return element

    def hydrate_html(self, element: pf.Element):
        """Create floaties and wrap in the container div."""
        # NOTE: Links are only ever included when the overlay is not present.

        element.classes.append("floaty")
        if self.container.classes is not None:
            element.classes += self.container.classes

        classes_items = ["floaty-item"]
        if self.container.classes_items is not None:
            classes_items += self.container.classes_items

        items = list(self.content.values())
        n = 1000 if self.container.columns == 0 else 1000
        n = 1 if self.container.columns < 0 else n

        sorted = (
            (
                pf.Div(item.hydrate(_parent=self), classes=classes_items)
                for item in items[k : k + n]
            )
            for k in range(0, len(items), n)
        )

        classes_rows = ["floaty-row"]
        if self.container.classes_rows is not None:
            classes_rows += self.container.classes_rows

        rows = (pf.Div(*items, classes=classes_rows) for items in sorted)

        element.content.append(pf.Div(*rows, classes=["floaty-container"]))

        self.hydrate_html_js(element)
        return element

    def get_content(self, element: pf.Element) -> T_ConfigFloaty | None:
        """Given an element, try to find its corresponding ``content`` item."""

        key = element.attributes.get("data-key")
        if key is None:
            return None

        return self.content.get(key)


class Config(pydantic.BaseModel):
    floaty: dict[str, ConfigFloaty[ConfigFloatyItem]]

    @pydantic.field_validator("floaty", mode="before")
    def _validate_floaty(cls, v):
        if isinstance(v, dict):
            return {k: {**w, "identifier": k} for k, w in v.items()}

        return v

    @pydantic.computed_field
    @property
    def overlay_identifiers(self) -> dict[str, str]:
        return {
            item.overlay.identifier: item.identifier
            for item in self.floaty.values()
            if item.overlay is not None
        }


class FilterFloaty(util.BaseFilter):
    filter_name = "floaty"
    filter_config_cls = Config

    _config: Config | None

    def __init__(self, doc: pf.Doc | None = None):
        super().__init__(doc=doc)
        self._config = None

    @property
    def config(self) -> Config | None:
        if self._config is not None:
            return self._config

        data = self.doc.get_metadata("floaty")  # type: ignore
        if data is None:
            self._config = None
            return None

        self._config = Config.model_validate({"floaty": data})
        return self._config

    def __call__(self, element: pf.Element):
        if self.doc.format != "html":
            return element

        if not isinstance(element, pf.Div) or self.config is None:
            return element

        if self.doc.format != "html":
            return element

        if element.identifier in self.config.floaty:
            config = self.config.floaty[element.identifier]
            element = config.hydrate_html(element)
            return element

        if element.identifier in self.config.overlay_identifiers:
            floaty_identifier = self.config.overlay_identifiers[element.identifier]
            config = self.config.floaty[floaty_identifier]
            element = config.overlay.hydrate_html(element)
            return element

        return element


filter = util.create_run_filter(FilterFloaty)
