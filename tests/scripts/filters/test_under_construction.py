import yaml

from acederbergio.filters.under_construction import Config, ConfigUnderConstruction

raw = yaml.safe_load(
    """
under_construction:
  # start snippet 5
  - identifier: uses-bootstrap
    container:
      size: 1
      mode: bootstrap
      classes:
        - floaty-shadow-1
    content:
      key: uses-bs
      title: This Floaty uses a Bootstrap Icon
      image:
        bootstrap:
          # NOTE: Applies classes specificaly to the bootstrap icon.
          classes:
            - bg-yellow
            - border
            - border-black
            - border-5
            - rounded-4
            - p-5
      classes:
        - p-3
        # end snippet 5
  # start snippet 6
  - identifier: custom
    container:
      size: 1
      mode: bootstrap
      classes:
        - floaty-shadow-1
    content:
      key: a-bug
      title: A Bug
      description: Look! *There is a bug.*
      image:
        bootstrap:
          name: bug-fill
          classes:
            - bg-black
            - border
            - border-red
            - border-5
            - rounded-5
            - p-5
      classes:
        - p-3
        - text-red
        # end snippet 6
"""
)


def test_config():
    ConfigUnderConstruction.model_validate({"content": {}, "identifier": "spamspam"})
    Config.model_validate(raw)
