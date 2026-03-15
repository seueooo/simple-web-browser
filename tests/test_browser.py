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
