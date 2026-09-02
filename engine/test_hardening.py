"""Tests for the SSRF, bounded-read, and XML-entity hardening in safefetch.

Run from the repository root (no network needed):

    python3 -m unittest discover -s engine -p 'test_*.py'
"""

import io
import socket
import unittest
import urllib.request
from unittest import mock

import safefetch


def _fake_getaddrinfo(ip):
    """Return a getaddrinfo stub that resolves any host to `ip`."""
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, 0, 0, 0) if ":" in ip else (ip, 0)
    return lambda *a, **k: [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)]


class XMLHardening(unittest.TestCase):
    NORMAL = (b'<?xml version="1.0"?>'
              b'<feed xmlns="http://www.w3.org/2005/Atom"'
              b' xmlns:media="http://search.yahoo.com/mrss/">'
              b'<entry><title>Tom &amp; Jerry &lt; 2.4</title>'
              b'<media:group><media:description>hi</media:description></media:group>'
              b'</entry></feed>')
    BILLION_LAUGHS = (b'<?xml version="1.0"?>'
                      b'<!DOCTYPE lolz [<!ENTITY a "aaaaaaaaaa">'
                      b' <!ENTITY b "&a;&a;&a;&a;&a;">]>'
                      b'<feed><title>&b;</title></feed>')
    EXTERNAL_DTD = (b'<?xml version="1.0"?>'
                    b'<!DOCTYPE foo SYSTEM "http://evil.example/x.dtd">'
                    b'<feed><title>x</title></feed>')

    def test_normal_feed_parses_with_namespaces(self):
        root = safefetch.safe_fromstring(self.NORMAL)
        self.assertEqual(root.tag, "{http://www.w3.org/2005/Atom}feed")
        title = root.find(".//{http://www.w3.org/2005/Atom}title")
        self.assertEqual(title.text, "Tom & Jerry < 2.4")  # predefined entities still expand
        desc = root.find(".//{http://search.yahoo.com/mrss/}description")
        self.assertEqual(desc.text, "hi")

    def test_bom_and_blank_prolog_tolerated(self):
        root = safefetch.safe_fromstring(b"\xef\xbb\xbf\r\n  " + self.NORMAL)
        self.assertTrue(root.tag.endswith("}feed"))

    def test_billion_laughs_rejected(self):
        with self.assertRaises(safefetch.ForbiddenXMLError):
            safefetch.safe_fromstring(self.BILLION_LAUGHS)

    def test_external_dtd_rejected(self):
        with self.assertRaises(safefetch.ForbiddenXMLError):
            safefetch.safe_fromstring(self.EXTERNAL_DTD)

    def test_transport_charset_applies_only_without_declaration(self):
        latin = "<feed><title>Caf\xe9</title></feed>".encode("latin-1")
        self.assertEqual(safefetch.safe_fromstring(latin, encoding="iso-8859-1")[0].text, "Café")
        declared = ('<?xml version="1.0" encoding="UTF-8"?><feed><title>Caf\xe9</title></feed>'
                    .encode("utf-8"))
        # a wrong transport charset must not override the document's own declaration
        self.assertEqual(safefetch.safe_fromstring(declared, encoding="iso-8859-1")[0].text, "Café")
        # nor turn a valid UTF-8 body served with a stale header into mojibake
        undeclared_utf8 = "<feed><title>Pittsburgh’s café</title></feed>".encode("utf-8")
        self.assertEqual(safefetch.safe_fromstring(undeclared_utf8, encoding="iso-8859-1")[0].text,
                         "Pittsburgh’s café")
        # an unknown transport charset is ignored (no LookupError); the undecodable
        # byte then fails as ordinary malformed XML, which the fetcher tolerates
        from xml.parsers import expat
        with self.assertRaises(expat.ExpatError):
            safefetch.safe_fromstring(latin, encoding="no-such-charset")


class URLHardening(unittest.TestCase):
    def test_non_http_scheme_rejected(self):
        for url in ("file:///etc/passwd", "ftp://example.com/x", "gopher://x"):
            with self.assertRaises(safefetch.BlockedURLError):
                safefetch.validate_url(url)

    def test_missing_host_or_bad_port_rejected(self):
        for url in ("https://", "https://example.com:99999/x"):
            with self.assertRaises(safefetch.BlockedURLError):
                safefetch.validate_url(url)

    def test_private_local_and_special_addresses_rejected(self):
        for ip in ("127.0.0.1", "169.254.169.254", "10.0.0.5", "192.168.1.1",
                   "172.16.0.1", "0.0.0.0", "::1",
                   "100.64.0.1", "100.127.255.254",   # carrier-grade NAT / Tailscale
                   "fc00::1", "fec0::1",              # ULA, deprecated site-local
                   "::ffff:10.0.0.1", "2002:7f00:1::1", "2002:5db8:d822::1",  # mapped, 6to4
                   "64:ff9b::7f00:1", "198.18.0.1", "240.0.0.1"):
            with mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo(ip)):
                with self.assertRaises(safefetch.BlockedURLError, msg=ip) as ctx:
                    safefetch.validate_url("https://feed.example.com/rss")
                self.assertNotIn(ip, str(ctx.exception))  # the address stays in the log only

    def test_blocked_redirect_message_hides_the_target(self):
        handler = safefetch.SafeRedirectHandler()
        with mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo("10.9.8.7")):
            with self.assertRaises(safefetch.BlockedURLError) as ctx:
                handler.redirect_request(None, None, 302, "Found", {},
                                         "http://nas.internal.example/admin")
        message = str(ctx.exception)
        self.assertNotIn("nas.internal", message)
        self.assertNotIn("10.9.8.7", message)

    def test_public_addresses_allowed(self):
        for ip in ("93.184.216.34", "2606:4700::1111"):
            with mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo(ip)):
                self.assertEqual(safefetch.validate_url("https://feed.example.com/rss"),
                                 "https://feed.example.com/rss")

    def test_unresolvable_host_rejected(self):
        def boom(*a, **k):
            raise socket.gaierror("nope")
        with mock.patch.object(safefetch.socket, "getaddrinfo", boom):
            with self.assertRaises(safefetch.BlockedURLError):
                safefetch.validate_url("https://does-not-resolve.example/rss")

    def test_redirect_to_private_address_blocked(self):
        handler = safefetch.SafeRedirectHandler()
        with mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo("127.0.0.1")):
            with self.assertRaises(safefetch.BlockedURLError):
                handler.redirect_request(None, None, 302, "Found", {},
                                         "http://127.0.0.1/admin")

    def test_safe_open_validates_before_connecting(self):
        opened = []
        with mock.patch.object(safefetch._opener, "open",
                               lambda req, timeout=None: opened.append(req) or "resp"), \
                mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo("10.1.1.1")):
            with self.assertRaises(safefetch.BlockedURLError):
                safefetch.safe_open(urllib.request.Request("https://feed.example.com/rss"), 5)
        self.assertEqual(opened, [])  # never reached the network
        with mock.patch.object(safefetch._opener, "open",
                               lambda req, timeout=None: opened.append(req) or "resp"), \
                mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34")):
            self.assertEqual(safefetch.safe_open("https://feed.example.com/rss", 5), "resp")
        self.assertEqual(opened, ["https://feed.example.com/rss"])


class BoundedRead(unittest.TestCase):
    def test_size_cap(self):
        resp = io.BytesIO(b"x" * 1000)
        with self.assertRaises(safefetch.ResponseTooLargeError):
            safefetch.read_bounded(resp, 999, 10)
        self.assertEqual(safefetch.read_bounded(io.BytesIO(b"x" * 1000), 1000, 10), b"x" * 1000)

    def test_wall_clock_deadline_beats_slow_drip(self):
        clock = [0.0]

        class Drip:
            def read(self, n):
                clock[0] += 5.0  # every chunk "takes" five seconds
                return b"y"       # and never ends

        with mock.patch.object(safefetch.time, "monotonic", lambda: clock[0]):
            with self.assertRaises(safefetch.ResponseTooSlowError):
                safefetch.read_bounded(Drip(), 10**9, 12)
        self.assertLessEqual(clock[0], 20)  # gave up after ~3 chunks, not 10**9


if __name__ == "__main__":
    unittest.main()
