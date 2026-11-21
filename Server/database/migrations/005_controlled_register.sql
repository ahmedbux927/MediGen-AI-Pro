-- Controlled-drug register: one row per batch sold of a medicine that has a schedule set.
-- Append-only: UPDATE and DELETE are blocked by triggers (created in pharmacy/services/controlled_register.py,
-- because trigger bodies cannot be split by this migration runner).
CREATE TABLE IF NOT EXISTS controlled_register (
    entry_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    medicine_id INT NOT NULL,
    schedule VARCHAR(20) NOT NULL,
    batch_id INT NULL,
    quantity INT NOT NULL,
    customer_id INT NULL,
    prescription_id INT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_register_sale (sale_id),
    KEY idx_register_medicine_time (medicine_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
