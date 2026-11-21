-- Drug interaction pairs (v87.07). Only the pairs the shop enters. No licensed drug database is included,
-- so an empty list does NOT mean two medicines are safe together. Pairs are stored with the lower id first.
CREATE TABLE IF NOT EXISTS drug_interactions (
    interaction_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    med_a_id INT NOT NULL,
    med_b_id INT NOT NULL,
    severity ENUM('minor','moderate','major') NOT NULL DEFAULT 'moderate',
    note VARCHAR(255) NULL,
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_interaction_pair (med_a_id, med_b_id),
    KEY idx_interaction_b (med_b_id),
    CONSTRAINT fk_interaction_a FOREIGN KEY (med_a_id) REFERENCES medicines (medicine_id) ON DELETE CASCADE,
    CONSTRAINT fk_interaction_b FOREIGN KEY (med_b_id) REFERENCES medicines (medicine_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
