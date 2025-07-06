def some_fn(data: str) -> int:
    """
    This function exists to test that watch mode (started by `@@tws`) works
    propertly. The intended functionality is that the test is rerun when
    this function is updated.
    """

    return 42 if data == "It works!" else 0


def foo():
    return "bar "
