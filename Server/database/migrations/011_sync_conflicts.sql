-- Phone sync conflicts (v87.22): a bill sent from the phone while offline sold more than the server's stock.
-- The bill is still saved (so the customer is not lost); this row tells the Admin to check the shelf.
CREATE TABLE IF NOT EXISTS sync_conflicts (
    conflict_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NULL,
    client_uuid VARCHAR(64) NULL,
    medicine_id INT NOT NULL,
    medicine_name VARCHAR(200) NOT NULL,
    requested INT NOT NULL,
    stock_before INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved TINYINT(1) NOT NULL DEFAULT 0,
    resolved_at DATETIME NULL,
    resolved_by INT NULL,
    resolve_note VARCHAR(255) NULL,
    INDEX ix_sync_conflicts_open (resolved, created_at)
);
