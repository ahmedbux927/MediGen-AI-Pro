-- AI agent write actions. A write is proposed first; it runs only after the user confirms with a one-time token.
-- The token itself is never stored, only its SHA-256 hash.
CREATE TABLE IF NOT EXISTS agent_actions (
    action_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    token_hash CHAR(64) NOT NULL,
    user_id INT NOT NULL,
    action VARCHAR(40) NOT NULL,
    params TEXT NOT NULL,
    summary VARCHAR(255) NOT NULL,
    status ENUM('pending','done','cancelled') NOT NULL DEFAULT 'pending',
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_agent_token (token_hash),
    KEY idx_agent_user (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
