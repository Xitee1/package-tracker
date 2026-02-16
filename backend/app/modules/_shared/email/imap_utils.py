import logging
from dataclasses import dataclass

from aioimaplib import IMAP4, IMAP4_SSL

logger = logging.getLogger(__name__)


@dataclass
class ImapTestResult:
    success: bool
    message: str
    idle_supported: bool | None


@dataclass
class ImapFoldersResult:
    folders: list[str]
    idle_supported: bool


async def _connect(
    host: str, port: int, user: str, password: str, use_ssl: bool,
) -> IMAP4_SSL | IMAP4:
    """Connect and authenticate to an IMAP server."""
    if use_ssl:
        imap = IMAP4_SSL(host=host, port=port)
    else:
        imap = IMAP4(host=host, port=port)
    await imap.wait_hello_from_server()
    await imap.login(user, password)
    return imap


def _parse_folder_list(raw_folders: list[bytes | str]) -> list[str]:
    """Parse IMAP LIST response lines into folder name strings.

    aioimaplib returns response lines as bytes. Handles formats like:
        b'(\\HasNoChildren) "/" "INBOX"'
        b'(\\HasNoChildren) "." INBOX'
    """
    folders = []
    for item in raw_folders:
        line = item.decode() if isinstance(item, bytes) else item
        parts = line.rsplit('" "', 1)
        if len(parts) == 2:
            folders.append(parts[1].strip('"'))
        else:
            parts = line.rsplit(" ", 1)
            folders.append(parts[-1].strip('"'))
    return folders


async def test_imap_connection(
    host: str, port: int, user: str, password: str, use_ssl: bool,
) -> ImapTestResult:
    """Test IMAP connection and return whether IDLE is supported."""
    try:
        imap = await _connect(host, port, user, password, use_ssl)
        idle_supported = imap.has_capability("IDLE")
        await imap.logout()
        return ImapTestResult(
            success=True,
            message="Connection successful",
            idle_supported=idle_supported,
        )
    except Exception as e:
        return ImapTestResult(success=False, message=str(e), idle_supported=None)


async def list_imap_folders(
    host: str, port: int, user: str, password: str, use_ssl: bool,
) -> ImapFoldersResult:
    """List available IMAP folders and check IDLE capability."""
    imap = await _connect(host, port, user, password, use_ssl)
    try:
        idle_supported = imap.has_capability("IDLE")
        result = await imap.list('""', "*")
        raw_folders = result.lines[:-1] if result.lines else []
        folders = _parse_folder_list(raw_folders)
        return ImapFoldersResult(folders=folders, idle_supported=idle_supported)
    finally:
        try:
            await imap.logout()
        except Exception:
            pass
