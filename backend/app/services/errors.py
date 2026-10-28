"""Domain errors.

Services raise these instead of ``HTTPException`` so the rules stay independent
of the transport; ``app.main`` registers one handler that turns them into JSON
error responses with the right status code.
"""

from __future__ import annotations


class AppError(Exception):
    status_code = 422


class Invalid(AppError):
    status_code = 422


class NotFound(AppError):
    status_code = 404


class Conflict(AppError):
    status_code = 409
