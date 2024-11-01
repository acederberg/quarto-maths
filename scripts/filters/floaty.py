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


class ConfigFloatySection(pydantic.BaseModel, Generic[T_ConfigFloatySection]):
    info_text: Annotated[
        str,
        pydantic.Field(default="Click on any of the icons to see more."),
    ]
    size: int
    li_margin: Annotated[int | None, pydantic.Field(default=None)]

    # TODO: This should just be included by having a fenced div ``overlay-content``
    #       with a header for each item.
    include_overlay: Annotated[bool, pydantic.Field(default=True)]

    # TODO: Add titles list type.
    include_titles: Annotated[bool, pydantic.Field(default=False)]
    kind: Annotated[Literal["table", "list"], pydantic.Field(default="list")]

    content: list[T_ConfigFloatySection]

    def hydrate_html_js(self, element: pf.Element):
        closure_name = "overlay_" + element.identifier.lower().replace("-", "_")

        li_margin = f"'{self.li_margin}px'" if self.li_margin is not None else "null"
        kwargs = f"{{ li_margin: {li_margin} }}"
        js = f"let {closure_name} = Floaty('{ element.identifier }', {kwargs})"

        if self.include_overlay:
            element.content = (
                *element.content,
                pf.Div(
                    pf.Div(
                        *(
                            item.hydrate_overlay_content_item(self.size, key)
                            for key, item in enumerate(self.content)
                        ),
                        classes=["overlay-content"],
                    ),
                    classes=["overlay"],
                ),
            )

        element.content = (
            *element.content,
            pf.RawBlock(f"<script>{js}</script>"),
        )
        return element

    def hydrate_html_list(self, element: pf.Element):
        # NOTE: Links are only ever included when the overlay is not present.
        list_items = (
            config_image.hydrate_iconify_li(
                self.size, key, include_link=not self.include_overlay
            )
            for key, config_image in enumerate(self.content)
        )

        element.content = (
            pf.Div(pf.BulletList(*list_items), classes=["floaty-container"]),
            *element.content,
        )

        return element

    def hydrate_html_table(self, element: pf.Element):

        table_rows = (
            config_image.hydrate_iconify_tr(self.size, key)
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
        if self.kind == "list":
            element = self.hydrate_html_list(element)
        else:
            element = self.hydrate_html_table(element)

        self.hydrate_html_js(element)
        info = pf.Div(
            pf.Para(pf.Str(self.info_text)),
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
