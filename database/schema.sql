-- =============================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM — MySQL Database Schema
-- Version 2.0
-- Engine: MySQL 8.0+  |  Charset: utf8mb4  |  Collation: utf8mb4_unicode_ci
--
-- This schema mirrors the SQLAlchemy models in backend/models/ exactly, so
-- the Docker database and the application agree on table/column names.
-- Tables (10): users, suppliers, categories, products, sales, sale_items,
--              inventory_logs, reorder_predictions, iot_device_logs,
--              iot_devices, alert_resolutions
-- =============================================================================

CREATE DATABASE IF NOT EXISTS smart_inventory
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_inventory;

-- =============================================================================
-- TABLE 1: users
-- New accounts always get the least-privileged role ("viewer").
-- =============================================================================
CREATE TABLE users (
    id            INT           AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(80)   NOT NULL,
    email         VARCHAR(120)  NOT NULL,
    password_hash VARCHAR(255)  NOT NULL,
    role          VARCHAR(20)   NOT NULL DEFAULT 'viewer' COMMENT 'admin | manager | viewer',
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    last_login    DATETIME      DEFAULT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email)
) ENGINE=InnoDB COMMENT='System users and administrators';


-- =============================================================================
-- TABLE 2: suppliers
-- =============================================================================
CREATE TABLE suppliers (
    id              INT           AUTO_INCREMENT PRIMARY KEY,
    user_id         INT           NOT NULL,
    name            VARCHAR(200)  NOT NULL,
    contact_person  VARCHAR(100)  DEFAULT NULL,
    email           VARCHAR(120)  DEFAULT NULL,
    phone           VARCHAR(30)   DEFAULT NULL,
    address         TEXT          DEFAULT NULL,
    lead_time_days  INT           DEFAULT NULL,
    is_active       TINYINT(1)    NOT NULL DEFAULT 1,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_suppliers_user (user_id),
    INDEX idx_suppliers_name (name),
    CONSTRAINT fk_suppliers_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Vendor and supplier directory';


-- =============================================================================
-- TABLE 3: categories
-- Category names are unique per user (multi-tenant isolation).
-- =============================================================================
CREATE TABLE categories (
    id                  INT           AUTO_INCREMENT PRIMARY KEY,
    user_id             INT           NOT NULL,
    name                VARCHAR(100)  NOT NULL,
    description         VARCHAR(255)  DEFAULT NULL,
    parent_category_id  INT           DEFAULT NULL,
    sort_order          INT           NOT NULL DEFAULT 0,
    is_active           TINYINT(1)    NOT NULL DEFAULT 1,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_category_user_name (user_id, name),
    INDEX idx_categories_parent (parent_category_id),
    CONSTRAINT fk_categories_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_category_id) REFERENCES categories(id)
        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Product categories (user-scoped)';


-- =============================================================================
-- TABLE 4: products
-- SKU / barcode uniqueness is scoped per user so tenants can reuse codes.
-- =============================================================================
CREATE TABLE products (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    user_id         INT             NOT NULL,
    name            VARCHAR(200)    NOT NULL,
    sku             VARCHAR(50)     NOT NULL,
    description     TEXT            DEFAULT NULL,
    quantity        INT             NOT NULL DEFAULT 0,
    reorder_level   INT             NOT NULL DEFAULT 10,
    reorder_quantity INT            NOT NULL DEFAULT 0,
    unit_price      DECIMAL(10, 2)  NOT NULL,
    cost_price      DECIMAL(10, 2)  DEFAULT NULL,
    weight_kg       DECIMAL(8, 3)   DEFAULT NULL,
    category_id     INT             NOT NULL,
    category        VARCHAR(100)    DEFAULT 'General',
    supplier_id     INT             DEFAULT NULL,
    barcode         VARCHAR(100)    DEFAULT NULL,
    barcode_format  VARCHAR(20)     DEFAULT NULL,
    image_url       VARCHAR(500)    DEFAULT NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_products_quantity CHECK (quantity >= 0),
    CONSTRAINT chk_products_price CHECK (unit_price >= 0),

    UNIQUE KEY uq_product_user_sku (user_id, sku),
    UNIQUE KEY uq_product_user_barcode (user_id, barcode),
    INDEX idx_products_user (user_id),
    INDEX idx_products_name (name),
    INDEX idx_products_category (category_id),
    INDEX idx_products_supplier (supplier_id),
    INDEX idx_products_stock_status (quantity, reorder_level),

    CONSTRAINT fk_products_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_products_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Core inventory — all tracked products live here';


-- =============================================================================
-- TABLE 5: sales (headers)
-- =============================================================================
CREATE TABLE sales (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    invoice_number  VARCHAR(50)     DEFAULT NULL,
    sale_date       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount    DECIMAL(12, 2)  NOT NULL DEFAULT 0.00,
    discount_amount DECIMAL(12, 2)  NOT NULL DEFAULT 0.00,
    tax_amount      DECIMAL(12, 2)  NOT NULL DEFAULT 0.00,
    customer_name   VARCHAR(200)    DEFAULT NULL,
    customer_email  VARCHAR(120)    DEFAULT NULL,
    payment_method  VARCHAR(50)     DEFAULT 'cash',
    payment_status  VARCHAR(30)     NOT NULL DEFAULT 'paid',
    status          VARCHAR(20)     NOT NULL DEFAULT 'active',
    processed_by    INT             DEFAULT NULL,
    notes           TEXT            DEFAULT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_sales_date (sale_date),
    INDEX idx_sales_status (status),
    INDEX idx_sales_processor (processed_by),
    CONSTRAINT fk_sales_processor
        FOREIGN KEY (processed_by) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Sale transaction headers';


-- =============================================================================
-- TABLE 6: sale_items (line items)
-- =============================================================================
CREATE TABLE sale_items (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    sale_id         INT             NOT NULL,
    product_id      INT             NOT NULL,
    quantity        INT             NOT NULL DEFAULT 1,
    unit_price      DECIMAL(10, 2)  NOT NULL,
    discount        DECIMAL(10, 2)  NOT NULL DEFAULT 0.00,
    total_price     DECIMAL(12, 2)  NOT NULL,

    CONSTRAINT chk_item_quantity CHECK (quantity > 0),
    INDEX idx_sale_items_sale (sale_id),
    INDEX idx_sale_items_product (product_id),
    CONSTRAINT fk_items_sale
        FOREIGN KEY (sale_id) REFERENCES sales(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_items_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Line items belonging to each sale transaction';


-- =============================================================================
-- TABLE 7: inventory_logs
-- Immutable audit trail for every stock quantity change.
-- =============================================================================
CREATE TABLE inventory_logs (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    product_id      INT             NOT NULL,
    user_id         INT             DEFAULT NULL,
    movement_type   ENUM(
                        'sale_out', 'purchase_in', 'adjustment', 'return_in',
                        'damage_out', 'transfer_out', 'transfer_in', 'count_correct'
                    )               NOT NULL,
    quantity_change INT             NOT NULL,
    quantity_before INT             NOT NULL,
    quantity_after  INT             NOT NULL,
    reference_type  VARCHAR(50)     DEFAULT NULL,
    reference_id    INT             DEFAULT NULL,
    notes           TEXT            DEFAULT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_logs_product (product_id),
    INDEX idx_logs_user (user_id),
    INDEX idx_logs_date (created_at),
    CONSTRAINT fk_logs_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Immutable stock-change audit trail';


-- =============================================================================
-- TABLE 8: reorder_predictions
-- =============================================================================
CREATE TABLE reorder_predictions (
    id                     INT           AUTO_INCREMENT PRIMARY KEY,
    product_id             INT           NOT NULL,
    forecast_date          DATE          NOT NULL,
    predicted_daily_demand FLOAT         NOT NULL,
    predicted_weekly_demand FLOAT        NOT NULL,
    confidence_score       FLOAT         DEFAULT NULL,
    days_until_stockout    INT           DEFAULT NULL,
    suggested_reorder_qty  INT           DEFAULT NULL,
    model_version          VARCHAR(50)   DEFAULT NULL,
    alert_level            ENUM('GREEN', 'YELLOW', 'RED', 'BLACK') DEFAULT NULL,
    notes                  TEXT          DEFAULT NULL,
    created_at             DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_predictions_product (product_id),
    INDEX idx_predictions_date (forecast_date),
    CONSTRAINT fk_predictions_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Demand forecasts per product per future date';


-- =============================================================================
-- TABLE 9: iot_devices (registered hardware)
-- Devices authenticate to the ingest endpoint with their API key.
-- =============================================================================
CREATE TABLE iot_devices (
    id            INT           AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NOT NULL,
    device_id     VARCHAR(100)  NOT NULL,
    device_type   ENUM('barcode_scanner', 'rfid_reader', 'temperature_sensor', 'weight_scale', 'generic')
                                NOT NULL DEFAULT 'generic',
    api_key       VARCHAR(64)   NOT NULL,
    location      VARCHAR(200)  DEFAULT NULL,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_iot_device_user_device (user_id, device_id),
    UNIQUE KEY uq_iot_device_api_key (api_key),
    INDEX idx_iot_devices_user (user_id),
    CONSTRAINT fk_iot_devices_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Registered IoT hardware devices with API keys';


-- =============================================================================
-- TABLE 10: iot_device_logs
-- Every hardware event, bound to the owning user for multi-tenant isolation.
-- =============================================================================
CREATE TABLE iot_device_logs (
    id                BIGINT          AUTO_INCREMENT PRIMARY KEY,
    user_id           INT             NOT NULL,
    device_id         VARCHAR(100)    NOT NULL,
    device_type       ENUM('barcode_scanner', 'rfid_reader', 'temperature_sensor', 'weight_scale', 'generic')
                                      NOT NULL,
    event_type        ENUM('scan', 'tag_read', 'tag_lost', 'connect', 'disconnect', 'heartbeat', 'error', 'data')
                                      NOT NULL DEFAULT 'scan',
    product_id        INT             DEFAULT NULL,
    barcode_data      VARCHAR(255)    DEFAULT NULL,
    rfid_epc          VARCHAR(255)    DEFAULT NULL,
    rfid_antenna      INT             DEFAULT NULL,
    rssi              FLOAT           DEFAULT NULL,
    raw_payload       JSON            DEFAULT NULL,
    location          VARCHAR(200)    DEFAULT NULL,
    battery_level     FLOAT           DEFAULT NULL,
    firmware_version  VARCHAR(50)     DEFAULT NULL,
    is_processed      TINYINT(1)      NOT NULL DEFAULT 0,
    error_message     TEXT            DEFAULT NULL,
    created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_iot_device (device_id),
    INDEX idx_iot_user (user_id),
    INDEX idx_iot_product (product_id),
    INDEX idx_iot_processed (is_processed),
    INDEX idx_iot_date (created_at),
    CONSTRAINT fk_iot_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_iot_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='IoT hardware event log';


-- =============================================================================
-- TABLE 11: alert_resolutions
-- Acknowledged low-stock alerts (auditable, not a no-op).
-- =============================================================================
CREATE TABLE alert_resolutions (
    id          INT           AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    product_id  INT           NOT NULL,
    resolved_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes       VARCHAR(255)  DEFAULT NULL,

    UNIQUE KEY uq_alert_resolution_user_product (user_id, product_id),
    CONSTRAINT fk_alert_resolution_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_alert_resolution_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Acknowledged low-stock alerts';


-- =============================================================================
-- SAMPLE DATA
-- =============================================================================

-- 1. users — the seeded admin is used by scripts/seed_data.py's manual flow
INSERT INTO users (username, email, password_hash, role) VALUES
('admin',    'admin@inventory.com',  'scrypt:32768:8:1$placeholder$not-a-valid-hash-created-by-seed-script', 'admin'),
('manager1', 'manager@inventory.com','scrypt:32768:8:1$placeholder$not-a-valid-hash-created-by-seed-script', 'manager'),
('viewer1',  'viewer@inventory.com', 'scrypt:32768:8:1$placeholder$not-a-valid-hash-created-by-seed-script', 'viewer');

-- 2. suppliers
INSERT INTO suppliers (user_id, name, contact_person, email, phone, address, lead_time_days) VALUES
(1, 'TechDistributor Inc.',  'John Smith',   'john@techdist.com',   '555-0100', 'San Jose, USA', 7),
(1, 'FashionWholesale Ltd.', 'Sarah Lee',    'sarah@fashionwl.com', '555-0101', 'New York, USA', 14),
(1, 'FreshSupply Co.',       'Mike Brown',   'mike@freshsupply.com','555-0102', 'Chicago, USA',  3),
(1, 'GlobalParts GmbH',      'Hans Mueller', 'hans@globalparts.de', '+49-30-1234', 'Berlin, Germany', 21);

-- 3. categories
INSERT INTO categories (user_id, name, description, parent_category_id, sort_order) VALUES
(1, 'Electronics',     'Electronic devices and components',     NULL, 1),
(1, 'Clothing',        'Apparel, footwear, and accessories',   NULL, 2),
(1, 'Food & Beverage', 'Edible goods and drinks',              NULL, 3),
(1, 'Office Supplies', 'Stationery and workplace essentials',  NULL, 4),
(1, 'Cables',          'Charging and data cables',             1,    10),
(1, 'Audio',           'Headphones, speakers, earbuds',        1,    20);

-- 4. products
INSERT INTO products (user_id, name, sku, description, quantity, reorder_level, reorder_quantity, unit_price, cost_price, weight_kg, category_id, category, supplier_id, barcode, barcode_format) VALUES
(1, 'USB-C Cable 1m',      'ELEC-001', 'High-speed USB-C charging & sync cable, braided nylon', 150, 20, 50,  12.99, 5.50,  0.050, 5, 'Electronics', 1, '5901234567897', 'EAN-13'),
(1, 'Wireless Mouse',      'ELEC-002', 'Ergonomic Bluetooth 5.0 wireless mouse, silent clicks',  45,  10, 30,  29.99, 14.00, 0.120, 1, 'Electronics', 1, '5901234567903', 'EAN-13'),
(1, 'Bluetooth Earbuds',   'ELEC-003', 'True wireless stereo earbuds, 24h battery, IPX5',        22,  5,  20,  49.99, 22.00, 0.045, 6, 'Electronics', 1, '5901234567910', 'EAN-13'),
(1, 'Cotton T-Shirt (M)',  'CLTH-001', 'Premium organic cotton crew-neck t-shirt, medium',        80,  15, 40,  19.99, 8.00,  0.200, 2, 'Clothing',    2, '6901234567890', 'EAN-13'),
(1, 'Denim Jacket',        'CLTH-002', 'Classic denim jacket, unisex, indigo blue',                3,  5,  10,  59.99, 28.00, 0.800, 2, 'Clothing',    2, '6901234567906', 'EAN-13'),
(1, 'Running Shoes (US 9)','CLTH-003', 'Lightweight running shoes, mesh upper, cushioned sole',   12,  10, 15,  89.99, 40.00, 0.350, 2, 'Clothing',    2, '6901234567913', 'EAN-13'),
(1, 'Green Tea (50 bags)', 'FOOD-001', 'Organic Japanese green tea, 50 teabags per box',          200, 30, 100,  8.99,  3.50,  0.150, 3, 'Food & Beverage', 3, '4901234567894', 'EAN-13'),
(1, 'Sparkling Water Case','FOOD-002', '12-pack premium sparkling mineral water, 330ml cans',       60,  20, 50,  15.99,  7.00,  5.200, 3, 'Food & Beverage', 3, '4901234567900', 'EAN-13'),
(1, 'Dark Chocolate Bar',  'FOOD-003', '72% cacao dark chocolate, organic, 100g',                  5,  15, 30,   4.99,  2.00,  0.100, 3, 'Food & Beverage', 3, '4901234567917', 'EAN-13'),
(1, 'Ballpoint Pens (12pk)','OFFC-001','Blue ink ballpoint pens, medium tip, 12-pack',            500, 50, 200,  4.99,  1.50,  0.080, 4, 'Office Supplies', NULL, '8801234567890', 'EAN-13'),
(1, 'A4 Paper (500 sheets)','OFFC-002','80gsm multipurpose white A4 printer paper, 500 sheets',     30,  15, 30,   7.99,  3.80,  2.500, 4, 'Office Supplies', NULL, '8801234567906', 'EAN-13'),
(1, 'Stapler',             'OFFC-003', 'Heavy-duty stapler, 50-sheet capacity, black',               4,  10, 15,  14.99,  6.00,  0.400, 4, 'Office Supplies', NULL, '8801234567913', 'EAN-13');

-- 5. sales
INSERT INTO sales (invoice_number, sale_date, total_amount, customer_name, payment_method, processed_by) VALUES
('INV-2026-0001', '2026-05-01 10:30:00',  42.97, 'Alice Johnson', 'card', 1),
('INV-2026-0002', '2026-05-03 14:15:00',  29.99, 'Bob Williams',  'cash', 1),
('INV-2026-0003', '2026-05-05 09:00:00',  35.97, 'Carol Davis',   'card', 1),
('INV-2026-0004', '2026-05-10 16:45:00',  59.99, 'David Miller',  'bank_transfer', 1),
('INV-2026-0005', '2026-05-15 11:20:00',  24.97, 'Eve Wilson',    'cash', 1);

-- 6. sale_items
INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price) VALUES
(1, 1,  2, 12.99, 25.98),
(1, 7,  2,  8.99, 17.98),
(2, 2,  1, 29.99, 29.99),
(3, 10, 3,  4.99, 14.97),
(3, 7,  2,  8.99, 17.98),
(4, 5,  1, 59.99, 59.99),
(5, 11, 1,  7.99,  7.99),
(5, 1,  1, 12.99, 12.99),
(5, 10, 1,  4.99,  4.99);

-- 7. inventory_logs
INSERT INTO inventory_logs (product_id, user_id, quantity_before, quantity_change, quantity_after, movement_type, reference_type, notes) VALUES
(1,  1, 0,   150, 150, 'purchase_in', 'setup', 'Initial inventory setup'),
(2,  1, 0,   45,  45,  'purchase_in', 'setup', 'Initial inventory setup'),
(3,  1, 0,   22,  22,  'purchase_in', 'setup', 'Initial inventory setup'),
(4,  1, 0,   80,  80,  'purchase_in', 'setup', 'Initial inventory setup'),
(5,  1, 0,   3,   3,   'purchase_in', 'setup', 'Initial inventory setup'),
(6,  1, 0,   12,  12,  'purchase_in', 'setup', 'Initial inventory setup'),
(7,  1, 0,   200, 200, 'purchase_in', 'setup', 'Initial inventory setup'),
(8,  1, 0,   60,  60,  'purchase_in', 'setup', 'Initial inventory setup'),
(9,  1, 0,   5,   5,   'purchase_in', 'setup', 'Initial inventory setup'),
(10, 1, 0,   500, 500, 'purchase_in', 'setup', 'Initial inventory setup'),
(11, 1, 0,   30,  30,  'purchase_in', 'setup', 'Initial inventory setup'),
(12, 1, 0,   4,   4,   'purchase_in', 'setup', 'Initial inventory setup');

-- 8. reorder_predictions (sample forecasts)
INSERT INTO reorder_predictions (product_id, forecast_date, predicted_daily_demand, predicted_weekly_demand, confidence_score, alert_level, model_version) VALUES
(1, '2026-05-26', 3.5,  24.5, 0.92, 'GREEN',  'v1.0'),
(1, '2026-05-27', 4.1,  28.7, 0.91, 'GREEN',  'v1.0'),
(1, '2026-05-28', 2.8,  19.6, 0.89, 'GREEN',  'v1.0'),
(5, '2026-05-26', 0.5,   3.5, 0.75, 'YELLOW', 'v1.0'),
(5, '2026-05-27', 0.3,   2.1, 0.72, 'YELLOW', 'v1.0'),
(5, '2026-05-28', 1.0,   7.0, 0.70, 'YELLOW', 'v1.0'),
(7, '2026-05-26', 8.0,  56.0, 0.94, 'GREEN',  'v1.0'),
(7, '2026-05-27', 7.5,  52.5, 0.93, 'GREEN',  'v1.0'),
(7, '2026-05-28', 9.2,  64.4, 0.92, 'GREEN',  'v1.0');

-- 9. iot_device_logs (sample events bound to user 1)
INSERT INTO iot_device_logs (user_id, device_id, device_type, event_type, product_id, barcode_data, rfid_epc, rssi, location, is_processed, raw_payload) VALUES
(1, 'SCANNER-WH001', 'barcode_scanner', 'scan',      1,  '5901234567897', NULL, NULL,     'Warehouse-A', 0, JSON_OBJECT('device', 'SCANNER-WH001')),
(1, 'SCANNER-WH001', 'barcode_scanner', 'scan',      7,  '4901234567894', NULL, NULL,     'Warehouse-A', 0, JSON_OBJECT('device', 'SCANNER-WH001')),
(1, 'RFID-GATE-01',  'rfid_reader',     'tag_read',  10, NULL,            'E280689400004002', -68.5, 'Loading-Dock', 0, JSON_OBJECT('device', 'RFID-GATE-01')),
(1, 'RFID-GATE-01',  'rfid_reader',     'tag_lost',  NULL, NULL,          'E280689400004002', -85.0, 'Loading-Dock', 0, JSON_OBJECT('device', 'RFID-GATE-01')),
(1, 'SCANNER-RT01',  'barcode_scanner', 'connect',   NULL, NULL,          NULL,         NULL,     'Retail-Floor', 0, JSON_OBJECT('device', 'SCANNER-RT01')),
(1, 'TEMP-SENSOR-1', 'temperature_sensor','data',    NULL, NULL,          NULL,         NULL,     'Cold-Storage', 0, JSON_OBJECT('device', 'TEMP-SENSOR-1'));

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================