-- B1: remembers recent bills so a double submit is saved once (see pharmacy/services/sale_guard.py)
CREATE TABLE IF NOT EXISTS sale_guard (
    fingerprint CHAR(64) NOT NULL PRIMARY KEY,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_sale_guard_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
