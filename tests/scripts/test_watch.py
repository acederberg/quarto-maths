import pathlib

from scripts import watch


def test_ignore_node():
    node = watch.IgnoreNode(False)

    assert not node.is_ignored(p := "/home/docker/.venv")

    node.add(p)
    assert node.is_ignored(p)
    assert node.is_ignored(q := p + "/bin")
    assert not node.is_ignored("/home/docker")
    assert not node.is_ignored("/home")

    node.add(q)
    assert node.is_ignored(q)
    assert node.is_ignored(q + "/python")
    assert not node.is_ignored("/home/docker")
    assert not node.is_ignored("/home")
