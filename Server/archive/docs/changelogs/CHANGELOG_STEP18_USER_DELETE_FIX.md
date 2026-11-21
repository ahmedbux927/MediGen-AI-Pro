# Step 18 - User delete and reset-code fixes (v48)

## Problem
- A user with sales or chatbot history (for example "hassain") could not be deleted.
  `sales.user_id` and `chat_history.user_id` point to `users`, and the delete had no rule for them.
  MySQL refused the delete, and the error was hidden behind "Something went wrong".

## Fix
- `delete_user` (pharmacy/routes/users.py) now checks the history first:
  - No sales and no chat history: the user is deleted (login tokens and reset codes removed first).
  - Has sales or chat history: the user is turned OFF (is_active = 0), history is kept, and the admin sees the reason.
- Real database errors are logged in full and rolled back. A foreign-key error shows a clear message.
- Audit log records `user.delete` or `user.deactivate`.

## Forgot password
- The flow is: Admin presses "Make one-time reset code" on the Users page, the user types it on the
  Forgot password page (valid 15 minutes, one use). Code and page were checked and match.
- Admin can also press "Set new password now" (key icon) to set a password immediately.

## Tests
- `tests/test_coverage_admin.py`: delete with no history, and deactivate with history.
- `python tests/run_all.py`: 1073 passed, 0 failed (mock database).
- Not run here: the live MySQL test (`--live`) and the Windows build. Run them on the shop PC.
