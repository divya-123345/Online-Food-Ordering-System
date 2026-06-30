create database Tastyhub;
use Tastyhub;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fullname VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile VARCHAR(15) NOT NULL,
    address VARCHAR(255),
    password VARCHAR(255) NOT NULL,
    usertype ENUM('customer','owner') NOT NULL
);

INSERT INTO users
(fullname, email, mobile, address, password, usertype)
VALUES
(
 'TastyHub Owner',
 'support@tastyhub.com',
 '9890123456',
 'Pune',
 'tastyhub@12',
 'owner'
);

CREATE TABLE menu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category ENUM('Veg','Non-Veg') NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    description TEXT,
    image VARCHAR(255) NOT NULL
);

CREATE TABLE cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    menu_id INT NOT NULL,
    quantity INT DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2) NOT NULL,
    status ENUM('Pending','Completed') DEFAULT 'Pending',

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    menu_id INT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,

    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (menu_id) REFERENCES menu(id) ON DELETE CASCADE
);

ALTER TABLE orders ADD COLUMN user_email VARCHAR(255);

CREATE TABLE payment_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    mobile VARCHAR(15) NOT NULL,
    address VARCHAR(255) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status ENUM('Pending','Paid') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

ALTER TABLE orders
ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE contact_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    mobile VARCHAR(15) NOT NULL,
    email VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

show tables;
select *from users;
select *from menu;
select *from cart;
select *from orders;
select *from order_items;
select *from contact_messages;
select *from payment_history;

