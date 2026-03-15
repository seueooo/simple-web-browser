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
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port in URL: {port_str!r}")
    else:
        host = host_port
        port = 443 if scheme == "https" else 80
    return scheme, host, port, path
