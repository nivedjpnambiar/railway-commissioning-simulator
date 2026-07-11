from __future__ import annotations

from collections import deque

from .models import BusMessage


class VirtualCanBus:
    """Small deterministic CAN-style message log used by the simulator.

    This is intentionally a software model, not a claim of physical CAN hardware.
    """

    def __init__(self, max_messages: int = 500) -> None:
        self.online = True
        self._messages: deque[BusMessage] = deque(maxlen=max_messages)

    def send(
        self,
        *,
        timestamp_s: float,
        message_id: int,
        signal: str,
        value: object,
        source: str,
    ) -> bool:
        if not self.online:
            return False
        self._messages.append(
            BusMessage(
                timestamp_s=timestamp_s,
                message_id=message_id,
                signal=signal,
                value=value,
                source=source,
            )
        )
        return True

    def messages(self, limit: int | None = None) -> list[BusMessage]:
        data = list(self._messages)
        return data[-limit:] if limit is not None else data

    def clear(self) -> None:
        self._messages.clear()
