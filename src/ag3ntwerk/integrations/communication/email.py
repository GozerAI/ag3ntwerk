"""
Email Integration for ag3ntwerk.

Provides IMAP/SMTP email handling for reading and sending emails.

Requirements:
    - Standard library (imaplib, smtplib, email)
    - Optional: pip install aiosmtplib aioimaplib

Email is ideal for:
    - Agent communication
    - Automated notifications
    - Email summarization and filtering
    - Newsletter and report distribution
"""

import asyncio
import email
import imaplib
import logging
import smtplib
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Configuration for email integration."""

    # IMAP settings
    imap_host: str = ""
    imap_port: int = 993
    imap_ssl: bool = True

    # SMTP settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_ssl: bool = False
    smtp_tls: bool = True

    # Authentication
    username: str = ""
    password: str = ""

    # Defaults
    from_address: str = ""
    from_name: str = ""


@dataclass
class EmailAddress:
    """Represents an email address."""

    address: str
    name: str = ""

    def __str__(self):
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address


@dataclass
class EmailAttachment:
    """Represents an email attachment."""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class EmailMessage:
    """Represents an email message."""

    subject: str
    body: str
    from_address: Optional[EmailAddress] = None
    to_addresses: List[EmailAddress] = field(default_factory=list)
    cc_addresses: List[EmailAddress] = field(default_factory=list)
    bcc_addresses: List[EmailAddress] = field(default_factory=list)
    reply_to: Optional[EmailAddress] = None
    html_body: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)
    message_id: Optional[str] = None
    date: Optional[datetime] = None
    headers: Dict[str, str] = field(default_factory=dict)
    is_read: bool = False
    is_starred: bool = False
    labels: List[str] = field(default_factory=list)
    uid: Optional[str] = None

    def add_attachment(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> "EmailMessage":
        """Add an attachment."""
        self.attachments.append(
            EmailAttachment(
                filename=filename,
                content=content,
                content_type=content_type,
            )
        )
        return self

    def add_attachment_from_file(self, path: str) -> "EmailMessage":
        """Add an attachment from a file path."""
        p = Path(path)
        with open(p, "rb") as f:
            content = f.read()

        import mimetypes

        content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"

        return self.add_attachment(p.name, content, content_type)


@dataclass
class EmailFilter:
    """Filter criteria for searching emails."""

    subject: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    since: Optional[datetime] = None
    before: Optional[datetime] = None
    is_unread: Optional[bool] = None
    is_starred: Optional[bool] = None
    has_attachment: Optional[bool] = None
    body_contains: Optional[str] = None
    folder: str = "INBOX"

    def to_imap_criteria(self) -> str:
        """Convert to IMAP search criteria."""
        criteria = []

        if self.is_unread is True:
            criteria.append("UNSEEN")
        elif self.is_unread is False:
            criteria.append("SEEN")

        if self.is_starred:
            criteria.append("FLAGGED")

        if self.subject:
            criteria.append(f'SUBJECT "{self.subject}"')

        if self.from_address:
            criteria.append(f'FROM "{self.from_address}"')

        if self.to_address:
            criteria.append(f'TO "{self.to_address}"')

        if self.since:
            date_str = self.since.strftime("%d-%b-%Y")
            criteria.append(f"SINCE {date_str}")

        if self.before:
            date_str = self.before.strftime("%d-%b-%Y")
            criteria.append(f"BEFORE {date_str}")

        if self.body_contains:
            criteria.append(f'BODY "{self.body_contains}"')

        return " ".join(criteria) if criteria else "ALL"


class EmailIntegration:
    """
    Integration for email via IMAP/SMTP.

    Provides email reading, sending, and management.

    Example:
        integration = EmailIntegration(EmailConfig(
            imap_host="imap.gmail.com",
            smtp_host="smtp.gmail.com",
            username="user@gmail.com",
            password="app-password",
        ))

        # Read unread emails
        emails = await integration.get_emails(
            EmailFilter(is_unread=True)
        )

        # Send an email
        await integration.send(EmailMessage(
            subject="Weekly Report",
            body="Here's the weekly summary...",
            to_addresses=[EmailAddress("team@example.com")],
        ))
    """

    def __init__(self, config: EmailConfig):
        """Initialize email integration."""
        self.config = config
        self._imap: Optional[imaplib.IMAP4_SSL] = None
        self._smtp: Optional[smtplib.SMTP] = None

    def _get_imap(self) -> imaplib.IMAP4_SSL:
        """Get IMAP connection."""
        if self._imap is None:
            if self.config.imap_ssl:
                self._imap = imaplib.IMAP4_SSL(
                    self.config.imap_host,
                    self.config.imap_port,
                )
            else:
                self._imap = imaplib.IMAP4(
                    self.config.imap_host,
                    self.config.imap_port,
                )

            self._imap.login(self.config.username, self.config.password)

        return self._imap

    def _get_smtp(self) -> smtplib.SMTP:
        """Get SMTP connection."""
        if self._smtp is None:
            if self.config.smtp_ssl:
                self._smtp = smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                )
            else:
                self._smtp = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                )

            if self.config.smtp_tls:
                self._smtp.starttls()

            self._smtp.login(self.config.username, self.config.password)

        return self._smtp

    async def send(self, message: EmailMessage) -> bool:
        """
        Send an email.

        Args:
            message: EmailMessage to send

        Returns:
            True if successful
        """
        loop = asyncio.get_running_loop()

        def _send():
            msg = MIMEMultipart("mixed")

            # Headers
            from_addr = message.from_address or EmailAddress(
                self.config.from_address,
                self.config.from_name,
            )
            msg["From"] = str(from_addr)
            msg["To"] = ", ".join(str(a) for a in message.to_addresses)
            msg["Subject"] = message.subject

            if message.cc_addresses:
                msg["Cc"] = ", ".join(str(a) for a in message.cc_addresses)

            if message.reply_to:
                msg["Reply-To"] = str(message.reply_to)

            for key, value in message.headers.items():
                msg[key] = value

            # Body
            if message.html_body:
                alt = MIMEMultipart("alternative")
                alt.attach(MIMEText(message.body, "plain"))
                alt.attach(MIMEText(message.html_body, "html"))
                msg.attach(alt)
            else:
                msg.attach(MIMEText(message.body, "plain"))

            # Attachments
            for attachment in message.attachments:
                part = MIMEBase(*attachment.content_type.split("/", 1))
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment.filename}",
                )
                msg.attach(part)

            # Recipients
            recipients = [a.address for a in message.to_addresses]
            recipients += [a.address for a in message.cc_addresses]
            recipients += [a.address for a in message.bcc_addresses]

            smtp = self._get_smtp()
            smtp.sendmail(from_addr.address, recipients, msg.as_string())

        await loop.run_in_executor(None, _send)
        return True

    async def get_emails(
        self,
        filter: Optional[EmailFilter] = None,
        limit: int = 50,
    ) -> List[EmailMessage]:
        """
        Get emails matching filter.

        Args:
            filter: Email filter criteria
            limit: Maximum emails to retrieve

        Returns:
            List of EmailMessages
        """
        filter = filter or EmailFilter()
        loop = asyncio.get_running_loop()

        def _fetch():
            imap = self._get_imap()
            imap.select(filter.folder)

            criteria = filter.to_imap_criteria()
            _, message_numbers = imap.search(None, criteria)

            if not message_numbers[0]:
                return []

            # Get latest emails first
            ids = message_numbers[0].split()[-limit:]
            ids.reverse()

            messages = []
            for msg_id in ids:
                _, msg_data = imap.fetch(msg_id, "(RFC822 FLAGS)")
                if not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                # Parse flags
                flags = msg_data[0][0].decode() if msg_data[0][0] else ""
                is_read = "\\Seen" in flags
                is_starred = "\\Flagged" in flags

                # Parse addresses
                from_addr = self._parse_address(email_message.get("From", ""))
                to_addrs = self._parse_addresses(email_message.get("To", ""))
                cc_addrs = self._parse_addresses(email_message.get("Cc", ""))

                # Parse date
                date_str = email_message.get("Date", "")
                date = None
                if date_str:
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except Exception as e:
                        logger.debug("Failed to parse email date '%s': %s", date_str, e)

                # Parse body
                body, html_body = self._extract_body(email_message)

                # Parse attachments
                attachments = self._extract_attachments(email_message)

                messages.append(
                    EmailMessage(
                        subject=email_message.get("Subject", ""),
                        body=body,
                        html_body=html_body,
                        from_address=from_addr,
                        to_addresses=to_addrs,
                        cc_addresses=cc_addrs,
                        message_id=email_message.get("Message-ID"),
                        date=date,
                        is_read=is_read,
                        is_starred=is_starred,
                        attachments=attachments,
                        uid=msg_id.decode(),
                    )
                )

            return messages

        return await loop.run_in_executor(None, _fetch)

    async def get_folders(self) -> List[str]:
        """Get list of email folders."""
        loop = asyncio.get_running_loop()

        def _list():
            imap = self._get_imap()
            _, folders = imap.list()
            folder_names = []
            for folder in folders:
                if folder:
                    name = folder.decode().split('"')[-2]
                    folder_names.append(name)
            return folder_names

        return await loop.run_in_executor(None, _list)

    async def mark_as_read(
        self,
        uid: str,
        folder: str = "INBOX",
    ) -> bool:
        """Mark an email as read."""
        loop = asyncio.get_running_loop()

        def _mark():
            imap = self._get_imap()
            imap.select(folder)
            imap.store(uid.encode(), "+FLAGS", "\\Seen")

        await loop.run_in_executor(None, _mark)
        return True

    async def mark_as_unread(
        self,
        uid: str,
        folder: str = "INBOX",
    ) -> bool:
        """Mark an email as unread."""
        loop = asyncio.get_running_loop()

        def _mark():
            imap = self._get_imap()
            imap.select(folder)
            imap.store(uid.encode(), "-FLAGS", "\\Seen")

        await loop.run_in_executor(None, _mark)
        return True

    async def star(
        self,
        uid: str,
        folder: str = "INBOX",
    ) -> bool:
        """Star/flag an email."""
        loop = asyncio.get_running_loop()

        def _star():
            imap = self._get_imap()
            imap.select(folder)
            imap.store(uid.encode(), "+FLAGS", "\\Flagged")

        await loop.run_in_executor(None, _star)
        return True

    async def move_to_folder(
        self,
        uid: str,
        source_folder: str,
        dest_folder: str,
    ) -> bool:
        """Move an email to a different folder."""
        loop = asyncio.get_running_loop()

        def _move():
            imap = self._get_imap()
            imap.select(source_folder)
            imap.copy(uid.encode(), dest_folder)
            imap.store(uid.encode(), "+FLAGS", "\\Deleted")
            imap.expunge()

        await loop.run_in_executor(None, _move)
        return True

    async def delete(
        self,
        uid: str,
        folder: str = "INBOX",
    ) -> bool:
        """Delete an email (move to trash)."""
        return await self.move_to_folder(uid, folder, "[Gmail]/Trash")

    async def get_unread_count(self, folder: str = "INBOX") -> int:
        """Get count of unread emails."""
        loop = asyncio.get_running_loop()

        def _count():
            imap = self._get_imap()
            imap.select(folder)
            _, messages = imap.search(None, "UNSEEN")
            if messages[0]:
                return len(messages[0].split())
            return 0

        return await loop.run_in_executor(None, _count)

    def _parse_address(self, addr_str: str) -> Optional[EmailAddress]:
        """Parse an email address string."""
        if not addr_str:
            return None

        name, address = email.utils.parseaddr(addr_str)
        if address:
            return EmailAddress(address=address, name=name)
        return None

    def _parse_addresses(self, addr_str: str) -> List[EmailAddress]:
        """Parse multiple email addresses."""
        if not addr_str:
            return []

        addresses = []
        for addr in addr_str.split(","):
            parsed = self._parse_address(addr.strip())
            if parsed:
                addresses.append(parsed)
        return addresses

    def _extract_body(self, msg: email.message.Message) -> Tuple[str, Optional[str]]:
        """Extract plain text and HTML body from email."""
        body = ""
        html_body = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                    except (UnicodeDecodeError, AttributeError):
                        body = str(part.get_payload())

                elif content_type == "text/html":
                    try:
                        html_body = part.get_payload(decode=True).decode()
                    except (UnicodeDecodeError, AttributeError):
                        html_body = str(part.get_payload())
        else:
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True).decode()
            except (UnicodeDecodeError, AttributeError):
                payload = str(msg.get_payload())

            if content_type == "text/html":
                html_body = payload
            else:
                body = payload

        return body, html_body

    def _extract_attachments(self, msg: email.message.Message) -> List[EmailAttachment]:
        """Extract attachments from email."""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in disposition:
                    filename = part.get_filename() or "attachment"
                    content_type = part.get_content_type()
                    try:
                        content = part.get_payload(decode=True)
                    except (UnicodeDecodeError, AttributeError):
                        content = part.get_payload().encode()

                    attachments.append(
                        EmailAttachment(
                            filename=filename,
                            content=content,
                            content_type=content_type,
                        )
                    )

        return attachments

    def close(self):
        """Close connections."""
        if self._imap:
            try:
                self._imap.logout()
            except Exception as e:
                logger.debug("Error closing IMAP connection: %s", e)
            self._imap = None

        if self._smtp:
            try:
                self._smtp.quit()
            except Exception as e:
                logger.debug("Error closing SMTP connection: %s", e)
            self._smtp = None

    def __del__(self):
        self.close()
