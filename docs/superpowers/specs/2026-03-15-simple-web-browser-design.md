# Simple Python Web Browser — Design Spec

Date: 2026-03-15

## Overview

A command-line Python web browser that fetches a URL using raw sockets, parses the HTTP response, and displays the plain text content of the page. No external packages required. Supports HTTPS and Korean-language sites.

## Usage

```bash
python browser.py https://example.com
```

## Architecture

Single file: `browser.py`, four functions with one clear responsibility each.

```
parse_url(url)          → (scheme, host, port, path)
request(url)            → (status_line, headers_dict, body_bytes)
show(body_bytes, headers_dict) → prints plain text to stdout
main()                  → reads sys.argv[1], orchestrates the above
```

## Function Specifications

### `parse_url(url) → (scheme, host, port, path)`

- Splits URL on `://` to extract scheme (`http` or `https`)
- Default ports: `http` → 80, `https` → 443
- Strips fragment (`#...`) before further parsing
- Separates host from path on first `/`; path defaults to `/` if absent
- Path includes query string (`?...`) if present
- Extracts explicit port from host if present (`host:8080`), converts to int

### `request(url, max_redirect=10) → (status_line, headers_dict, body_bytes)`

- Calls `parse_url(url)` to get connection parameters
- Creates a TCP socket via `socket.socket(AF_INET, SOCK_STREAM)`
- Sets `socket.settimeout(10)` to avoid hanging on unresponsive servers
- For HTTPS: wraps socket with `ssl.create_default_context().wrap_socket(s, server_hostname=host)`
- Uses **HTTP/1.0** — server closes connection after response, so no chunked encoding or Content-Length parsing needed
- Request format:
  ```
  GET {path} HTTP/1.0\r\n
  Host: {host}\r\n
  \r\n
  ```
- Reads full response in a loop (`recv(4096)`) until socket returns empty bytes
- Splits raw bytes on first `b'\r\n\r\n'` into header section and body bytes
- Parses status line (first line of header section)
- Parses headers: `line.split(': ', 1)` (maxsplit=1 to handle colons in values like URLs or dates)
- Header keys stored lowercased for case-insensitive lookup
- On 3xx response: extracts `location` header, calls `request(location, max_redirect - 1)` recursively; raises `RuntimeError` if `max_redirect` reaches 0

### `show(body_bytes, headers_dict)`

- Encoding resolution (in order):
  1. Parse `charset=` value from `content-type` header using `str.split`
  2. If not found, try UTF-8 decode
  3. On `UnicodeDecodeError`, try EUC-KR
  4. Final fallback: latin-1 (never raises)
- Decodes body bytes to string
- Skips `show()` if `content-type` does not contain `html` (prints raw text instead)
- Uses `HTMLParser` subclass `TextExtractor`:
  - Maintains a `_skip` counter (int, not bool) initialized to 0
  - `handle_starttag`: increments `_skip` when tag is `script` or `style`
  - `handle_endtag`: decrements `_skip` when tag is `script` or `style` (floor at 0)
  - `handle_data`: appends data to list only when `_skip == 0`
- Joins collected text chunks, strips lines that are blank or whitespace-only, prints result

### `main()`

- Reads `sys.argv[1]` as URL; prints `Usage: browser.py <url>` and exits with code 1 if missing
- Calls `request(url)` and prints the full response structure in labeled sections:
  1. `=== Request ===` — shows the request line and Host header that was sent
  2. `=== Response Status ===` — shows the raw status line
  3. `=== Response Headers ===` — shows all headers as `key: value` pairs
  4. `=== Body (text) ===` — calls `show()` to print parsed plain text
- Each section is separated by a blank line for readability

## Output Format

```
=== Request ===
GET / HTTP/1.0
Host: example.com

=== Response Status ===
HTTP/1.0 200 OK

=== Response Headers ===
content-type: text/html; charset=UTF-8
content-length: 1256
...

=== Body (text) ===
Example Domain
This domain is for use in illustrative examples...
```

`main()` prints each section separated by a labeled divider (`=== ... ===`), so the full HTTP request/response structure is visible at a glance.

## Error Handling

| Condition | Behavior |
|---|---|
| Missing URL argument | Print usage, exit(1) |
| Redirect loop > 10 | Raise RuntimeError |
| Socket timeout | Exception propagates with message |
| UnicodeDecodeError | Fallback encoding chain (UTF-8 → EUC-KR → latin-1) |
| Non-HTML content-type | Print body as raw text |

## Constraints

- Standard library only: `socket`, `ssl`, `html.parser`, `sys`
- Python 3.6+
- HTTP/1.0 only (no chunked transfer encoding, no persistent connections)
- Handles 3xx redirects (301, 302, 303, 307, 308); all use `Location` header
