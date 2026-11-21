# Database user for MediGen (replace root)

The app currently connects as `root` (see `DB_USER` in `.env`). Root can do anything on the MySQL server, so a separate user is safer. This takes about 5 minutes.

## Steps

1. Open `database/create_app_user.sql` in Notepad. Change `CHANGE_ME_STRONG_PASSWORD` to a long password (at least 16 characters, letters, numbers and symbols). Write it down; do not paste it in chat.
2. Open PowerShell in the project folder and run (you will be asked for the MySQL root password):

       mysql -u root -p < database\create_app_user.sql

   The last line prints the grants. You should see the list in step 1 and no `ALL PRIVILEGES`.
3. Open `.env` in Notepad and change these two lines (keep the rest):

       DB_USER=medigen_app
       DB_PASSWORD=the password from step 1

4. Stop the app (Ctrl+C) and start it again: `python app.py`.
   - The startup check should show the database as connected.
   - If it says "Access denied", check the password and the user name in `.env`.
   - If it says "command denied" or a table or trigger error, the grants are missing. Run the SQL again as root.
5. Test the backup: `scripts\backup_db.bat`. A new `.sql` file should appear in `backups\`.
6. Log in and make one sale, then check the Audit Log page.

## Rollback

If anything fails, set `DB_USER=root` and the old `DB_PASSWORD` in `.env` again, and restart the app.

## Notes

- The old root password was pasted in chat earlier. After this change, also change the root password: `ALTER USER 'root'@'localhost' IDENTIFIED BY 'new strong password';`
- The app still needs rights to create and change its tables and triggers, because it sets them up on every start. The audit log cannot be edited or deleted through the app, because the database blocks UPDATE and DELETE on it. Someone with the root password can still change that, so keep the root password private.
