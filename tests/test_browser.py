import sys
import os
import io
import gzip as gzip_module
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_browser_state():
    """Reset module-level socket pool and cache before/after every test."""
    import browser as br
    br._socket_pool.clear()
    br._cache.clear()
    yield
    br._socket_pool.clear()
    br._cache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_sock(response_bytes):
    """Return a MagicMock socket that yields response_bytes then EOF."""
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [response_bytes, b""]
    return mock_sock


def _capture_show(body_bytes, headers):
    from browser import show
    f = io.StringIO()
    with redirect_stdout(f):
        show(body_bytes, headers)
    return f.getvalue()


# ---------------------------------------------------------------------------
# parse_url
# ---------------------------------------------------------------------------

def test_http_defaults():
    from browser import parse_url
    scheme, host, port, path = parse_url("http://example.com")
    assert scheme == "http"
    assert host == "example.com"
    assert port == 80
    assert path == "/"


def test_https_defaults():
    from browser import parse_url
    scheme, host, port, path = parse_url("https://example.com")
    assert scheme == "https"
    assert port == 443


def test_explicit_port():
    from browser import parse_url
    scheme, host, port, path = parse_url("http://example.com:8080/foo")
    assert port == 8080
    assert host == "example.com"
    assert path == "/foo"


def test_path_and_query():
    from browser import parse_url
    _, _, _, path = parse_url("https://example.com/search?q=hello")
    assert path == "/search?q=hello"


def test_fragment_stripped():
    from browser import parse_url
    _, host, _, path = parse_url("https://example.com/page#section")
    assert path == "/page"
    assert "#" not in host


def test_no_path_defaults_to_slash():
    from browser import parse_url
    _, _, _, path = parse_url("https://example.com")
    assert path == "/"


def test_parse_url_file_scheme():
    from browser import parse_url
    scheme, host, port, path = parse_url("file:///tmp/test.html")
    assert scheme == "file"
    assert path == "/tmp/test.html"


# ---------------------------------------------------------------------------
# request() — HTTP/1.1 headers (1-1)
# ---------------------------------------------------------------------------

def test_request_sends_http11():
    """request() must use HTTP/1.1 and send Host, Connection, User-Agent, Accept-Encoding."""
    sent = []
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nHello",
        b""
    ]
    mock_sock.sendall.side_effect = lambda data: sent.append(data.decode())

    with patch("socket.socket", return_value=mock_sock):
        from browser import request
        request("http://example.com/")

    req_text = "".join(sent)
    assert "HTTP/1.1" in req_text
    assert "Host: example.com" in req_text
    assert "Connection: keep-alive" in req_text
    assert "User-Agent:" in req_text
    assert "Accept-Encoding: gzip" in req_text


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


# ---------------------------------------------------------------------------
# request() — file:// scheme (1-2)
# ---------------------------------------------------------------------------

def test_request_file_scheme(tmp_path):
    """file:// URL should read a local file."""
    f = tmp_path / "hello.html"
    f.write_bytes(b"<p>Hello file</p>")
    from browser import request
    status, headers, body = request(f"file://{f}")
    assert status == "200 OK"
    assert body == b"<p>Hello file</p>"


# ---------------------------------------------------------------------------
# request() — data: scheme (1-3)
# ---------------------------------------------------------------------------

def test_request_data_scheme_text():
    from browser import request
    status, headers, body = request("data:text/html,Hello world!")
    assert status == "200 OK"
    assert headers["content-type"] == "text/html"
    assert body == b"Hello world!"


def test_request_data_scheme_default_type():
    from browser import request
    status, headers, body = request("data:,plain text")
    assert status == "200 OK"
    assert b"plain text" in body


# ---------------------------------------------------------------------------
# show() — HTML entities (1-4)
# ---------------------------------------------------------------------------

def test_show_html_entities():
    """&lt; &gt; &amp; entities must be converted to their characters."""
    html = b"<p>&lt;div&gt; &amp; &quot;hello&quot;</p>"
    out = _capture_show(html, {"content-type": "text/html"})
    assert "<div>" in out
    assert "&" in out
    assert '"hello"' in out
    assert "&lt;" not in out


# ---------------------------------------------------------------------------
# request() / show() — view-source: scheme (1-5)
# ---------------------------------------------------------------------------

def test_request_view_source():
    """view-source: scheme fetches the URL and marks headers for raw display."""
    mock_response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html\r\n"
        b"Content-Length: 30\r\n"
        b"\r\n"
        b"<html><body>Hello</body></html>"
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = mock_response[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv

    with patch("socket.socket", return_value=mock_sock):
        import browser as br
        status, headers, body = br.request("view-source:http://example.com/")
    assert headers.get("_view_source") is True
    assert b"<html>" in body


def test_show_view_source_prints_raw_html():
    """When _view_source is True, show() prints raw HTML without parsing."""
    html = b"<html><body><p>Hello</p></body></html>"
    out = _capture_show(html, {"content-type": "text/html", "_view_source": True})
    assert "<html>" in out
    assert "<body>" in out


# ---------------------------------------------------------------------------
# request() — keep-alive socket pool (1-6)
# ---------------------------------------------------------------------------

def test_keepalive_reuses_socket():
    """Two requests to the same host should reuse the same socket."""
    import browser as br

    combined = (
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Type: text/html\r\n\r\nHello"
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Type: text/html\r\n\r\nWorld"
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = combined[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv

    with patch("socket.socket", return_value=mock_sock) as mock_ctor:
        br.request("http://example.com/a")
        br.request("http://example.com/b")
    assert mock_ctor.call_count == 1


def test_keepalive_reads_content_length_only():
    """Should read only Content-Length bytes, leaving the rest for the next response."""
    import browser as br

    combined = (
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Type: text/html\r\n\r\nHello"
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Type: text/html\r\n\r\nWorld"
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = combined[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv

    with patch("socket.socket", return_value=mock_sock):
        _, _, body1 = br.request("http://example.com/a")
        _, _, body2 = br.request("http://example.com/b")
    assert body1 == b"Hello"
    assert body2 == b"World"


# ---------------------------------------------------------------------------
# request() — redirects (1-7)
# ---------------------------------------------------------------------------

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
    mock_sock = _make_mock_sock(redirect_response)
    with patch("socket.socket", return_value=mock_sock):
        from browser import request
        with pytest.raises(RuntimeError, match="Too many redirects"):
            request("http://example.com/old", max_redirect=0)


def test_redirect_relative_path():
    """A Location starting with / should be resolved against the original host."""
    redirect_response = (
        b"HTTP/1.1 302 Found\r\n"
        b"Location: /new-path\r\n"
        b"Content-Length: 0\r\n"
        b"\r\n"
    )
    final_response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 8\r\n"
        b"Content-Type: text/html\r\n"
        b"\r\n"
        b"Arrived!"
    )
    sock1 = MagicMock()
    pos1 = [0]
    def recv1(n):
        chunk = redirect_response[pos1[0]:pos1[0]+n]
        pos1[0] += len(chunk)
        return chunk
    sock1.recv.side_effect = recv1

    sock2 = MagicMock()
    pos2 = [0]
    def recv2(n):
        chunk = final_response[pos2[0]:pos2[0]+n]
        pos2[0] += len(chunk)
        return chunk
    sock2.recv.side_effect = recv2

    with patch("socket.socket", side_effect=[sock1, sock2]):
        import browser as br
        _, _, body = br.request("http://example.com/old")
    assert b"Arrived!" in body


# ---------------------------------------------------------------------------
# request() — caching (1-8)
# ---------------------------------------------------------------------------

def test_cache_stores_and_returns_200():
    """200 responses with max-age should be served from cache on repeat requests."""
    import browser as br

    mock_response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 5\r\n"
        b"Content-Type: text/html\r\n"
        b"Cache-Control: max-age=60\r\n"
        b"\r\n"
        b"Hello"
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = mock_response[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv

    with patch("socket.socket", return_value=mock_sock) as mock_ctor:
        br.request("http://example.com/cached")
        br.request("http://example.com/cached")
    assert mock_ctor.call_count == 1


def test_cache_respects_no_store():
    """Cache-Control: no-store must not populate the cache."""
    import browser as br

    combined = (
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nCache-Control: no-store\r\n\r\nHello"
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nCache-Control: no-store\r\n\r\nWorld"
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = combined[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv

    with patch("socket.socket", return_value=mock_sock):
        br.request("http://example.com/nocache")
    assert "http://example.com/nocache" not in br._cache


def test_cache_expires():
    """Cached responses should be re-fetched after max-age seconds have elapsed."""
    import browser as br

    # Two responses on the same keep-alive socket
    combined = (
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nCache-Control: max-age=1\r\n\r\nHello"
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nCache-Control: max-age=1\r\n\r\nWorld"
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = combined[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv

    sent_count = [0]
    mock_sock.sendall.side_effect = lambda d: sent_count.__setitem__(0, sent_count[0] + 1)

    with patch("socket.socket", return_value=mock_sock):
        with patch("time.time", side_effect=[0, 2, 2]):
            br.request("http://example.com/expire")
            br.request("http://example.com/expire")
    # Both requests hit the network (cache expired between them)
    assert sent_count[0] == 2


# ---------------------------------------------------------------------------
# request() — gzip + chunked (1-9)
# ---------------------------------------------------------------------------

def test_request_accepts_gzip():
    """Request headers must include Accept-Encoding: gzip."""
    sent = []
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nHello", b""
    ]
    mock_sock.sendall.side_effect = lambda d: sent.append(d.decode())
    import browser as br
    with patch("socket.socket", return_value=mock_sock):
        br.request("http://example.com/")
    assert "Accept-Encoding: gzip" in "".join(sent)


def test_request_decompresses_gzip_body():
    """Content-Encoding: gzip responses must be automatically decompressed."""
    compressed = gzip_module.compress(b"Hello gzip!")
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Encoding: gzip\r\n"
        + f"Content-Length: {len(compressed)}\r\n".encode()
        + b"Content-Type: text/html\r\n"
        b"\r\n"
        + compressed
    )
    mock_sock = MagicMock()
    pos = [0]
    def fake_recv(n):
        chunk = response[pos[0]:pos[0]+n]
        pos[0] += len(chunk)
        return chunk
    mock_sock.recv.side_effect = fake_recv
    import browser as br
    with patch("socket.socket", return_value=mock_sock):
        _, _, body = br.request("http://example.com/gz")
    assert body == b"Hello gzip!"


def test_request_handles_chunked():
    """Transfer-Encoding: chunked responses must be correctly reassembled."""
    chunked_body = b"5\r\nHello\r\n6\r\n World\r\n0\r\n\r\n"
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"Content-Type: text/html\r\n"
        b"\r\n"
        + chunked_body
    )
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [response, b""]
    import browser as br
    with patch("socket.socket", return_value=mock_sock):
        _, _, body = br.request("http://example.com/chunked")
    assert body == b"Hello World"


# ---------------------------------------------------------------------------
# show()
# ---------------------------------------------------------------------------

def test_show_extracts_text():
    html = b"<html><body><p>Hello World</p></body></html>"
    out = _capture_show(html, {"content-type": "text/html"})
    assert "Hello World" in out


def test_show_skips_script():
    html = b"<html><body><script>alert(1)</script><p>Visible</p></body></html>"
    out = _capture_show(html, {"content-type": "text/html"})
    assert "alert" not in out
    assert "Visible" in out


def test_show_skips_style():
    html = b"<html><head><style>body{color:red}</style></head><body>Text</body></html>"
    out = _capture_show(html, {"content-type": "text/html"})
    assert "color" not in out
    assert "Text" in out


def test_show_handles_utf8_encoding():
    html = "안녕하세요".encode("utf-8")
    out = _capture_show(html, {"content-type": "text/html; charset=utf-8"})
    assert "안녕하세요" in out


def test_show_handles_euckr_fallback():
    html = b"<p>" + "안녕".encode("euc-kr") + b"</p>"
    out = _capture_show(html, {"content-type": "text/html"})
    assert "안녕" in out


def test_show_non_html_prints_raw():
    body = b"{'key': 'value'}"
    out = _capture_show(body, {"content-type": "application/json"})
    assert "key" in out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_default_url_used_when_no_arg(monkeypatch, tmp_path, capsys):
    """Running with no URL argument should open DEFAULT_URL."""
    monkeypatch.setattr(sys, "argv", ["browser.py"])
    default_file = tmp_path / "default.html"
    default_file.write_bytes(b"<p>Default page</p>")
    import browser
    monkeypatch.setattr(browser, "DEFAULT_URL", f"file://{default_file}")
    browser.main()
    out = capsys.readouterr().out
    assert "Default page" in out


def test_main_shows_section_headers(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["browser.py", "http://example.com"])
    import browser
    monkeypatch.setattr(browser, "request", lambda url, **kw: (
        "HTTP/1.0 200 OK",
        {"content-type": "text/html"},
        b"<p>Hi</p>"
    ))
    browser.main()
    out = capsys.readouterr().out
    assert "=== Request ===" in out
    assert "=== Response Status ===" in out
    assert "=== Response Headers ===" in out
    assert "=== Body (text) ===" in out
