import datetime
import pathlib
import re
import subprocess
from typing import Annotated, Any, Self

import pydantic

from acederbergio import db, util


class LogItem(pydantic.BaseModel):
    created: util.FieldTimestamp
    filename: str
    funcName: str
    levelname: str
    levelno: int
    lineno: int
    module: str
    msg: str
    name: str
    pathname: str
    threadName: str

    @pydantic.computed_field
    @property
    def created_time(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.created)


class LogQuartoItem(util.HasTime):
    origin: str
    command: str
    stderr: list[str]
    stdout: list[str]
    status_code: int

    @classmethod
    def removeANSIEscape(cls, v):
        ansi_escape = re.compile(r"\x1b\[.*?m")
        return ansi_escape.sub("", v)

    @classmethod
    def fromCompletedProcess(
        cls, origin: pathlib.Path, out: subprocess.CompletedProcess
    ) -> Self:
        return cls.model_validate(
            {
                "origin": str(origin),
                "command": out.args,
                "stderr": cls.removeANSIEscape(out.stdout.decode()).split("\n"),
                "stdout": cls.removeANSIEscape(out.stderr.decode()).split("\n"),
                "status_code": out.returncode,
            }
        )


class BaseLogSchema(util.HasTime, db.HasMongoId): ...


class LogSchema(BaseLogSchema):
    count: Annotated[int, pydantic.Field(default=0)]
    items: Annotated[
        list[LogItem],
        pydantic.Field(default_factory=list),
    ]


class LogSchemaQuarto(BaseLogSchema):
    count: Annotated[int, pydantic.Field(default=0)]
    items: Annotated[
        list[str],
        pydantic.Field(default_factory=list),
    ]
