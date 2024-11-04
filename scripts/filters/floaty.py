from typing import Annotated, Generic, Iterable, Literal, TypeVar

import panflute as pf
import pydantic

from scripts.filters import util


class ConfigFloatyItemIconify(pydantic.BaseModel):
    set_: Annotated[str, pydantic.Field(alias="set")]
    name: str
    size: Annotated[int | None, pydantic.Field(default=None)]
    label: Annotated[str | None, pydantic.Field(default=None)]


class ConfigFloatyItemImage(pydantic.BaseModel):
    iconify: ConfigFloatyItemIconify


class ConfigFloatyItem(pydantic.BaseModel):
    image: ConfigFloatyItemImage
    href: Annotated[
        str | None,
        pydantic.Field(
            "A link to go to when clicked on. Should open in a new tab."
            "Will be ignored when an overlay is included."
        ),
    ]
    # name: str
    title: str

    # TODO: It might be better to put the overlay directly in the document so
    #       that overlay content can be written a quarto directly.
    # TODO: This belongs in a separate overlay section.
    description: Annotated[
        str,
        pydantic.Field(description="Description to be displayed in the overlay."),
    ]

    def hydrate_iconify_li(self, *args, include_link: bool, **kwargs):
        res = self.hydrate_iconify(*args, **kwargs)
        if include_link and self.href is not None:
            res = pf.Link(res, url=self.href)

        return pf.ListItem(pf.Para(res))

    def hydrate_iconify_tr(
        self, *args, cells_extra: Iterable[pf.TableCell] | None = None, **kwargs
    ):

        kwargs["inline"] = False

        cells = (
            pf.TableCell(self.hydrate_iconify(*args, **kwargs)),
            pf.TableCell(pf.Para(pf.Str(self.title))),
        )
        if cells_extra is not None:
            cells = (*cells, *cells_extra)

        return pf.TableRow(*cells)

    def hydrate_iconify(
        self,
        size: int,
        key: int,
        *,
        inline: bool = True,
    ):
        """Should make the iconify icon."""

        # NOTE: Font size MUST be in pixels for JS to ensure list item resize.
        attrs = (
            f'icon="{self.image.iconify.set_}:{self.image.iconify.name}"',
            f"aria-label={self.image.iconify.label or self.title}",
            f"title={self.title}",
            f"style='font-size: {self.image.iconify.size or size}px;'",
            f"data-key={key}",
        )
        raw = f'<iconify-icon {" ".join(attrs)}></iconify-icon>'

        if inline:
            el = pf.RawInline(raw, format="html")
        else:
            el = pf.RawBlock(raw, format="html")

        return el

    def hydrate_overlay_content_item(
        self,
        size: int,
        key: int,
    ):
        """Should make content to put in overlay-content"""

        # NOTE: Hidden by js.
        overlay_text = pf.RawBlock(
            pf.convert_text(self.description, "markdown", "html")
        )

        return pf.Div(
            pf.Div(
                self.hydrate_iconify(size, key, inline=False),
            ),
            pf.Div(pf.Header(pf.Str(self.title)), classes=["p-1"]),
            pf.Div(overlay_text, classes=["p-1"]),
            classes=["overlay-content-item", "p-5"],
            attributes={"data-key": str(key)},
        )


T_ConfigFloatySection = TypeVar("T_ConfigFloatySection", bound=ConfigFloatyItem)
FieldClasses = Annotated[list[str], pydantic.Field(default_factory=list)]
FieldInclude = Annotated[bool, pydantic.Field(default=True)]


class ConfigFloatySectionContainer(pydantic.BaseModel):
    # TODO: Add titles list type.
    include: FieldInclude
    classes: FieldClasses

    kind: Annotated[Literal["table", "list"], pydantic.Field(default="list")]
    size_item: int
    size_item_margin: Annotated[
        int | None,
        pydantic.Field(default=None, alias="li_margin"),
    ]


class ConfigFloatySectionOverlay(pydantic.BaseModel):
    include: FieldInclude
    classes: FieldClasses

    size_icon: int


class ConfigFloatySectionTip(pydantic.BaseModel):
    include: FieldInclude
    classes: FieldClasses

    text: Annotated[
        str,
        pydantic.Field(default="Click on any of the icons to see more."),
    ]


class ConfigFloatySection(pydantic.BaseModel, Generic[T_ConfigFloatySection]):

    include: FieldInclude
    classes: FieldClasses

    container: ConfigFloatySectionContainer
    content: list[T_ConfigFloatySection]
    overlay: ConfigFloatySectionOverlay
    tooltip: ConfigFloatySectionTip

    def hydrate_html_js(self, element: pf.Element):
        closure_name = "overlay_" + element.identifier.lower().replace("-", "_")

        li_margin = self.container.size_item_margin
        li_margin = f"'{li_margin}px'" if li_margin is not None else "null"
        kwargs = f"{{ li_margin: {li_margin} }}"
        js = f"let {closure_name} = Floaty('{ element.identifier }', {kwargs})"

        # NOTE: Javascript will look for this using ``id=overlay``.
        if self.overlay.include:
            overlay_content = (
                pf.Div(
                    # TODO: This should just be included by having a fenced div ``overlay-content``
                    #       with a header for each item.
                    *(
                        item.hydrate_overlay_content_item(self.overlay.size_icon, key)
                        for key, item in enumerate(self.content)
                    ),
                    classes=["overlay-content"],
                ),
            )

            element.content = (
                *element.content,
                pf.Div(*overlay_content, classes=["overlay"]),
            )

        element.content = (
            *element.content,
            pf.RawBlock(f"<script>{js}</script>"),
        )
        return element

    def hydrate_html_list(self, element: pf.Element):
        """Create floaties and wrap in the container div."""
        # NOTE: Links are only ever included when the overlay is not present.
        list_items = (
            config_image.hydrate_iconify_li(
                self.container.size_item,
                key,
                include_link=not self.container.include,
            )
            for key, config_image in enumerate(self.content)
        )

        classes = ["floaty-container", *self.container.classes]
        element.content = (
            pf.Div(pf.BulletList(*list_items), classes=classes),
            *element.content,
        )

        return element

    def hydrate_html_table(self, element: pf.Element):

        table_rows = (
            config_image.hydrate_iconify_tr(self.container.size_item, key)
            for key, config_image in enumerate(self.content)
        )

        element.content = (
            pf.Div(
                pf.Table(pf.TableBody(*table_rows)),
                classes=["floaty-container"],
            ),
            *element.content,
        )

        return element

    def hydrate_html(self, element: pf.Element):
        if self.container.kind == "list":
            element = self.hydrate_html_list(element)
        else:
            element = self.hydrate_html_table(element)

        self.hydrate_html_js(element)

        if self.tooltip.include:
            info = pf.Div(
                pf.Para(pf.Str(self.tooltip.text)),
                classes=["floaty-info"],
            )
            element.content.append(info)

        return element


class ConfigFloaty(pydantic.BaseModel):
    floaty: dict[str, ConfigFloatySection[ConfigFloatyItem]]


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

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        if element.identifier not in self.config.floaty or self.doc.format != "html":
            return element

        config = self.config.floaty[element.identifier]
        element = config.hydrate_html(element)

        return element


filter = util.create_run_filter(FilterFloaty)
