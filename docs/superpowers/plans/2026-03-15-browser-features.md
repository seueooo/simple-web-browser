# Browser Features Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 9 features to the educational web browser: HTTP/1.1, multiple URL schemes, Keep-alive, caching, and compression.

**Architecture:** All features are added to `browser.py`. Socket pool and cache are module-level dicts. Scheme-specific handling is dispatched at the top of `request()`.

**Tech Stack:** Python 3 standard library (socket, ssl, gzip, html, time)

---

## File Structure

- Modify: `browser.py` — all new features
- Modify: `tests/test_browser.py` — tests for each feature

---

## Chunk 1: HTTP/1.1, file://, data:, HTML entities, view-source

### Task 1: HTTP/1.1 Header Refactor (1-1)

**Files:**
- Modify: `browser.py` (request function)
- Modify: `tests/test_browser.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_browser.py`:
```python
def test_request_sends_http11(monkeypatch):
    """request() must use HTTP/1.1 and send Host, Connection, User-Agent headers."""
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
    assert "Connection: close" in req_text
    assert "User-Agent:" in req_text
```

- [ ] **Step 2: Run test — expect failure**

```bash
pytest tests/test_browser.py::test_request_sends_http11 -v
```
Expected: FAIL

- [ ] **Step 3: Update request() to send HTTP/1.1 headers**

In `browser.py`, replace:
```python
req = f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n"
s.sendall(req.encode("utf-8"))
```
with:
```python
headers_to_send = {
    "Host": host,
    "Connection": "close",
    "User-Agent": "SimpleBrowser/1.0",
}
header_lines = "\r\n".join(f"{k}: {v}" for k, v in headers_to_send.items())
req = f"GET {path} HTTP/1.1\r\n{header_lines}\r\n\r\n"
s.sendall(req.encode("utf-8"))
```

- [ ] **Step 4: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 5: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: upgrade to HTTP/1.1 with Host, Connection, User-Agent headers"
```

---

### Task 2: file:// Scheme Support (1-2)

**Files:**
- Modify: `browser.py` (parse_url, request, main)
- Modify: `tests/test_browser.py`

- [ ] **Step 1: Write failing tests**

```python
def test_parse_url_file_scheme():
    from browser import parse_url
    scheme, host, port, path = parse_url("file:///tmp/test.html")
    assert scheme == "file"
    assert path == "/tmp/test.html"

def test_request_file_scheme(tmp_path):
    """file:// URL should read a local file."""
    f = tmp_path / "hello.html"
    f.write_bytes(b"<p>Hello file</p>")
    from browser import request
    status, headers, body = request(f"file://{f}")
    assert status == "200 OK"
    assert body == b"<p>Hello file</p>"

def test_main_default_file(monkeypatch, tmp_path, capsys):
    """Running with no URL argument should open the default file."""
    monkeypatch.setattr(sys, "argv", ["browser.py"])
    default_file = tmp_path / "default.html"
    default_file.write_bytes(b"<p>Default</p>")
    import browser
    monkeypatch.setattr(browser, "DEFAULT_URL", f"file://{default_file}")
    browser.main()
    out = capsys.readouterr().out
    assert "Default" in out
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_browser.py::test_parse_url_file_scheme tests/test_browser.py::test_request_file_scheme -v
```
Expected: FAIL

- [ ] **Step 3: Add DEFAULT_URL constant and file scheme to parse_url**

At the top of `browser.py` add:
```python
DEFAULT_URL = "file:///etc/hosts"
```

At the top of `parse_url()` add:
```python
    if url.startswith("file://"):
        return "file", "", 0, url[len("file://"):]
```

- [ ] **Step 4: Add file scheme dispatch to request()**

At the top of `request()` (after parse_url call) add:
```python
    if scheme == "file":
        with open(path, "rb") as f:
            body = f.read()
        return "200 OK", {"content-type": "text/html"}, body
```

- [ ] **Step 5: Update main() to use DEFAULT_URL when no argument given**

```python
def main():
    url = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_URL
    print("=== Request ===")
    print(f"URL: {url}")
    print()
    status_line, headers, body = request(url)
    # ... rest unchanged
```

Remove the old `if len(sys.argv) < 2` early-exit block.

- [ ] **Step 6: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 7: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: add file:// scheme support and default URL fallback"
```

---

### Task 3: data: Scheme Support (1-3)

**Files:**
- Modify: `browser.py`
- Modify: `tests/test_browser.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_browser.py::test_request_data_scheme_text -v
```
Expected: FAIL

- [ ] **Step 3: Add data scheme dispatch to parse_url and request()**

In `parse_url()`:
```python
    if url.startswith("data:"):
        return "data", "", 0, url[len("data:"):]
```

In `request()` after file scheme:
```python
    if scheme == "data":
        meta, _, content = path.partition(",")
        content_type = meta if meta else "text/plain"
        return "200 OK", {"content-type": content_type}, content.encode("utf-8")
```

- [ ] **Step 4: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 5: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: add data: scheme support"
```

---

### Task 4: HTML Entity Decoding (1-4)

**Files:**
- Modify: `browser.py` (TextExtractor.get_text)
- Modify: `tests/test_browser.py`

- [ ] **Step 1: Write failing test**

```python
def test_show_html_entities():
    """&lt; &gt; &amp; entities must be converted to their characters."""
    html = b"<p>&lt;div&gt; &amp; &quot;hello&quot;</p>"
    out = _capture_show(html, {"content-type": "text/html"})
    assert "<div>" in out
    assert "&" in out
    assert '"hello"' in out
    assert "&lt;" not in out
```

- [ ] **Step 2: Run test — expect failure**

```bash
pytest tests/test_browser.py::test_show_html_entities -v
```
Expected: FAIL

- [ ] **Step 3: Add html.unescape to TextExtractor.get_text()**

Add to `browser.py` imports:
```python
import html as html_module
```

Update `get_text()`:
```python
    def get_text(self):
        lines = []
        for part in self._parts:
            part = html_module.unescape(part)
            for line in part.splitlines():
                if line.strip():
                    lines.append(line)
        return "\n".join(lines)
```

- [ ] **Step 4: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 5: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: unescape HTML entities in text output"
```

---

### Task 5: view-source: Scheme (1-5)

**Files:**
- Modify: `browser.py`
- Modify: `tests/test_browser.py`

- [ ] **Step 1: Write failing tests**

```python
def test_request_view_source():
    """view-source: scheme fetches the URL and marks headers for raw display."""
    mock_response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html\r\n"
        b"Content-Length: 30\r\n"
        b"\r\n"
        b"<html><body>Hello</body></html>"
    )
    mock_sock = _make_mock_sock(mock_response)
    with patch("socket.socket", return_value=mock_sock):
        import browser as br
        br._socket_pool.clear()
        status, headers, body = br.request("view-source:http://example.com/")
    assert headers.get("_view_source") is True
    assert b"<html>" in body

def test_show_view_source_prints_raw_html():
    """When _view_source is True, show() prints raw HTML without parsing."""
    html = b"<html><body><p>Hello</p></body></html>"
    out = _capture_show(html, {"content-type": "text/html", "_view_source": True})
    assert "<html>" in out
    assert "<body>" in out
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_browser.py::test_request_view_source -v
```
Expected: FAIL

- [ ] **Step 3: Add view-source scheme to parse_url and request()**

In `parse_url()`:
```python
    if url.startswith("view-source:"):
        return "view-source", "", 0, url[len("view-source:"):]
```

In `request()` after data scheme:
```python
    if scheme == "view-source":
        inner_url = path
        status, headers, body = request(inner_url, max_redirect)
        headers["_view_source"] = True
        return "200 OK", headers, body
```

- [ ] **Step 4: Add _view_source check to show()**

At the top of `show()`:
```python
def show(body_bytes, headers):
    if headers.get("_view_source"):
        print(body_bytes.decode("utf-8", errors="replace"))
        return
    # ... existing code
```

- [ ] **Step 5: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 6: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: add view-source: scheme to display raw HTML source"
```

---

## Chunk 2: Keep-alive, Redirect Verification, Caching, Compression

### Task 6: Keep-alive Socket Pool (1-6)

**Files:**
- Modify: `browser.py`
- Modify: `tests/test_browser.py`

Design:
- Module-level `_socket_pool: dict` keyed by `(scheme, host, port)`
- Send `Connection: keep-alive`
- Read exactly `Content-Length` bytes, then return socket to pool
- If no `Content-Length`, read until EOF and close socket

- [ ] **Step 1: Write failing tests**

```python
def test_keepalive_reuses_socket():
    """Two requests to the same host should reuse the same socket."""
    import browser as br
    br._socket_pool.clear()

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
    br._socket_pool.clear()

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
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_browser.py::test_keepalive_reuses_socket -v
```
Expected: FAIL

- [ ] **Step 3: Rewrite HTTP socket logic in request() for keep-alive**

Add at top of `browser.py`:
```python
_socket_pool: dict = {}  # (scheme, host, port) -> socket
```

Replace the socket connect + send + receive block in `request()` with:
```python
    pool_key = (scheme, host, port)
    s = _socket_pool.pop(pool_key, None)

    if s is None:
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(10)
        if scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(raw_sock, server_hostname=host)
        else:
            s = raw_sock
        s.connect((host, port))

    headers_to_send = {
        "Host": host,
        "Connection": "keep-alive",
        "User-Agent": "SimpleBrowser/1.0",
    }
    header_lines = "\r\n".join(f"{k}: {v}" for k, v in headers_to_send.items())
    req = f"GET {path} HTTP/1.1\r\n{header_lines}\r\n\r\n"
    s.sendall(req.encode("utf-8"))

    # Read response headers
    raw_header = b""
    while b"\r\n\r\n" not in raw_header:
        chunk = s.recv(4096)
        if not chunk:
            break
        raw_header += chunk
    header_section, _, leftover = raw_header.partition(b"\r\n\r\n")
    header_lines_list = header_section.decode("utf-8", errors="replace").split("\r\n")
    status_line = header_lines_list[0]
    headers = {}
    for line in header_lines_list[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k.lower()] = v

    # Read body
    content_length = int(headers.get("content-length", -1))
    body = leftover
    if content_length >= 0:
        while len(body) < content_length:
            chunk = s.recv(4096)
            if not chunk:
                break
            body += chunk
        body = body[:content_length]
        _socket_pool[pool_key] = s  # return socket to pool
    else:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            body += chunk
        s.close()
```

- [ ] **Step 4: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 5: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: implement keep-alive socket pool with Content-Length based reading"
```

---

### Task 7: Redirect Verification (1-7)

Redirects are already implemented. This task verifies coverage.

- [ ] **Step 1: Confirm existing redirect tests pass**

```bash
pytest tests/test_browser.py::test_redirect_followed tests/test_browser.py::test_redirect_limit_raises -v
```
Expected: PASS

- [ ] **Step 2: Add relative-path redirect test**

```python
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
        b"Content-Length: 7\r\n"
        b"Content-Type: text/html\r\n"
        b"\r\n"
        b"Arrived!"
    )
    import browser as br
    br._socket_pool.clear()
    sock1 = MagicMock()
    pos1 = [0]
    def recv1(n):
        chunk = redirect_response[pos1[0]:pos1[0]+n]; pos1[0]+=len(chunk); return chunk
    sock1.recv.side_effect = recv1
    sock2 = MagicMock()
    pos2 = [0]
    def recv2(n):
        chunk = final_response[pos2[0]:pos2[0]+n]; pos2[0]+=len(chunk); return chunk
    sock2.recv.side_effect = recv2

    with patch("socket.socket", side_effect=[sock1, sock2]):
        _, _, body = br.request("http://example.com/old")
    assert b"Arrived!" in body
```

- [ ] **Step 3: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 4: Commit (tests only)**

```bash
git add tests/test_browser.py
git commit -m "test: verify relative redirect handling"
```

---

### Task 8: HTTP Caching (1-8)

**Files:**
- Modify: `browser.py`
- Modify: `tests/test_browser.py`

Design:
- `_cache: dict[url, (expires_at, status_line, headers, body)]`
- `Cache-Control: no-store` → do not cache
- `Cache-Control: max-age=N` → cache for N seconds
- Any other Cache-Control value → do not cache
- Only cache 200 GET responses

- [ ] **Step 1: Write failing tests**

```python
import time as time_module

def test_cache_stores_and_returns_200():
    """200 responses with max-age should be cached and returned on repeat requests."""
    import browser as br
    br._cache.clear()
    br._socket_pool.clear()

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
        chunk = mock_response[pos[0]:pos[0]+n]; pos[0]+=len(chunk); return chunk
    mock_sock.recv.side_effect = fake_recv

    with patch("socket.socket", return_value=mock_sock) as mock_ctor:
        br.request("http://example.com/cached")
        br.request("http://example.com/cached")
    assert mock_ctor.call_count == 1

def test_cache_respects_no_store():
    """Cache-Control: no-store must not cache the response."""
    import browser as br
    br._cache.clear()
    br._socket_pool.clear()

    def make_resp():
        r = (b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nCache-Control: no-store\r\n\r\nHello")
        m = MagicMock()
        pos = [0]
        def recv(n): chunk = r[pos[0]:pos[0]+n]; pos[0]+=len(chunk); return chunk
        m.recv.side_effect = recv
        return m

    with patch("socket.socket", side_effect=[make_resp(), make_resp()]) as mock_ctor:
        br.request("http://example.com/nocache")
        br.request("http://example.com/nocache")
    assert mock_ctor.call_count == 2

def test_cache_expires():
    """Cached responses should be re-fetched after max-age seconds."""
    import browser as br
    br._cache.clear()
    br._socket_pool.clear()

    def make_resp():
        r = (b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nCache-Control: max-age=1\r\n\r\nHello")
        m = MagicMock()
        pos = [0]
        def recv(n): chunk = r[pos[0]:pos[0]+n]; pos[0]+=len(chunk); return chunk
        m.recv.side_effect = recv
        return m

    with patch("socket.socket", side_effect=[make_resp(), make_resp()]) as mock_ctor:
        with patch("time.time", side_effect=[0, 0, 2, 2]):
            br.request("http://example.com/expire")
            br.request("http://example.com/expire")
    assert mock_ctor.call_count == 2
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_browser.py::test_cache_stores_and_returns_200 -v
```
Expected: FAIL

- [ ] **Step 3: Add _cache and caching logic to browser.py**

Add at top of `browser.py`:
```python
import time
_cache: dict = {}  # url -> (expires_at, status_line, headers, body)
```

In `request()`, before opening socket:
```python
    if url in _cache:
        expires_at, cached_status, cached_headers, cached_body = _cache[url]
        if time.time() < expires_at:
            return cached_status, cached_headers, cached_body
        else:
            del _cache[url]
```

After reading body, before the redirect check:
```python
    status_code = status_line.split(" ", 2)[1] if " " in status_line else ""
    if status_code == "200":
        cache_control = headers.get("cache-control", "")
        if "no-store" not in cache_control:
            max_age = None
            for part in cache_control.split(","):
                part = part.strip()
                if part.startswith("max-age="):
                    try:
                        max_age = int(part[len("max-age="):])
                    except ValueError:
                        pass
            if max_age is not None:
                _cache[url] = (time.time() + max_age, status_line, headers, body)
```

- [ ] **Step 4: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 5: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: add HTTP response caching with Cache-Control support"
```

---

### Task 9: gzip Compression + Chunked Transfer (1-9)

**Files:**
- Modify: `browser.py`
- Modify: `tests/test_browser.py`

- [ ] **Step 1: Write failing tests**

```python
import gzip as gzip_module

def test_request_accepts_gzip():
    """Request headers must include Accept-Encoding: gzip."""
    sent = []
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = [
        b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nHello", b""
    ]
    mock_sock.sendall.side_effect = lambda d: sent.append(d.decode())
    import browser as br
    br._socket_pool.clear()
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
        chunk = response[pos[0]:pos[0]+n]; pos[0]+=n; return chunk
    mock_sock.recv.side_effect = fake_recv
    import browser as br
    br._socket_pool.clear()
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
    br._socket_pool.clear()
    with patch("socket.socket", return_value=mock_sock):
        _, _, body = br.request("http://example.com/chunked")
    assert body == b"Hello World"
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_browser.py::test_request_accepts_gzip tests/test_browser.py::test_request_decompresses_gzip_body -v
```
Expected: FAIL

- [ ] **Step 3: Add gzip import and Accept-Encoding header**

Add to `browser.py` imports:
```python
import gzip
```

Add `Accept-Encoding` to `headers_to_send` in `request()`:
```python
headers_to_send = {
    "Host": host,
    "Connection": "keep-alive",
    "User-Agent": "SimpleBrowser/1.0",
    "Accept-Encoding": "gzip",
}
```

- [ ] **Step 4: Add _decode_chunked helper and apply decodings after body read**

Add helper function before `request()`:
```python
def _decode_chunked(data: bytes) -> bytes:
    """Decode chunked transfer-encoding data."""
    result = b""
    while data:
        newline = data.index(b"\r\n")
        size = int(data[:newline], 16)
        if size == 0:
            break
        result += data[newline + 2: newline + 2 + size]
        data = data[newline + 2 + size + 2:]
    return result
```

After the body-reading block in `request()`, before the redirect check:
```python
    # Chunked decoding
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = _decode_chunked(body)
        _socket_pool.pop(pool_key, None)  # cannot reuse after chunked

    # Gzip decompression
    if headers.get("content-encoding", "").lower() == "gzip":
        body = gzip.decompress(body)
```

- [ ] **Step 5: Run all tests — expect all pass**

```bash
pytest tests/test_browser.py -v
```

- [ ] **Step 6: Final full test run**

```bash
pytest tests/test_browser.py -v
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add browser.py tests/test_browser.py
git commit -m "feat: add gzip decompression and chunked transfer encoding support"
```

---

## Completion Checklist

- [ ] 1-1: HTTP/1.1, structured headers dict
- [ ] 1-2: file:// scheme, default URL
- [ ] 1-3: data: scheme
- [ ] 1-4: HTML entities
- [ ] 1-5: view-source: scheme
- [ ] 1-6: Keep-alive socket pool
- [ ] 1-7: Redirect verification
- [ ] 1-8: Caching
- [ ] 1-9: gzip + chunked
