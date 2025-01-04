import random

import panflute as pf
import pytest

from acederbergio.filters import floaty
from acederbergio.filters.links import Config, ConfigLinkItem, ConfigLinks

CONTAINER_DATA = dict()
ITEM_DATA = [
    {
        "key": f"key-{k}",
        "label": f"test-{k}",
        "title": f"Test `{k}`",
        "since": f"201{k}-01-02",
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
    return ConfigLinks.model_validate(dict(container=CONTAINER_DATA, content=ITEM_DATA))


class TestConfigLinkItem:

    def test_basic(self, item: ConfigLinkItem, container: floaty.ConfigFloatyContainer):
        item.container_maybe = container
        element = item.hydrate_tex()
        assert isinstance(element, pf.Link)

        item.href = None
        element = item.hydrate_tex()
        assert isinstance(element, pf.RawInline)


class TestConfigLink:

    def test_basic(self, config: ConfigLinks): ...


class TestConfig:

    def test_basic(self, config: ConfigLinks):

        Config(floaty_links=[config])  # type: ignore
