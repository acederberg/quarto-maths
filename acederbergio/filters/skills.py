from datetime import date, timedelta
from typing import Annotated

import panflute as pf
import pydantic

from acederbergio import env
from acederbergio.filters import floaty, util

logger = env.create_logger(__name__)
TODAY = date.today()


# DEFAULT_CLASSES_PROGRESS = []
# DEFAULT_CLASSES = [] #["bg-primary", "progress-bar-animated", "progress-bar-striped"]
FieldClassesProgress = Annotated[list[str] | None, pydantic.Field(None)]
FieldClassesProgressBar = Annotated[list[str] | None, pydantic.Field(None)]


class HasProgressClasses(util.BaseConfig):
    classes_progress: FieldClassesProgress
    classes_progress_bar: FieldClassesProgressBar


# TODO: Skillbar to take up row on hover (and in overlay).
class ConfigSkillsItem(
    HasProgressClasses, floaty.ConfigFloatyItem["ConfigSkillsContainer"]
):
    since: Annotated[date, pydantic.Field]
    duration_total_maybe: Annotated[timedelta | None, pydantic.Field(None)]

    @property
    def duration_total(self) -> timedelta:
        if self.duration_total_maybe is None:
            raise ValueError

        return self.duration_total_maybe

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def duration(self) -> timedelta:
        diff = TODAY - self.since
        return diff

    def hydrate_progress_bar(self):
        percent = (100 * self.duration.days) // self.duration_total.days

        _n_years = self.duration.days // 365
        _n_months = (self.duration.days % 365) // 31

        content_str = []
        if _n_years:
            content_str.append(f"{_n_years} Years")
        if _n_months:
            content_str.append(f"{_n_months} Months")

        classes_progress_bar = util.update_classes(
            ["progress-bar"],
            self.container.classes_progress_bar,
            self.classes_progress_bar,
        )
        classes_progress = util.update_classes(
            ["progress"],
            self.container.classes_progress,
            self.classes_progress,
        )

        return pf.Div(
            pf.Div(
                pf.RawBlock(", ".join(content_str)),
                classes=classes_progress_bar,
                attributes={"style": f"width: {percent}%;"},
            ),
            attributes={
                "aria-valuenow": str(self.duration.days),
                "aria-valuemin": "0",
                "aria-valuemax": str(self.duration_total.days),
                "role": "progressbar",
            },
            classes=classes_progress,
        )

    def hydrate_footer(self):
        if not self.container.include_progress:
            return None

        pb = self.hydrate_progress_bar()
        return pf.Div(pb, classes=[self.class_name("footer")])

    # def hydrate_overlay_content_item(  # type: ignore
    #     self,
    #     element: pf.Element,
    #     *,
    #     _parent: "ConfigProgress",
    # ):
    #
    #     el = super().hydrate_overlay_content_item(element,container=_container)
    #     el.content.insert(2, self.hydrate_progress_bar(_parent))
    #     el.content.insert(
    #         3,
    #         pf.Plain(
    #             pf.Strong(pf.Str("Since "), pf.Str(self.since.strftime("%B, %Y"))),
    #         ),
    #     )
    #
    #     wrapper = pf.Div(*el.content, classes=["skills-page", "p-5"])
    #     el.content = (wrapper,)
    #
    #     return el


class ConfigSkillsContainer(HasProgressClasses, floaty.ConfigFloatyContainer):

    include_progress: Annotated[bool, pydantic.Field(True)]

    @property
    def classes_always(self) -> list[str]:
        out = super().classes_always
        out.append("skills")
        return out


class ConfigSkills(floaty.ConfigFloaty[ConfigSkillsItem, ConfigSkillsContainer]):

    @pydantic.computed_field  # type: ignore[prop-decorator]
    @property
    def duration(
        self,
    ) -> timedelta:
        """In display, each section has its progress relative to the maximum
        in its own section."""

        vv = max(self.content.values(), key=lambda item: item.duration)  # type: ignore
        return vv.duration

    def _set_container(self, item: ConfigSkillsItem):
        item.container_maybe = self.container  # type: ignore
        item.duration_total_maybe = self.duration


class Config(floaty.BaseFloatyConfig):
    filter_name = "skills"
    skills: Annotated[
        dict[str, ConfigSkills] | None,
        pydantic.Field(None),
        pydantic.BeforeValidator(util.content_from_list_identifier),
    ]


class FilterSkills(util.BaseFilterHasConfig[Config]):

    filter_name = "skills"
    filter_config_cls = Config

    def __call__(self, element: pf.Element):

        if self.doc.format != "html":
            return element

        if (
            not isinstance(element, pf.Div)
            or self.config is None
            or (config := self.config.skills) is None
        ):
            return element

        if self.doc.format != "html":
            return element

        if (config_skills := config.get(element.identifier)) is not None:
            element = config_skills.hydrate_html(element)

        return self.config.hydrate_overlay(element)


filter = util.create_run_filter(FilterSkills)
