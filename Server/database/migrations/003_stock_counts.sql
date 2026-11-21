-- Phase 3 (stock count): one count session at a time. Lines keep the stock seen at the start (system_qty),
-- what was counted, and who counted it. Approval writes stock adjustments and audit rows.
CREATE TABLE IF NOT EXISTS stock_counts (
    count_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    status ENUM('open','submitted','approved','cancelled') NOT NULL DEFAULT 'open',
    started_by INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP NULL,
    approved_by INT NULL,
    approved_at TIMESTAMP NULL,
    note VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stock_count_lines (
    line_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    count_id INT NOT NULL,
    medicine_id INT NOT NULL,
    system_qty INT NOT NULL,
    counted_qty INT NULL,
    counted_by INT NULL,
    counted_at TIMESTAMP NULL,
    UNIQUE KEY uq_count_medicine (count_id, medicine_id),
    KEY idx_count_line_medicine (medicine_id),
    CONSTRAINT fk_count_line_count FOREIGN KEY (count_id) REFERENCES stock_counts (count_id) ON DELETE CASCADE,
    CONSTRAINT fk_count_line_medicine FOREIGN KEY (medicine_id) REFERENCES medicines (medicine_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
