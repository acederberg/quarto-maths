"""Automate the rendering of certain mermaid daigrams.

While this can be done in quarto already, it is a pain and does not work in 
a way I like.
"""

import subprocess
from typing import Annotated

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import util

logger = env.create_logger(__name__)


class MermaidConfig(util.BaseConfig):
    file: Annotated[str, pydantic.Field()]
    output: Annotated[str, pydantic.Field(description="Output name.")]
    # s3: Annotated[
    #     S3AssetConfig | None,
    #     pydantic.Field(None, description="S3 Bucket Configuration"),
    # ]

    def render(self):
        subprocess.run(
            ["mmdc", "-i", self.file, "-o", self.output],
            capture_output=True,
            text=True,
            check=True,
        )


class Config(pydantic.BaseModel):

    mermaid_export: Annotated[
        list[MermaidConfig] | None,
        pydantic.Field(None),
    ]


class FilterMermaidExport(util.BaseFilterHasConfig):
    filter_name = "mermaid_export"
    filter_config_cls = Config

    def __call__(self, elem: pf.Element):
        return elem

    def action(self, element: pf.Element, doc: pf.Doc):

        if self.config is None:
            return

        for item in self.config.mermaid_export:
            item.render()


filter = FilterMermaidExport.createFilter()
