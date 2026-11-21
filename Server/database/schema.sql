-- =====================================================================
-- MediGen AI Pro - database schema   (MySQL 8)  - full current version
-- Run this whole file in MySQL Workbench to build an EMPTY database.
-- (Your existing database already has these tables - do NOT run it on it.)
-- =====================================================================
CREATE DATABASE IF NOT EXISTS pharmacy_management_system
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE pharmacy_management_system;

SET FOREIGN_KEY_CHECKS = 0;

-- ---- roles ----
CREATE TABLE IF NOT EXISTS `roles` (
  `role_id` int NOT NULL AUTO_INCREMENT,
  `role_name` varchar(50) NOT NULL,
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_name` (`role_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- users ----
CREATE TABLE IF NOT EXISTS `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `full_name` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role_id` int NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `access_start_time` time DEFAULT '08:00:00',
  `access_end_time` time DEFAULT '22:00:00',
  `gender` varchar(20) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `birthday` date DEFAULT NULL,
  `language` varchar(50) DEFAULT NULL,
  `home_address` varchar(255) DEFAULT NULL,
  `work_address` varchar(255) DEFAULT NULL,
  `other_address` varchar(255) DEFAULT NULL,
  `about` text,
  `position` varchar(100) DEFAULT NULL,
  `projects` text,
  `license_info` varchar(255) DEFAULT NULL,
  `experience` text,
  `recommendations` text,
  `volunteer` text,
  `honors` text,
  `awards` text,
  `causes` text,
  `services` text,
  `profile_pic` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- customers ----
CREATE TABLE IF NOT EXISTS `customers` (
  `customer_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `contact_number` varchar(15) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `gender` enum('Male','Female','Other') DEFAULT NULL,
  `medical_history` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- categories ----
CREATE TABLE IF NOT EXISTS `categories` (
  `category_id` int NOT NULL AUTO_INCREMENT,
  `category_name` varchar(50) NOT NULL,
  PRIMARY KEY (`category_id`),
  UNIQUE KEY `category_name` (`category_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- suppliers ----
CREATE TABLE IF NOT EXISTS `suppliers` (
  `supplier_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `contact` varchar(15) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`supplier_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- medicines ----
CREATE TABLE IF NOT EXISTS `medicines` (
  `medicine_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `category_id` int DEFAULT NULL,
  `price` decimal(15,2) DEFAULT NULL,
  `cost_price` decimal(15,2) NOT NULL DEFAULT 0,
  `stock_quantity` int DEFAULT '0',
  `reorder_level` int DEFAULT '20',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',   -- v90.00 fix: the views below use this column; a fresh load of this file failed without it (the app migration also adds it when missing)
  PRIMARY KEY (`medicine_id`),
  KEY `category_id` (`category_id`),
  CONSTRAINT `medicines_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- batches ----
CREATE TABLE IF NOT EXISTS `batches` (
  `batch_id` int NOT NULL AUTO_INCREMENT,
  `medicine_id` int NOT NULL,
  `batch_number` varchar(50) NOT NULL,
  `expiry_date` date NOT NULL,
  `quantity` int NOT NULL,
  `purchase_price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`batch_id`),
  KEY `medicine_id` (`medicine_id`),
  CONSTRAINT `batches_ibfk_1` FOREIGN KEY (`medicine_id`) REFERENCES `medicines` (`medicine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- purchase_orders ----
CREATE TABLE IF NOT EXISTS `purchase_orders` (
  `po_id` int NOT NULL AUTO_INCREMENT,
  `supplier_id` int NOT NULL,
  `order_date` date NOT NULL,
  `delivery_date` date DEFAULT NULL,
  `total_amount` decimal(15,2) DEFAULT '0.00',
  `status` enum('Pending','Received','Cancelled') DEFAULT 'Pending',
  PRIMARY KEY (`po_id`),
  KEY `supplier_id` (`supplier_id`),
  CONSTRAINT `purchase_orders_ibfk_1` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- purchase_items ----
CREATE TABLE IF NOT EXISTS `purchase_items` (
  `po_item_id` int NOT NULL AUTO_INCREMENT,
  `po_id` int NOT NULL,
  `medicine_id` int NOT NULL,
  `batch_number` varchar(50) DEFAULT NULL,
  `expiry_date` date DEFAULT NULL,
  `quantity` int NOT NULL,
  `unit_price` decimal(15,2) DEFAULT NULL,
  PRIMARY KEY (`po_item_id`),
  KEY `po_id` (`po_id`),
  KEY `medicine_id` (`medicine_id`),
  CONSTRAINT `purchase_items_ibfk_1` FOREIGN KEY (`po_id`) REFERENCES `purchase_orders` (`po_id`) ON DELETE CASCADE,
  CONSTRAINT `purchase_items_ibfk_2` FOREIGN KEY (`medicine_id`) REFERENCES `medicines` (`medicine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- sales ----
CREATE TABLE IF NOT EXISTS `sales` (
  `sale_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  `sale_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `total_amount` decimal(15,2) DEFAULT '0.00',
  `payment_method` enum('Cash','Card','Online','JazzCash','Easypaisa') DEFAULT 'Cash',
  `subtotal_amount` decimal(15,2) NOT NULL DEFAULT 0,
  `discount_amount` decimal(15,2) NOT NULL DEFAULT 0,
  `tax_rate` decimal(5,2) NOT NULL DEFAULT 0,
  `tax_amount` decimal(15,2) NOT NULL DEFAULT 0,
  `paid_amount` decimal(15,2) NOT NULL DEFAULT 0,
  `returned_amount` decimal(15,2) NOT NULL DEFAULT 0,
  `prescription_id` int NULL,
  PRIMARY KEY (`sale_id`),
  KEY `customer_id` (`customer_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `sales_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`customer_id`),
  CONSTRAINT `sales_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- sale_items ----
CREATE TABLE IF NOT EXISTS `sale_items` (
  `sale_item_id` int NOT NULL AUTO_INCREMENT,
  `sale_id` int NOT NULL,
  `medicine_id` int NOT NULL,
  `batch_id` int DEFAULT NULL,
  `quantity` int NOT NULL,
  `unit_price` decimal(15,2) DEFAULT NULL,
  `subtotal` decimal(15,2) DEFAULT NULL,
  PRIMARY KEY (`sale_item_id`),
  KEY `sale_id` (`sale_id`),
  KEY `medicine_id` (`medicine_id`),
  KEY `batch_id` (`batch_id`),
  CONSTRAINT `sale_items_ibfk_1` FOREIGN KEY (`sale_id`) REFERENCES `sales` (`sale_id`) ON DELETE CASCADE,
  CONSTRAINT `sale_items_ibfk_2` FOREIGN KEY (`medicine_id`) REFERENCES `medicines` (`medicine_id`),
  CONSTRAINT `sale_items_ibfk_3` FOREIGN KEY (`batch_id`) REFERENCES `batches` (`batch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- prescriptions ----
CREATE TABLE IF NOT EXISTS `prescriptions` (
  `prescription_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `doctor_name` varchar(100) DEFAULT NULL,
  `date_issued` date NOT NULL,
  `notes` text,
  PRIMARY KEY (`prescription_id`),
  KEY `customer_id` (`customer_id`),
  CONSTRAINT `prescriptions_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- prescription_items ----
CREATE TABLE IF NOT EXISTS `prescription_items` (
  `item_id` int NOT NULL AUTO_INCREMENT,
  `prescription_id` int NOT NULL,
  `medicine_id` int NOT NULL,
  `dosage` varchar(100) DEFAULT NULL,
  `duration_days` int DEFAULT NULL,
  PRIMARY KEY (`item_id`),
  KEY `prescription_id` (`prescription_id`),
  KEY `medicine_id` (`medicine_id`),
  CONSTRAINT `prescription_items_ibfk_1` FOREIGN KEY (`prescription_id`) REFERENCES `prescriptions` (`prescription_id`) ON DELETE CASCADE,
  CONSTRAINT `prescription_items_ibfk_2` FOREIGN KEY (`medicine_id`) REFERENCES `medicines` (`medicine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---- chat_history ----
CREATE TABLE IF NOT EXISTS `chat_history` (
  `chat_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `question` text NOT NULL,
  `answer` text NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`chat_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `chat_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ---- stock history, payments, returns, audit (used by the app) ----
CREATE TABLE IF NOT EXISTS stock_adjustments (
    adjustment_id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_id INT NOT NULL,
    user_id INT NULL,
    change_qty INT NOT NULL,
    old_stock INT NOT NULL,
    new_stock INT NOT NULL,
    reason VARCHAR(40) NOT NULL,
    note VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_adj_medicine (medicine_id),
    CONSTRAINT fk_adj_medicine FOREIGN KEY (medicine_id) REFERENCES medicines (medicine_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sale_payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    user_id INT NULL,
    amount DECIMAL(15,2) NOT NULL,
    method VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_pay_sale (sale_id),
    CONSTRAINT fk_pay_sale FOREIGN KEY (sale_id) REFERENCES sales (sale_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sale_returns (
    return_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    user_id INT NULL,
    refund_amount DECIMAL(15,2) NOT NULL,
    reason VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_ret_sale (sale_id),
    CONSTRAINT fk_ret_sale FOREIGN KEY (sale_id) REFERENCES sales (sale_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sale_return_items (
    return_item_id INT AUTO_INCREMENT PRIMARY KEY,
    return_id INT NOT NULL,
    sale_item_id INT NOT NULL,
    medicine_id INT NOT NULL,
    batch_id INT NULL,
    quantity INT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    KEY idx_rit_item (sale_item_id),
    CONSTRAINT fk_rit_return FOREIGN KEY (return_id) REFERENCES sale_returns (return_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    username VARCHAR(50) NULL,
    action VARCHAR(40) NOT NULL,
    entity VARCHAR(40) NULL,
    entity_id INT NULL,
    details VARCHAR(500) NULL,
    ip VARCHAR(45) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_audit_created (created_at),
    KEY idx_audit_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---- triggers: stock changes automatically ----
DROP TRIGGER IF EXISTS trg_sale_stock;
DROP TRIGGER IF EXISTS trg_purchase_stock;
DELIMITER ;;
CREATE TRIGGER trg_sale_stock AFTER INSERT ON sale_items FOR EACH ROW
BEGIN
    UPDATE medicines SET stock_quantity = stock_quantity - NEW.quantity
    WHERE medicine_id = NEW.medicine_id;
    UPDATE batches SET quantity = quantity - NEW.quantity
    WHERE batch_id = NEW.batch_id;
END;;
CREATE TRIGGER trg_purchase_stock AFTER INSERT ON purchase_items FOR EACH ROW
BEGIN
    UPDATE medicines SET stock_quantity = stock_quantity + NEW.quantity
    WHERE medicine_id = NEW.medicine_id;
END;;
DELIMITER ;

-- ---- views used by dashboard and reports ----
CREATE OR REPLACE VIEW v_expiring_soon AS
SELECT b.batch_id, m.name, b.batch_number, b.expiry_date, b.quantity
FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
WHERE m.is_deleted = 0 AND b.expiry_date BETWEEN CURDATE() AND (CURDATE() + INTERVAL 90 DAY);

CREATE OR REPLACE VIEW v_low_stock AS
SELECT medicine_id, name, stock_quantity, reorder_level
FROM medicines WHERE is_deleted = 0 AND stock_quantity <= reorder_level;

CREATE OR REPLACE VIEW v_daily_sales AS
SELECT CAST(sale_date AS DATE) AS sale_day, COUNT(0) AS invoices, SUM(total_amount) AS revenue
FROM sales GROUP BY CAST(sale_date AS DATE);
