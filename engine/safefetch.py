"""Security hardening helpers for infosecfollow, stdlib only.

Two defense-in-depth measures against the one untrusted input the pipeline
ingests — third-party feed content and the servers behind feed URLs:

1. safe_open / SafeRedirectHandler: refuse outbound HTTP(S) requests (and
   redirects) whose host resolves to a private, loopback, link-local, or
   otherwise non-public address. Blocks the common SSRF case where a hijacked
   feed domain redirects to an internal service or a cloud metadata endpoint
   (169.254.169.254) whose contents would otherwise be summarized into the
   public briefing.

2. safe_fromstring: parse RSS/Atom/RDF with DTDs and entity declarations
   forbidden, defeating "billion laughs"/entity-expansion denial of service.
   The five predefined XML entities (&amp; &lt; &gt; &quot; &apos;) are not
   DTD-declared, so real feeds keep parsing; only the attack vector is refused.

Honest limitation (item 1): the host check resolves the name and inspects the
addresses, then a separate connection is made, so a determined DNS-rebind
(TOCTOU) can still slip through. Pinning the connection to the vetted IP with a
Host header would close that, but is more than this is worth; the check stops
the realistic cases.
"""

import ipaddress
import socket
import urllib.request
from urllib.parse import urlsplit
from xml.etree.ElementTree import TreeBuilder
from xml.parsers import expat

ALLOWED_SCHEMES = ("http", "https")


class BlockedURLError(ValueError):
    """Raised when a URL's scheme or resolved address is not allowed."""


class ForbiddenXMLError(ValueError):
    """Raised when a feed declares a DTD or entities (DoS/XXE vector)."""


# --------------------------------------------------------------------------- SSRF

def _address_blocked(ip):
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def validate_url(url):
    """Allow only http(s) URLs whose host resolves entirely to public addresses.

    Raises BlockedURLError otherwise. Every resolved address is checked, so a
    name that maps to even one private address is refused.
    """
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise BlockedURLError(f"scheme {parts.scheme!r} not allowed: {url}")
    host = parts.hostname
    if not host:
        raise BlockedURLError(f"missing host: {url}")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise BlockedURLError(f"cannot resolve {host}: {exc}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _address_blocked(ip):
            raise BlockedURLError(f"{host} resolves to blocked address {ip}")
    return url


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect target before following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)  # raises BlockedURLError, aborting the fetch
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(SafeRedirectHandler())


def safe_open(req, timeout):
    """Drop-in for urllib.request.urlopen that vets the URL and all redirects.

    `req` is a urllib.request.Request (or a URL string). Returns the response,
    usable as a context manager exactly like urlopen.
    """
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    validate_url(url)
    return _opener.open(req, timeout=timeout)


# --------------------------------------------------------------------------- XML

# expat reports namespaced names as "uri}local"; ElementTree's convention is
# "{uri}local", so prefix "{" whenever a namespace is present.
def _qname(name):
    return "{" + name if "}" in name else name


def safe_fromstring(raw):
    """Parse RSS/Atom/RDF bytes into an ElementTree root with DTDs/entities
    forbidden. Output matches xml.etree.ElementTree.fromstring (namespaced tags
    as "{uri}local"); raises ForbiddenXMLError on any DTD or entity declaration.
    """
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    raw = raw.lstrip(b"\xef\xbb\xbf\r\n\t ")  # tolerate a BOM/blank prolog (TribLive)

    builder = TreeBuilder()
    parser = expat.ParserCreate(namespace_separator="}")
    parser.buffer_text = True

    def forbid(*args, **kwargs):
        raise ForbiddenXMLError("DTD or entity declarations are not allowed")

    parser.StartDoctypeDeclHandler = forbid
    parser.EntityDeclHandler = forbid
    parser.UnparsedEntityDeclHandler = forbid
    parser.ExternalEntityRefHandler = forbid

    def start(name, attrs):
        builder.start(_qname(name), {_qname(k): v for k, v in attrs.items()})

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda name: builder.end(_qname(name))
    parser.CharacterDataHandler = builder.data
    parser.Parse(raw, True)
    return builder.close()
