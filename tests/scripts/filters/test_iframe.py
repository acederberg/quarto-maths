import panflute as pf
import yaml
from kagglehub.gcs_upload import pathlib

from acederbergio.filters.iframe import Config, FilterIFrame


def test_config():

    config = Config.model_validate(
        yaml.safe_load(
            """
        iframes:
          - identifier: contacts-pdf-iframe
            target: blog/components/floaty/resume-contacts.qmd
            kind: pdf
            # height: 256
          - identifier: links-pdf-iframe
            target: blog/components/floaty/resume-links.qmd
            kind: pdf
            # height: 256
        """
        )
    )


HERE = pathlib.Path(__file__).resolve().parent


def test_filter():

    # with open(HERE / "iframe-example.qmd", "r") as file:
    #     doc = pf.convert_text(file.read())

    filter = FilterIFrame(doc=doc)
    pf.run_filter(filter.action, doc=doc)
