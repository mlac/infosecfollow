"""Security hardening helpers for infosecfollow, stdlib only.

Defense-in-depth measures against the one untrusted input the pipeline
ingests — third-party feed content and the servers behind feed URLs:

1. safe_open / SafeRedirectHandler: refuse outbound HTTP(S) requests (and
   redirects) whose host resolves to a private, loopback, link-local,
   carrier-grade-NAT, or otherwise non-public address. Blocks the common SSRF
   case where a hijacked feed domain redirects to an internal service, a
   tailnet host, or a cloud metadata endpoint (169.254.169.254) whose contents
   would otherwise be summarized into the public briefing.

2. read_bounded: read a response with BOTH a byte cap and a wall-clock
   deadline. urllib's timeout bounds each socket operation, not the whole
   transfer, so a server that trickles one byte every few seconds could
   otherwise hold a worker (and the whole scheduler) indefinitely.

3. safe_fromstring: parse RSS/Atom/RDF with DTDs and entity declarations
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
import re
import socket
import time
import urllib.request
from urllib.parse import urlsplit
from xml.etree.ElementTree import TreeBuilder
from xml.parsers import expat

ALLOWED_SCHEMES = ("http", "https")
READ_CHUNK = 64 * 1024


class BlockedURLError(ValueError):
    """Raised when a URL's scheme or resolved address is not allowed."""


class ForbiddenXMLError(ValueError):
    """Raised when a feed declares a DTD or entities (DoS/XXE vector)."""


class ResponseTooLargeError(ValueError):
    """Raised when a response exceeds the byte cap."""


class ResponseTooSlowError(TimeoutError):
    """Raised when a response is not fully read before its wall-clock deadline."""


# --------------------------------------------------------------------------- SSRF

def _address_blocked(ip):
    # `not is_global` catches the ranges the explicit predicates miss, notably
    # 100.64.0.0/10 (carrier-grade NAT, also Tailscale's address pool). The
    # explicit predicates are kept because is_global alone would admit a few
    # special-purpose ranges (e.g. 64:ff9b::/96 NAT64) that must stay blocked.
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified
            or not ip.is_global)


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
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as exc:
        raise BlockedURLError(f"bad port in {url}: {exc}")
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
    usable as a context manager exactly like urlopen. `timeout` bounds each
    socket operation; use read_bounded on the response to bound the whole
    transfer.
    """
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    validate_url(url)
    return _opener.open(req, timeout=timeout)


def read_bounded(resp, max_bytes, deadline):
    """Read the whole response body, raising if it exceeds `max_bytes` or is not
    complete within `deadline` seconds of wall-clock time.

    Reads in chunks so a slow-drip server cannot hold the caller for longer
    than the deadline (plus one socket timeout).
    """
    start = time.monotonic()
    chunks, total = [], 0
    while True:
        if time.monotonic() - start > deadline:
            raise ResponseTooSlowError(
                f"response not complete after {deadline}s ({total} bytes read)")
        chunk = resp.read(READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ResponseTooLargeError(f"response larger than {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


# --------------------------------------------------------------------------- XML

# expat reports namespaced names as "uri}local"; ElementTree's convention is
# "{uri}local", so prefix "{" whenever a namespace is present.
def _qname(name):
    return "{" + name if "}" in name else name


_XML_DECL_ENCODING = re.compile(rb"^\s*<\?xml[^>]*\bencoding\s*=", re.IGNORECASE)


def safe_fromstring(raw, encoding=None):
    """Parse RSS/Atom/RDF bytes into an ElementTree root with DTDs/entities
    forbidden. Output matches xml.etree.ElementTree.fromstring (namespaced tags
    as "{uri}local"); raises ForbiddenXMLError on any DTD or entity declaration.

    `encoding` is the transport-level charset (from the HTTP Content-Type). It
    is applied only when the document itself declares no encoding, which is
    when expat would otherwise assume UTF-8 and mis-decode a Latin-1 feed.
    """
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    raw = raw.lstrip(b"\xef\xbb\xbf\r\n\t ")  # tolerate a BOM/blank prolog (TribLive)
    if encoding and encoding.lower().replace("_", "-") not in ("utf-8", "utf8") \
            and not _XML_DECL_ENCODING.match(raw):
        try:
            raw = raw.decode(encoding, "replace").encode("utf-8")
        except LookupError:
            pass  # unknown charset name: let expat try

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
