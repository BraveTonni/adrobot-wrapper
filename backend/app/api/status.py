"""HTTP-статусы, используемые API."""

from enum import IntEnum


class HttpStatus(IntEnum):
    CREATED = 201
    NOT_FOUND = 404
    CONFLICT = 409
    BAD_GATEWAY = 502
