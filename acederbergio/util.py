from datetime import datetime
from typing import Annotated

import pydantic
import rich
import rich.syntax
import yaml


def print_yaml(data, *, name: str | None = None):
    s = rich.syntax.Syntax(
        "---\n" + (f"# {name}\n" if name is not None else "") + yaml.dump(data),
        "yaml",
        theme="fruity",
        background_color="default",
    )
    rich.print(s)


class HasTimestamp(pydantic.BaseModel):
    time: Annotated[
        datetime,
        pydantic.Field(default_factory=lambda: datetime.now()),
    ]

    @pydantic.computed_field
    def timestamp(self) -> int:
        return int(datetime.timestamp(self.time))
