"""Routes: service worker and web app manifest (Sprint 3). They must sit at the site root to control every page."""
import os
from flask import send_from_directory
from pharmacy.core import app  # noqa: F401
from pharmacy.lib import guarded  # noqa: F401

_STATIC = app.static_folder   # the project's static folder (Flask resolves it)


@app.route('/sw.js')
@guarded
def service_worker():
    resp = send_from_directory(os.path.join(_STATIC, 'js'), 'sw.js', mimetype='application/javascript')
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/manifest.webmanifest')
@guarded
def web_manifest():
    return send_from_directory(_STATIC, 'manifest.webmanifest', mimetype='application/manifest+json')
