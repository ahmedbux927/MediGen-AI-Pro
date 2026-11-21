-- =====================================================================
-- OPTIONAL: clean the doctor names stored in the database.
-- The app already SHOWS them correctly ("Dr. Ahmed") without this,
-- so you may skip it. Take a backup first (Workbench > Data Export).
-- =====================================================================
USE pharmacy_management_system;

-- 1. REPORT ONLY (changes nothing): names that start with Dr / Doctor
SELECT prescription_id, doctor_name
FROM prescriptions
WHERE REGEXP_LIKE(doctor_name, '^(dr|doctor)([.][[:space:]]*|[[:space:]]+)', 'i');

-- 2. Remove the leading "Dr." / "Dr " / "Doctor "  ("Drake" is NOT touched)
UPDATE prescriptions
SET doctor_name = TRIM(REGEXP_REPLACE(doctor_name, '^(dr|doctor)([.][[:space:]]*|[[:space:]]+)', '', 1, 0, 'i'))
WHERE REGEXP_LIKE(doctor_name, '^(dr|doctor)([.][[:space:]]*|[[:space:]]+)', 'i');

-- 3. Check the result
SELECT prescription_id, doctor_name FROM prescriptions ORDER BY prescription_id;
