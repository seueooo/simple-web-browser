import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from browser import parse_url

def test_http_defaults():
    scheme, host, port, path = parse_url("http://example.com")
    assert scheme == "http"
    assert host == "example.com"
    assert port == 80
    assert path == "/"

def test_https_defaults():
    scheme, host, port, path = parse_url("https://example.com")
    assert scheme == "https"
    assert port == 443

def test_explicit_port():
    scheme, host, port, path = parse_url("http://example.com:8080/foo")
    assert port == 8080
    assert host == "example.com"
    assert path == "/foo"

def test_path_and_query():
    _, _, _, path = parse_url("https://example.com/search?q=hello")
    assert path == "/search?q=hello"

def test_fragment_stripped():
    _, host, _, path = parse_url("https://example.com/page#section")
    assert path == "/page"
    assert "#" not in host

def test_no_path_defaults_to_slash():
    _, _, _, path = parse_url("https://example.com")
    assert path == "/"

from unittest.mock import patch, MagicMock

def _make_mock_sock(response_bytes):
    """Return a MagicMock socket that yields response_bytes then EOF."""
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [response_bytes, b""]
    return mock_sock

def test_request_returns_tuple():
    """request() should return (status_line, headers_dict, body_bytes)."""
    mock_response = (
        b"HTTP/1.0 200 OK\r\n"
        b"Content-Type: text/html; charset=UTF-8\r\n"
        b"\r\n"
        b"<html><body>Hello</body></html>"
    )
    mock_sock = _make_mock_sock(mock_response)

    with patch("socket.socket", return_value=mock_sock):
        from browser import request
        status, headers, body = request("http://example.com")

    assert status == "HTTP/1.0 200 OK"
    assert headers["content-type"] == "text/html; charset=UTF-8"
    assert body == b"<html><body>Hello</body></html>"

def test_headers_are_lowercased():
    mock_response = b"HTTP/1.0 200 OK\r\nX-Custom-Header: Value\r\n\r\nbody"
    mock_sock = _make_mock_sock(mock_response)

    with patch("socket.socket", return_value=mock_sock):
        from browser import request
        _, headers, _ = request("http://example.com")

    assert "x-custom-header" in headers

def test_redirect_followed():
    """301 response should cause request() to fetch the Location URL."""
    redirect_response = (
        b"HTTP/1.0 301 Moved Permanently\r\n"
        b"Location: http://example.com/new\r\n"
        b"\r\n"
    )
    final_response = (
        b"HTTP/1.0 200 OK\r\n"
        b"Content-Type: text/html\r\n"
        b"\r\n"
        b"<p>Final</p>"
    )
    sock1 = _make_mock_sock(redirect_response)
    sock2 = _make_mock_sock(final_response)

    with patch("socket.socket", side_effect=[sock1, sock2]):
        from browser import request
        status, _, body = request("http://example.com/old")

    assert status == "HTTP/1.0 200 OK"
    assert body == b"<p>Final</p>"

def test_redirect_limit_raises():
    """max_redirect=0 with a 3xx response should raise RuntimeError immediately."""
    redirect_response = (
        b"HTTP/1.0 301 Moved Permanently\r\n"
        b"Location: http://example.com/new\r\n"
        b"\r\n"
    )
    import pytest
    mock_sock = _make_mock_sock(redirect_response)
    with patch("socket.socket", return_value=mock_sock):
        from browser import request
        with pytest.raises(RuntimeError, match="Too many redirects"):
            request("http://example.com/old", max_redirect=0)
