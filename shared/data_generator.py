from __future__ import annotations

import random
import string
import time
import uuid

from shared.models import Item, LargeMessage, SmallMessage

_ADJECTIVES = ["fast", "slow", "bright", "dark", "heavy", "light", "warm", "cool", "smart", "solid"]
_NOUNS = ["widget", "gadget", "device", "module", "component", "sensor", "unit", "board", "chip", "node"]
_TAGS = ["electronics", "hardware", "iot", "sensor", "network", "cloud", "edge", "embedded", "wireless", "digital"]

# Canonical payload sizes (KB) for the "large" scenario. Single source of truth
# for ALL load tests — every protocol must exercise exactly these sizes, so that
# cross-protocol comparisons cover identical payloads.
LARGE_PAYLOAD_BASE_KB = 50
LARGE_PAYLOAD_EXTENDED_KB = 100


def _random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_small_message() -> SmallMessage:
    payload_len = random.randint(80, 400)
    return SmallMessage(
        id=str(uuid.uuid4()),
        timestamp=time.time(),
        source=f"service-{random.randint(1, 10)}",
        payload=_random_string(payload_len),
    )


def generate_large_message(size_kb: int = 50) -> LargeMessage:
    # Each item serialises to roughly 300-400 bytes; adjust count accordingly
    target_bytes = size_kb * 1024
    approx_item_size = 350
    count = max(1, target_bytes // approx_item_size)

    items: list[Item] = []
    for i in range(count):
        adj = random.choice(_ADJECTIVES)
        noun = random.choice(_NOUNS)
        items.append(
            Item(
                name=f"{adj}-{noun}-{i}",
                description=_random_string(120),
                value=round(random.uniform(0.01, 9999.99), 2),
                tags=random.sample(_TAGS, k=random.randint(1, 5)),
                metadata={
                    "sku": _random_string(8),
                    "warehouse": f"WH-{random.randint(1, 20)}",
                    "batch": _random_string(6),
                },
            )
        )

    return LargeMessage(
        id=str(uuid.uuid4()),
        timestamp=time.time(),
        items=items,
    )


def generate_batch(count: int, message_type: str) -> list:
    if message_type == "small":
        return [generate_small_message() for _ in range(count)]
    elif message_type == "large":
        return [generate_large_message() for _ in range(count)]
    else:
        raise ValueError(f"Unknown message_type: {message_type!r}")
