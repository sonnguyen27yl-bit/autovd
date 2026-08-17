from autovd.diagnostic import diagnostic_status


def test_diagnostic_status_is_stable() -> None:
    assert diagnostic_status() == {
        "service": "autovd",
        "status": "ok",
        "version": "0.1.0-dev",
    }
