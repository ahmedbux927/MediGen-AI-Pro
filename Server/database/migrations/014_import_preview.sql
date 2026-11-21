-- Stage 5 (Master Prompt v4): one import flow with preview, confirm and undo.
-- import_previews holds a parsed plan until the user confirms or leaves it.
-- import_batches records what a confirmed import changed, so it can be undone.
CREATE TABLE IF NOT EXISTS import_previews (
    preview_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(160) NOT NULL,
    update_existing TINYINT(1) NOT NULL DEFAULT 0,
    plan_json MEDIUMTEXT NOT NULL,
    summary_json TEXT NOT NULL,
    status ENUM('preview','confirmed','discarded') NOT NULL DEFAULT 'preview',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_import_preview_user (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS import_batches (
    batch_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    preview_id INT NULL,
    user_id INT NOT NULL,
    filename VARCHAR(160) NOT NULL,
    created_ids TEXT NULL,
    updated_snapshot MEDIUMTEXT NULL,
    summary_json TEXT NULL,
    status ENUM('applied','undone') NOT NULL DEFAULT 'applied',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    undone_at TIMESTAMP NULL,
    KEY idx_import_batch_user (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
