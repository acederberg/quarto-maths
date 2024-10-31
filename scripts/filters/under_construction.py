import panflute as pf

from scripts.filters import util

DONOTPANIC = (
    "Do not panic, you (the user) have done nothing wrong. There will be "
    "something here soon but changes are yet to be deployed."
)


class FilterUnderConstruction(util.BaseFilter):
    filter_name = "under_construction"
    filter_config_cls = None

    def under_construction(self, element: pf.Element):
        header = pf.Header(pf.Str("This Page is Currently Under Construction."))
        p = pf.Para(pf.Str(DONOTPANIC))
        floaty = pf.Div(
            pf.Div(
                pf.Div(
                    pf.RawBlock(
                        "<iconify-icon icon='misc:construction' style='font-size: 512px;'></iconify-icon>"
                    ),
                    classes=["floaty"],
                ),
                pf.Div(
                    header,
                    p,
                    identifier="under-construction-detail",
                    classes=["px-3"],
                ),
                classes=["floaty-container-single"],
            ),
        )
        element.content = (floaty, *element.content)
        return element

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        if "under-construction" == element.identifier:
            return self.under_construction(element)
        return element


filter = util.create_run_filter(FilterUnderConstruction)
