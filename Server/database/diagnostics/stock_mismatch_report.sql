-- B2 diagnostic: "No stock" shown for medicines that have stock.
-- READ-ONLY. Only SELECT statements. Nothing is changed.
-- Run on the shop PC: open MySQL (or MySQL Workbench) on database pharmacy_management_system, paste, run.
-- Each section explains one reason. Send the results (no customer names are in these queries).

-- 1) Medicines the POS hides: stock > 0 but sellable (fresh batches) is 0.
--    This is the likely cause of "No stock" when stock_quantity is high.
SELECT m.medicine_id, m.name, m.stock_quantity,
       (SELECT COUNT(*) FROM batches b WHERE b.medicine_id = m.medicine_id) AS batch_rows,
       IFNULL((SELECT SUM(b.quantity) FROM batches b
               WHERE b.medicine_id = m.medicine_id AND b.quantity > 0 AND b.expiry_date >= CURDATE()), 0) AS fresh_qty,
       IFNULL((SELECT SUM(b.quantity) FROM batches b WHERE b.medicine_id = m.medicine_id), 0) AS all_batch_qty
FROM medicines m
WHERE m.stock_quantity > 0 AND m.is_deleted = 0
  AND (SELECT COUNT(*) FROM batches b WHERE b.medicine_id = m.medicine_id) > 0
  AND IFNULL((SELECT SUM(b.quantity) FROM batches b
              WHERE b.medicine_id = m.medicine_id AND b.quantity > 0 AND b.expiry_date >= CURDATE()), 0) = 0
ORDER BY m.name;

-- 2) Medicines where stock_quantity and the batch total do not match (any direction).
SELECT m.medicine_id, m.name, m.stock_quantity,
       IFNULL(SUM(b.quantity), 0) AS batch_total,
       m.stock_quantity - IFNULL(SUM(b.quantity), 0) AS difference
FROM medicines m
LEFT JOIN batches b ON b.medicine_id = m.medicine_id
WHERE m.is_deleted = 0
GROUP BY m.medicine_id, m.name, m.stock_quantity
HAVING m.stock_quantity <> IFNULL(SUM(b.quantity), 0)
ORDER BY ABS(difference) DESC, m.name;

-- 3) Expired batches that still hold quantity (these must not be sold; write-off or return them).
SELECT m.name, b.batch_number, b.expiry_date, b.quantity
FROM batches b JOIN medicines m ON m.medicine_id = b.medicine_id
WHERE b.quantity > 0 AND b.expiry_date < CURDATE()
ORDER BY b.expiry_date;

-- 4) Summary counts (send these numbers first).
SELECT
  (SELECT COUNT(*) FROM medicines WHERE is_deleted = 0 AND stock_quantity > 0) AS medicines_with_stock,
  (SELECT COUNT(*) FROM medicines WHERE is_deleted = 0 AND stock_quantity > 0 AND medicine_id NOT IN (SELECT medicine_id FROM batches)) AS stock_without_any_batch,
  (SELECT COUNT(*) FROM batches WHERE quantity > 0 AND expiry_date < CURDATE()) AS expired_batches_with_qty;
