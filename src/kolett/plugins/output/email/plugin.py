import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

from kolett.plugins.base import CallbackPlugin
from kolett.protocol import DeliveryOutput

logger = logging.getLogger("kolett.plugins.output.email")


class Plugin(CallbackPlugin):
    """
    Email Output Plugin for Kolett.
    Sends the Markdown manifest as an email notification.
    """

    def run(self, delivery_output: DeliveryOutput) -> bool:
        smtp_server = self.config.get("smtp_server", "localhost")
        smtp_port = self.config.get("smtp_port", 587)
        smtp_user = self.config.get("smtp_user")
        smtp_pass = self.config.get("smtp_password")
        use_tls = self.config.get("use_tls", True)

        sender = self.config.get("sender", "kolett@bottleshipvfx.com")
        recipients = self.config.get("recipients", [])

        if not recipients:
            logger.error("No recipients provided for email plugin.")
            return False

        subject = f"Delivery Manifest: {delivery_output.package_name}"

        # Read manifest content if it exists
        manifest_content = ""
        if Path(delivery_output.manifest_path).exists():
            with open(delivery_output.manifest_path, "r") as f:
                manifest_content = f.read()
        else:
            manifest_content = f"Delivery summary: {delivery_output.summary}"

        if self.dry_run:
            logger.info(
                f"DRY RUN: Email would be sent to {recipients} via {smtp_server}"
            )
            logger.info(f"Subject: {subject}")
            return True

        # Construct Email
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        # Attach the markdown content as plain text
        # (Many modern email clients render MD or at least keep it readable)
        msg.attach(MIMEText(manifest_content, "plain"))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)

                server.send_message(msg)

            logger.info(f"Email notification sent to {len(recipients)} recipients.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
