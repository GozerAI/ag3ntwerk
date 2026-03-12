"""Smoke tests for basic imports."""


def test_import_app():
    from ag3ntwerk.api.app import app

    assert app.title
