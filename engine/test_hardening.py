"""Tests for the SSRF and XML-entity hardening in safefetch.

Run: python3 -m unittest engine/test_hardening.py   (no network needed)
"""

import socket
import unittest
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


class URLHardening(unittest.TestCase):
    def test_non_http_scheme_rejected(self):
        for url in ("file:///etc/passwd", "ftp://example.com/x", "gopher://x"):
            with self.assertRaises(safefetch.BlockedURLError):
                safefetch.validate_url(url)

    def test_missing_host_rejected(self):
        with self.assertRaises(safefetch.BlockedURLError):
            safefetch.validate_url("https://")

    def test_private_and_local_addresses_rejected(self):
        for ip in ("127.0.0.1", "169.254.169.254", "10.0.0.5", "192.168.1.1",
                   "172.16.0.1", "0.0.0.0", "::1"):
            with mock.patch.object(safefetch.socket, "getaddrinfo", _fake_getaddrinfo(ip)):
                with self.assertRaises(safefetch.BlockedURLError):
                    safefetch.validate_url("https://feed.example.com/rss")

    def test_public_address_allowed(self):
        with mock.patch.object(safefetch.socket, "getaddrinfo",
                               _fake_getaddrinfo("93.184.216.34")):
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


if __name__ == "__main__":
    unittest.main()
