-- =====================================================================
-- MediGen AI Pro - demo data for a NEW empty database (run after schema.sql)
-- Stock numbers match the batch numbers, expiry dates are always in the future.
-- The first admin user is made by:  python create_admin.py
-- =====================================================================
USE pharmacy_management_system;

INSERT INTO roles (role_id, role_name) VALUES (1,'Admin'),(2,'Pharmacist'),(3,'Cashier');

INSERT INTO categories (category_id, category_name) VALUES (6,'Analgesic'),(7,'Antacid'),(9,'Anti-inflammatory'),(34,'Antiallergic'),(2,'Antibiotic'),(12,'Antidepressant'),(13,'Antidiabetic'),(39,'Antidiarrheal'),(40,'Antiemetic'),(11,'Antifungal'),(8,'Antihistamine'),(14,'Antihypertensive'),(1,'Antipyretic'),(4,'Antiseptic'),(10,'Antiviral'),(27,'Capsule'),(15,'Cardiovascular'),(35,'Cough Suppressant'),(28,'Cream'),(36,'Decongestant'),(16,'Dermatology'),(49,'Diagnostic'),(30,'Drops'),(47,'Emergency'),(37,'Expectorant'),(17,'Gastrointestinal'),(46,'Geriatric'),(41,'Hormonal'),(31,'Inhaler'),(23,'Injectable'),(38,'Laxative'),(21,'Nasal'),(42,'Neurological'),(50,'Nutraceutical'),(29,'Ointment'),(44,'Oncology'),(19,'Ophthalmic'),(24,'Oral'),(20,'Otic'),(3,'Painkiller'),(45,'Pediatric'),(43,'Psychiatric'),(18,'Respiratory'),(32,'Suppository'),(48,'Surgical'),(25,'Syrup'),(26,'Tablet'),(22,'Topical'),(33,'Vaccine'),(5,'Vitamin');

INSERT INTO suppliers (supplier_id, name, contact, email, address) VALUES
 (1,'Arslan Traders','03261489','arslan@sup.com','Karachi'),
 (2,'Shareef Distributors','03234489','shareef@sup.com','Lahore'),
 (3,'Adnan Pharma','032998989','adnan@sup.com','Islamabad');

INSERT INTO customers (customer_id, name, contact_number, email, gender, medical_history) VALUES
 (1,'Hasnain','031251351','hasnain@email.com','Male','Fever'),
 (2,'Sasui','0312545245','sasui@email.com','Female','Cough'),
 (3,'Hamid','03121245','hamid@email.com','Male','Headache');

INSERT INTO medicines (medicine_id, name, category_id, price, stock_quantity, reorder_level) VALUES
 (1,'Panadol',1,100.00,500,50),
 (2,'Paracetamol',1,50.00,300,30),
 (3,'Ibuprofen',3,30.00,200,20),
 (4,'Amoxicillin',2,100.00,800,50),
 (5,'Aspirin',3,40.00,400,25);

INSERT INTO batches (batch_id, medicine_id, batch_number, expiry_date, quantity, purchase_price) VALUES
 (1,1,'PAN-DEMO-01', DATE_ADD(CURDATE(), INTERVAL 18 MONTH),500,80.00),
 (2,2,'PAR-DEMO-02', DATE_ADD(CURDATE(), INTERVAL 12 MONTH),300,40.00),
 (3,3,'IBU-DEMO-03', DATE_ADD(CURDATE(), INTERVAL 10 MONTH),200,25.00),
 (4,4,'AMO-DEMO-04', DATE_ADD(CURDATE(), INTERVAL 14 MONTH),800,85.00),
 (5,5,'ASP-DEMO-05', DATE_ADD(CURDATE(), INTERVAL 8 MONTH),400,30.00);
