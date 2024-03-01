import pytest
import tarfile
import zipfile
from unittest.mock import MagicMock, patch
import pyzstd


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


def test_extract_archive_zip():
    from main import extract_archive

    with patch("zipfile.ZipFile") as mock_zip:
        extract_archive("file.zip", "destination")
        mock_zip.assert_called_with("file.zip", "r")

        mock_zip_ref = mock_zip.return_value.__enter__.return_value

        mock_zip_ref.extractall.assert_called_with("destination")


def test_extract_archive_tar_bz2():
    from main import extract_archive

    with patch("tarfile.open") as mock_tar:
        extract_archive("file.tar.bz2", "destination")
        mock_tar.assert_called_with("file.tar.bz2", "r:bz2")

        mock_tar_ref = mock_tar.return_value.__enter__.return_value

        mock_tar_ref.extractall.assert_called_with("destination")


def test_extract_archive_tar_zst():
    from main import extract_archive

    with patch("tarfile.open") as mock_tar:
        with patch("builtins.open"):
            with patch("pyzstd.decompress") as mock_decompress:
                extract_archive("file.tar.zst", "destination")
                mock_tar.assert_called_with("/temp.tar", "r")

                mock_tar_ref = mock_tar.return_value.__enter__.return_value

                mock_tar_ref.extractall.assert_called_with("destination")

                mock_decompress.assert_called()
