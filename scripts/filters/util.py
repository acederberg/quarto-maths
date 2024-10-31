import abc
import contextlib
import pathlib
import sys
from typing import Any, ClassVar, Protocol

import panflute as pf
import pydantic

from scripts import env


def record(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


@contextlib.contextmanager
def print_to_log(log_file: pathlib.Path):
    with open(log_file, "w") as file:
        with contextlib.redirect_stderr(file):
            yield file


class BaseFilter(abc.ABC):

    doc: pf.Doc

    filter_config_cls: ClassVar[type[pydantic.BaseModel] | None]
    filter_name: ClassVar[str]
    filter_log: ClassVar[pathlib.Path]

    def __init__(self, doc: pf.Doc):
        self.doc = doc

    def __init_subclass__(cls):

        if getattr(cls, "filter_name", None) is None:
            raise AttributeError(
                f"Missing attribute `filter_name` of `{cls.__name__}`."
            )

        cls.filter_log = env.BUILD / f"{cls.filter_name}.txt"
        return super().__init_subclass__()

    @abc.abstractmethod
    def __call__(self, element: pf.Element) -> pf.Element: ...


def create_run_filter(Filter: type[BaseFilter]):
    def wrapped(doc: pf.Doc | None = None):

        with print_to_log(Filter.filter_log):

            context: dict[str, Any] = {"filter": None}

            def do_filter(element: pf.Element, doc: pf.Doc):
                if context["filter"] is None:
                    context["filter"] = Filter(doc)

                filter = context["filter"]
                return filter(element)

            out = pf.run_filter(do_filter, doc=doc)

        return out

    return wrapped
