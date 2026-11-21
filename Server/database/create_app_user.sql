-- MediGen AI Pro: create a separate database user for the app (instead of root).
-- Run once, as the MySQL root user, for example:
--   mysql -u root -p < database/create_app_user.sql
-- Then change the password below BEFORE running it, and put the same user and password in .env.
--
-- Why these rights:
--   The app checks and updates its own tables and triggers every time it starts (ensure_schema),
--   so it needs schema rights on its own database only. Nothing outside pharmacy_management_system is granted.
--   The audit log is protected by database triggers that block UPDATE and DELETE on audit_log.
--   The backup script (mysqldump) needs SHOW VIEW, TRIGGER, EVENT and LOCK TABLES.

CREATE USER IF NOT EXISTS 'medigen_app'@'localhost' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';

-- Rights on this one database only.
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX,
      CREATE VIEW, SHOW VIEW, TRIGGER, EVENT, LOCK TABLES
      ON `pharmacy_management_system`.* TO 'medigen_app'@'localhost';

FLUSH PRIVILEGES;

-- Check: this should list the grants above and no ALL PRIVILEGES.
SHOW GRANTS FOR 'medigen_app'@'localhost';
