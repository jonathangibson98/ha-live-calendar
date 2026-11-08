"""Network layer: fetch calendar data from an ICS feed or a CalDAV server."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import logging
from urllib.parse import urljoin, urlparse

import aiohttp

from .caldav_xml import (
    PROPFIND_DISCOVERY,
    PROPFIND_ETAGS,
    PROPFIND_TOKEN,
    XmlError,
    build_multiget,
    parse_calendar_data,
    parse_discovery,
    parse_etags,
    parse_sync_token,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)
_MULTIGET_CHUNK = 50


class SourceError(Exception):
    """Could not fetch data from the calendar source."""


class AuthError(SourceError):
    """The server rejected the credentials."""


@dataclass
class SourceResult:
    """Outcome of one fetch."""

    changed: bool
    texts: list[str] = field(default_factory=list)


def normalize_url(url: str) -> str:
    """Turn webcal:// links into https:// links and strip whitespace."""
    url = url.strip()
    lower = url.lower()
    if lower.startswith("webcal://"):
        return "https://" + url[len("webcal://") :]
    if lower.startswith("webcals://"):
        return "https://" + url[len("webcals://") :]
    return url


async def dav_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    body: str,
    depth: str,
    auth: aiohttp.BasicAuth | None,
) -> str:
    """Send a WebDAV request and return the response text."""
    headers = {"Content-Type": "application/xml; charset=utf-8", "Depth": depth}
    try:
        async with session.request(
            method,
            url,
            data=body.encode("utf-8"),
            headers=headers,
            auth=auth,
            timeout=_TIMEOUT,
        ) as resp:
            if resp.status in (401, 403):
                raise AuthError(f"HTTP {resp.status}")
            if resp.status not in (200, 207):
                raise SourceError(f"HTTP {resp.status} from {method} {url}")
            return await resp.text(errors="replace")
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        raise SourceError(f"Cannot reach server: {err}") from err


class IcsSource:
    """Poll an ``.ics`` URL using conditional requests and a content hash.

    A fetch that returns HTTP 304 (or identical bytes) costs almost nothing, so
    it is cheap to poll every few seconds.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        url: str,
        auth: aiohttp.BasicAuth | None,
    ) -> None:
        self._session = session
        self._url = normalize_url(url)
        self._auth = auth
        self._etag: str | None = None
        self._last_modified: str | None = None
        self._digest: str | None = None
        self._texts: list[str] = []

    async def fetch(self, force: bool = False) -> SourceResult:
        headers = {"Accept": "text/calendar, text/plain;q=0.5, */*;q=0.1"}
        if not force and self._texts:
            if self._etag:
                headers["If-None-Match"] = self._etag
            if self._last_modified:
                headers["If-Modified-Since"] = self._last_modified
        try:
            async with self._session.get(
                self._url, headers=headers, auth=self._auth, timeout=_TIMEOUT
            ) as resp:
                if resp.status == 304 and self._texts:
                    return SourceResult(False, self._texts)
                if resp.status in (401, 403):
                    raise AuthError(f"HTTP {resp.status}")
                if resp.status >= 400:
                    raise SourceError(f"HTTP {resp.status}")
                body = await resp.text(errors="replace")
                etag = resp.headers.get("ETag")
                last_modified = resp.headers.get("Last-Modified")
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SourceError(f"Cannot reach server: {err}") from err

        if "BEGIN:VCALENDAR" not in body.upper():
            raise SourceError("The URL did not return an iCalendar (.ics) file")

        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self._etag, self._last_modified = etag, last_modified
        if digest == self._digest and self._texts:
            return SourceResult(False, self._texts)
        self._digest = digest
        self._texts = [body]
        return SourceResult(True, self._texts)


class CaldavSource:
    """Incrementally sync one CalDAV calendar collection.

    Each poll first asks for the collection's ctag/sync-token (one tiny
    request). Only when it changed do we list ETags and download the resources
    that are new or modified.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        url: str,
        auth: aiohttp.BasicAuth | None,
    ) -> None:
        self._session = session
        self._url = url
        self._auth = auth
        self._token: str | None = None
        self._etags: dict[str, str] = {}
        self._data: dict[str, str] = {}
        self._loaded = False

    def _texts(self) -> list[str]:
        return list(self._data.values())

    async def _get_token(self) -> str | None:
        try:
            text = await dav_request(
                self._session, "PROPFIND", self._url, PROPFIND_TOKEN, "0", self._auth
            )
            return parse_sync_token(text)
        except XmlError:
            return None

    async def fetch(self, force: bool = False) -> SourceResult:
        token = await self._get_token()
        if not force and self._loaded and token is not None and token == self._token:
            return SourceResult(False, self._texts())

        try:
            etag_text = await dav_request(
                self._session, "PROPFIND", self._url, PROPFIND_ETAGS, "1", self._auth
            )
            etags = parse_etags(etag_text)
        except XmlError as err:
            raise SourceError(str(err)) from err

        if force:
            wanted = list(etags)
        else:
            wanted = [h for h, e in etags.items() if self._etags.get(h) != e]
        removed = [h for h in self._data if h not in etags]

        fetched: dict[str, tuple[str, str]] = {}
        for i in range(0, len(wanted), _MULTIGET_CHUNK):
            chunk = wanted[i : i + _MULTIGET_CHUNK]
            try:
                text = await dav_request(
                    self._session,
                    "REPORT",
                    self._url,
                    build_multiget(chunk),
                    "1",
                    self._auth,
                )
                fetched.update(parse_calendar_data(text))
            except XmlError as err:
                raise SourceError(str(err)) from err

        changed = bool(removed) or not self._loaded
        for href, (etag, ics) in fetched.items():
            if self._data.get(href) != ics:
                changed = True
            self._data[href] = ics
            self._etags[href] = etag or etags.get(href, "")
        for href in removed:
            self._data.pop(href, None)
            self._etags.pop(href, None)

        # Only remember the token when every wanted resource arrived, so a
        # partial download is retried on the next poll.
        complete = all(h in self._data for h in etags)
        self._token = token if complete else None
        self._loaded = True
        return SourceResult(changed, self._texts())


@dataclass
class DiscoveredCalendar:
    """A calendar collection found on a CalDAV server."""

    url: str
    name: str


async def discover_calendars(
    session: aiohttp.ClientSession,
    url: str,
    auth: aiohttp.BasicAuth | None,
) -> list[DiscoveredCalendar]:
    """Find calendars from a server root, principal, home-set or calendar URL."""
    url = normalize_url(url)
    try:
        items = parse_discovery(
            await dav_request(session, "PROPFIND", url, PROPFIND_DISCOVERY, "0", auth)
        )
    except XmlError as err:
        raise SourceError(str(err)) from err

    first = items[0] if items else None
    if first and first.is_calendar and first.supports_events:
        return [DiscoveredCalendar(url, first.displayname or "Calendar")]

    principal = first.principal if first else None
    home = first.home if first else None
    base = url

    if not home and not principal:
        parsed = urlparse(url)
        well_known = f"{parsed.scheme}://{parsed.netloc}/.well-known/caldav"
        try:
            items = parse_discovery(
                await dav_request(
                    session, "PROPFIND", well_known, PROPFIND_DISCOVERY, "0", auth
                )
            )
        except (SourceError, XmlError) as err:
            if isinstance(err, AuthError):
                raise
            items = []
        if items:
            principal, home = items[0].principal, items[0].home
            base = well_known

    if not home and principal:
        principal_url = urljoin(base, principal)
        try:
            items = parse_discovery(
                await dav_request(
                    session, "PROPFIND", principal_url, PROPFIND_DISCOVERY, "0", auth
                )
            )
        except XmlError as err:
            raise SourceError(str(err)) from err
        home = items[0].home if items else None
        base = principal_url

    if not home:
        return []

    home_url = urljoin(base, home)
    try:
        items = parse_discovery(
            await dav_request(
                session, "PROPFIND", home_url, PROPFIND_DISCOVERY, "1", auth
            )
        )
    except XmlError as err:
        raise SourceError(str(err)) from err

    return [
        DiscoveredCalendar(urljoin(home_url, item.href), item.displayname or "Calendar")
        for item in items
        if item.is_calendar and item.supports_events
    ]
