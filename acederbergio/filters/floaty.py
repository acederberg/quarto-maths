import secrets
from typing import Annotated, Generic, Iterable, Literal, TypedDict, TypeVar

import panflute as pf
import pydantic
from typing_extensions import NotRequired, Required, Unpack

from acederbergio.filters import util


class ConfigFloatyItemIconify(pydantic.BaseModel):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str
    size: Annotated[int | None, pydantic.Field(default=None)]
    label: Annotated[str | None, pydantic.Field(default=None)]


# NOTE: Looks far better
class ConfigFloatyItemBoostrap(pydantic.BaseModel):
    name: str
    label: Annotated[str | None, pydantic.Field(default=None)]


class ConfigFloatyItemImage(pydantic.BaseModel):
    iconify: ConfigFloatyItemIconify


# class IconifyKwargs(TypedDict):
#
#     inline: NotRequired[bool]
#     _parent: Required["ConfigFloatySection"]


class ConfigFloatyItem(pydantic.BaseModel):
    key: Annotated[
        str,
        pydantic.Field(
            default_factory=lambda: secrets.token_urlsafe(8),
        ),
    ]
    image: ConfigFloatyItemImage
    href: Annotated[
        str | None,
        pydantic.Field(
            description=(
                "A link to go to when clicked on. Should open in a new tab."
                "Will be ignored when an overlay is included."
            ),
            default=None,
        ),
    ]
    title: str
    tooltip: Annotated[str | None, pydantic.Field(default=None)]

    def get_attributes(self, *, _parent: "ConfigFloatySection") -> dict[str, str]:

        out = {
            "data-key": self.key,
            "aria-label": f"{self.image.iconify.label or self.title}",
            "icon": f"{self.image.iconify.set_}:{self.image.iconify.name}",
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

        return out

    # def hydrate_iconify_li(
    #     self,
    #     *,
    #     include_link: bool,
    #     **kwargs: Unpack[IconifyKwargs],
    # ):
    #     _parent = kwargs["_parent"]
    #     res = self.hydrate_iconify(**kwargs)
    #
    #     if include_link and self.href is not None:
    #         res = pf.Link(res, url=self.href)
    #
    #     out = pf.ListItem(pf.Para(res))
    #     if _parent.container.titles:
    #         # NOTE: Link must be added via js.
    #         attributes = {}
    #         if include_link and self.href is not None:
    #             attributes["data-url"] = self.href
    #
    #         title = pf.Header(
    #             pf.Str(self.title),
    #             level=3,
    #             classes=["floaty-title"],
    #             attributes=attributes,
    #         )
    #         out.content.append(title)
    #
    #     return out
    #
    # def hydrate_iconify_tr(
    #     self,
    #     # cells_extra: Iterable[pf.TableCell] | None = None,
    #     **kwargs: Unpack[IconifyKwargs],
    # ):
    #
    #     kwargs["inline"] = False
    #     cells: Iterable[pf.TableCell]
    #     cells = [pf.TableCell(self.hydrate_iconify(**kwargs))]
    #
    #     if kwargs["_parent"].container.titles:
    #         cells.append(pf.TableCell(pf.Para(pf.Str(self.title))))
    #
    #     # if cells_extra is not None:
    #     #     cells = (*cells, *cells_extra)
    #
    #     return pf.TableRow(*cells)

    def hydrate_iconify(
        self,
        *,
        _parent: "ConfigFloatySection",
    ):
        """Should make the iconify icon."""

        # NOTE: Font size MUST be in pixels for JS to ensure list item resize.
        attrs = " ".join(
            f"{key}='{value}'"
            for key, value in self.get_attributes(_parent=_parent).items()
        )
        raw = f"<iconify-icon { attrs }></iconify-icon>"
        el = pf.RawBlock(raw, format="html")

        return el

    def hydrate(
        self,
        *,
        _parent: "ConfigFloatySection",
        # inline: bool = True,
        # include_link: bool,
    ):
        el = pf.Div(
            pf.Div(
                self.hydrate_iconify(_parent=_parent),
                classes=["card-img-top"],
            ),
            classes=["card", *_parent.container.classes_items],
        )

        if _parent.container.include_titles:
            el.content.append(
                pf.Div(
                    pf.Plain(pf.Str(self.title)),
                    classes=["card-body"],
                )
            )

        return el

    # def hydrate_overlay_content_item(
    #     self,
    #     element: pf.Element,
    #     *,
    #     _parent: "ConfigFloatySection",
    # ):
    #     """Should match ``.overlay-content``."""
    #     element.classes.append("overlay-content-item")
    #     element.content = (
    #         pf.Div(
    #             self.hydrate_iconify(
    #                 _parent=_parent,
    #                 for_overlay=True,
    #                 inline=False,
    #             )
    #         ),
    #         pf.Div(pf.Header(pf.Str(self.title)), classes=["p-1"]),
    #         *element.content,
    #     )
    #
    #     return element


T_ConfigFloatySection = TypeVar("T_ConfigFloatySection", bound=ConfigFloatyItem)
FieldClasses = Annotated[list[str], pydantic.Field(default_factory=list)]
FieldInclude = Annotated[bool, pydantic.Field(default=True)]


class ConfigFloatySectionContainer(pydantic.BaseModel):
    # TODO: Add titles list type.
    include: FieldInclude
    include_titles: Annotated[bool, pydantic.Field(default=False)]

    classes: FieldClasses
    classes_items: FieldClasses
    classes_rows: FieldClasses

    columns: Annotated[int, pydantic.Field(3)]
    # kind: Annotated[Literal["table", "list"], pydantic.Field(default="list")]


# NOTE: The overlay should be added explicitly using fence, no exceptions.
#       This should update the item and include the icon and more in the slide.
class ConfigFloatySectionOverlay(pydantic.BaseModel):
    include: FieldInclude
    classes: FieldClasses


class ConfigFloatySectionTip(pydantic.BaseModel):
    include: FieldInclude
    include_item: FieldInclude
    classes: FieldClasses

    text: Annotated[
        str,
        pydantic.Field(default="Click on any of the icons to see more."),
    ]


class ConfigFloatySection(pydantic.BaseModel, Generic[T_ConfigFloatySection]):

    include: FieldInclude

    container: ConfigFloatySectionContainer
    content: dict[str, T_ConfigFloatySection]
    overlay: Annotated[
        ConfigFloatySectionOverlay,
        pydantic.Field(default_factory=dict, validate_default=True),
    ]
    tooltip: Annotated[
        ConfigFloatySectionTip,
        pydantic.Field(default_factory=dict, validate_default=True),
    ]

    @pydantic.field_validator("content", mode="before")
    def content_from_list(cls, v):

        if isinstance(v, list):
            v_as_dict = {v.get("key") or str(k): v for k, v in enumerate(v)}

            if len(v_as_dict) != len(v):
                raise ValueError("Key collisions found.")

            return v_as_dict

        return v

    def hydrate_html_js(self, element: pf.Element):
        if not element.identifier:
            util.record(element)
            raise ValueError("Missing identifier for div.")

        closure_name_segments = map(str.title, element.identifier.lower().split("-"))
        closure_name = "overlay" + "".join(closure_name_segments)

        sim = self.container.size_item_margin
        li_margin = f"'{sim}px'" if sim is not None else "null"
        kwargs = f"{{ li_margin: {li_margin}, kind: '{ self.container.kind }' }}"
        js = f"let {closure_name} = Floaty(document.getElementById('{ element.identifier }'), { kwargs })"

        element.content = (
            *element.content,
            pf.RawBlock(f"<script>{js}</script>"),
        )
        return element

    def hydrate_html(self, element: pf.Element):
        """Create floaties and wrap in the container div."""
        # NOTE: Links are only ever included when the overlay is not present.

        element.classes.append("floaty")
        element.classes += self.container.classes

        items = list(self.content.values())
        sorted = (
            (
                pf.Div(
                    item.hydrate(_parent=self),
                    classes=["floaty-item", *self.container.classes_items],
                )
                for item in items[k : k + self.container.columns]
            )
            for k in range(0, len(items), self.container.columns)
        )
        rows = (
            pf.Div(*items, classes=["floaty-row", *self.container.classes_rows])
            for items in sorted
        )
        container = pf.Div(*rows, classes=["floaty-container"])
        element.content.append(container)

        return element

        # element.classes = ["floaty", *self.container.class
        #
        # items = (
        #     config_image.hydrate(
        #         include_link=not self.overlay.include,
        #         _parent=self,
        #     )
        #     for config_image in self.content.values()
        # )
        #
        # classes = ["floaty-container", *self.container.classes]
        # element.content = (
        #     pf.Div(*list_items, classes=classes),
        #     *element.content,
        # )
        #
        # return element

    # def hydrate_html_table(self, element: pf.Element):
    #
    #     table_rows = (
    #         # config_image.hydrate_iconify_tr(self.container.size_item, _parent=self)
    #         config_image.hydrate_iconify_tr(_parent=self)
    #         for config_image in self.content.values()
    #     )
    #
    #     element.content = (
    #         pf.Div(
    #             pf.Table(pf.TableBody(*table_rows)),
    #             classes=["floaty-container"],
    #         ),
    #         *element.content,
    #     )
    #
    #     return element

    def get_content(self, element: pf.Element) -> T_ConfigFloatySection | None:
        """Given an element, try to find its corresponding ``content`` item."""

        key = element.attributes.get("data-key")
        if key is None:
            return None

        return self.content.get(key)

    # def hydrate_html_overlay_content(self, element: pf.Element):
    #     """Match .overlay-content and take care of its items."""
    #
    #     if not self.overlay.include:
    #         return element
    #
    #     # Look for overlay content
    #     needs_config = set()
    #
    #     def hydrate_overlay_content_item(_: pf.Doc, el: pf.Element) -> pf.Element:
    #         if not isinstance(el, pf.Div):
    #             return el
    #
    #         if "overlay-content-item" not in el.classes:
    #             return el
    #
    #         el_config = self.get_content(el)
    #         if el_config is None:
    #             needs_config.add(el.attributes.get("data-key"))
    #             return el
    #
    #         util.record(
    #             f"Hydrating overlay content for `#{element.identifier} "
    #             ".overlay data-key={el.attributes.get('data-key')}`."
    #         )
    #         el = el_config.hydrate_overlay_content_item(el, _parent=self)
    #         return el
    #
    #     element.walk(lambda doc, el: hydrate_overlay_content_item(el, doc))
    #     if needs_config:
    #         raise ValueError(f"Missing overlay content for ``{needs_config}``.")
    #     return element

    # def hydrate_html(self, element: pf.Element):
    #     if self.container.kind == "list":
    #         element = self.hydrate_html_list(element)
    #     else:
    #         element = self.hydrate_html_table(element)
    #
    #     # NOTE: Try to find the overlay.
    #     element = self.hydrate_html_overlay_content(element)
    #     self.hydrate_html_js(element)
    #
    #     if self.tooltip.include:
    #
    #         info = pf.Div(
    #             pf.Para(pf.Str(self.tooltip.text)),
    #             classes=["floaty-info"],
    #         )
    #         element.content.append(info)
    #
    #     return element


class ConfigFloaty(pydantic.BaseModel):
    floaty: dict[str, ConfigFloatySection[ConfigFloatyItem]]


# def wrap_overlay_content(element: pf.Element) -> pf.Element:
#     """Since it is a pain to wrap ``overlay-content`` in ``overlay-body``
#     this can be added. This means that
#
#     ```qmd
#     ::: { .overlay }
#
#     ::: { .overlay-content }
#     :::
#
#     :::
#     ```
#
#     should become
#
#     ```html
#     <div classes="overlay">
#         <div classes="overlay-body">
#             <div classes="overlay-content">
#             </div>
#         </div>
#     </div>
#     ```
#     """
#
#     # NOTE: Navbar is added by JS.
#     element.content = (
#         pf.Div(
#             *element.content,
#             classes=["overlay-body"],
#         ),
#     )
#     return element


class FilterFloaty(util.BaseFilter):
    filter_name = "floaty"
    filter_config_cls = ConfigFloaty

    _config: ConfigFloaty | None

    def __init__(self, doc: pf.Doc | None = None):
        super().__init__(doc=doc)
        self._config = None

    @property
    def config(self) -> ConfigFloaty:
        if self._config is not None:
            return self._config

        self._config = ConfigFloaty.model_validate(
            {"floaty": self.doc.get_metadata("floaty")}  # type: ignore
        )
        return self._config

    def __call__(self, element: pf.Element):
        if self.doc.format != "html":
            return element

        if not isinstance(element, pf.Div):
            return element

        # if "overlay" in element.classes:
        #     return wrap_overlay_content(element)

        if element.identifier not in self.config.floaty or self.doc.format != "html":
            return element

        config = self.config.floaty[element.identifier]
        element = config.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterFloaty)
