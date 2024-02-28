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
def initialize():
    if not os.path.exists(WORKING_DIR):
        os.mkdir(WORKING_DIR)


# Called at the end of the script to clean up the resources
def deinitialize():
    if os.path.exists(WORKING_DIR):
        os.rmdir(WORKING_DIR)


def exit_with_error(message):
    logging.error(message)
    deinitialize()
    sys.exit(1)


# Parses the command line arguments and returns the values
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", help="Username and password", default="")
    parser.add_argument("serial", help="Serial number of the device")
    parser.add_argument("url", help="URL of the file to download")
    args = parser.parse_args()

    if args.credentials:
        username, password = args.credentials.split(":")
    else:
        username, password = "", ""

    if ":" not in args.credentials and args.credentials != "":
        exit_with_error("Invalid credentials format. Use the following format: username:password")

    return username, password, args.serial, args.url


# Extracts the filename and extension from the Content-Disposition header
def get_filename(content_disposition):
    start = content_disposition.find("filename=") + len("filename=")
    end = content_disposition.find(";", start)

    filename = content_disposition[start:end]

    return filename


def get_response(url, username, password):
    authorization_needed = username != "" and password != ""

    logging.debug(f"Sending request to {url}")
    if authorization_needed:
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
    else:
        response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        exit_with_error(f"Failed to get the file. Status code: {response.status_code}")

    return response


def download_file(response, filename, extension, serial):
    if os.path.exists(os.path.join(WORKING_DIR, filename)):
        os.remove(os.path.join(WORKING_DIR, filename))

    with open(os.path.join(WORKING_DIR, filename), "wb") as file:
        file.write(response.content)

    logging.debug(f"File {filename} has been downloaded")


def extractor_zip(archive_path, destination_path):
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(destination_path)


def extractor_tar_bz2(archive_path, destination_path):
    with tarfile.open(archive_path, "r:bz2") as tar:
        tar.extractall(destination_path)


def extractor_tar_zst(archive_path, destination_path):
    with open(archive_path, "rb") as file:
        decompressed_data = pyzstd.decompress(file.read())

    temp_archive_path = os.path.dirname(archive_path) + "/temp.tar"

    with open(temp_archive_path, "wb") as file:
        file.write(decompressed_data)

    with tarfile.open(temp_archive_path, "r") as tar:
        tar.extractall(destination_path)


EXTRACTORS = {
    ".zip": extractor_zip,
    ".tar.bz2": extractor_tar_bz2,
    ".tar.zst": extractor_tar_zst,
}


# Extracts the archive to the destination path
def extract_archive(archive_path, destination_path, extension):
    if extension not in EXTRACTORS:
        exit_with_error(f"Unsupported extension: {extension}")

    EXTRACTORS[extension](archive_path, destination_path)


def run_flash_script(script_path, serial):
    subprocess.run(["chmod", "+x", script_path])

    logging.debug("Flashing the device")
    subprocess.run([script_path, "--extra-opts", "-s", serial])
    logging.debug("Device has been flashed")

    logging.debug("Rebooting the device")
    subprocess.run(["fastboot", "reboot"])
    logging.debug("Device has been rebooted")


def main():
    # Parse the command line arguments
    username, password, serial, url = parse_args()

    response = get_response(url, username, password)

    filename = get_filename(response.headers["Content-Disposition"])
    extension = os.path.splitext(filename)[1]

    download_file(response, filename, extension, serial)

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
