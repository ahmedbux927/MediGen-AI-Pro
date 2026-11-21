"""Data-access layer: plain SQL functions that take an open cursor.

Rules for this package:
  * No Flask imports here (no request, session, flash, redirect).
  * Functions only run SQL; the route decides commit / rollback.
  * Every query uses %s placeholders, never string formatting of user input.
"""
