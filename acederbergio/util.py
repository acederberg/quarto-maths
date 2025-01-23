import json
import logging
import logging.handlers
import queue
from datetime import datetime
from typing import Annotated, Any, Mapping

import pydantic
import rich
import rich.console
import rich.syntax
import yaml

CONSOLE = rich.console.Console()


def print_yaml(
    data,
    *,
    as_json: bool = False,
    items: bool = False,
    name: str | None = None,
    pretty: bool = True,
    rule_title: str = "",
    rule_kwargs: dict[str, Any] = dict(),
    **kwargs_model_dump,
):
    if items:
        data = [item.model_dump(mode="json", **kwargs_model_dump) for item in data]
    elif isinstance(data, pydantic.BaseModel):
        data = data.model_dump(mode="json", **kwargs_model_dump)

    if not as_json:
        code = (
            "---\n" + (f"# {name}\n" if name is not None else "") + yaml.safe_dump(data)
        )
    else:
        code = json.dumps(data, indent=2, default=str)

    if not pretty:
        print(code)
        return

    s = rich.syntax.Syntax(
        code,
        "yaml" if not as_json else "json",
        theme="fruity",
        background_color="default",
    )

    if rule_title or rule_kwargs:
        CONSOLE.rule(rule_title, **rule_kwargs)

    CONSOLE.print(s)


# class Field(FieldInfo):
#
#     def __init__(self, *args, fake: Callable[[], Any] | None = None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fake = fake
FieldTime = Annotated[
    datetime,
    pydantic.Field(default_factory=lambda: datetime.now()),
]
FieldTimestamp = Annotated[
    int,
    pydantic.Field(
        gt=0,
        default_factory=lambda: int(datetime.timestamp(datetime.now())),
    ),
    pydantic.BeforeValidator(int),
]


class HasTimestamp(pydantic.BaseModel):
    time: FieldTime

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def timestamp(self) -> int:
        return int(datetime.timestamp(self.time))


class HasTime(pydantic.BaseModel):
    """Inverse of ``HasTimestamp``."""

    timestamp: FieldTimestamp

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def time(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)


# Thanks mCoding: https://www.youtube.com/watch?v=9L77QExPmI0
class JSONFormatter(logging.Formatter):
    fmt_keys: set[str]

    @property
    def fmt_keys_default(self) -> set[str]:
        return {
            # "args",
            # "asctime",
            "created",
            # "exc_info",
            # "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            # "msecs",
            "msg",
            "name",
            "pathname",
            # "process",
            # "processName",
            # "relativeCreated",
            # "stack_info",
            # "thread",
            "threadName",
            # "taskName",
        }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style="%",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
        fmt_keys: list[str] | None = None,
    ) -> None:
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)

        self.fmt_keys = (
            (set(fmt_keys)) if fmt_keys is not None else self.fmt_keys_default
        )
        if "message" in self.fmt_keys:
            raise ValueError("Cannot specify `message` in format keys.")

    def format(self, record: logging.LogRecord) -> str:
        line = {key: getattr(record, key, None) for key in self.fmt_keys}
        line.update(msg=record.getMessage())
        if record.exc_info is not None:
            line.update(exc_info=self.formatException(record.exc_info))
        if record.stack_info is not None:
            line.update(stack_info=self.formatStack(record.stack_info))

        return json.dumps(line, default=str) + "\n"


class QueueHandler(logging.handlers.QueueHandler):
    """Used to queue messages that are then handled by ``SocketHandler``."""

    listener: logging.handlers.QueueListener
    handlers: list[logging.Handler]

    # NOTE: Separate queues are required otherwise handlers are overwritten.
    def __init__(self, handlers: list[logging.Handler]) -> None:
        super().__init__(q := queue.Queue())

        # NOTE: This next instruction looks stupid, but is really magic. See
        #       https://rob-blackbourn.medium.com/how-to-use-python-logging-queuehandler-with-dictconfig-1e8b1284e27a
        _handlers = list(handlers[index] for index in range(len(handlers)))
        self.handlers = _handlers
        self.listener = logging.handlers.QueueListener(q, *self.handlers)
        self.listener.start()


class SocketHandler(logging.handlers.SocketHandler):

    def emit(self, record: logging.LogRecord):
        """Emit a record without pickling.

        Ideally, the formatter is ``JSONFormatter`` from above.
        """

        # NOTE: Might be hitting a race condition. Sometim
        try:
            self.send(self.format(record).encode())
        except Exception:
            self.handleError(record)
