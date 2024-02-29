import requests
import sys
import os
from requests.auth import HTTPBasicAuth
import logging
import tarfile
import zipfile
import pyzstd
import subprocess
import argparse

logging.basicConfig(level=logging.DEBUG)

WORKING_DIR = "/tmp/script-temp-dir"
SCRIPT_NAME = "flash.sh"


# Called at the beginning of the script to initialize the prerequisites
def initialize() -> None:
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)


# Called at the end of the script to clean up the resources
def deinitialize() -> None:
    if os.path.exists(WORKING_DIR):
        os.rmdir(WORKING_DIR)


def exit_with_error(message: str) -> None:
    logging.error(message)
    deinitialize()
    sys.exit(1)


# Parses the command line arguments and returns the values
def parse_args() -> tuple[str, str, str, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", help="Username and password", default="")
    parser.add_argument("serial", help="Serial number of the device")
    parser.add_argument("url", help="URL of the file to download")
    args = parser.parse_args()

    if ":" not in args.credentials and args.credentials != "":
        exit_with_error(
            "Invalid credentials format. Use the following format: username:password"
        )

    if args.credentials:
        username, password = args.credentials.split(":")
    else:
        username, password = "", ""

    return username, password, args.serial, args.url


# Extracts the filename and extension from the Content-Disposition header
def get_filename(content_disposition: str) -> str:
    start = content_disposition.find("filename=") + len("filename=")
    end = content_disposition.find(";", start)

    filename = content_disposition[start:end]

    return filename


# Sends a GET request to the given URL and returns the response
def get_response(url: str, username: str, password: str) -> requests.Response:
    auth = HTTPBasicAuth(username, password) if username and password else None
    response = requests.get(url, auth=auth)

    # Check if the request was successful
    if response.status_code != 200:
        exit_with_error(f"Failed to get the file. Status code: {response.status_code}")

    return response


# Downloads the file from the response to the working directory
def download_file(response: requests.Response, filename: str) -> None:
    if os.path.exists(os.path.join(WORKING_DIR, filename)):
        os.remove(os.path.join(WORKING_DIR, filename))

    with open(os.path.join(WORKING_DIR, filename), "wb") as file:
        file.write(response.content)

    logging.debug(f"File {filename} has been downloaded")


# Extracts the zip archive to the destination path
def extractor_zip(archive_path: str, destination_path: str) -> None:
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(destination_path)


# Extracts the tar.bz2 archive to the destination path
def extractor_tar_bz2(archive_path: str, destination_path: str) -> None:
    with tarfile.open(archive_path, "r:bz2") as tar:
        tar.extractall(destination_path)


# Extracts the tar.zst archive to the destination path
def extractor_tar_zst(archive_path: str, destination_path: str) -> None:
    with open(archive_path, "rb") as file:
        decompressed_data = pyzstd.decompress(file.read())

    temp_archive_path = os.path.dirname(archive_path) + "/temp.tar"

    with open(temp_archive_path, "wb") as file:
        file.write(decompressed_data)

    with tarfile.open(temp_archive_path, "r") as tar:
        tar.extractall(destination_path)


# Mappping of file extensions to the appropriate extractor
EXTRACTORS = {
    ".zip": extractor_zip,
    ".tar.bz2": extractor_tar_bz2,
    ".tar.zst": extractor_tar_zst,
}


# Extracts the archive to the destination path using the appropriate extractor
def extract_archive(archive_path: str, destination_path: str, extension: str) -> None:
    if extension not in EXTRACTORS:
        exit_with_error(f"Unsupported extension: {extension}")

    EXTRACTORS[extension](archive_path, destination_path)


# Runs the flash.sh script to flash the device
def run_flash_script(script_path: str, serial: str) -> None:
    subprocess.run(["chmod", "+x", script_path])

    logging.debug("Flashing the device")
    subprocess.run([script_path, "--extra-opts", "-s", serial])
    logging.debug("Device has been flashed")

    logging.debug("Rebooting the device")
    subprocess.run(["fastboot", "reboot"])
    logging.debug("Device has been rebooted")


def main() -> None:
    # Parse the command line arguments
    username, password, serial, url = parse_args()

    response = get_response(url, username, password)

    filename = get_filename(response.headers["Content-Disposition"])
    extension = os.path.splitext(filename)[1]

    download_file(response, filename)

    extract_archive(
        os.path.join(WORKING_DIR, filename),
        WORKING_DIR,
        extension,
    )

    script_path = os.path.join(WORKING_DIR, SCRIPT_NAME)

    if not os.path.exists(script_path):
        exit_with_error("flash.sh script not found")

    run_flash_script(script_path, serial)


if __name__ == "__main__":
    # Set the prerequisites
    initialize()

    # Run the main function
    main()

    # Clean up the resources
    deinitialize()
