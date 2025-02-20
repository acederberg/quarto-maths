"""Pandoc filter to add ``iframe`` elements to quarto documents.

This is helpful for showing other pages, especially in demos.


Demo and Usage
-------------------------------

See the demo [here](./components/iframe/index.qmd).

"""

from typing import Annotated, Literal

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.api import schemas
from acederbergio.filters import util

logger = env.create_logger(__name__)

# <iframe id="live-pdf" type="application/pdf" width="100%" height="256px" src="/components/resume/experience.pdf"></iframe>
FieldKind = Annotated[Literal["pdf", "html"], pydantic.Field("pdf")]


class IFrameConfig(util.BaseHasIdentifier):
    """IFrame filter configuration.

    Specifies exactly one ``iframe``.

    :ivar target: URL or path to the target.
    :ivar height: Height of the ``iframe``.
    :ivar kind: Document type.
    """

    target: Annotated[
        str,
        pydantic.Field(),
        schemas.create_check_items(False, singleton=True),
    ]
    height: Annotated[str, pydantic.Field("512px")]
    kind: FieldKind

    @property
    def url_path(self):
        return schemas.path_to_url(self.target, self.kind)

    def hydrate(self, element: pf.Element) -> pf.Element:
        """Turn :param:`element` into an ``iframe``.

        :param element: Element to inject the iframe into.
        :returns: :param:``element`` with iframe content injected.
        """

        element.classes.append("embed-responsive")
        element.attributes.update({"height": "100%", "width": "100%"})

        raw = pf.RawBlock(
            f"<iframe id='{self.identifier}' type='application/{self.kind}'"
            f"width='100%' height='{self.height}' src='{self.url_path}'"
            "></iframe>"
        )
        element.content.append(raw)

        return element


class Config(util.BaseConfig):
    """Schema used to validate quarto metadata.

    Specifies many iframes.

    :ivar iframes: An optional list of iframe configurations.
    """

    iframes: Annotated[
        dict[str, IFrameConfig] | None,
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterIFrame(util.BaseFilterHasConfig):
    "Iframe filter."

    filter_name = "iframes"
    filter_config_cls = Config

    def __call__(self, element: pf.Element) -> pf.Element:
        # self.doc.format != "html"
        # self.config is None
        # not isinstance(element, pf.Div)

        if (
            self.doc.format != "html"
            or self.config is None
            or not isinstance(element, pf.Div)
        ):
            return element

        # logger.warning("%s", self.config)

        if element.identifier in self.config.iframes:
            config = self.config.iframes[element.identifier]
            element = config.hydrate(element)

        return element


filter = util.create_run_filter(FilterIFrame)
