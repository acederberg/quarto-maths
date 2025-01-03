"""Unit tests for floaty.

Integration tests will be performed on the outputs into ``components``.
"""

import pytest

from acederbergio.filters.floaty import (
    ConfigFloaty,
    ConfigFloatyContainer,
    ConfigFloatyItem,
    ConfigFloatyItemImage,
)

MinimalItem = ConfigFloatyItem[ConfigFloatyContainer]
MinimalFloaty = ConfigFloaty[MinimalItem, ConfigFloatyContainer]


class TestConfigFloatyItemImage:

    def test_default(self):
        """Should be able to be constructed without any additional parameters."""

        default = ConfigFloatyItemImage.model_validate({})
        assert default.iconify.set_ == "mdi"
        assert default.iconify.name == "bug"

        assert default.bootstrap.name == "bug"
        assert default.tex.font_awesome == "phone"


class TestConfigFloatyItem:

    item_args = {"key": "key", "title": "Item", "label": "item"}

    @pytest.fixture(scope="class")
    def item(self) -> MinimalItem:
        return ConfigFloatyItem.model_validate(self.item_args)

    def test_basic(self, item: MinimalItem):

        # NOTE: Minimum properties required.
        assert item.key == "key" and item.title == "Item" and item.label == "item"
        assert item.mode is None

    def test_container(self, item: MinimalItem):
        container = ConfigFloatyContainer.model_validate({})

        with pytest.raises(ValueError) as err:
            item.container

        assert "Container not set" in str(err)

        item.container_maybe = container
        assert item.container == container


class TestConfigFloatyBasic:

    @pytest.fixture(scope="class")
    def container(self):
        return ConfigFloatyContainer.model_validate({})

    def test_defaults(self, container: ConfigFloatyContainer):

        assert container.classes is None
        assert container.classes_rows is None
        assert container.classes_items is None
        assert container.classes_cards is None
        assert container.classes_card_bodys is None

        assert not container.include_titles
        assert not container.include_descriptions
        assert container.columns == 3
        assert container.mode == "iconify"


class TestConfigFloaty:

    def test_basic(self):
        content = [TestConfigFloatyItem.item_args]
        floaty = MinimalFloaty.model_validate({"content": content})
        assert floaty.overlay is None

        # NOTE: Check that container is populated.
        assert isinstance(floaty.content, dict)
        assert len(floaty.content) == 1 and "key" in floaty.content

        item = floaty.content["key"]
        assert item.container_maybe is not None
        assert item.container_maybe == floaty.container == item.container
