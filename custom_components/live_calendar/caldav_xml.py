"""Pure-Python helpers for building and parsing CalDAV (WebDAV) XML.

This module intentionally has no Home Assistant or aiohttp imports so it can
be unit tested on its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

try:  # defusedxml is preferred when available (it ships with Home Assistant).
    from defusedxml import ElementTree as _SafeET
except ImportError:  # pragma: no cover
    _SafeET = ET

NS_DAV = "DAV:"
NS_CALDAV = "urn:ietf:params:xml:ns:caldav"
NS_CS = "http://calendarserver.org/ns/"


def _d(name: str) -> str:
    return f"{{{NS_DAV}}}{name}"


def _c(name: str) -> str:
    return f"{{{NS_CALDAV}}}{name}"


def _cs(name: str) -> str:
    return f"{{{NS_CS}}}{name}"


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------

_XML_HEAD = '<?xml version="1.0" encoding="utf-8"?>'

PROPFIND_TOKEN = (
    f"{_XML_HEAD}"
    '<d:propfind xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">'
    "<d:prop><cs:getctag/><d:sync-token/></d:prop></d:propfind>"
)

PROPFIND_ETAGS = (
    f"{_XML_HEAD}"
    '<d:propfind xmlns:d="DAV:"><d:prop><d:getetag/></d:prop></d:propfind>'
)

PROPFIND_DISCOVERY = (
    f"{_XML_HEAD}"
    '<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
    "<d:prop>"
    "<d:resourcetype/><d:displayname/><d:current-user-principal/>"
    "<c:calendar-home-set/><c:supported-calendar-component-set/>"
    "</d:prop></d:propfind>"
)


def build_multiget(hrefs: list[str]) -> str:
    """Build a calendar-multiget REPORT body for the given resource hrefs."""
    items = "".join(f"<d:href>{escape(h)}</d:href>" for h in hrefs)
    return (
        f"{_XML_HEAD}"
        '<c:calendar-multiget xmlns:d="DAV:" '
        'xmlns:c="urn:ietf:params:xml:ns:caldav">'
        "<d:prop><d:getetag/><c:calendar-data/></d:prop>"
        f"{items}</c:calendar-multiget>"
    )


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


class XmlError(ValueError):
    """The server returned XML we could not parse."""


def _fromstring(text: str) -> ET.Element:
    try:
        return _SafeET.fromstring(text)
    except (ET.ParseError, ValueError) as err:
        raise XmlError(f"Invalid XML from server: {err}") from err


def parse_multistatus(text: str) -> list[tuple[str, dict[str, ET.Element]]]:
    """Return ``[(href, {qualified-tag: element})]`` for 200-OK properties."""
    root = _fromstring(text)
    out: list[tuple[str, dict[str, ET.Element]]] = []
    for resp in root.iter(_d("response")):
        href_el = resp.find(_d("href"))
        href = (href_el.text or "").strip() if href_el is not None else ""
        if not href:
            continue
        props: dict[str, ET.Element] = {}
        for propstat in resp.findall(_d("propstat")):
            status = propstat.findtext(_d("status")) or ""
            if " 200" not in status:
                continue
            prop = propstat.find(_d("prop"))
            if prop is None:
                continue
            for child in prop:
                props[child.tag] = child
        out.append((href, props))
    return out


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _href_of(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    href = el.find(_d("href"))
    value = _text(href)
    return value or None


def parse_sync_token(text: str) -> str | None:
    """Return the collection's ctag (or sync-token) if the server exposes one."""
    for _href, props in parse_multistatus(text):
        for tag in (_cs("getctag"), _d("sync-token")):
            value = _text(props.get(tag))
            if value:
                return value
    return None


def parse_etags(text: str) -> dict[str, str]:
    """Return ``{href: etag}`` for calendar object resources."""
    etags: dict[str, str] = {}
    for href, props in parse_multistatus(text):
        etag = _text(props.get(_d("getetag")))
        if etag and not href.endswith("/"):
            etags[href] = etag
    return etags


def parse_calendar_data(text: str) -> dict[str, tuple[str, str]]:
    """Return ``{href: (etag, ics_text)}`` from a multiget/query response."""
    data: dict[str, tuple[str, str]] = {}
    for href, props in parse_multistatus(text):
        ics = props.get(_c("calendar-data"))
        if ics is None or not (ics.text or "").strip():
            continue
        data[href] = (_text(props.get(_d("getetag"))), ics.text or "")
    return data


@dataclass
class DiscoveryItem:
    """A resource returned by a discovery PROPFIND."""

    href: str
    is_calendar: bool = False
    displayname: str = ""
    principal: str | None = None
    home: str | None = None
    components: set[str] | None = None  # None = server did not say
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def supports_events(self) -> bool:
        return self.components is None or "VEVENT" in self.components


def parse_discovery(text: str) -> list[DiscoveryItem]:
    """Parse a discovery PROPFIND response."""
    items: list[DiscoveryItem] = []
    for href, props in parse_multistatus(text):
        rtype = props.get(_d("resourcetype"))
        is_calendar = rtype is not None and rtype.find(_c("calendar")) is not None
        comp_set = props.get(_c("supported-calendar-component-set"))
        components: set[str] | None = None
        if comp_set is not None:
            components = {
                (c.get("name") or "").upper() for c in comp_set.findall(_c("comp"))
            }
        items.append(
            DiscoveryItem(
                href=href,
                is_calendar=is_calendar,
                displayname=_text(props.get(_d("displayname"))),
                principal=_href_of(props.get(_d("current-user-principal"))),
                home=_href_of(props.get(_c("calendar-home-set"))),
                components=components,
            )
        )
    return items
