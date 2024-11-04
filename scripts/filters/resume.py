from datetime import date, timedelta
from typing import Annotated, Callable

import panflute as pf
import pydantic

from scripts.filters import floaty, util

ELEMENTS_SIDEBAR = {
    "resume-contact",
    "resume-skills",
    "resume-headshot",
    "resume-links",
}
ELEMENTS_BODY = {"resume-experience", "resume-projects", "resume-education"}


def get_hydrate(
    instance, element: pf.Element, elements: set[str]
) -> Callable[[pf.Doc, pf.Element], pf.Element] | None:
    if element.identifier not in elements:
        return None

    meth_name = element.identifier.replace("resume-", "hydrate_")
    hydrator = getattr(instance, meth_name)
    return hydrator


class BaseExperienceItem(pydantic.BaseModel):
    organization: str
    start: str
    stop: str
    content: Annotated[list[str] | None, pydantic.Field(default=None)]

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
            pf.Header(pf.Str(self.title), level=3),  # type: ignore[attr-exists]
            pf.Para(pf.Strong(pf.Str(self.organization))),
            pf.Para(pf.Emph(*self.create_start_stop())),
        )

    def create_header_tex(self) -> tuple[pf.Element]:
        header_textbar = (
            pf.Space(),
            pf.RawInline("\\textbar{}", format="latex"),
            pf.Space(),
        )
        return (
            pf.Header(
                pf.Str(self.title),  # type: ignore[attr-exists]
                *header_textbar,
                pf.Str(self.organization),
                pf.Space(),
                pf.RawInline("\\hfill", format="latex"),
                pf.Space(),
                *self.create_start_stop(),
                level=3,
            ),
        )

    def hydrate(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        if doc.format == "latex":
            head_elements = self.create_header_tex()
        else:
            head_elements = self.create_header_html()

        if self.content is not None:
            element.content = (
                *element.content,
                pf.BulletList(
                    *(pf.ListItem(pf.Para(pf.Str(item))) for item in self.content)
                ),
            )

        element.content = (*head_elements, *element.content)

        return element


class ConfigExperienceItem(BaseExperienceItem):
    title: str
    tools: Annotated[
        None | floaty.ConfigFloatySection[floaty.ConfigFloatyItem],
        pydantic.Field(
            default=None,
            description="Some tools to enumerate.",
        ),
    ]

    def hydrate(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        element = super().hydrate(doc, element)
        if self.tools is not None and format == "html":
            identifier = f"floaty_tools_{self.title}_{self.organization}"
            identifier = identifier.replace("-", "_").replace(" ", "_")
            element.content = (
                pf.Div(
                    *element.content,
                    pf.Div(
                        pf.Header(pf.Str("Tools"), level=4),
                        self.tools.hydrate_html(
                            pf.Div(
                                identifier=identifier,
                                classes=["floaty"],
                            )
                        ),
                    ),
                ),
            )

        return element


class ConfigEducationItem(BaseExperienceItem):
    concentration: str
    degree: str

    @pydantic.computed_field
    def title(self) -> str:
        return self.degree + ", " + self.concentration


class ConfigContactItem(floaty.ConfigFloatyItem):
    value: str

    def hydrate_iconify_tr(self, *args, **kwargs):
        extra = pf.TableCell(pf.Para(pf.Str(self.value)))
        return super().hydrate_iconify_tr(
            *args,
            cells_extra=[extra],
            **kwargs,
        )


TODAY = date.today()


# TODO: Skillbar to take up row on hover (and in overlay).
class ConfigSkillsItem(floaty.ConfigFloatyItem):
    since: date
    progress_classes: Annotated[
        list,
        pydantic.Field(
            default_factory=lambda: [
                "bg-warning",
                "progress-bar-animated",
                "progress-bar-striped",
            ]
        ),
    ]

    @pydantic.computed_field
    @property
    def duration(self) -> timedelta:
        diff = TODAY - self.since
        return diff

    def hydrate_progress_bar(self, _parent: "ConfigSkills"):
        percent = (100 * self.duration.days) // _parent.duration.days

        _n_years = self.duration.days // 365
        _n_months = (self.duration.days % 365) // 31

        content_str = []
        if _n_years:
            content_str.append(f"{_n_years} Years")
        if _n_months:
            content_str.append(f"{_n_months} Months")

        return pf.Div(
            pf.Div(
                pf.RawBlock(", ".join(content_str)),
                classes=["progress-bar", "px-2", *self.progress_classes],
                attributes={"style": f"width: {percent}%;"},
            ),
            classes=["progress", "my-5"],
            attributes={
                "aria-valuenow": str(self.duration.days),
                "aria-valuemin": "0",
                "aria-valuemax": str(_parent.duration.days),
                "role": "progressbar",
            },
        )

    def hydrate_overlay_content_item(  # type: ignore
        self,
        element: pf.Element,
        *,
        _parent: "ConfigSkills",
    ):
        el = super().hydrate_overlay_content_item(element, _parent=_parent)
        el.content.insert(2, self.hydrate_progress_bar(_parent))
        el.content.insert(
            3,
            pf.Plain(
                pf.Strong(pf.Str("Since "), pf.Str(self.since.strftime("%B, %Y"))),
            ),
        )

        return el


class ConfigSkills(floaty.ConfigFloatySection[ConfigSkillsItem]):

    @pydantic.computed_field
    @property
    def duration(self) -> timedelta:
        vv = max(self.content.values(), key=lambda item: item.duration)  # type: ignore
        return vv.duration


class ConfigHeadshot(pydantic.BaseModel):
    url: Annotated[str, pydantic.Field()]
    title: Annotated[str, pydantic.Field()]
    description: Annotated[str, pydantic.Field()]


class ConfigSidebar(pydantic.BaseModel):
    tex_width: Annotated[float, pydantic.Field(lt=1, gt=0, default=0.35)]
    headshot: Annotated[ConfigHeadshot | None, pydantic.Field(default=None)]
    skills: Annotated[
        ConfigSkills | None,
        pydantic.Field(default=None, description="Skills configuration."),
    ]
    contact: Annotated[
        floaty.ConfigFloatySection[ConfigContactItem] | None,
        pydantic.Field(
            default=None,
            description="Contact information configuration.",
        ),
    ]
    links: Annotated[
        floaty.ConfigFloatySection[floaty.ConfigFloatyItem] | None,
        pydantic.Field(
            default=None,
            description=(
                "Links configuration. Make sure to set "
                "``$.overlay.include=False`` so that links are clickable."
            ),
        ),
    ]

    def do_floaty(
        self, config: floaty.ConfigFloatySection, doc: pf.Doc, element: pf.Element
    ) -> None:
        """Given a section, look for its floaty (or make it) and hydrate.

        Only floaties with overlay content should need to include their own
        floaty explicitly.
        """

        floaty_identifier = element.identifier + "-floaty"
        state = {"count": 0}

        def handle_floaty(el: pf.Element, _: pf.Doc) -> pf.Element:
            if not isinstance(el, pf.Div):
                return el

            if el.identifier != floaty_identifier:
                return el

            el = config.hydrate_html(el)
            state["count"] += 1
            return el

        element.walk(handle_floaty)

        util.record(floaty_identifier)
        util.record(state)
        if not state["count"]:
            floaty = pf.Div(
                identifier=floaty_identifier,
                classes=["floaty"],
            )
            handle_floaty(floaty, doc)
            element.content.append(floaty)

    def hydrate_contact(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        """Sidebar skills."""
        if self.contact is None:
            return element

        if doc.format == "html":
            self.do_floaty(self.contact, doc, element)
        else:
            pf.Para(pf.Str("Paceholder content"))
        #
        element.content = (
            pf.Header(pf.Str("Contact"), level=2),
            *element.content,
        )

        return element

    def hydrate_skills(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        """Sidebar skills."""

        if self.skills is None:
            return element
        # NOTE: Adding both results in broken overlays.
        if doc.format == "html":
            self.do_floaty(self.skills, doc, element)
        else:
            ...
            # skills = pf.Para(pf.Str("Placeholder content."))

        element.content = (
            pf.Header(pf.Str("Skills"), level=2),
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
                    classes=["p-5"],
                )
            )

        else:
            headshot = pf.Para(pf.Str("Paceholder content"))

        element.content = (headshot, *element.content)
        return element

    def hydrate_links(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        """Sidebar links."""
        if self.links is None:
            return element

        if doc.format == "html":
            links = self.links.hydrate_html(
                pf.Div(identifier="resume_links_floaty", classes=["floaty"])
            )

        else:
            links = pf.Para(pf.Str("Paceholder content"))

        element.content = (
            pf.Header(pf.Str("Links"), level=2),
            *element.content,
            links,
        )
        return element

    def __call__(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        if (hydrator := get_hydrate(self, element, ELEMENTS_SIDEBAR)) is not None:
            return hydrator(doc, element)
        return element


class ConfigBody(pydantic.BaseModel):
    experience: Annotated[
        dict[str, ConfigExperienceItem] | None,
        pydantic.Field(
            default=None,
            description="Work experience configuration.",
        ),
    ]
    education: Annotated[
        dict[str, ConfigEducationItem] | None,
        pydantic.Field(
            default=None,
            description="Education experience configuration.",
        ),
    ]

    def hydrate_projects(self, _: pf.Doc, element: pf.Element) -> pf.Element:
        """Body projects."""
        # if self.doc.format == "html":
        #     projects = self.config.sidebar.projects.hydrate_html(
        #         pf.Div(identifier="_projects", classes=["floaty"])
        #     )
        # else:
        #     projects = pf.Para(pf.Str("Paceholder content"))

        element.content = (
            pf.Header(pf.Str("Projects"), level=2),
            *element.content,
            # projects,
        )
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
            pf.Header(pf.Str("Experience"), level=2), *element.content
        )
        return element

    def __call__(self, doc: pf.Doc, element: pf.Element) -> pf.Element:
        if not isinstance(element, pf.Div):
            return element

        if (hydrator := get_hydrate(self, element, ELEMENTS_BODY)) is not None:
            return hydrator(doc, element)

        if "experience" in element.classes and self.experience is not None:
            config = self.experience[element.attributes["experience_item"]]
            return config.hydrate(doc, element)

        if "education" in element.classes and self.education is not None:
            config = self.education[element.attributes["education_item"]]
            return config.hydrate(doc, element)

        return element


class ConfigResume(pydantic.BaseModel):
    # NOTE: These are required so tex layout is not whacky.
    sidebar: Annotated[
        ConfigSidebar,
        pydantic.Field(
            description="Sidebar content configuration.",
        ),
    ]
    body: Annotated[
        ConfigBody | None,
        pydantic.Field(
            description="Main body configuration.",
        ),
    ]

    def __call__(self, doc: pf.Doc, element: pf.Element):
        if self.sidebar is not None:
            element = self.sidebar(doc, element)

        if self.body is not None:
            element = self.body(doc, element)

        return element


# --------------------------------------------------------------------------- #


class FilterResume(util.BaseFilter):
    filter_config_cls = ConfigResume
    filter_name = "resume"

    config: ConfigResume
    doc: pf.Doc
    identifier_to_hydrate: dict[str, Callable[[pf.Element], pf.Element]]

    def __init__(self, doc: pf.Doc):
        self.doc = doc
        self.config = ConfigResume.model_validate(doc.get_metadata("resume"))  # type: ignore

    def layout(self, element: pf.Element):

        # NOTE: ``HTML`` formatting is to be done using bootstrap in the
        #       document itself. Bootstrap divs (obviously) only affect ``HTML``.
        if self.doc.format == "html":
            pass

        elif self.doc.format == "latex":

            size = self.config.sidebar.tex_width
            if element.identifier == "resume-sidebar":
                element.content = (
                    pf.RawBlock(
                        "\\begin{minipage}[t][0.7\\textheight][t]{"
                        + str(size)
                        + "\\textwidth}",
                        format="latex",
                    ),
                    *element.content,
                )

            elif element.identifier == "resume-body":
                # NOTE: End of minipage must be next to start of next for columns.
                element.content = (
                    pf.RawBlock(
                        "\\end{minipage}\\hfill\\begin{minipage}[t][0.7\\textheight][t]{"
                        + str(1 - size - 0.05)
                        + "\\textwidth}",
                        format="latex",
                    ),
                    *element.content,
                    pf.RawBlock("\\end{minipage}", format="latex"),
                )

            elif element.identifier == "resume":
                ...

        return element

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        element = self.layout(element)
        element = self.config(self.doc, element)

        return element


filter = util.create_run_filter(FilterResume)
