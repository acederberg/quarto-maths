from typing import Annotated, Callable

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import util

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
    level: Annotated[int, pydantic.Field(4, ge=1, le=6)]

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
                pf.RawInline(
                    "<div class='d-flex'>"
                    f"  <div class='experience-title'><strong>{ self.title }</strong></div>"  # type: ignore[attr-defined]
                    f"  <div class='experience-organization'><strong>{ self.organization }</strong></div>"
                    "</div>"
                ),
                level=self.level,
                classes=["experience-header"],
            ),
            pf.Div(
                pf.Para(pf.Emph(*self.create_start_stop())),
                classes=["experience-duration"],
            ),
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
        element.classes.append("experience")
        return element

    def hydrate_tex(self, element: pf.Element) -> pf.Element:
        head_elements = self.create_header_tex()
        element.content = (*head_elements, *element.content)
        return element


class ConfigExperienceItem(BaseExperienceItem):
    title: str


class ConfigEducationItem(BaseExperienceItem):
    concentration: str
    degree: str

    @pydantic.computed_field
    @property
    def title(self) -> str:
        return self.degree


class ConfigHeadshot(pydantic.BaseModel):
    url: Annotated[str, pydantic.Field()]
    title: Annotated[str, pydantic.Field()]
    description: Annotated[str, pydantic.Field()]


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
        pydantic.BeforeValidator(util.content_from_list_identifier),
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


class Config(pydantic.BaseModel):
    resume: ConfigResume


# --------------------------------------------------------------------------- #


class FilterResume(util.BaseFilterHasConfig):
    filter_config_cls = Config
    filter_name = "resume"

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div) or self.config is None:
            return element

        for subconfig in (self.config.resume.education, self.config.resume.experience):
            element = self.hydrate(element, subconfig)

        if element.identifier == "resume-headshot":
            element = self.config.resume.hydrate_headshot(self.doc, element)

        return element

    def hydrate(self, element, subconfig: dict[str, util.BaseHasIdentifier]):
        if not subconfig:
            return element

        if element.identifier in subconfig:
            config = subconfig[element.identifier]
            if self.doc.format == "html":
                element = config.hydrate_html(element)  # type: ignore
            else:
                element = config.hydrate_tex(element)  # type: ignore

        return element


filter = util.create_run_filter(FilterResume)
