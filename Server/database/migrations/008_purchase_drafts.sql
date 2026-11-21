-- Purchase drafts (v87.05): suggested orders kept for staff to review. A draft never changes stock.
-- Stock changes only when the purchase is received on the Purchase page (purchase_items trigger).
CREATE TABLE IF NOT EXISTS purchase_drafts (
    draft_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NULL,
    status ENUM('draft','sent','cancelled') NOT NULL DEFAULT 'draft',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    note VARCHAR(255) NULL,
    KEY idx_draft_status (status),
    CONSTRAINT fk_draft_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS purchase_draft_lines (
    line_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    draft_id INT NOT NULL,
    medicine_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_cost DECIMAL(15,2) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_draft_line (draft_id, medicine_id),
    KEY idx_draft_line_medicine (medicine_id),
    CONSTRAINT fk_draft_line_draft FOREIGN KEY (draft_id) REFERENCES purchase_drafts (draft_id) ON DELETE CASCADE,
    CONSTRAINT fk_draft_line_medicine FOREIGN KEY (medicine_id) REFERENCES medicines (medicine_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
