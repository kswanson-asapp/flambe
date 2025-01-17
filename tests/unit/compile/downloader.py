from moto import mock_s3

import pytest
import boto3
import responses
import tempfile

from flambe.compile import downloader
from urllib.parse import urlparse

# This fixture will run for each test method automatically
@pytest.fixture(scope='function', autouse=True)
def s3_mock():
    mock = mock_s3()
    mock.start()

    yield

    mock.stop()


def test_s3_file():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')

    s3.put_object(Bucket='mybucket', Key="some_file.txt", Body="CONTENT")
    s3.put_object(Bucket='mybucket', Key="some_folder/some_file.txt", Body="CONTENT")

    assert downloader.s3_remote_file(urlparse("s3://mybucket/some_file.txt")) is True
    assert downloader.s3_remote_file(urlparse("s3://mybucket/some_folder")) is False


def test_s3_existing():
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='mybucket')

    s3.put_object(Bucket='mybucket', Key="some_file.txt", Body="CONTENT")

    assert downloader.s3_exists(urlparse("s3://mybucket/some_file.txt")) is True
    assert downloader.s3_exists(urlparse("s3://mybucket/some_other_file.txt")) is False
    assert downloader.s3_exists(urlparse("s3://other/some_file.txt")) is False
    assert downloader.s3_exists(urlparse("s3://some_file.txt")) is False


def test_local_file():
    path = __file__
    with downloader.download_manager(path) as p:
        assert path == p


def test_invalid_protocol():
    with pytest.raises(ValueError):
        with downloader.download_manager("sftp://something") as p:
            _ = p


def test_s3_inexistent_path():
    with pytest.raises(ValueError):
        with downloader.download_manager("s3://inexistent_bucket/file.txt") as p:
            _ = p


@responses.activate
def test_http_exists():
    url = 'https://some_host.com/resource.zip'
    responses.add(responses.HEAD, url, status=200)

    assert downloader.http_exists(url) is True
    assert downloader.http_exists("https://some_other_host.com/inexistent") is False


@responses.activate
def test_http_exists_2():
    url = 'https://some_host.com/resource.zip'
    responses.add(responses.HEAD, url, status=404)

    assert downloader.http_exists(url) is False


@responses.activate
def test_http_download():
    url = 'https://some_host.com/resource.txt'
    responses.add(responses.GET, url,
                  body='CONTENT')

    with tempfile.NamedTemporaryFile('wb') as f:
        downloader.download_http_file(url, f.name)
        assert open(f.name, 'rb').read() == b'CONTENT'
