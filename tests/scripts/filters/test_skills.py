import datetime
from typing import Any

import pytest

from acederbergio.filters.skills import (
    TODAY,
    ConfigSkills,
    ConfigSkillsContainer,
    ConfigSkillsItem,
)

# TODAY = datetime.date.fromisoformat("2024-01-01")
CONTAINER_DATA: Any = dict()
ITEM_DATA = [
    {
        "key": f"key-{k}",
        "label": f"test-{k}",
        "title": f"Test `{k}`",
        "since": f"201{k}-01-02",
    }
    for k in range(10)
]
CONFIG_DATA = {
    "container": CONTAINER_DATA,
    "content": ITEM_DATA,
    "identifier": "pytest-skills-floaty",
}


@pytest.fixture
def item() -> ConfigSkillsItem:
    return ConfigSkillsItem.model_validate(ITEM_DATA[0])


@pytest.fixture
def container() -> ConfigSkillsContainer:
    return ConfigSkillsContainer.model_validate(CONTAINER_DATA)


@pytest.fixture
def config() -> ConfigSkills:
    return ConfigSkills.model_validate(CONFIG_DATA)


class TestConfigSkillsContainer: ...


class TestConfigSkillsItem:

    def test_basic(self, item: ConfigSkillsItem, container: ConfigSkillsContainer):

        # NOTE: These should all work.
        assert item.duration == TODAY - item.since
        assert (
            item.key == "key-0" and item.label == "test-0" and item.title == "Test `0`"
        )
        assert item.since.month == 1 and item.since.day == 2 and item.since.year == 2010

        # NOTE: Should raise an error when ``container_maybe`` is not yet set.
        assert item.container_maybe is None
        assert item.duration_total_maybe is None

        with pytest.raises(ValueError) as err:
            item.container

        assert "Container not set." in str(err.value)

        with pytest.raises(ValueError) as _:
            item.duration_total

        # NOTE: Setting the container and container maybe should make props accessable
        item.container_maybe = container
        item.duration_total_maybe = datetime.timedelta(days=365)

        assert item.duration_total == item.duration_total_maybe
        assert item.container == item.container_maybe


class TestConfigSkills:

    def test_basic(self, config: ConfigSkills):
        assert type(config.container) is ConfigSkillsContainer
        assert all(
            isinstance(item, ConfigSkillsItem)
            and item.container_maybe is not None
            and item.duration_total is not None
            for item in config.content.values()
        )

    def test_duration_total(self, config: ConfigSkills):

        # NOTE: Total duration should be the same accross all items.
        items = config.content.values()
        duration_total = config.duration
        assert all(item.duration_total == duration_total for item in items)

        # NOTE: No two items should be the same.
        durations = sorted(map(lambda item: item.duration, items))
        assert all(a < b for a, b in zip(durations, durations[1:]))

        # NOTE: Only one item should match.
        _sum = (item.duration >= item.duration_total for item in items)
        assert sum(_sum) == 1, "Only one item should match or exceed."
