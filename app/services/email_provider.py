from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    recipient: str
    subject: str
    body: str


class FakeEmailProvider:
    """Test email provider that records messages without sending them."""

    def __init__(self) -> None:
        self.sent_messages: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        """Record the message as successfully delivered by the fake provider."""
        self.sent_messages.append(message)
