from typing import Annotated

import panflute as pf
import pydantic

from scripts.filters import floaty, util


class ConfigExperience(pydantic.BaseModel):
    title: str
    organization: str
    start: str
    stop: str
    content: Annotated[list[str] | None, pydantic.Field(default=None)]


class ConfigBody(pydantic.BaseModel):
    experience: dict[str, ConfigExperience]


class ConfigContactItem(floaty.ConfigFloatyItem):
    value: str


# NOTE: This should look like ``ConfigFloatySection``.
# class ConfigContact(floaty.ConfigFloatySection[ConfigContactItem]):
#     size: int
#     content: list[ConfigContactItem]


class ConfigSidebar(pydantic.BaseModel):
    width: Annotated[float, pydantic.Field(lt=1, gt=0, default=0.35)]
    contact: floaty.ConfigFloatySection[ConfigContactItem]
    skills: list[str]


class ConfigSkills(pydantic.BaseModel):
    display_name: str
    display_description: Annotated[str | None, pydantic.Field(default=None)]
    experience: str
    # icon: Any
    category: str


class ConfigResume(pydantic.BaseModel):
    skills: dict[str, ConfigSkills]
    sidebar: ConfigSidebar
    body: ConfigBody


# --------------------------------------------------------------------------- #


class FilterResume(util.BaseFilter):
    filter_config_cls = ConfigResume
    filter_name = "resume"

    config: ConfigResume
    doc: pf.Doc

    def __init__(self, doc: pf.Doc):
        self.doc = doc
        self.config = ConfigResume.model_validate(doc.get_metadata("resume"))

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
        if self.doc.format == "html":
            contact = self.config.sidebar.contact.hydrate_html(
                pf.Div(
                    identifier="contact",
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

    def hydrate_education(self, element: pf.Element):
        element.content = (
            pf.Header(pf.Str("Education"), level=2),
            *element.content,
        )
        return element

    def hydrate_projects(self, element: pf.Element):
        element.content = (
            pf.Header(pf.Str("Projects"), level=2),
            *element.content,
        )
        return element

    def hydrate_skills(self, element: pf.Element):
        element.content = pf.ListContainer(
            pf.Header(pf.Str("Skills"), level=2), *element.content
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

    def hydrate_experience_item(self, element: pf.Element):
        experience_field = element.attributes["experience_item"]
        config_experience = self.config.body.experience[experience_field]

        title = pf.Str(config_experience.title)
        organization = pf.Str(config_experience.organization)
        start_stop = (
            pf.Str(config_experience.start),
            pf.Space(),
            pf.Str("-"),
            pf.Space(),
            pf.Str(config_experience.stop),
        )

        if self.doc.format == "latex":
            header_textbar = (
                pf.Space(),
                pf.RawInline("\\textbar{}", format="latex"),
                pf.Space(),
            )
            element.content.insert(
                0,
                pf.Header(
                    title,
                    *header_textbar,
                    organization,
                    pf.Space(),
                    pf.RawInline("\\hfill", format="latex"),
                    pf.Space(),
                    *start_stop,
                    level=3,
                ),
            )

        elif self.doc.format == "html":
            element.content.insert(0, pf.Para(pf.Emph(*start_stop)))
            element.content.insert(0, pf.Para(pf.Strong(organization)))
            element.content.insert(
                0,
                pf.Header(
                    title,
                    # pf.Space(),
                    # pf.RawInline("|", format="html"),
                    # pf.Space(),
                    level=3,
                ),
            )
        else:
            element.content.append(self.unsupported_format())

        if config_experience.content is not None:
            blah = (
                pf.ListItem(pf.Para(pf.Str(item))) for item in config_experience.content
            )
            element.content = (
                *element.content,
                pf.BulletList(*blah),
            )

        return element

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

            size = self.config.sidebar.width
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

        if element.identifier == "contact":
            return self.hydrate_contact(element)

        elif element.identifier == "skills":
            return self.hydrate_skills(element)

        elif element.identifier == "experience":
            return self.hydrate_experience(element)

        elif element.identifier == "projects":
            return self.hydrate_projects(element)

        elif element.identifier == "education":
            return self.hydrate_education(element)

        elif "experience" in element.classes:
            return self.hydrate_experience_item(element)

        return element


filter = util.create_run_filter(FilterResume)
