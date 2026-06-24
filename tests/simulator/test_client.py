"""Unit tests for the API client (network mocked)."""

from unittest import mock

import pytest
import requests

from simulator.client import APIError, BlockchainAPIClient


def fake_response(status_code, body=None, text=""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.json.return_value = body or {}
    resp.text = text
    return resp


def test_register_device_posts_to_correct_url():
    session = mock.Mock()
    session.post.return_value = fake_response(201, {"device_id": "d1"})
    client = BlockchainAPIClient(base_url="http://api", session=session)

    result = client.register_device("d1", "PEM")

    assert result == {"device_id": "d1"}
    url, kwargs = session.post.call_args[0][0], session.post.call_args[1]
    assert url == "http://api/api/v1/devices/register"
    assert kwargs["json"] == {"device_id": "d1", "public_key": "PEM"}


def test_send_telemetry_posts_to_telemetry_endpoint():
    session = mock.Mock()
    session.post.return_value = fake_response(201, {"block_index": 1})
    client = BlockchainAPIClient(base_url="http://api", session=session)

    result = client.send_telemetry({"device_id": "d1"})

    assert result == {"block_index": 1}
    assert session.post.call_args[0][0] == "http://api/api/v1/telemetry"


def test_non_2xx_raises_api_error_with_status():
    session = mock.Mock()
    session.post.return_value = fake_response(401, text="invalid signature")
    client = BlockchainAPIClient(base_url="http://api", session=session)

    with pytest.raises(APIError) as exc:
        client.send_telemetry({})
    assert exc.value.status_code == 401


def test_network_failure_is_wrapped_in_api_error():
    session = mock.Mock()
    session.post.side_effect = requests.RequestException("connection refused")
    client = BlockchainAPIClient(base_url="http://api", session=session)

    with pytest.raises(APIError) as exc:
        client.register_device("d1", "PEM")
    assert exc.value.status_code is None
