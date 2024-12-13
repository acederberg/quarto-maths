import abc
import contextlib
import pathlib
import sys
from typing import ClassVar

import panflute as pf
import pydantic

from acederbergio import env


def record(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


@contextlib.contextmanager
def print_to_log(log_file: pathlib.Path):
    with open(log_file, "w") as file:
        with contextlib.redirect_stderr(file):
            yield file


class BaseFilter(abc.ABC):

    _doc: pf.Doc | None

    filter_config_cls: ClassVar[type[pydantic.BaseModel] | None]
    filter_name: ClassVar[str]
    filter_log: ClassVar[pathlib.Path]

    @property
    def doc(self) -> pf.Doc:
        d = self._doc
        if d is None:
            raise ValueError("Document not yet set.")

        return d

    def __init__(self, doc: pf.Doc | None = None):
        self._doc = doc

    def __init_subclass__(cls):

        if getattr(cls, "filter_name", None) is None:
            raise AttributeError(
                f"Missing attribute `filter_name` of `{cls.__name__}`."
            )

        cls.filter_log = env.DEV / f"{cls.filter_name}.txt"
        return super().__init_subclass__()

    @abc.abstractmethod
    def __call__(self, element: pf.Element) -> pf.Element: ...

    def prepare(self, doc: pf.Doc) -> None:
        self._doc = doc

    def finalize(self, doc: pf.Doc) -> None: ...

    def action(self, element: pf.Element, doc: pf.Doc):
        if self._doc is None:
            self._doc = doc
        return self(element)


def create_run_filter(Filter: type[BaseFilter]):
    def wrapped(doc: pf.Doc | None = None):

        filter = Filter()
        with print_to_log(Filter.filter_log):
            out = pf.run_filter(
                filter.action,
                finalize=filter.finalize,
                prepare=filter.prepare,
                doc=doc,
            )

        return out

    return wrapped
