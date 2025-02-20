import random
from typing import Any

import panflute as pf
import pytest

from acederbergio.filters import floaty
from acederbergio.filters.links import (
    Config,
    ConfigLinkItem,
    ConfigLinks,
    ConfigLinksContainer,
)

CONTAINER_DATA: Any = dict()
ITEM_DATA = [
    {
        "key": f"key-{k}",
        "label": f"test-{k}",
        "title": f"Test `{k}`",
        "href": "https://acederberg.io",
    }
    for k in range(10)
]


@pytest.fixture
def item() -> ConfigLinkItem:
    return ConfigLinkItem.model_validate(random.choice(ITEM_DATA))


@pytest.fixture
def container() -> floaty.ConfigFloatyContainer:
    return floaty.ConfigFloatyContainer.model_validate(CONTAINER_DATA)


@pytest.fixture
def config() -> ConfigLinks:
    return ConfigLinks.model_validate(
        dict(container=CONTAINER_DATA, content=ITEM_DATA, identifier="1234abcd")
    )


class TestConfigLinkItem:

    def test_basic(self, item: ConfigLinkItem, container: ConfigLinksContainer):
        item.container_maybe = container
        element = item.hydrate_tex()
        assert isinstance(element, pf.Link)

        item.href = None
        element = item.hydrate_tex()
        assert isinstance(element, pf.RawInline)


# class TestConfigLink:
#
#     def test_basic(self, config: ConfigLinks): ...


class TestConfig:

    def test_basic(self, config: ConfigLinks):

        Config.model_validate(dict(links=[config]))
