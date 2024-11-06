from scripts import env, watch


def test_ignore_node():
    node = watch.Node(False)

    assert not node.has_prefix(p := "/home/docker/.venv")

    node.add(p)
    assert node.has_prefix(p)
    assert node.has_prefix(q := p + "/bin")
    assert not node.has_prefix("/home/docker")
    assert not node.has_prefix("/home")

    node.add(q)
    assert node.has_prefix(q)
    assert node.has_prefix(q + "/httpx")  # Cannot be link!
    assert not node.has_prefix("/home/docker")

    assert not node.has_prefix("/home")


def test_context():

    context = watch.Context()
    assert context.is_ignored_path(env.BUILD / "index.html")
    assert not context.is_ignored_path(env.BLOG / "filters")
    assert not context.is_ignored_path(env.BLOG / "filters/floaty.py")
    assert not context.is_ignored_path(env.SCRIPTS / "filters")
    assert not context.is_ignored_path(env.BLOG / "includes")
    assert not context.is_ignored_path(env.BLOG / "themes")
    assert context.is_ignored_path(env.BLOG / ".quarto")
    assert context.is_ignored_path(env.BLOG / "_freeze")
    assert context.is_ignored_path(env.BUILD / "site_libs")
    assert context.is_ignored_path(env.ROOT / ".git")
