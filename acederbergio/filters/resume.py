from typing import Annotated, Any, Callable, Iterable, Literal

import panflute as pf
import pydantic
from pydantic.v1.utils import deep_update

from acederbergio import env
from acederbergio.filters import floaty, util

ELEMENTS = {
    "resume-profile",
    "resume-headshot",
    "resume-experience",
    "resume-education",
}

logger = env.create_logger(__name__)


def get_hydrate(
    instance, element: pf.Element, elements: set[str] = ELEMENTS
) -> Callable[[pf.Doc, pf.Element], pf.Element] | None:
    """For an element with an identifier, find the corresponding hydrator."""
    if element.identifier not in elements:
        return None

    meth_name = element.identifier.replace("resume-", "hydrate_")
    hydrator = getattr(instance, meth_name)
    return hydrator


class BaseExperienceItem(util.BaseHasIdentifier):
    organization: str
    start: str
    stop: str
    level: Annotated[int, pydantic.Field(3, ge=1, le=6)]

    def create_start_stop(self):
        return (
            pf.Str(self.start),
            pf.Space(),
            pf.Str("-"),
            pf.Space(),
            pf.Str(self.stop),
        )

    def create_header_html(self) -> tuple[pf.Element, ...]:
        return (
            pf.Header(
                pf.Str(self.title),  # type: ignore[attr-defined]
                pf.Space(),
                pf.Str("|"),
                pf.Space(),
                pf.Strong(pf.Str(self.organization)),
                level=self.level,
            ),
            pf.Para(pf.Emph(*self.create_start_stop())),
        )

    def create_header_tex(self) -> tuple[pf.Element, pf.Element]:
        header_textbar = (
            pf.Space(),
            pf.RawInline("\\hfill", format="latex"),
            pf.Space(),
        )
        return (
            pf.Header(
                pf.Str(self.organization),
                level=3,
            ),
            pf.Header(
                pf.Str(self.title),  # type: ignore[attr-defined]
                *header_textbar,
                pf.Emph(*self.create_start_stop()),
                level=4,
            ),
        )

    def hydrate_html(self, element: pf.Element) -> pf.Element:

        def handle_list_group(element: pf.Element, doc: pf.Doc):
            if not isinstance(element, pf.BulletList):
                return

            element = pf.Div(
                *(
                    pf.Div(*item.content, classes=["list-group-item"])
                    for item in element.content
                ),
                classes=["list-group"],
            )
            return element

        element.walk(handle_list_group)

        head_elements = self.create_header_html()
        element.content = (*head_elements, *element.content)
        return element

    def hydrate_tex(self, element: pf.Element) -> pf.Element:
        head_elements = self.create_header_tex()
        element.content = (*head_elements, *element.content)
        return element


class ConfigExperienceItem(BaseExperienceItem):
    title: str

    def hydrate(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        element = super().hydrate(doc, element)
        # if self.tools is not None and format == "html":
        #     identifier = f"floaty_tools_{self.title}_{self.organization}"
        #     identifier = identifier.replace("-", "_").replace(" ", "_")
        #     element.content = (
        #         pf.Div(
        #             *element.content,
        #             pf.Div(
        #                 pf.Header(pf.Str("Tools"), level=4),
        #                 self.tools.hydrate_html(
        #                     pf.Div(
        #                         identifier=identifier,
        #                         classes=["floaty"],
        #                     )
        #                 ),
        #             ),
        #         ),
        #     )

        # if self.tools is not None:
        #     do_floaty(self.tools, doc, element)

        return element


class ConfigEducationItem(BaseExperienceItem):
    concentration: str
    degree: str

    @pydantic.computed_field
    def title(self) -> str:
        return self.degree


class ConfigHeadshot(pydantic.BaseModel):
    url: Annotated[str, pydantic.Field()]
    title: Annotated[str, pydantic.Field()]
    description: Annotated[str, pydantic.Field()]


# class ResumeFloatySection(floaty.ConfigFloatySection[floaty.T_ConfigFloatySection]):


class ConfigResume(pydantic.BaseModel):
    headshot: Annotated[ConfigHeadshot | None, pydantic.Field(default=None)]

    experience: Annotated[
        dict[str, ConfigExperienceItem] | None,
        pydantic.Field(
            default=None,
            description="Work experience configuration.",
        ),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]
    education: Annotated[
        dict[str, ConfigEducationItem] | None,
        pydantic.Field(
            default=None,
            description="Education experience configuration.",
        ),
    ]
    projects: Annotated[
        floaty.ConfigFloaty | None,
        pydantic.Field(default=None, description="Projects configuration."),
    ]

    def hydrate_profile(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        element.content = (
            pf.Header(pf.Str("Career Profile"), level=2),
            *element.content,
        )

        return element

    def hydrate_headshot(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        """Sidebar headshot."""

        if self.headshot is None:
            return element

        if doc.format == "html":
            headshot = pf.Plain(
                pf.Image(
                    url=self.headshot.url,
                    title=self.headshot.title,
                    classes=["p-5", "img-fluid"],
                )
            )

        else:
            headshot = pf.Para(pf.Str("Paceholder content"))

        element.content = (headshot, *element.content)
        return element

    def hydrate_education(self, _: pf.Doc, element: pf.Element) -> pf.Element:
        """Body education."""

        element.content = (
            pf.Header(pf.Str("Education"), level=2),
            *element.content,
        )
        return element

    def hydrate_experience(self, _: pf.Doc, element: pf.Element) -> pf.Element:
        element.content = pf.ListContainer(
            pf.Header(pf.Str("Experience"), level=2),
            *element.content,
        )
        return element

    def __call__(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        if not isinstance(element, pf.Div):
            return element

        if (hydrator := get_hydrate(self, element)) is not None:
            return hydrator(doc, element)

        config: Any
        if "experience" in element.classes and self.experience is not None:
            config = self.experience[element.attributes["experience-item"]]
            return config.hydrate(doc, element)

        if "education" in element.classes and self.education is not None:
            config = self.education[element.attributes["education-item"]]
            return config.hydrate(doc, element)

        return element


class Config(pydantic.BaseModel):
    resume: ConfigResume


# --------------------------------------------------------------------------- #


class FilterResume(util.BaseFilterHasConfig):
    filter_config_cls = Config
    filter_name = "resume"

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div) or self.config is None:
            return element

        if element.identifier in self.config.resume.experience:
            config = self.config.resume.experience[element.identifier]
            if self.doc.format == "html":
                element = config.hydrate_html(element)
            else:
                element = config.hydrate_tex(element)

        return element


filter = util.create_run_filter(FilterResume)
