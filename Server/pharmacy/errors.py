"""Typed application errors (Stage 2).

Each error has a message that is safe to show to a user (English, professional)
and an internal detail that is written to the log only.
Use these in services. Routes turn them into friendly pages or JSON.
"""


class MediGenError(Exception):
    """Base class. `user_message` is shown to the user; `detail` is for the log only."""
    default_message = 'Something went wrong. Please try again.'

    def __init__(self, user_message=None, detail=None):
        self.user_message = user_message or self.default_message
        self.detail = detail or self.user_message
        super().__init__(self.user_message)


class ValidationError(MediGenError):
    default_message = 'Please check the entered values and try again.'


class NotFoundError(MediGenError):
    default_message = 'The requested item was not found.'


class PermissionDenied(MediGenError):
    default_message = 'You do not have permission for this action.'


class StockError(MediGenError):
    default_message = 'Not enough stock for this item. No changes were saved.'


class ConflictError(MediGenError):
    default_message = 'This record was changed by someone else. Please reload and try again.'


class PaymentError(MediGenError):
    default_message = 'The payment could not be recorded. No changes were saved.'


class ExternalServiceError(MediGenError):
    default_message = 'Service not available right now. Please try again later.'


class DatabaseError(MediGenError):
    default_message = 'A database error occurred. No changes were saved.'
