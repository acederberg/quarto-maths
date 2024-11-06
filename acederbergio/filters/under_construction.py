from typing import Literal

import panflute as pf

from acederbergio.filters import util

FONTSIZES = {"small": 64, "medium": 128, "large": 256, "#": 512}
HEADERS = {
    "small": 4,
    "medium": 3,
    "large": 2,
    "#": 1,
}
CLASSES = {f"under-construction-{key}": key for key in FONTSIZES if key != "#"}
MSG_HEAD_PAGE = "This Page is Currently Under Construction."
MSG_HEAD_SECTION = "This Section is Currently Under Construction."
MSG_DONOTPANIC = (
    "Do not panic, you (the user) have done nothing wrong. There will be "
    "something here soon but changes are yet to be deployed."
)

Size = Literal["small", "medium", "large", "#"]


class FilterUnderConstruction(util.BaseFilter):
    filter_name = "under_construction"
    filter_config_cls = None

    def under_construction(
        self,
        element: pf.Element,
        size: Size,
    ):
        header = pf.Header(
            pf.Str(MSG_HEAD_PAGE if size == "#" else MSG_HEAD_SECTION),
            level=HEADERS[size],
        )
        if not element.content:
            element.content.append(pf.Para(pf.Str(MSG_DONOTPANIC)))

        detail = pf.Div(
            header,
            *element.content,
            identifier="under-construction-detail",
            classes=["px-3"],
        )

        floaty = pf.Div(
            pf.Div(
                pf.Div(
                    pf.RawBlock(
                        "<iconify-icon icon='misc:construction' style='font-"
                        f"size: {FONTSIZES[size]}px;'></iconify-icon>"
                    ),
                    classes=["floaty"],
                ),
                detail,
                classes=["floaty-container-single"],
            ),
        )
        element.content = (floaty,)
        return element

    def is_under_construction(self, element: pf.Element) -> Size | None:
        if "under-construction" == element.identifier:
            return "#"

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
        if not isinstance(element, pf.Div):
            return element

        # NOTE: Generally use `#under-construction` for pages and
        #       `#under-construction-{size}` for sections.

        if (size := self.is_under_construction(element)) is not None:
            return self.under_construction(element, size)

        return element


filter = util.create_run_filter(FilterUnderConstruction)
