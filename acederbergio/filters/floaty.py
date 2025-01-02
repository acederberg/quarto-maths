"""Filters to generate floaty from configuration.

For exact detail on how to use, see `./blog/dev/componants/floaty.qmd`.
"""

import itertools
import secrets
from typing import Annotated, Generic, Iterable, Literal, TypeVar

import panflute as pf
import pydantic
from pydantic.v1.utils import deep_update

from acederbergio import env
from acederbergio.filters import overlay, util

logger = env.create_logger(__name__)

TEX_SPACER = pf.RawInline(r" \hfill \\", format="latex")
TEX_SPACER_INLINE = pf.RawInline(r" \hfill ", format="latex")

FieldSize = Annotated[int, pydantic.Field(ge=1, le=6)]
FieldSep = Annotated[Literal["newline", "hfill"], pydantic.Field("newline")]
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


def create_null_item(index: str | int, *, data: dict | str | None = None) -> dict:
    overwrites = {
        "image": {
            "iconify": {
                "set": "empty",
                "name": "empty",
            },
        },
        "key": f"empty-{index}",
        "title": "empty",
        "description": "This is a placeholder, it indicates that a pandoc filter is misconfigured.",
        "classes": ["hidden"],
    }

    # NOTE: Passing strings should just create empty (invisible) cards,
    #       in quarto files themselves it is possible to put ``None`` for
    #       list items but ``_metadata.yaml`` will ommit repeated values
    #       (which is probably a bug).
    match data:
        case dict():
            overwrites = deep_update(overwrites, data)

    return overwrites


def replace_null_items(v):
    """Replace junk content with ``empty``."""

    v_as_dict = util.content_from_list_key(v)
    out = {
        k: item if isinstance(item, dict) else create_null_item(item, data=item)
        for k, item in v_as_dict.items()
    }
    logger.warning(out)
    return out


class BaseConfigFloatyItemImageItem(pydantic.BaseModel):
    classes: util.FieldClasses
    attributes: FieldAttributes


class ConfigFloatyItemBootstrap(BaseConfigFloatyItemImageItem):
    name: str


class ConfigFloatyItemIconify(BaseConfigFloatyItemImageItem):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str


class ComfigFloatyItemTex(BaseConfigFloatyItemImageItem):
    font_awesome: str


class ConfigFloatyItemImage(pydantic.BaseModel):
    tex: Annotated[
        ComfigFloatyItemTex,
        pydantic.Field(
            default_factory=lambda: dict(font_awesome="phone"),
            validate_default=True,
        ),
    ]
    iconify: Annotated[
        ConfigFloatyItemIconify,
        pydantic.Field(
            default_factory=lambda: dict(set="mdi", name="bug"),
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

    # TODO: ``include_title`` should be ``include_body``.
    title: str
    description: Annotated[str | None, pydantic.Field(default=None)]
    label: FieldLabel

    tooltip: Annotated[str | None, pydantic.Field(default=None)]
    classes: util.FieldClasses
    classes_body: util.FieldClasses

    def get_attributes(
        self, *, container: "ConfigFloatyContainer", mode: FieldMode | None = None
    ) -> dict[str, str]:

        mode = self.resolve_mode(container, mode)
        out = {
            "data-key": self.key,
            "aria-label": f"{self.label or self.title}",
            "title": self.title,
        }

        # NOTE: Tooltip section should be configured to include tooltips.
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

    def get_classes(
        self, *, container: "ConfigFloatyContainer", mode: FieldMode | None = None
    ):
        mode = self.resolve_mode(container, mode)
        if mode == "iconify":
            return self.image.iconify.classes or list()

        out = ["bi", f"bi-{self.image.bootstrap.name}"]
        if (extra := self.image.bootstrap.classes) is not None:
            out += extra

        return out

    def create_attrs(
        self, *, container: "ConfigFloatyContainer", mode: FieldMode | None = None
    ) -> str:
        return " ".join(
            f"{key}='{value}'"
            for key, value in self.get_attributes(
                container=container, mode=mode
            ).items()
        )

    def create_classes(
        self, *, container: "ConfigFloatyContainer", mode: FieldMode | None = None
    ) -> str:
        classes = self.get_classes(container=container, mode=mode)
        if not classes:
            return ""

        classes = "class=" + "'" + " ".join(classes) + "'"
        return classes

    def resolve_mode(
        self, container: "ConfigFloatyContainer", mode: FieldMode | None
    ) -> FieldMode:
        return mode or self.mode or container.mode

    def hydrate_image(
        self,
        *,
        container: "ConfigFloatyContainer",
        inline: bool = False,
        mode: FieldMode | None = None,
    ) -> pf.RawBlock | pf.RawInline:
        """Should make the iconify icon."""

        mode = self.resolve_mode(container, mode)

        attrs = self.create_attrs(container=container, mode=mode)
        classes = self.create_classes(container=container, mode=mode)
        tag = "iconify-icon" if mode != "bootstrap" else "i"
        raw = f"<{tag} {attrs} {classes}></{tag}>"
        el = (pf.RawInline if inline else pf.RawBlock)(raw, format="html")

        return el

    def hydrate_card_image(self, *, container: "ConfigFloatyContainer"):
        return pf.Div(
            self.hydrate_image(container=container),
            classes=["card-img-top"],
        )

    def iter_body(
        self, *, container: "ConfigFloatyContainer", is_container: bool | None = None
    ):
        is_container = is_container or (container.columns < 0)
        base_name = "floaty-item" if is_container else "card"

        if container.include_titles:
            yield pf.Div(
                pf.Plain(pf.Str(self.title)),
                classes=[base_name + "-title"],
            )

        if container.include_descriptions and self.description is not None:
            yield pf.Div(
                pf.Plain(pf.Str(self.description)),
                classes=[base_name + "-text"],
            )

    def hydrate_card_body(self, *, container: "ConfigFloatyContainer"):
        classes = self.resolve_classes(
            ["card-body"], self.classes_body, container.classes_card_bodys
        )
        return pf.Div(
            *self.iter_body(container=container, is_container=False),
            classes=classes,
        )

    def resolve_classes(self, update: list[str], *args: list[str] | None):
        for item in args:
            if item is not None:
                update += item

        return update

    def hydrate_card(self, *, container: "ConfigFloatyContainer"):
        classes = self.resolve_classes(["card"], container.classes_cards, self.classes)
        return pf.Div(
            self.hydrate_card_image(container=container),
            self.hydrate_card_body(container=container),
            classes=classes,
            attributes={"data-key": self.key},
        )

    def hydrate_container(self, *, container: "ConfigFloatyContainer"):
        return pf.Div(
            pf.Div(
                self.hydrate_image(container=container),
                classes=["floaty-item-img"],
            ),
            *self.iter_body(container=container, is_container=True),
            classes=["floaty-item-container"],
        )

    def hydrate_html(
        self,
        *,
        container: "ConfigFloatyContainer",
    ):
        return (
            self.hydrate_container(container=container)
            if container.columns < 0
            else self.hydrate_card(container=container)
        )

    def hydrate_tex(self, *, container: "ConfigFloatyContainer") -> pf.Inline:
        """This will be very subclass specific, do not implement."""
        raise ValueError(f"Not implement for `{self.__class__.__name__}`.")

    def hydrate_overlay_content_item(
        self,
        element: pf.Element,
        *,
        container: "ConfigFloatyContainer",
    ):
        """Should match ``.overlay-content``."""
        element.classes.append("overlay-content-item")
        element.content = (
            pf.Div(self.hydrate_image(container=container, inline=False)),
            *element.content,
        )

        return element


class ConfigFloatyTex(pydantic.BaseModel):
    """Options for rendering latex."""

    sep: FieldSep


class ConfigFloatyContainer(pydantic.BaseModel):
    """Global configuration for floaty items is defined here.

    This is passed to most methods of ``ConfigFloatyItem`` to determine how
    each ``card`` or ``grid`` renders.

    ``content`` is not specified here since it might have different types
    in items that re-use floaty.
    """

    tex: Annotated[
        ConfigFloatyTex,
        pydantic.Field(default_factory=dict, validate_default=True),
    ]

    include_titles: Annotated[bool, pydantic.Field(default=False)]
    include_descriptions: Annotated[bool, pydantic.Field(default=False)]

    size: FieldSize
    mode: FieldMode
    columns: Annotated[
        int,
        pydantic.Field(
            default=3,
            description="""
            Number of columns in each ``floaty-row``.
            When this is negative, ``floaty-grid`` is used.
            When this is ``0``, there will be only one row.
        """,
        ),
    ]

    classes: util.FieldClasses
    classes_items: Annotated[
        util.FieldClasses,
        pydantic.Field(
            description="""
                ``SCSS`` classes to be applied to all items. 
                This controls the classes on ``floaty-items``, not the cards.
                To apply classes to all cards, use ``$.classes_cards`.
                To apply classes to a specific item, use ``.classes`` of 
                ``ConfigFloatyItem``.
            """
        ),
    ]
    classes_rows: Annotated[
        util.FieldClasses,
        pydantic.Field(
            description="""
                ``SCSS`` classes to be applied to all rows (``.floaty-row``).
            """
        ),
    ]

    classes_cards: Annotated[
        util.FieldClasses,
        pydantic.Field(
            description="""
            ``SCSS`` classes to be applied to all cards.
            To apply this to each card container (the ``floaty-item`` containing
            the card) use ``$.classes_items``.
        """
        ),
    ]
    classes_card_bodys: Annotated[
        util.FieldClasses,
        pydantic.Field(
            description="SCSS classes to be applied to the body of each card."
        ),
    ]

    @pydantic.computed_field
    @property
    def classes_always(self) -> list[str]:
        return ["floaty", f"floaty-size-{self.size}"]

    def hydrate(self, element: pf.Element):
        element.classes += self.classes_always
        if self.classes is not None:
            element.classes += self.classes

        return element

    def hydrate_html(
        self,
        owner: util.BaseHasIdentifier,
        element: pf.Element,
        *items: ConfigFloatyItem,
    ):
        """Create floaties and wrap in the container div."""
        # NOTE: Links are only ever included when the overlay is not present.

        element = self.hydrate(element)

        classes_items = ["floaty-item"]
        if self.classes_items is not None:
            classes_items += self.classes_items

        n = 1000 if self.columns == 0 else self.columns
        n = 1 if self.columns < 0 else n

        sorted = (
            (
                pf.Div(
                    item.hydrate_html(container=self),
                    classes=classes_items,
                )
                for item in items[k : k + n]
            )
            for k in range(0, len(items), n)
        )

        classes_rows = ["floaty-row"]
        if self.classes_rows is not None:
            classes_rows += self.classes_rows

        rows = (pf.Div(*items, classes=classes_rows) for items in sorted)

        element.content.append(pf.Div(*rows, classes=["floaty-container"]))

        if "overlay" in owner.model_fields:
            element = self.hydrate_html_js(
                element,
                overlay=owner.overlay,  # type: ignore
                owner=owner,
            )
        return element

    def hydrate_html_js(
        self,
        element: pf.Element,
        *,
        overlay: overlay.ConfigOverlay | None,
        owner: util.BaseHasIdentifier,
    ):
        if overlay is None:
            return element

        if not element.identifier:
            raise ValueError("Missing identifier for div.")

        js_overlay_id = f"overlayControls: {overlay.js_name}"
        js = f"const {owner.js_name} = lazyFloaty('{ element.identifier }', {{ {js_overlay_id} }})\n"
        js += f"globalThis.{owner.js_name} = {owner.js_name}\n"
        js += f'console.log("overlay", {overlay.js_name})'

        element.content.append(
            pf.RawBlock(f"<script id={owner.identifier + '-script' }>{js}</script>")
        )

        return element

    def hydrate_tex(self, items: Iterable[pf.Inline]):

        # NOTE: Putting these in separate paragraphs does not work.
        #       In the first case, put each on a new line. In the second,
        #       try to share a line an equally.
        match self.tex.sep:
            case "newline":
                listed = ((item, TEX_SPACER) for item in items)
            case "fill":
                listed = ((item, TEX_SPACER_INLINE) for item in items)
            case _:
                raise ValueError

        return pf.Para(*itertools.chain(*listed))


T_ConfigFloaty = TypeVar("T_ConfigFloaty", bound=ConfigFloatyItem)


class ConfigFloaty(util.BaseHasIdentifier, Generic[T_ConfigFloaty]):
    content: Annotated[
        dict[str, T_ConfigFloaty],
        pydantic.Field(description=""),
        pydantic.BeforeValidator(replace_null_items),
    ]

    container: Annotated[
        ConfigFloatyContainer,
        pydantic.Field(description="", validate_default=True, default_factory=dict),
    ]
    overlay: Annotated[overlay.ConfigOverlay | None, pydantic.Field(None)]

    def hydrate_html(self, element: pf.Element) -> pf.Element:
        return self.container.hydrate_html(self, element, *self.content.values())

    def get_content(self, element: pf.Element) -> T_ConfigFloaty | None:
        """Given an element, try to find its corresponding ``content`` item."""

        key = element.attributes.get("data-key")
        if key is None:
            return None

        return self.content.get(key)


class Config(pydantic.BaseModel):
    floaty: Annotated[
        dict[str, ConfigFloaty[ConfigFloatyItem]] | None,
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]

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
