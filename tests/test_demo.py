import demo


def test_cli_returns_nonzero_when_startup_fails(monkeypatch):
    def boom():
        raise RuntimeError("startup failed")

    monkeypatch.setattr(demo, "main", boom)

    assert demo.cli() == 1


def test_select_bind_host_uses_ipv6_when_available(monkeypatch):
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            self.bound = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def bind(self, addr):
            self.bound = addr

    monkeypatch.setattr(demo.socket, "socket", lambda *args, **kwargs: FakeSocket())

    assert demo.select_bind_host("0.0.0.0") == "::"


def test_select_bind_host_keeps_ipv4_when_ipv6_unavailable(monkeypatch):
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def bind(self, addr):
            raise OSError("ipv6 unavailable")

    monkeypatch.setattr(demo.socket, "socket", lambda *args, **kwargs: FakeSocket())

    assert demo.select_bind_host("0.0.0.0") == "0.0.0.0"
