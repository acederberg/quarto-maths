from datetime import date
from typing import Annotated, Callable

import panflute as pf
import pydantic

from scripts.filters import floaty, util


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
            pf.Header(pf.Str(self.title), level=3),
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
                pf.Str(self.title),
                *header_textbar,
                pf.Str(self.organization),
                pf.Space(),
                pf.RawInline("\\hfill", format="latex"),
                pf.Space(),
                *self.create_start_stop(),
                level=3,
            ),
        )

    def hydrate(self, element: pf.Element, *, format: str):
        if format == "latex":
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
        pydantic.Field(default=None),
    ]

    def hydrate(self, element: pf.Element, *, format: str):
        element = super().hydrate(element, format=format)
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


class ConfigBody(pydantic.BaseModel):
    experience: dict[str, ConfigExperienceItem]
    education: dict[str, ConfigEducationItem]


class ConfigContactItem(floaty.ConfigFloatyItem):
    value: str

    def hydrate_iconify_tr(self, *args, **kwargs):
        extra = pf.TableCell(pf.Para(pf.Str(self.value)))
        return super().hydrate_iconify_tr(
            *args,
            cells_extra=[extra],
            **kwargs,
        )


# TODO: Skillbar to take up row on hover (and in overlay).
class ConfigSkillsItem(floaty.ConfigFloatyItem):
    since: date
    category: str


class ConfigHeadshot(pydantic.BaseModel):
    url: Annotated[str, pydantic.Field()]
    title: Annotated[str, pydantic.Field()]
    description: Annotated[str, pydantic.Field()]


class ConfigSidebar(pydantic.BaseModel):
    tex_width: Annotated[float, pydantic.Field(lt=1, gt=0, default=0.35)]
    headshot: Annotated[ConfigHeadshot, pydantic.Field()]
    contact: floaty.ConfigFloatySection[ConfigContactItem]
    skills: floaty.ConfigFloatySection[ConfigSkillsItem]
    links: floaty.ConfigFloatySection[floaty.ConfigFloatyItem]


class ConfigResume(pydantic.BaseModel):
    sidebar: ConfigSidebar
    body: ConfigBody


# --------------------------------------------------------------------------- #


class FilterResume(util.BaseFilter):
    filter_config_cls = ConfigResume
    filter_name = "resume"

    config: ConfigResume
    doc: pf.Doc
    identifier_to_hydrate: dict[str, Callable[[pf.Element], pf.Element]]

    def __init__(self, doc: pf.Doc):
        self.doc = doc
        self.config = ConfigResume.model_validate(doc.get_metadata("resume"))

        self.identifier_to_hydrate = {
            "resume-contact": self.hydrate_contact,
            "resume-skills": self.hydrate_skills,
            "resume-headshot": self.hydrate_headshot,
            "resume-experience": self.hydrate_experience,
            "resume-projects": self.hydrate_projects,
            "resume-education": self.hydrate_education,
            "resume-links": self.hydrate_links,
        }

    # def hydrate_contact_item(self, config: ConfigContactItem):
    #
    #     # iconify = "{{< iconify " + " ".join(config.icon.split(":")) + " >}}"
    #
    #     if self.doc.format == "html":
    #         return pf.TableRow(
    #             pf.TableCell(pf.Para(self.hydrate_icon(config.icon))),
    #             pf.TableCell(pf.Para(pf.Str(config.value))),
    #         )
    #
    #     return pf.TableRow(pf.TableCell(pf.Para(pf.Str(config.value))))
    # self.config.sidebar.contact.hydrate_html(element)
    # elif self.doc.format == "latex":
    #     contact_list = pf.Table(
    #         pf.TableBody(
    #             *(
    #                 self.hydrate_contact_item(contact_config)
    #                 for contact_config in self.config.sidebar.contact
    #             ),
    #         ),
    #     )

    def hydrate_contact(self, element: pf.Element):
        """Sidebar skills."""
        if self.doc.format == "html":
            contact = self.config.sidebar.contact.hydrate_html(
                pf.Div(
                    identifier="resume_contact_floaty",
                    classes=["floaty"],
                )
            )
        else:
            contact = pf.Para(pf.Str("Paceholder content"))
        #
        element.content = (
            pf.Header(pf.Str("Contact"), level=2),
            *element.content,
            contact,
        )

        return element

    def hydrate_skills(self, element: pf.Element):
        """Sidebar skills."""

        # NOTE: Adding both results in broken overlays.
        if self.doc.format == "html":
            skills = self.config.sidebar.skills.hydrate_html(
                pf.Div(
                    identifier="resume_skills_floaty",
                    classes=["floaty"],
                )
            )
        else:
            skills = pf.Para(pf.Str("Placeholder content."))

        element.content = (
            pf.Header(pf.Str("Skills"), level=2),
            *element.content,
            skills,
        )

        return element

    def hydrate_headshot(self, element: pf.Element):
        """Sidebar headshot."""

        config = self.config.sidebar.headshot
        if self.doc.format == "html":
            headshot = pf.Plain(
                pf.Image(
                    url=config.url,
                    title=config.title,
                    classes=["p-5"],
                )
            )

        else:
            headshot = pf.Para(pf.Str("Paceholder content"))

        element.content = (headshot, *element.content)
        return element

    def hydrate_links(self, element: pf.Element):
        """Sidebar links."""

        if self.doc.format == "html":
            links = self.config.sidebar.links.hydrate_html(
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

    def hydrate_projects(self, element: pf.Element):
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

    def hydrate_education(self, element: pf.Element):
        """Body education."""

        element.content = (
            pf.Header(pf.Str("Education"), level=2),
            *element.content,
        )
        return element

    def hydrate_experience(self, element: pf.Element):
        element.content = pf.ListContainer(
            pf.Header(pf.Str("Experience"), level=2), *element.content
        )
        return element

    def hydrate_icon(self, icon: str):
        """Make the icon span.

        NOTE: Not sure how insert shortcodes from icon configurations.
              For now this is good enough.
              See the [discussion on github]().
        """

        return pf.RawInline(
            f"<iconify-icon inline icon={icon}></iconify-icon>", format="html"
        )

    def unsupported_format(self):
        return pf.Header(f"Format `{self.doc.format}` Not Supported.")

    def layout(self, element: pf.Element):

        if self.doc.format == "html":
            # if element.identifier == "resume":
            #     element.classes.append("columns")
            #
            # elif element.identifier == "resume-sidebar":
            #     element.classes.append("column")
            #     element.attributes["width"] = "30%"
            #
            #     # element.parent.content.insert(element.index, pf.Div())
            #
            # elif element.identifier == "resume-body":
            #     element.classes.append("column")
            #     element.attributes["width"] = "65%"
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
                util.record(
                    list(
                        (type(item), getattr(item, "identifier", None))
                        for item in element.content
                    )
                )

        return element

    def __call__(self, element: pf.Element):
        if not isinstance(element, pf.Div):
            return element

        element = self.layout(element)

        if element.identifier in self.identifier_to_hydrate:
            return self.identifier_to_hydrate[element.identifier](element)

        if "experience" in element.classes:
            config = self.config.body.experience[element.attributes["experience_item"]]
            return config.hydrate(element, format=self.doc.format)

        if "education" in element.classes:
            config = self.config.body.education[element.attributes["education_item"]]
            return config.hydrate(element, format=self.doc.format)

        return element


filter = util.create_run_filter(FilterResume)
