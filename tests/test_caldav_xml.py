"""Tests for the CalDAV XML helpers (no Home Assistant needed)."""

import pytest

import caldav_xml as x

CTAG = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">
 <d:response><d:href>/cal/personal/</d:href>
  <d:propstat><d:prop><cs:getctag>ctag-42</cs:getctag></d:prop>
  <d:status>HTTP/1.1 200 OK</d:status></d:propstat>
  <d:propstat><d:prop><d:sync-token/></d:prop>
  <d:status>HTTP/1.1 404 Not Found</d:status></d:propstat>
 </d:response></d:multistatus>"""

ETAGS = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
 <d:response><d:href>/cal/personal/</d:href>
  <d:propstat><d:prop><d:getcontenttype/></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
 <d:response><d:href>/cal/personal/a.ics</d:href>
  <d:propstat><d:prop><d:getetag>"e1"</d:getetag></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
 <d:response><d:href>/cal/personal/b.ics</d:href>
  <d:propstat><d:prop><d:getetag>"e2"</d:getetag></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
</d:multistatus>"""

MULTIGET = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
 <d:response><d:href>/cal/personal/a.ics</d:href>
  <d:propstat><d:prop><d:getetag>"e1"</d:getetag>
   <c:calendar-data>BEGIN:VCALENDAR
BEGIN:VEVENT
UID:a
END:VEVENT
END:VCALENDAR</c:calendar-data></d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
 <d:response><d:href>/cal/personal/gone.ics</d:href>
  <d:status>HTTP/1.1 404 Not Found</d:status></d:response>
</d:multistatus>"""

DISCOVERY_ROOT = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
 <d:response><d:href>/</d:href><d:propstat><d:prop>
  <d:current-user-principal><d:href>/principals/me/</d:href></d:current-user-principal>
 </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response></d:multistatus>"""

DISCOVERY_PRINCIPAL = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
 <d:response><d:href>/principals/me/</d:href><d:propstat><d:prop>
  <c:calendar-home-set><d:href>/calendars/me/</d:href></c:calendar-home-set>
 </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response></d:multistatus>"""

DISCOVERY_HOME = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
 <d:response><d:href>/calendars/me/</d:href><d:propstat><d:prop>
  <d:resourcetype><d:collection/></d:resourcetype></d:prop>
  <d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
 <d:response><d:href>/calendars/me/personal/</d:href><d:propstat><d:prop>
  <d:resourcetype><d:collection/><c:calendar/></d:resourcetype>
  <d:displayname>Personal</d:displayname>
  <c:supported-calendar-component-set><c:comp name="VEVENT"/><c:comp name="VTODO"/></c:supported-calendar-component-set>
 </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
 <d:response><d:href>/calendars/me/tasks/</d:href><d:propstat><d:prop>
  <d:resourcetype><d:collection/><c:calendar/></d:resourcetype>
  <d:displayname>Tasks</d:displayname>
  <c:supported-calendar-component-set><c:comp name="VTODO"/></c:supported-calendar-component-set>
 </d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
</d:multistatus>"""


def test_sync_token_prefers_ctag():
    assert x.parse_sync_token(CTAG) == "ctag-42"


def test_sync_token_missing():
    assert x.parse_sync_token(ETAGS) is None


def test_etags_skip_collection_itself():
    assert x.parse_etags(ETAGS) == {
        "/cal/personal/a.ics": '"e1"',
        "/cal/personal/b.ics": '"e2"',
    }


def test_calendar_data_ignores_404_entries():
    data = x.parse_calendar_data(MULTIGET)
    assert list(data) == ["/cal/personal/a.ics"]
    etag, ics = data["/cal/personal/a.ics"]
    assert etag == '"e1"'
    assert "UID:a" in ics


def test_build_multiget_escapes_hrefs():
    body = x.build_multiget(["/a&b.ics", "/c<d>.ics"])
    assert "/a&amp;b.ics" in body
    assert "/c&lt;d&gt;.ics" in body
    # And it must be well-formed XML.
    x.parse_multistatus  # noqa: B018  (import smoke)
    import xml.etree.ElementTree as ET

    ET.fromstring(body)


def test_discovery_chain():
    root = x.parse_discovery(DISCOVERY_ROOT)[0]
    assert root.principal == "/principals/me/"
    assert not root.is_calendar
    principal = x.parse_discovery(DISCOVERY_PRINCIPAL)[0]
    assert principal.home == "/calendars/me/"


def test_discovery_lists_only_event_calendars():
    items = x.parse_discovery(DISCOVERY_HOME)
    cals = [i for i in items if i.is_calendar and i.supports_events]
    assert [(c.href, c.displayname) for c in cals] == [
        ("/calendars/me/personal/", "Personal")
    ]


def test_unknown_component_set_counts_as_events():
    assert x.DiscoveryItem(href="/x", is_calendar=True).supports_events


def test_invalid_xml_raises():
    with pytest.raises(x.XmlError):
        x.parse_multistatus("<not-xml")
