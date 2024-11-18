from datetime import datetime
from typing import Annotated, Any, Callable

import pydantic
import rich
import rich.syntax
import yaml
from pydantic.fields import FieldInfo


def print_yaml(data, *, name: str | None = None, pretty: bool = True):
    if isinstance(data, pydantic.BaseModel):
        data = data.model_dump(mode="json")

    code = "---\n" + (f"# {name}\n" if name is not None else "") + yaml.dump(data)
    if not pretty:
        print(code)
        return

    s = rich.syntax.Syntax(
        code,
        "yaml",
        theme="fruity",
        background_color="default",
    )
    rich.print(s)


# class Field(FieldInfo):
#
#     def __init__(self, *args, fake: Callable[[], Any] | None = None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fake = fake


class HasTimestamp(pydantic.BaseModel):
    time: Annotated[
        datetime,
        pydantic.Field(default_factory=lambda: datetime.now()),
    ]

    @pydantic.computed_field
    @property
    def timestamp(self) -> int:
        return int(datetime.timestamp(self.time))
