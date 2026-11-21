-- Customer portal accounts (v87.10): a PIN set by the shop for a customer phone. Read-only portal use.
-- The PIN is stored as a bcrypt hash. Five wrong PINs lock the account for 15 minutes.
CREATE TABLE IF NOT EXISTS customer_portal_accounts (
    customer_id INT NOT NULL PRIMARY KEY,
    phone_digits VARCHAR(20) NOT NULL,
    pin_hash VARCHAR(100) NOT NULL,
    failed_count INT NOT NULL DEFAULT 0,
    locked_until DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    UNIQUE KEY uq_portal_phone (phone_digits),
    CONSTRAINT fk_portal_customer FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
