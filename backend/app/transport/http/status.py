"""HTTP-статусы, используемые API."""

from enum import IntEnum


class HttpStatus(IntEnum):
    CREATED = 201
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
