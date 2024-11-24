-- Tạo cơ sở dữ liệu
CREATE DATABASE  parking_db;
USE parking_db;

-- Tạo bảng users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 0.00,
    role ENUM('admin', 'user') NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng rfid_cards
CREATE TABLE rfid_cards (
    rfid_id INT AUTO_INCREMENT PRIMARY KEY,
    rfid_code VARCHAR(50) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tạo bảng pricing
CREATE TABLE pricing (
    pricing_id INT AUTO_INCREMENT PRIMARY KEY,
    amount_per_second DECIMAL(10, 4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo bảng parking_slots
CREATE TABLE parking_slots (
    slot_id INT AUTO_INCREMENT PRIMARY KEY,
    status ENUM('available', 'occupied') NOT NULL
);

-- Tạo bảng invoices
CREATE TABLE invoices (
    invoice_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    parking_slot_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_status ENUM('paid', 'unpaid') NOT NULL,
    entry_time DATETIME NOT NULL,
    exit_time DATETIME NULL,
    vehicle_type VARCHAR(50) NOT NULL, -- Chấp nhận giá trị tùy ý cho loại phương tiện
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (parking_slot_id) REFERENCES parking_slots(slot_id)
);
