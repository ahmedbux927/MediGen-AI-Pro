"""Routes: errors."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _error_page


# v88.00: E6 - one stable JSON error shape for API callers: {"error": {"code", "message"}}
def _api_error(code, message, status):
    return jsonify({'error': {'code': code, 'message': message}}), status


# v89.00: the remaining common HTTP errors get the same treatment as 404/500:
# a stable JSON shape for API callers, a friendly page (never a stack trace) for people.
_WEB_ERROR_TEXT = {
    400: ('Bad request', 'The request could not be read. Please go back and try again.'),
    403: ('Not allowed', 'You do not have permission to open this. If you think this is wrong, ask the Admin.'),
    405: ('Not allowed that way', 'This action needs the proper button or form. Please go back and use the page.'),
    413: ('File too large', 'The file is too large for the server. Please choose a smaller file.'),
    429: ('Too many requests', 'Please wait a minute and try again.'),
}


def _web_error(status):
    title, msg = _WEB_ERROR_TEXT.get(status, ('Error', 'Something went wrong. Please try again.'))
    html = (f"<div style='font-family:system-ui,sans-serif;max-width:520px;margin:60px auto;padding:24px'>"
            f"<h2>{status} - {title}</h2><p>{msg}</p>"
            f"<p><button onclick='location.reload()'>Try again</button> "
            f"<a href='/dashboard'>Back to Dashboard</a></p></div>")
    return html, status


def _make_web_error_handler(status):
    def handler(e):
        if request.path.startswith('/api/'):
            return _api_error(_WEB_ERROR_TEXT.get(status, ('Error', ''))[0].lower().replace(' ', '_'),
                              _WEB_ERROR_TEXT.get(status, ('', 'Something went wrong. Please try again.'))[1], status)
        return _web_error(status)
    return handler


for _code in (400, 403, 405, 413, 429):
    app.errorhandler(_code)(_make_web_error_handler(_code))


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return _api_error('not_found', 'The requested API address was not found.', 404)
    return _error_page('404.html', 404, 'Page not found')

# Stage 2: typed application errors (pharmacy/errors.py). Services raise these;
# the user sees user_message (English, safe), the detail goes to the log only.
from pharmacy.errors import (MediGenError, ValidationError, NotFoundError,  # noqa: E402
                             PermissionDenied, StockError, ConflictError,
                             PaymentError, ExternalServiceError, DatabaseError)

_TYPED_STATUS = ((ValidationError, 400, 'validation_error'),
                 (PermissionDenied, 403, 'permission_denied'),
                 (NotFoundError, 404, 'not_found'),
                 (StockError, 409, 'stock_error'),
                 (ConflictError, 409, 'conflict'),
                 (PaymentError, 422, 'payment_error'),
                 (ExternalServiceError, 503, 'service_unavailable'),
                 (DatabaseError, 500, 'database_error'))


@app.errorhandler(MediGenError)
def typed_error(e):
    status, code = 400, 'application_error'
    for cls, st, cd in _TYPED_STATUS:
        if isinstance(e, cls):
            status, code = st, cd
            break
    app.logger.warning('Typed error on %s: %s | %s', request.path, code, e.detail)
    if request.path.startswith('/api/'):
        return _api_error(code, e.user_message, status)
    flash(e.user_message, 'error')
    return redirect(request.referrer or url_for('dashboard'))


@app.errorhandler(Exception)
def unexpected_error(e):
    """Safety net for every route: normal HTTP errors (404, 405...) keep their own page,
    anything else is logged in full on the server and shown as a short friendly page."""
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    app.logger.error('Unhandled error on %s: %r', request.path, e, exc_info=e)
    if request.path.startswith('/api/'):   # v88.00: E6 - no stack traces to API users either
        return _api_error('server_error', 'Something went wrong. Please try again.', 500)
    return server_error(e)

@app.errorhandler(500)
def server_error(e):
    orig = getattr(e, 'original_exception', None) or e
    app.logger.error('500 error on %s: %r', request.path, orig)
    detail = None
    if Config.DEBUG:      # technical text only in DEBUG mode; always in the terminal log
        detail = f'{type(orig).__name__}: {orig}'[:600]
    try:
        return render_template('500.html', detail=detail), 500
    except Exception:
        return (f"<h2>500 - Server error</h2><pre>{detail or ''}</pre><p><a href='/dashboard'>Back to Dashboard</a></p>"), 500
