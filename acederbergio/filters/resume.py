"""Pandoc filters for the resume.

Much of the functionality in the resume is acheived through 
[the overlay filter](/components/overlay/index.html) and [the floaty filter 
and its variations](/components/floaty/index.html).

This code is responsible for turning experience items item ``list-groups``
for the ``html`` document, and makes nice headers for both ``html`` and ``pdf``
outputs.

For a demo, see [the component demo](/components/resume/index.html).
For the final result, see [my resume](/resume/index.html) for a demonstation of 
the ``HTML`` result or [my resume as a ``PDF``](/resume/resume.pdf).
"""

from typing import Annotated, ClassVar

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import util

logger = env.create_logger(__name__)


class BaseExperienceItem(util.BaseHasIdentifier):
    organization: str
    start: str
    stop: str
    level: Annotated[int, pydantic.Field(4, ge=1, le=6)]

    def create_start_stop(self):
        """Create start and stop range."""
        return (
            pf.Str(self.start),
            pf.Space(),
            pf.Str("-"),
            pf.Space(),
            pf.Str(self.stop),
        )

    def create_header_html(self) -> tuple[pf.Element, ...]:
        """Create the ``HTML`` header."""
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
        """Create the ``TeX`` or ``PDF`` header."""
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
        """Tranform an ``HTML`` list into a bootstrap listgroup and add a nice header."""

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
        """Transform the header into a fancy header."""

        head_elements = self.create_header_tex()
        element.content = (*head_elements, *element.content)
        logger.critical("%s", element.to_json())
        return element


class ConfigExperienceItem(BaseExperienceItem):
    title: str


class ConfigEducationItem(BaseExperienceItem):
    concentration: str
    degree: str

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def title(self) -> str:
        return self.degree


class ConfigHeadshot(pydantic.BaseModel):
    url: Annotated[str, pydantic.Field()]
    title: Annotated[str, pydantic.Field()]
    description: Annotated[str, pydantic.Field()]


class ConfigResume(pydantic.BaseModel):
    """Resume configuration.

    :ivar headshot: Specifies the headshot.
    :ivar experience: Specifies a work experience to transform.
    :ivar education: Specifies an education experience to transform.
    """

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

    # def hydrate_profile(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
    #     element.content = (
    #         pf.Header(pf.Str("Career Profile"), level=2),
    #         *element.content,
    #     )
    #
    #     return element

    def hydrate_headshot(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        """Hydrate the headshot."""

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
    """Schema used to validate quarto metadata."""

    resume: ConfigResume


# --------------------------------------------------------------------------- #


class FilterResume(util.BaseFilterHasConfig):
    """Resume filter."""

    filter_config_cls = Config
    filter_name: ClassVar[str] = "resume"

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
