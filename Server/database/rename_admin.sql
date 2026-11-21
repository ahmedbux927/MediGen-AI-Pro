-- Rename the Admin account shown in the app (Dashboard greeting, My Profile, audit log).
-- Run inside the MySQL client:   source database/rename_admin.sql
-- Only the Admin user whose name is exactly 'Ahmed' is changed.
USE pharmacy_management_system;
UPDATE users SET full_name = 'Admin: CEO' WHERE role_id = 1 AND full_name = 'Ahmed';
SELECT user_id, username, full_name, role_id FROM users WHERE role_id = 1;
