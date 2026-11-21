-- v88.00: B2 - READ-ONLY check. Run this in MySQL Workbench on a COPY first if you prefer.
-- It only lists medicines that share one barcode. It changes nothing.
-- Fix duplicates by editing the barcode on the Medicines page (give each medicine its own
-- barcode, or clear the barcode on the copies). The unique index uq_medicines_barcode is
-- added by the app automatically once no duplicates remain.
SELECT barcode,
       COUNT(*) AS medicines_with_this_barcode,
       GROUP_CONCAT(CONCAT(medicine_id, ': ', name) ORDER BY name SEPARATOR ' | ') AS medicines
FROM medicines
WHERE is_deleted = 0 AND barcode IS NOT NULL AND barcode <> ''
GROUP BY barcode
HAVING COUNT(*) > 1
ORDER BY barcode;
