"""Contains Error classes for the web support package."""

from __future__ import annotations


class DocumentNotFoundError(Exception):
    pass


class UserNotAuthorizedError(Exception):
    pass


class CommentNotAllowedError(Exception):
    pass


class NullSearchException(Exception):
    pass
