-- Phone OTP for password reset (v87.23): a 6-digit code sent on WhatsApp. Only a keyed hash is stored.
-- A code works 10 minutes, once, and after 5 wrong tries it stops working.
CREATE TABLE IF NOT EXISTS phone_otps (
    otp_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    code_hash CHAR(64) NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    used TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    INDEX ix_phone_otps_user (user_id, used, expires_at)
);
