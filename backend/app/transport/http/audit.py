"""HTTP identity metadata used by audit records."""

from fastapi import Request


def audit_actor(request: Request) -> str:
    user = request.headers.get("X-User", "").strip()
    if user:
        return " ".join(user.split())[:150]
    if request.client is not None and request.client.host:
        return request.client.host[:150]
    return "unknown"
