import yaml

from acederbergio.filters.iframe import Config


def test_config():

    Config.model_validate(
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
