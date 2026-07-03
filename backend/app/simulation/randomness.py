from __future__ import annotations

import hashlib
import random
from collections.abc import Hashable


def stable_rng(seed: int, *parts: Hashable) -> random.Random:
    key = ":".join([str(seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))
