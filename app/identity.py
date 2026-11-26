"""Stable restaurant identity from name and address."""

import hashlib

from app.errors import IdentityCollision


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def display_text(value: str) -> str:
    """Trim for display. Case is preserved."""
    return value.strip()


def identity_key(name: str, address: str) -> str | None:
    """Return a dedup key, or None when name or address is blank."""
    normalized_name = _normalize(name)
    normalized_address = _normalize(address)
    if not normalized_name or not normalized_address:
        return None
    return f"{normalized_name}|{normalized_address}"


def restaurant_id(name: str, address: str) -> str:
    key = identity_key(name, address)
    if key is None:
        raise ValueError("name and address are required to build an id")
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def register_identity(seen: dict[str, str], name: str, address: str) -> str:
    """Record an id. Fail if a different name and address produce the same id."""
    key = identity_key(name, address)
    if key is None:
        raise ValueError("name and address are required to build an id")
    new_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
    previous = seen.get(new_id)
    if previous is not None and previous != key:
        raise IdentityCollision(
            f"id {new_id} already belongs to a different restaurant"
        )
    seen[new_id] = key
    return new_id
