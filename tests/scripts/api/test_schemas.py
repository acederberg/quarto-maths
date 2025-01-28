import pydantic
import pytest

from acederbergio.api.schemas import QuartoRenderRequest, QuartoRenderRequestItem


class TestQuartoRenderRequest:

    def test_from_string(self):

        req = QuartoRenderRequest.model_validate(
            {"items": ["blog", "blog/resume/index.qmd"]}
        )
        assert len(req.items) == 2
        assert all(isinstance(item, QuartoRenderRequestItem) for item in req.items)

        item = req.items[0]
        assert item.path == "blog/index.qmd" and item.kind == "file"

        item = req.items[1]
        assert item.path == "blog/resume/index.qmd" and item.kind == "file"

    def test_directory(self):
        req = QuartoRenderRequest.model_validate(
            {"items": [{"path": "blog", "kind": "directory"}, "blog"]}
        )
        assert len(req.items) == 2
        assert all(isinstance(item, QuartoRenderRequestItem) for item in req.items)

        item = req.items[0]
        assert item.path == "blog" and item.kind == "directory"

        item = req.items[1]
        assert item.path == "blog/index.qmd" and item.kind == "file"

    def test_invalid_paths(self):
        with pytest.raises(pydantic.ValidationError) as err:
            QuartoRenderRequest.model_validate({"items": ["foo"]})

        assert "`foo` is not a file or does not exist" in str(err.value)
