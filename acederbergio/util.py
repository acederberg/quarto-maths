import json
import logging
import logging.handlers
import queue
from datetime import datetime
from typing import Annotated, Any, Mapping, overload

import pandas
import pydantic
import rich
import rich.console
import rich.syntax
import rich.table
import yaml

CONSOLE = rich.console.Console()


def print_error(err: pydantic.ValidationError, **kwargs):
    print_yaml(
        json.loads(err.json()),
        rule_title="Error Detail",
        rule_kwargs=dict(characters="=", style="bold red"),
        **kwargs,
    )


class MagicEncoder(json.JSONEncoder):

    kwargs_model_dump: dict[str, Any]

    def __init__(self, kwargs_model_dump: dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.kwargs_model_dump = kwargs_model_dump

    def default(self, o: Any) -> Any:
        if isinstance(o, pydantic.BaseModel):
            return o.model_dump(mode="json")

        try:
            return super().default(o)
        except json.JSONDecodeError:
            return str(o)


# def _pydantic_representer(dumper, obj):
#     return dumper.represent_mapping(
#         f"!{obj.__class__.__name__}", obj.model_dump(mode="json")
#     )
#
#
#
# def pydantic_representer(obj):
#     if isinstance(obj, pydantic.BaseModel):
#         return obj.model_dump(mode="json")
#     elif isinstance(obj, list):
#         return [pydantic_representer(item) for item in obj]  # Process lists
#     elif isinstance(obj, dict):
#         return {
#             key: pydantic_representer(value) for key, value in obj.items()
#         }  # Process dicts
#
#     return obj  # Return unchanged if not Pydantic-related
#
#
# def dict_representer(dumper, obj):
#     """Handles dictionaries that may contain Pydantic models."""
#     return dumper.represent_mapping("tag:yaml.org,2002:map", pydantic_representer(obj))
#
#
# yaml.add_multi_representer(pydantic.BaseModel, dict_representer)


def print_yaml(
    data,
    *,
    as_json: bool = False,
    items: bool = False,
    name: str | None = None,
    pretty: bool = True,
    rule_title: str = "",
    rule_kwargs: dict[str, Any] = dict(),
    is_complex: bool = False,
    **kwargs_model_dump,
) -> rich.syntax.Syntax | None:
    if items:
        data = [item.model_dump(mode="json", **kwargs_model_dump) for item in data]
    elif isinstance(data, pydantic.BaseModel):
        data = data.model_dump(mode="json", **kwargs_model_dump)

    if not as_json:
        if is_complex:
            encoder = MagicEncoder(kwargs_model_dump, indent=2)
            data = json.loads(encoder.encode(data))
        code = (
            "---\n" + (f"# {name}\n" if name is not None else "") + yaml.safe_dump(data)
        )
    else:
        code = MagicEncoder(kwargs_model_dump, indent=2).encode(data)

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
    return s


def print_df(
    df: pandas.DataFrame,
    *,
    index_name: str | None = None,
    colors: tuple[str, ...] = ("bright_blue", "bright_cyan"),
    **kwargs,
    # rule_title: str = "",
    # rule_kwargs: dict[str, Any] = dict(),
):
    table = rich.table.Table(**kwargs)
    if index_name is not None:
        index_name = str(index_name) if index_name else ""
        table.add_column(index_name)

    n_colors = len(colors)
    for index, column in enumerate(df.columns):
        table.add_column(str(column), justify="center")
        col = table.columns[index]
        color = colors[index % n_colors]
        col.header_style = "bold " + color
        col.style = color

    for index, value_list in enumerate(df.values.tolist()):
        row = [str(index)] if index_name is not None else []
        row += [str(x) for x in value_list]
        table.add_row(*row)

    CONSOLE.print(table)


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
        q: queue.Queue
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
