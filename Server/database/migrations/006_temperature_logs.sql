-- Cold chain: fridge and store temperature readings (insulin, injections, vaccines).
CREATE TABLE IF NOT EXISTS temperature_logs (
    log_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    location VARCHAR(40) NOT NULL,
    temperature_c DECIMAL(4,1) NOT NULL,
    in_range TINYINT(1) NOT NULL,
    user_id INT NOT NULL,
    note VARCHAR(200) NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_temp_location_time (location, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
