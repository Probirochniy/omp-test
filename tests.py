import pytest
from unittest.mock import MagicMock, patch


def test_parse_args_valid():
    from main import parse_args

    with patch("sys.argv", ["main.py", "--credentials", "user:pass", "serial", "url"]):
        assert parse_args() == ("user", "pass", "serial", "url")


def test_parse_args_valid_no_creds():
    from main import parse_args

    with patch("sys.argv", ["main.py", "serial", "url"]):
        assert parse_args() == ("", "", "serial", "url")


def test_parse_args_invalid():
    from main import parse_args

    with patch("sys.argv", ["main.py", "--credentials", "user", "serial", "url"]):
        with pytest.raises(SystemExit):
            parse_args()


def test_get_filename():
    from main import get_filename

    assert get_filename('attachment; filename="file.zip"') == "file.zip"
    assert get_filename('attachment; filename="file.zip";') == "file.zip"
    assert get_filename('attachment; filename="file.zip"; other') == "file.zip"


def test_get_response():
    from main import get_response

    response = MagicMock()
    response.headers = {"Content-Disposition": 'attachment; filename="file.zip"'}
    response.status_code = 200
    response.raise_for_status = MagicMock()
    with patch("requests.get", return_value=response):
        assert get_response("url", "user", "pass") == response
