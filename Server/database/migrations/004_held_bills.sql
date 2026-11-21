-- Phase 2: a bill can be put on hold at one counter and resumed later. Holding does NOT reserve stock;
-- stock is checked again when the bill is completed.
CREATE TABLE IF NOT EXISTS held_bills (
    hold_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    counter_no TINYINT NOT NULL DEFAULT 1,
    user_id INT NOT NULL,
    customer_id INT NULL,
    payload TEXT NOT NULL,
    status ENUM('open','resumed','discarded','expired') NOT NULL DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL,
    KEY idx_held_status_counter (status, counter_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
