# Simple Web Browser Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a command-line Python web browser that fetches a URL over raw sockets and prints the page's plain text.

**Architecture:** Single file `browser.py` with four functions — `parse_url`, `request`, `show`, `main` — each with one responsibility. HTTP/1.0 over raw sockets (with SSL wrapping for HTTPS). HTML parsed by stdlib `html.parser`.

**Tech Stack:** Python 3.6+, standard library only — `socket`, `ssl`, `html.parser`, `sys`

---

## Chunk 1: URL Parser

### Task 1: `parse_url`

**Files:**
- Create: `browser.py`
- Create: `tests/test_browser.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_browser.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py -v
```

Expected: `ModuleNotFoundError: No module named 'browser'`

- [ ] **Step 3: Implement `parse_url` in `browser.py`**

```python
# browser.py
import socket
import ssl
import sys
from html.parser import HTMLParser


def parse_url(url):
    """Return (scheme, host, port, path) from a URL string."""
    scheme, rest = url.split("://", 1)
    # Strip fragment
    if "#" in rest:
        rest = rest[:rest.index("#")]
    # Separate host+port from path
    if "/" in rest:
        host_port, path = rest.split("/", 1)
        path = "/" + path
    else:
        host_port = rest
        path = "/"
    # Path includes query string already
    # Extract port from host if present
    if ":" in host_port:
        host, port_str = host_port.rsplit(":", 1)
        port = int(port_str)
    else:
        host = host_port
        port = 443 if scheme == "https" else 80
    return scheme, host, port, path
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Initialize git repo and commit**

```bash
cd /Users/bduesige/Desktop/test && git init && git add browser.py tests/test_browser.py && git commit -m "feat: add parse_url with full URL decomposition"
```

---

## Chunk 2: HTTP Request

### Task 2: `request`

**Files:**
- Modify: `browser.py` — add `request()` function
- Modify: `tests/test_browser.py` — add request tests

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_browser.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py::test_request_returns_tuple tests/test_browser.py::test_redirect_followed -v
```

Expected: `ImportError` or `AttributeError` — `request` not yet defined

- [ ] **Step 3: Implement `request` in `browser.py`**

Add after `parse_url`:

```python
def request(url, max_redirect=10):
    """Fetch URL, return (status_line, headers_dict, body_bytes).
    Follows 3xx redirects up to max_redirect times.
    """
    scheme, host, port, path = parse_url(url)

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.settimeout(10)
    if scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(raw_sock, server_hostname=host)
    else:
        s = raw_sock

    try:
        s.connect((host, port))

        # Send HTTP/1.0 request
        req = f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n"
        s.send(req.encode("utf-8"))

        # Read full response until EOF
        raw = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            raw += chunk
    finally:
        s.close()  # closes the SSL wrapper (and underlying socket) if HTTPS

    # Split headers from body on first blank line
    header_section, _, body = raw.partition(b"\r\n\r\n")
    header_lines = header_section.decode("utf-8", errors="replace").split("\r\n")

    status_line = header_lines[0]
    headers = {}
    for line in header_lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value

    # Follow 3xx redirects
    status_code = status_line.split(" ", 2)[1] if " " in status_line else ""
    if status_code.startswith("3") and "location" in headers:
        if max_redirect == 0:
            raise RuntimeError("Too many redirects")
        return request(headers["location"], max_redirect - 1)

    return status_line, headers, body
```

- [ ] **Step 4: Run all tests**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py -v
```

Expected: all tests PASS (the socket mock tests may pass or skip based on mock setup — verify no crashes)

- [ ] **Step 5: Quick manual smoke test**

```bash
cd /Users/bduesige/Desktop/test && python -c "
from browser import request
status, headers, body = request('http://example.com')
print(status)
print(headers)
print(body[:100])
"
```

Expected: prints `HTTP/1.0 200 OK` and some headers and HTML bytes

- [ ] **Step 6: Commit**

```bash
cd /Users/bduesige/Desktop/test && git add browser.py tests/test_browser.py && git commit -m "feat: add request() with socket, SSL, redirect handling"
```

---

## Chunk 3: HTML Text Extractor

### Task 3: `show`

**Files:**
- Modify: `browser.py` — add `TextExtractor` class and `show()` function
- Modify: `tests/test_browser.py` — add show tests

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_browser.py`:

```python
import io
from contextlib import redirect_stdout

def _capture_show(body_bytes, headers):
    from browser import show
    f = io.StringIO()
    with redirect_stdout(f):
        show(body_bytes, headers)
    return f.getvalue()

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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py::test_show_extracts_text -v
```

Expected: `ImportError` — `show` not yet defined

- [ ] **Step 3: Implement `TextExtractor` and `show` in `browser.py`**

Add after `request`:

```python
class TextExtractor(HTMLParser):
    """Collects visible text, skipping <script> and <style> blocks."""

    def __init__(self):
        super().__init__()
        self._skip = 0      # counter, not bool — handles nesting correctly
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if self._skip == 0:
            self._parts.append(data)

    def get_text(self):
        lines = []
        for part in self._parts:
            for line in part.splitlines():
                if line.strip():
                    lines.append(line)
        return "\n".join(lines)


def show(body_bytes, headers):
    """Decode body and print plain text, stripping HTML tags."""
    content_type = headers.get("content-type", "")

    # Encoding resolution
    encoding = "utf-8"
    if "charset=" in content_type:
        encoding = content_type.split("charset=", 1)[1].split(";")[0].strip()

    # Decode with fallback chain (deduplicated so declared encoding isn't tried twice)
    candidates = [encoding] + [e for e in ["utf-8", "euc-kr", "latin-1"] if e != encoding]
    text = None
    for enc in candidates:
        try:
            text = body_bytes.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise ValueError("Unable to decode body with any supported encoding")

    if "html" not in content_type:
        print(text)
        return

    extractor = TextExtractor()
    extractor.feed(text)
    print(extractor.get_text())
```

- [ ] **Step 4: Run all tests**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/bduesige/Desktop/test && git add browser.py tests/test_browser.py && git commit -m "feat: add show() with HTML text extraction and encoding fallback"
```

---

## Chunk 4: Main Entry Point

### Task 4: `main` + response structure display

**Files:**
- Modify: `browser.py` — add `main()` and `if __name__ == "__main__"` block
- Modify: `tests/test_browser.py` — add main tests

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_browser.py`:

```python
import pytest

def test_main_missing_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["browser.py"])
    with pytest.raises(SystemExit):
        from browser import main
        main()

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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py::test_main_missing_arg_exits tests/test_browser.py::test_main_shows_section_headers -v
```

Expected: `ImportError` — `main` not yet defined

- [ ] **Step 3: Implement `main` in `browser.py`**

Append to `browser.py`:

```python
def main():
    if len(sys.argv) < 2:
        print("Usage: browser.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    scheme, host, port, path = parse_url(url)

    # Show what request will be sent
    print("=== Request ===")
    print(f"GET {path} HTTP/1.0")
    print(f"Host: {host}")
    print()

    status_line, headers, body = request(url)

    # Show response status
    print("=== Response Status ===")
    print(status_line)
    print()

    # Show all response headers
    print("=== Response Headers ===")
    for key, value in headers.items():
        print(f"{key}: {value}")
    print()

    # Show parsed body text
    print("=== Body (text) ===")
    show(body, headers)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/test_browser.py -v
```

Expected: all tests PASS

- [ ] **Step 5: End-to-end test**

```bash
cd /Users/bduesige/Desktop/test && python browser.py https://example.com
```

Expected output:
```
=== Request ===
GET / HTTP/1.0
Host: example.com

=== Response Status ===
HTTP/1.0 200 OK

=== Response Headers ===
content-type: text/html; charset=UTF-8
...

=== Body (text) ===
Example Domain
This domain is for use in illustrative examples in documents.
```

- [ ] **Step 6: Test missing argument**

```bash
cd /Users/bduesige/Desktop/test && python browser.py
```

Expected: `Usage: browser.py <url>` then exit

- [ ] **Step 7: Test redirect following (http → https)**

```bash
cd /Users/bduesige/Desktop/test && python browser.py http://naver.com
```

Expected: follows redirect to `https://www.naver.com`, shows Korean text

- [ ] **Step 8: Run full test suite**

```bash
cd /Users/bduesige/Desktop/test && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 9: Final commit**

```bash
cd /Users/bduesige/Desktop/test && git add browser.py tests/test_browser.py && git commit -m "feat: add main() with structured request/response display"
```

---

## Running the Browser

```bash
# Basic usage
python browser.py https://example.com

# Korean site (tests EUC-KR fallback + redirect)
python browser.py http://naver.com

# HTTP site
python browser.py http://info.cern.ch
```
