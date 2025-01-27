"""Filters to generate floaty from configuration.

Demo and Usage
-----------------------------------

See the demo [here](./blog/dev/componants/floaty.qmd).
"""

import itertools
import secrets
from typing import Annotated, Any, ClassVar, Generic, Literal, TypeVar

import panflute as pf
import pydantic
from pydantic.v1.utils import deep_update

from acederbergio import env
from acederbergio.filters import overlay, util

logger = env.create_logger(__name__)

TEX_SPACER_NEWLINE = pf.RawInline(r" \hfill \\", format="latex")
TEX_SPACER_HFILL = pf.RawInline(r" \hfill ", format="latex")

FieldSize = Annotated[int, pydantic.Field(default=2, ge=1, le=6)]
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
    return out


class BaseConfigFloatyItemImageItem(util.BaseConfig):
    classes: util.FieldClasses
    attributes: Annotated[
        util.FieldAttributes,
        pydantic.Field(description="Image attributes for this particular image."),
    ]


class ConfigFloatyItemBootstrap(BaseConfigFloatyItemImageItem):
    name: str


class ConfigFloatyItemIconify(BaseConfigFloatyItemImageItem):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str


class ConfigFloatyItemTex(BaseConfigFloatyItemImageItem):
    font_awesome: str


class ConfigFloatyItemImage(util.BaseConfig):
    tex: Annotated[
        ConfigFloatyItemTex,
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

T_ConfigFloatyContainer = TypeVar(
    "T_ConfigFloatyContainer", bound="ConfigFloatyContainer"
)


class ConfigFloatyItem(util.BaseConfig, Generic[T_ConfigFloatyContainer]):
    """Configuration for one item in the floaty."""

    key: FieldKey
    container_maybe: Annotated[
        T_ConfigFloatyContainer | None,
        pydantic.Field(None, exclude=True),
    ]

    mode: FieldModeOptional
    image: Annotated[
        ConfigFloatyItemImage,
        pydantic.Field(default_factory=dict, validate_default=True),
    ]
    href: FieldHref

    # TODO: ``include_title`` should be ``include_body``.
    title: str
    description: Annotated[str | None, pydantic.Field(default=None)]
    label: FieldLabel

    tooltip: Annotated[str | None, pydantic.Field(default=None)]
    classes: util.FieldClasses
    classes_body: util.FieldClasses
    attributes: Annotated[dict[str, str], pydantic.Field(default_factory=dict)]

    @pydantic.computed_field
    @property
    def container(self) -> T_ConfigFloatyContainer:
        if self.container_maybe is None:
            raise ValueError("Container not set.")

        return self.container_maybe

    @pydantic.field_serializer("container")
    def serialize_container(self, v) -> bool:
        return v is not None

    @pydantic.computed_field
    @property
    def is_container(self) -> bool:
        return self.container.columns < 0

    @pydantic.computed_field
    @property
    def class_base_name(self) -> str:
        return "floaty-item" if self.is_container else "card"

    def class_name(self, *v: str) -> str:
        return self.class_base_name + "-" + "-".join(v)

    def get_attributes(self, *, mode: FieldMode | None = None) -> dict[str, str]:

        mode = self.resolve_mode(mode)
        out = {
            "data-key": self.key,
            "aria-label": f"{self.label or self.title}",
            "aria-title": self.title,
            "aria-description": self.description or "",
        }

        return out

    def get_tooltips(self) -> dict[str, str]:
        return {
            "data-bs-toggle": "tooltip",
            "data-bs-title": self.tooltip or self.title,
            "data-bs-placement": "top",
            "data-bs-custom-class": "floaty-tooltip",
        }

    def get_classes_image(self, *, mode: FieldMode | None = None):
        mode = self.resolve_mode(mode)
        classes = util.update_classes(list(), self.container.classes_card_images)

        if mode == "iconify":
            classes = util.update_classes(classes, self.image.iconify.classes)
        else:
            classes = util.update_classes(
                classes,
                ["bi", f"bi-{self.image.bootstrap.name}"],
                self.image.bootstrap.classes,
            )

        return classes

    # def create_attrs(self, *, mode: FieldMode | None = None) -> str:
    #     return " ".join(
    #         f"{key}='{value}'" for key, value in self.get_attributes(mode=mode).items()
    #     )

    def create_classes_image(self, *, mode: FieldMode | None = None) -> str:
        classes = self.get_classes_image(mode=mode)
        if not classes:
            return ""

        classes = "class=" + "'" + " ".join(classes) + "'"
        return classes

    def iter_body(self, *, is_container: bool | None = None):
        is_container = is_container if is_container is None else self.is_container

        if self.container.include_titles:
            yield pf.Div(
                pf.Plain(pf.Str(self.title)),
                classes=[self.class_name("title")],
            )

        if self.container.include_descriptions and self.description is not None:
            yield pf.Div(
                pf.Plain(pf.Str(self.description)),
                classes=[self.class_name("text")],
            )

    def resolve_mode(self, mode: FieldMode | None) -> FieldMode:
        return mode or self.mode or self.container.mode

    def hydrate_image(
        self,
        *,
        inline: bool = False,
        mode: FieldMode | None = None,
    ) -> pf.RawBlock | pf.RawInline:
        """Should make the iconify icon."""

        mode = self.resolve_mode(mode)

        classes = self.create_classes_image(mode=mode)
        tag = "iconify-icon" if mode != "bootstrap" else "i"

        attrs = ""
        if mode == "iconify":
            attrs = f"icon={self.image.iconify.set_}:{self.image.iconify.name}"

        raw = f"<{tag} {attrs} {classes}></{tag}>"
        el = (pf.RawInline if inline else pf.RawBlock)(raw, format="html")

        return el

    def hydrate_footer(self) -> pf.Div | None:
        return None

    def hydrate_card_image(
        self,
    ):
        return pf.Div(
            self.hydrate_image(),
            classes=["card-img-top"],
        )

    def hydrate_card_body(
        self,
    ):
        classes = util.update_classes(
            ["card-body"],
            self.classes_body,
            self.container.classes_card_bodys,
        )
        return pf.Div(
            *self.iter_body(is_container=False),
            classes=classes,
        )

    def hydrate_card(
        self,
    ):
        classes = util.update_classes(
            ["card"],
            self.container.classes_cards,
            self.classes,
        )
        out = pf.Div(
            self.hydrate_card_image(),
            classes=classes,
        )

        if len((body := self.hydrate_card_body()).content):
            out.content.append(body)

        footer = self.hydrate_footer()
        if footer is not None:
            out.content.append(footer)

        return out

    def hydrate_container(self):
        out = pf.Div(
            pf.Div(
                self.hydrate_image(),
                classes=["floaty-item-img"],
            ),
            *self.iter_body(is_container=True),
            classes=["floaty-item-container"],
        )

        footer = self.hydrate_footer()
        if footer is not None:
            out.content.append(footer)

        return out

    def hydrate_html(self):
        out = (
            self.hydrate_container()
            if self.container.columns < 0
            else self.hydrate_card()
        )

        # NOTE: From least priority to greatest priority.
        items = (
            out.attributes,
            self.container.attributes_cards,
            self.get_attributes(),
            (
                out.attributes.update(self.get_tooltips())
                if self.container.include_tooltips
                else None
            ),
            (
                {"data-floaty-url": self.href}
                if self.href and self.container.include_href
                else None
            ),
            self.attributes,
        )

        out.attributes = util.update_attributes(*items)

        return out

    def hydrate_tex(
        self,
    ) -> pf.Inline:
        """This will be very subclass specific, do not implement."""
        raise ValueError(f"Not implement for `{self.__class__.__name__}`.")

    def hydrate_overlay_content_item(
        self,
        element: pf.Element,
    ):
        """Should match ``.overlay-content``."""
        element.classes.append("overlay-content-item")
        element.content = (
            pf.Div(self.hydrate_image(inline=False)),
            *element.content,
        )

        return element


class ConfigFloatyTex(util.BaseConfig):
    """Options for rendering latex."""

    sep: FieldSep


class ConfigFloatyContainer(util.BaseConfig):
    """Configuration for floaty grid and common configuration for floaty items.

    This is passed to most methods of ``ConfigFloatyItem`` to determine how
    each ``card`` or ``grid`` renders.

    ``content`` is not specified here since it might have different types
    in items that re-use floaty.
    """

    tex: Annotated[
        ConfigFloatyTex,
        pydantic.Field(default_factory=dict, validate_default=True),
    ]

    include_href: Annotated[bool, pydantic.Field(default=False)]
    include_tooltips: Annotated[bool, pydantic.Field(default=False)]
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
    resize: Annotated[
        dict[util.Breakpoint, int] | bool,
        pydantic.Field(
            False,
            description="""
                Include responsive resizing or not.
                When true, the default resizings are used.
            """,
        ),
    ]
    tooltips_toggle: Annotated[
        util.Breakpoint | bool,
        pydantic.Field(
            True,
            description="""
            Include responsive tooltip toggling.
            Tooltips should be moved to card descriptions when this is set.
            If set to ``True``, the default breakpoint is used.
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
    classes_card_images: Annotated[
        util.FieldClasses,
        pydantic.Field(
            description="""
            ``SCSS`` classes to be applied to the card images.
            This applies to the `<i></i>` or `<iconify></iconify>` element, and
            not ``card-img-top`` element. The current use case for this is to 
            ensure that bootstrap icons can fill their background.
        """
        ),
    ]

    attributes_cards: util.FieldAttributes

    @pydantic.computed_field
    @property
    def classes_always(self) -> list[str]:
        return ["floaty", f"floaty-size-{self.size}"]

    def hydrate(self, element: pf.Element):
        util.update_classes(element.classes, self.classes_always, self.classes)
        return element

    def hydrate_html(
        self,
        element: pf.Element,
        *items: ConfigFloatyItem,
        owner: util.BaseHasIdentifier,
    ):
        """Create floaties and wrap in the container div."""
        # NOTE: Links are only ever included when the overlay is not present.

        element = self.hydrate(element)
        classes_items = util.update_classes(["floaty-item"], self.classes_items)
        classes_rows = util.update_classes(["floaty-row"], self.classes_rows)

        n = 1000 if self.columns == 0 else self.columns
        n = 1 if self.columns < 0 else n

        sorted = (
            (
                pf.Div(
                    item.hydrate_html(),
                    classes=classes_items,
                )
                for item in items[k : k + n]
            )
            for k in range(0, len(items), n)
        )

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
        if not element.identifier:
            raise ValueError("Missing identifier for div.")

        options: dict[str, Any] = {
            "resize": bool(self.resize),
            "tooltipsToggle": bool(self.tooltips_toggle),
            "overlayControls": overlay.js_name if overlay is not None else "null",
        }
        options["resizeBreakpoints"] = (
            self.resize
            if options["resize"] and not isinstance(self.resize, bool)
            else None
        )
        options["tooltipsToggleBreakpoint"] = (
            self.tooltips_toggle
            if options["tooltipsToggle"] and not isinstance(self.tooltips_toggle, bool)
            else "null"
        )

        # js = "import { Overlay } from '/js/overlay.js'\n"
        # js += "import { lazyFloaty } from '/js/floaty.js'\n"
        # js += f"const {owner.js_name} = lazyFloaty('{ element.identifier }', {json.dumps(options)})\n"
        # js += f"globalThis.{owner.js_name} = {owner.js_name}\n"
        # js += f'console.log("overlay", {overlay.js_name if overlay is not None else "null"})'

        js = util.JINJA_ENV.get_template("floaty.js.j2").render(
            owner=owner,
            overlay=overlay,
            element=element,
            options=options,
        )

        element.content.append(
            pf.RawBlock(
                f"<script id={owner.identifier + '-script' } type='module'>{js}</script>"
            )
        )

        return element

    def hydrate_tex(self, element: pf.Element, *items: ConfigFloatyItem):

        # NOTE: Putting these in separate paragraphs does not work.
        #       In the first case, put each on a new line. In the second,
        #       try to share a line an equally.
        match self.tex.sep:
            case "newline":
                listed = ((item.hydrate_tex(), TEX_SPACER_NEWLINE) for item in items)
            case "hfill":
                listed = ((item.hydrate_tex(), TEX_SPACER_HFILL) for item in items)
            case _:
                raise ValueError(f"Invalid separator `{self.tex.sep}` for `tex`.")

        element.content.append(pf.Para(*itertools.chain(*listed)))
        return element


T_ConfigFloatyItem = TypeVar("T_ConfigFloatyItem", bound=ConfigFloatyItem)


class ConfigFloaty(
    util.BaseHasIdentifier, Generic[T_ConfigFloatyItem, T_ConfigFloatyContainer]
):
    """Configuration for a ``floaty``.

    Specifies exacly one floaty.
    """

    content: Annotated[
        dict[str, T_ConfigFloatyItem],
        pydantic.Field(description=""),
        pydantic.BeforeValidator(replace_null_items),
    ]

    container: Annotated[
        T_ConfigFloatyContainer,
        pydantic.Field(description="", validate_default=True, default_factory=dict),
    ]
    overlay: Annotated[overlay.ConfigOverlay | None, pydantic.Field(None)]

    def _set_container(self, item: T_ConfigFloatyItem):
        item.container_maybe = self.container

    @pydantic.model_validator(mode="after")
    def set_container(self):

        for item in self.content.values():
            self._set_container(item)

        return self

    def hydrate_html(self, element: pf.Element) -> pf.Element:
        return self.container.hydrate_html(element, *self.content.values(), owner=self)

    def hydrate_tex(self, element: pf.Element) -> pf.Element:
        return self.container.hydrate_tex(element, *self.content.values())  # type: ignore

    def get_content(self, element: pf.Element) -> T_ConfigFloatyItem | None:
        """Given an element, try to find its corresponding ``content`` item."""

        key = element.attributes.get("data-key")
        if key is None:
            return None

        return self.content.get(key)


class BaseFloatyConfig(util.BaseConfig):

    filter_name: ClassVar[str]

    @pydantic.computed_field
    @property
    def overlay_identifiers(self) -> dict[str, str] | None:
        if (attr := getattr(self, self.filter_name, None)) is None:
            return

        return {
            item.overlay.identifier: item.identifier
            for item in attr.values()
            if item.overlay is not None
        }

    def hydrate_overlay(self, element: pf.Div):
        if (
            self.overlay_identifiers is None
            or element.identifier not in self.overlay_identifiers
        ):
            return element

        floaty_identifier = self.overlay_identifiers[element.identifier]
        config = getattr(self, self.filter_name)[floaty_identifier]
        element = config.overlay.hydrate_html(element)
        return element


class Config(BaseFloatyConfig):
    """Configuration used to validate quarto metadata."""

    filter_name = "floaty"
    floaty: Annotated[
        dict[
            str,
            ConfigFloaty[
                ConfigFloatyItem[ConfigFloatyContainer], ConfigFloatyContainer
            ],
        ]
        | None,
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterFloaty(util.BaseFilterHasConfig):
    """Floaty pandoc filter."""

    filter_name = "floaty"
    filter_config_cls = Config

    def __call__(self, element: pf.Element):
        if self.doc.format != "html":
            return element

        if not isinstance(element, pf.Div) or self.config is None:
            return element

        if element.identifier in self.config.floaty:
            config = self.config.floaty[element.identifier]
            element = config.hydrate_html(element)
            return element

        element = self.config.hydrate_overlay(element)
        return element


filter = util.create_run_filter(FilterFloaty)
__all__ = (
    "ConfigFloatyContainer",
    "ConfigFloatyItemBootstrap",
    "ConfigFloatyItemImage",
    "ConfigFloatyTex",
    "ConfigFloatyItemIconify",
    "ConfigFloatyItemTex",
    "ConfigFloaty",
    "Config",
    "FilterFloaty",
)
