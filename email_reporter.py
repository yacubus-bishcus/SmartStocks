"""Utility helpers for sending SmartStocks reports via email."""
from __future__ import annotations

import logging
import mimetypes
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SMTPSettings:
    """Configuration required to connect to an SMTP server."""

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True


def _attach_files(message: EmailMessage, attachments: Iterable[Path]) -> None:
    for path in attachments:
        file_path = Path(path)
        if not file_path.exists():
            logger.warning("Attachment %s does not exist and will be skipped.", file_path)
            continue

        ctype, encoding = mimetypes.guess_type(file_path.name)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        with file_path.open("rb") as file_handle:
            message.add_attachment(
                file_handle.read(),
                maintype=maintype,
                subtype=subtype,
                filename=file_path.name,
            )


def send_email_report(
    settings: SMTPSettings,
    subject: str,
    body: str,
    recipients: Iterable[str],
    attachments: Optional[Iterable[Path]] = None,
) -> None:
    """Send an email containing the SmartStocks report."""

    recipients = list(recipients)
    if not recipients:
        raise ValueError("At least one recipient email address must be provided.")

    sender = settings.username
    if not sender:
        raise ValueError("An email sender must be provided via SMTP settings.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    if attachments:
        _attach_files(message, attachments)

    logger.info("Connecting to SMTP server %s:%s", settings.host, settings.port)
    with smtplib.SMTP(settings.host, settings.port) as server:
        server.ehlo()
        if settings.use_tls:
            server.starttls()
            server.ehlo()
        if settings.username and settings.password:
            server.login(settings.username, settings.password)
        server.send_message(message)
    logger.info("Email successfully sent to %s", ", ".join(recipients))
