-- =====================================================================
-- Clean-up for YOUR EXISTING database (safe: removes only empty sales).
-- Take a backup first:  Workbench > Server > Data Export.
-- =====================================================================
USE pharmacy_management_system;

-- 1. Remove empty sales (total 0, no items). The old new_sale bug created them (ids 19, 24, 26, 31).
SET SQL_SAFE_UPDATES = 0;
DELETE s FROM sales s
LEFT JOIN sale_items si ON si.sale_id = s.sale_id
WHERE si.sale_id IS NULL AND s.total_amount = 0;
SET SQL_SAFE_UPDATES = 1;

-- 2. REPORT ONLY (changes nothing): medicines whose stock does not match their batches.
--    Step 4 (purchase + batch) will fix this properly.
SELECT m.medicine_id, m.name, m.stock_quantity AS stock_in_medicines,
       IFNULL(SUM(b.quantity), 0) AS stock_in_batches
FROM medicines m LEFT JOIN batches b ON b.medicine_id = m.medicine_id
GROUP BY m.medicine_id, m.name, m.stock_quantity
HAVING m.stock_quantity <> IFNULL(SUM(b.quantity), 0);

-- 3. REPORT ONLY: batches that already expired but still have quantity.
SELECT m.name, b.batch_number, b.expiry_date, b.quantity
FROM batches b JOIN medicines m ON m.medicine_id = b.medicine_id
WHERE b.expiry_date < CURDATE() AND b.quantity > 0;
