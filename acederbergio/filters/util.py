import abc
import os
import pathlib
from typing import (
    Annotated,
    Any,
    ClassVar,
    Literal,
    Protocol,
    Required,
    Type,
    TypeAlias,
    TypedDict,
    TypeVar,
)

import jinja2
import panflute as pf
import pydantic
from dsa.bst import secrets
from pydantic.v1.utils import deep_update

from acederbergio import env

logger = env.create_logger(__name__)

Breakpoint = Literal["xs", "sm", "md", "lg", "xl", "xxl"]
FieldKey = Annotated[
    str,
    pydantic.Field(default_factory=lambda: secrets.token_urlsafe(16)),
]
FieldClasses = Annotated[list[str] | None, pydantic.Field(None)]
FieldAttributes = Annotated[dict[str, str] | None, pydantic.Field(None)]
FieldIdentifier = Annotated[str, pydantic.Field()]


class BaseFilter(abc.ABC):

    _doc: pf.Doc | None

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
        if cls.__name__.startswith("Base"):
            return

        if getattr(cls, "filter_name", None) is None:
            raise AttributeError(
                f"Missing attribute `filter_name` of `{cls.__name__}`."
            )

        if not os.path.exists(env.DEV):
            os.mkdir(env.DEV)

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

    @classmethod
    def createFilter(cls):
        def wrapped(doc: pf.Doc | None = None):
            filter = cls(doc=doc)
            out = pf.run_filter(
                filter.action,
                finalize=filter.finalize,
                prepare=filter.prepare,
                doc=doc,
            )

            return out

        return wrapped


T_BaseMapFilter = TypeVar("T_BaseMapFilter", bound=pydantic.BaseModel)


# NOTE: Protocol cannot be factored into ``BaseFilterHasConfig`` since subclasses
#       should inherit from genertic.
class BaseFilterHasConfigProto(Protocol[T_BaseMapFilter]):
    filter_name: str
    filter_config_cls: ClassVar[Type[T_BaseMapFilter]]
    _config: T_BaseMapFilter | None

    @property
    def config(self) -> T_BaseMapFilter | None: ...


class BaseFilterHasConfig(BaseFilter, BaseFilterHasConfigProto[T_BaseMapFilter]):
    """Should expect metadata like

    ```yaml
    ---
    {{ cls.filter_name }}:
        ...
    ```
    """

    class FilterConfigInfo(TypedDict):

        name_filter_cls: Required[str]
        name_filter: Required[str]
        name_cls: Required[str]
        cls: Required[Type[pydantic.BaseModel]]
        module: Required[str]

    filter_config_infos: ClassVar[dict[str, FilterConfigInfo]] = dict()
    filter_config_default: ClassVar[Any] = None

    def __init__(self, doc: pf.Doc | None = None):
        super().__init__(doc)
        self._config = None

    def __init_subclass__(cls) -> None:
        if cls.__name__.startswith("Base"):
            return

        if getattr(cls, "filter_config_cls", None) is None:
            raise ValueError(f"Missing `filter_config_cls` on `{cls.__name__}`.")

        if cls.filter_name not in cls.filter_config_cls.model_fields:
            raise ValueError(
                f"`{cls.filter_config_cls.__name__}` should have a field with "
                f"the filter name `{cls.filter_name}`."
            )

        cls.filter_config_infos[cls.filter_name] = cls.FilterConfigInfo(
            cls=cls.filter_config_cls,
            name_cls=cls.filter_config_cls.__name__,
            name_filter_cls=cls.__name__,
            name_filter=cls.filter_name,
            module=cls.__module__,
        )

    @property
    def config(self) -> T_BaseMapFilter | None:
        if self._config is not None:
            return self._config

        logger.debug("Getting metadata for filter `%s`.", self.filter_name)
        data = self.doc.get_metadata(self.filter_name, self.filter_config_default)  # type: ignore
        if data is None or data == "":  # Because panflute can get '' instead of null.
            logger.debug("Metadata was empty, `%s`.", data)
            self._config = None
            return None

        logger.debug("Validating metadata for filter `%s`.", self.filter_name)
        self._config = self.filter_config_cls.model_validate({self.filter_name: data})
        return self._config


class BaseConfig(pydantic.BaseModel):

    model_config = pydantic.ConfigDict(
        extra="forbid",
    )


class BaseHasIdentifier(BaseConfig):

    identifier: FieldIdentifier

    @pydantic.computed_field
    @property
    def js_name(self) -> str:
        """Make the name for any javascript variables."""
        name_segments = tuple(map(str.title, self.identifier.lower().split("-")))
        return "floaty" + "".join(name_segments)


class BaseElemConfig(BaseConfig):
    classes: FieldClasses
    identifier: FieldIdentifier


class BaseHasKey(BaseConfig):
    key: FieldKey


ContentFromListMode = Literal["identifier", "key"]


def create_content_from_list(mode="identifier"):
    """This allows user input of a list of items with ``identifiers``.

    Use this to turn a list of items like ``BaseHasIdentifier`` into a dictionary
    mapping indentifiers to their respective configs.

    Checks for repeated keys.
    """

    def res(v):

        if isinstance(v, list):
            # NOTE: Handle singleton.
            v_as_dict = {
                w.get(mode) if isinstance(w, dict) else str(k): w
                for k, w in enumerate(v)
            }

            if len(v_as_dict) != len(v):
                raise ValueError("Key collisions found.")

            return v_as_dict

        return v

    return res


content_from_list_identifier = create_content_from_list("identifier")
content_from_list_key = create_content_from_list("key")


def ignore_null_string(v: Any):
    """Because getting metadata using panflute results in `''` when `null`
    is provided and pydantic does not ignore it."""
    if isinstance(v, dict):
        return v

    return None if not v else v


ValidatorIgnoreFalsy = pydantic.BeforeValidator(ignore_null_string)


def update_classes(update: list[str], *args: list[str] | None):
    """Merge classes from a list of optional amendments."""
    for item in args:
        if item is not None:
            update += item

    return update


def update_attributes(
    update: dict[str, str], *args: dict[str, str] | None
) -> dict[str, str]:
    items = tuple(item for item in args if item is not None)
    return deep_update(update, *items)


def config_infos():
    """Get all config info from registry of ``BaseFilterHasConfig``.

    Should be generated by its ``__init_subclass__`` method.
    """
    return BaseFilterHasConfig.filter_config_infos


def compile_model(*names: str):
    infos = config_infos()
    if names:
        _bases = tuple(infos[name] for name in names)
    else:
        _bases = infos.values()

    bases = tuple(map(lambda item: item["cls"], _bases))

    return pydantic.create_model(
        "ConfigComposite",
        __base__=type(
            "_ConfigComposite",
            bases,
            {},
        ),
    )


def create_run_filter(Filter: type[BaseFilter]):
    return Filter.createFilter()


JINJA_ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(env.TEMPLATES))
JINJA_ENV.get_template("./floaty.j2")
