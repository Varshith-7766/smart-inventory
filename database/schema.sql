-- =============================================================================
-- SMART INVENTORY MANAGEMENT SYSTEM — MySQL Database Schema
-- Version 1.0
-- Engine: MySQL 8.0+  |  Charset: utf8mb4  |  Collation: utf8mb4_unicode_ci
-- =============================================================================
-- TABLES:
--   1. users              — Admin/operator authentication
--   2. suppliers          — Vendor directory
--   3. categories         — Product taxonomy
--   4. products           — Core inventory (barcode-ready)
--   5. sales_history      — Sale transactions (header + line items)
--   6. inventory_logs     — Audit trail for all stock changes
--   7. reorder_predictions — ML forecast outputs
--   8. iot_device_logs    — Barcode scanner / RFID reader events
-- =============================================================================

CREATE DATABASE IF NOT EXISTS smart_inventory
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_inventory;

-- =============================================================================
-- TABLE 1: users
-- Purpose: Stores admin credentials and access control.
-- Relationships:
--   - Referenced by: sales_history (who recorded the sale)
--   - Referenced by: inventory_logs (who performed the adjustment)
-- =============================================================================
CREATE TABLE users (
    id            INT           AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique user identifier',
    username      VARCHAR(80)   NOT NULL                     COMMENT 'Login username',
    email         VARCHAR(120)  NOT NULL                     COMMENT 'User email address',
    password_hash VARCHAR(255)  NOT NULL                     COMMENT 'bcrypt hash of the password',
    role          ENUM('admin', 'manager', 'viewer')
                                NOT NULL DEFAULT 'admin'    COMMENT 'Access level',
    is_active     TINYINT(1)    NOT NULL DEFAULT 1           COMMENT 'Soft-delete flag (0 = disabled)',
    last_login    DATETIME      DEFAULT NULL                 COMMENT 'Timestamp of most recent login',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_active (is_active)
) ENGINE=InnoDB COMMENT='System users and administrators';


-- =============================================================================
-- TABLE 2: suppliers
-- Purpose: Directory of product vendors / suppliers.
-- Relationships:
--   - One-to-many with: products (a supplier can provide many products)
-- =============================================================================
CREATE TABLE suppliers (
    id              INT           AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique supplier identifier',
    name            VARCHAR(200)  NOT NULL                     COMMENT 'Company or individual name',
    contact_person  VARCHAR(100)  DEFAULT NULL                 COMMENT 'Primary point of contact',
    email           VARCHAR(120)  DEFAULT NULL                 COMMENT 'Contact email address',
    phone           VARCHAR(30)   DEFAULT NULL                 COMMENT 'Contact phone number',
    address_line1   VARCHAR(255)  DEFAULT NULL                 COMMENT 'Street address',
    address_line2   VARCHAR(255)  DEFAULT NULL                 COMMENT 'Apartment / suite / unit',
    city            VARCHAR(100)  DEFAULT NULL,
    state           VARCHAR(100)  DEFAULT NULL,
    postal_code     VARCHAR(20)   DEFAULT NULL,
    country         VARCHAR(100)  DEFAULT NULL,
    payment_terms   VARCHAR(100)  DEFAULT NULL                 COMMENT 'e.g. Net-30, Net-60',
    lead_time_days  INT UNSIGNED  DEFAULT NULL                 COMMENT 'Average days from order to delivery',
    is_active       TINYINT(1)    NOT NULL DEFAULT 1           COMMENT 'Soft-delete flag',
    notes           TEXT          DEFAULT NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_suppliers_name (name),
    INDEX idx_suppliers_active (is_active),
    INDEX idx_suppliers_city (city)
) ENGINE=InnoDB COMMENT='Vendor and supplier directory';


-- =============================================================================
-- TABLE 3: categories
-- Purpose: Product taxonomy for grouping and filtering.
-- Relationships:
--   - One-to-many with: products (each product belongs to one category)
--   - Self-referencing via parent_category_id for sub-categories
-- =============================================================================
CREATE TABLE categories (
    id                  INT           AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique category identifier',
    name                VARCHAR(100)  NOT NULL                     COMMENT 'Category display name',
    description         VARCHAR(255)  DEFAULT NULL                 COMMENT 'Short description of the category',
    parent_category_id  INT           DEFAULT NULL                 COMMENT 'NULL = top-level; otherwise parent category ID',
    sort_order          INT           NOT NULL DEFAULT 0           COMMENT 'Display ordering (lower = first)',
    is_active           TINYINT(1)    NOT NULL DEFAULT 1,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_category_name (name),
    INDEX idx_categories_parent (parent_category_id),
    INDEX idx_categories_active (is_active),
    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_category_id) REFERENCES categories(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Product categories (supports hierarchy via parent_category_id)';


-- =============================================================================
-- TABLE 4: products
-- Purpose: Core inventory table. Every physical or virtual item is a row here.
-- Relationships:
--   - Many-to-one with: categories (via category_id)
--   - Many-to-one with: suppliers (via supplier_id)
--   - One-to-many with: sales_history_items (line items in a sale)
--   - One-to-many with: inventory_logs (stock change audit trail)
--   - One-to-many with: reorder_predictions (forecast records)
--   - One-to-many with: iot_device_logs (scanner events for this product)
-- IoT Ready: barcode column indexed for scanner lookups.
-- =============================================================================
CREATE TABLE products (
    id              INT             AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique product identifier',
    name            VARCHAR(200)    NOT NULL                     COMMENT 'Product display name',
    sku             VARCHAR(50)     NOT NULL                     COMMENT 'Stock Keeping Unit (unique internal code)',
    description     TEXT            DEFAULT NULL                 COMMENT 'Detailed product description',
    quantity        INT             NOT NULL DEFAULT 0           COMMENT 'Current stock on hand (must be >= 0)',
    reorder_level   INT             NOT NULL DEFAULT 10          COMMENT 'Stock level that triggers a low-stock alert',
    reorder_quantity INT            NOT NULL DEFAULT 0           COMMENT 'Recommended qty to order when reordering',
    unit_price      DECIMAL(10, 2)  NOT NULL                     COMMENT 'Current selling price per unit',
    cost_price      DECIMAL(10, 2)  DEFAULT NULL                 COMMENT 'Purchase cost per unit (for profit calc)',
    weight_kg       DECIMAL(8, 3)   DEFAULT NULL                 COMMENT 'Physical weight for shipping calculations',
    category_id     INT             NOT NULL                     COMMENT 'FK to categories table',
    supplier_id     INT             DEFAULT NULL                 COMMENT 'FK to suppliers table (primary supplier)',
    barcode         VARCHAR(100)    DEFAULT NULL                 COMMENT 'EAN-13 / UPC-A / QR code for scanner',
    barcode_format  VARCHAR(20)     DEFAULT NULL                 COMMENT 'e.g. EAN-13, UPC-A, QR, CODE128',
    image_url       VARCHAR(500)    DEFAULT NULL                 COMMENT 'URL to product image',
    is_active       TINYINT(1)      NOT NULL DEFAULT 1           COMMENT 'Soft-delete flag (0 = archived)',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Prevent negative stock
    CONSTRAINT chk_products_quantity CHECK (quantity >= 0),
    CONSTRAINT chk_products_price CHECK (unit_price >= 0),

    UNIQUE KEY uk_sku (sku),
    UNIQUE KEY uk_barcode (barcode),

    -- Performance indexes
    INDEX idx_products_name (name),
    INDEX idx_products_category (category_id),
    INDEX idx_products_supplier (supplier_id),
    INDEX idx_products_active (is_active),
    INDEX idx_products_stock_status (quantity, reorder_level),

    -- Fulltext index for product search
    FULLTEXT INDEX ft_products_search (name, description),

    -- Foreign keys
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_products_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Core inventory — all tracked products live here';


-- =============================================================================
-- TABLE 5a: sales_history (header)
-- Purpose: Each row is one sale transaction (header-level data).
-- Relationships:
--   - One-to-many with: sales_history_items (line items in this sale)
--   - Many-to-one with: users (who processed the sale)
-- =============================================================================
CREATE TABLE sales_history (
    id              INT             AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique sale transaction ID',
    invoice_number VARCHAR(50)      DEFAULT NULL                 COMMENT 'Human-readable invoice reference',
    sale_date       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When the sale occurred',
    total_amount    DECIMAL(12, 2)  NOT NULL                     COMMENT 'Sum of all line-item totals',
    discount_amount DECIMAL(12, 2)  NOT NULL DEFAULT 0.00        COMMENT 'Discount applied to the whole sale',
    tax_amount      DECIMAL(12, 2)  NOT NULL DEFAULT 0.00        COMMENT 'Total tax applied',
    grand_total     DECIMAL(12, 2)  GENERATED ALWAYS AS (total_amount - discount_amount + tax_amount) STORED COMMENT 'Final amount charged',
    customer_name   VARCHAR(200)    DEFAULT NULL                 COMMENT 'Optional customer identifier',
    customer_email  VARCHAR(120)    DEFAULT NULL                 COMMENT 'For digital receipts',
    payment_method  ENUM('cash', 'card', 'bank_transfer', 'credit', 'other')
                                    DEFAULT 'cash'               COMMENT 'How payment was collected',
    payment_status  ENUM('pending', 'paid', 'refunded', 'partially_refunded')
                                    NOT NULL DEFAULT 'paid'      COMMENT 'Payment lifecycle state',
    processed_by    INT             DEFAULT NULL                 COMMENT 'FK to users (who processed this sale)',
    notes           TEXT            DEFAULT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_sales_date (sale_date),
    INDEX idx_sales_customer (customer_name),
    INDEX idx_sales_payment_status (payment_status),
    INDEX idx_sales_processor (processed_by),

    CONSTRAINT fk_sales_processor
        FOREIGN KEY (processed_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Sale transaction headers';


-- =============================================================================
-- TABLE 5b: sales_history_items (line items)
-- Purpose: Individual product lines within each sale.
-- Relationships:
--   - Many-to-one with: sales_history (via sale_id)
--   - Many-to-one with: products (via product_id)
-- =============================================================================
CREATE TABLE sales_history_items (
    id              INT             AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique line-item identifier',
    sale_id         INT             NOT NULL                     COMMENT 'FK to sales_history',
    product_id      INT             NOT NULL                     COMMENT 'FK to products',
    quantity        INT             NOT NULL                     COMMENT 'Number of units sold',
    unit_price      DECIMAL(10, 2)  NOT NULL                     COMMENT 'Price per unit at time of sale',
    discount        DECIMAL(10, 2)  NOT NULL DEFAULT 0.00        COMMENT 'Per-line discount',
    total_price     DECIMAL(12, 2)  GENERATED ALWAYS AS ((unit_price * quantity) - discount) STORED COMMENT 'Line total after discount',

    CONSTRAINT chk_item_quantity CHECK (quantity > 0),
    CONSTRAINT chk_item_price CHECK (unit_price >= 0),

    INDEX idx_sale_items_sale (sale_id),
    INDEX idx_sale_items_product (product_id),

    CONSTRAINT fk_items_sale
        FOREIGN KEY (sale_id) REFERENCES sales_history(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_items_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Line items belonging to each sale transaction';


-- =============================================================================
-- TABLE 6: inventory_logs
-- Purpose: Immutable audit trail for every stock quantity change.
--          Enables traceability, reporting, and rollback analysis.
-- Relationships:
--   - Many-to-one with: products (via product_id)
--   - Many-to-one with: users (who made the change)
-- =============================================================================
CREATE TABLE inventory_logs (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique log entry (BIGINT for high volume)',
    product_id      INT             NOT NULL                     COMMENT 'FK to products',
    quantity_before INT             NOT NULL                     COMMENT 'Stock level BEFORE the change',
    quantity_change INT             NOT NULL                     COMMENT 'Change amount (+ = inward, - = outward)',
    quantity_after  INT             NOT NULL                     COMMENT 'Stock level AFTER the change',
    movement_type   ENUM(
                        'purchase_in',
                        'sale_out',
                        'return_in',
                        'return_out',
                        'adjustment',
                        'transfer_out',
                        'transfer_in',
                        'damage',
                        'expiry',
                        'initial_stock',
                        'correction'
                    )               NOT NULL                     COMMENT 'Category of the movement',
    reference_type  VARCHAR(50)     DEFAULT NULL                 COMMENT 'Entity type that triggered this (sale, purchase, etc.)',
    reference_id    INT             DEFAULT NULL                 COMMENT 'ID of the triggering entity',
    reason          VARCHAR(255)    DEFAULT NULL                 COMMENT 'Free-text explanation for the change',
    performed_by    INT             DEFAULT NULL                 COMMENT 'FK to users (NULL = system auto-action)',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Prevent illogical changes
    CONSTRAINT chk_log_quantity_before CHECK (quantity_before >= 0),
    CONSTRAINT chk_log_quantity_after  CHECK (quantity_after >= 0),
    CONSTRAINT chk_log_change_not_zero CHECK (quantity_change != 0),

    INDEX idx_logs_product (product_id),
    INDEX idx_logs_movement_type (movement_type),
    INDEX idx_logs_date (created_at),
    INDEX idx_logs_performer (performed_by),

    -- Composite index for product-level audit queries
    INDEX idx_logs_product_date (product_id, created_at),

    CONSTRAINT fk_logs_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_logs_user
        FOREIGN KEY (performed_by) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Immutable stock-change audit trail — every add/remove is logged';


-- =============================================================================
-- TABLE 7: reorder_predictions
-- Purpose: Stores ML-generated demand forecasts per product per future date.
--          Used by the dashboard to suggest restocking.
-- Relationships:
--   - Many-to-one with: products (via product_id)
-- =============================================================================
CREATE TABLE reorder_predictions (
    id                INT           AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique prediction record',
    product_id        INT           NOT NULL                     COMMENT 'FK to products',
    predicted_demand  DECIMAL(10, 2) NOT NULL                    COMMENT 'Forecasted units needed',
    confidence_score  DECIMAL(5, 4) DEFAULT NULL                 COMMENT 'Model confidence (0.0000 - 1.0000)',
    forecast_date     DATE          NOT NULL                     COMMENT 'The date this prediction applies to',
    model_version     VARCHAR(50)   DEFAULT 'v1.0'               COMMENT 'Which model version produced this',
    features_hash     VARCHAR(64)   DEFAULT NULL                 COMMENT 'Hash of input features (for debugging)',
    generated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_pred_demand CHECK (predicted_demand >= 0),
    CONSTRAINT chk_confidence CHECK (confidence_score BETWEEN 0 AND 1),

    UNIQUE KEY uk_prediction_product_date (product_id, forecast_date),

    INDEX idx_predictions_product (product_id),
    INDEX idx_predictions_date (forecast_date),
    INDEX idx_predictions_model (model_version),

    CONSTRAINT fk_predictions_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='ML-based demand forecasts per product per future date';


-- =============================================================================
-- TABLE 8: iot_device_logs
-- Purpose: Records every hardware event from barcode scanners, RFID readers,
--          or other IoT peripherals. Enables traceability, debugging, and
--          real-time inventory event processing.
-- Relationships:
--   - Many-to-one with: products (if the scanned tag maps to a known product)
--   - Many-to-one with: users (if the device is associated with an operator)
-- IoT Ready: Stores raw payload + device metadata for any peripheral type.
-- =============================================================================
CREATE TABLE iot_device_logs (
    id                BIGINT          AUTO_INCREMENT PRIMARY KEY  COMMENT 'Unique event ID (BIGINT for high-frequency IoT data)',
    device_id         VARCHAR(100)    NOT NULL                     COMMENT 'Unique identifier of the hardware device',
    device_type       ENUM('barcode_scanner', 'rfid_reader', 'temperature_sensor', 'weight_scale', 'generic')
                                      NOT NULL                     COMMENT 'Class of IoT device',
    event_type        ENUM('scan', 'tag_read', 'tag_lost', 'connect', 'disconnect', 'heartbeat', 'error', 'data')
                                      NOT NULL DEFAULT 'scan'      COMMENT 'Type of event',
    product_id        INT             DEFAULT NULL                 COMMENT 'FK to products (resolved by lookup)',
    barcode_data      VARCHAR(255)    DEFAULT NULL                 COMMENT 'Raw barcode or RFID tag value scanned',
    rfid_epc          VARCHAR(255)    DEFAULT NULL                 COMMENT 'RFID Electronic Product Code (if applicable)',
    rfid_antenna      INT             DEFAULT NULL                 COMMENT 'Which antenna detected the tag (1-4)',
    rssi              DECIMAL(8, 2)   DEFAULT NULL                 COMMENT 'Signal strength in dBm',
    raw_payload       JSON            DEFAULT NULL                 COMMENT 'Full raw payload from the device for future reprocessing',
    location          VARCHAR(200)    DEFAULT NULL                 COMMENT 'Physical location of the device / event',
    battery_level     DECIMAL(5, 2)   DEFAULT NULL                 COMMENT 'Device battery % (0.00 - 100.00)',
    firmware_version  VARCHAR(50)     DEFAULT NULL                 COMMENT 'Device firmware at time of event',
    is_processed      TINYINT(1)      NOT NULL DEFAULT 0            COMMENT '0 = awaiting processing, 1 = handled by business logic',
    error_message     TEXT            DEFAULT NULL                 COMMENT 'Error details if event_type = error',
    created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_iot_device (device_id),
    INDEX idx_iot_device_type (device_type),
    INDEX idx_iot_event_type (event_type),
    INDEX idx_iot_product (product_id),
    INDEX idx_iot_processed (is_processed),
    INDEX idx_iot_date (created_at),

    -- Composite for dashboard queries: unprocessed events by device
    INDEX idx_iot_device_pending (device_id, is_processed, created_at),

    CONSTRAINT fk_iot_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='IoT hardware event log — barcode scans, RFID reads, sensor data';


-- =============================================================================
-- INDEX USAGE SUMMARY
-- =============================================================================
-- Table                  | Indexes                                                | Purpose
-- -----------------------|--------------------------------------------------------|-------------------------------------------
-- users                  | uk_username, uk_email, idx_users_role, idx_users_active | Login speed, role filtering
-- suppliers              | idx_suppliers_name, idx_suppliers_active, idx_city     | Search, active-only queries
-- categories             | uk_category_name, idx_categories_parent                 | Taxonomy lookup, hierarchy traversal
-- products               | uk_sku, uk_barcode, idx_name, ft_products_search       | Fast lookup, search-as-you-type
--                        | idx_stock_status                                       | Low-stock alert queries
-- sales_history          | idx_sales_date, idx_customer, idx_payment_status       | Date-range reports, customer search
-- sales_history_items    | idx_sale_items_sale, idx_sale_items_product            | Sale detail drill-down, product sales
-- inventory_logs         | idx_logs_product_date (composite)                      | Product-level audit trail queries
--                        | idx_logs_movement_type, idx_logs_date                  | Aggregation reports
-- reorder_predictions    | uk_prediction_product_date (unique composite)          | Upsert forecasts, avoid duplicates
-- iot_device_logs        | idx_iot_device_pending (composite)                     | Process pending events per device
--                        | idx_iot_product, idx_iot_date                          | Product-scan history, time-series
-- =============================================================================


-- =============================================================================
-- SAMPLE DATA — 50+ realistic records
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. users (3 records)
-- ---------------------------------------------------------------------------
INSERT INTO users (username, email, password_hash, role) VALUES
('admin',     'admin@inventory.com',  '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Yq8d5G0x3H6j9K0LmNqO', 'admin'),
('manager1',  'manager@inventory.com','$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Yq8d5G0x3H6j9K0LmNqO', 'manager'),
('viewer1',   'viewer@inventory.com', '$2b$12$LJ3m4ys3Lk0TSwHnbfOMiOXPm1Qlq5Gz0Yq8d5G0x3H6j9K0LmNqO', 'viewer');

-- ---------------------------------------------------------------------------
-- 2. suppliers (4 records)
-- ---------------------------------------------------------------------------
INSERT INTO suppliers (name, contact_person, email, phone, city, country, lead_time_days, payment_terms) VALUES
('TechDistributor Inc.',   'John Smith',   'john@techdist.com',    '555-0100', 'San Jose',  'USA',  7,  'Net-30'),
('FashionWholesale Ltd.',  'Sarah Lee',    'sarah@fashionwl.com',  '555-0101', 'New York',  'USA',  14,  'Net-45'),
('FreshSupply Co.',        'Mike Brown',   'mike@freshsupply.com', '555-0102', 'Chicago',   'USA',  3,   'Net-15'),
('GlobalParts GmbH',       'Hans Mueller', 'hans@globalparts.de',  '+49-30-1234','Berlin',   'Germany', 21, 'Net-60');

-- ---------------------------------------------------------------------------
-- 3. categories (with parent-child hierarchy)
-- ---------------------------------------------------------------------------
INSERT INTO categories (id, name, description, parent_category_id, sort_order) VALUES
(1, 'Electronics',    'Electronic devices and components',     NULL, 1),
(2, 'Clothing',       'Apparel, footwear, and accessories',   NULL, 2),
(3, 'Food & Beverage','Edible goods and drinks',              NULL, 3),
(4, 'Office Supplies','Stationery and workplace essentials',   NULL, 4),
(5, 'Cables',         'Charging and data cables',             1,    10),
(6, 'Audio',          'Headphones, speakers, earbuds',        1,    20),
(7, 'Men''s Clothing','Apparel for men',                      2,    10),
(8, 'Women''s Clothing','Apparel for women',                  2,    20);

-- ---------------------------------------------------------------------------
-- 4. products (12 records with realistic data, including IoT barcodes)
-- ---------------------------------------------------------------------------
INSERT INTO products (name, sku, description, quantity, reorder_level, reorder_quantity, unit_price, cost_price, weight_kg, category_id, supplier_id, barcode, barcode_format) VALUES
('USB-C Cable 1m',         'ELEC-001', 'High-speed USB-C charging & sync cable, braided nylon', 150, 20, 50,  12.99, 5.50,  0.050, 5, 1, '5901234567897', 'EAN-13'),
('Wireless Mouse',         'ELEC-002', 'Ergonomic Bluetooth 5.0 wireless mouse, silent clicks',  45,  10, 30,  29.99, 14.00, 0.120, 1, 1, '5901234567903', 'EAN-13'),
('Bluetooth Earbuds',      'ELEC-003', 'True wireless stereo earbuds, 24h battery, IPX5',        22,  5,  20,  49.99, 22.00, 0.045, 6, 1, '5901234567910', 'EAN-13'),
('Cotton T-Shirt (M)',     'CLTH-001', 'Premium organic cotton crew-neck t-shirt, medium',        80,  15, 40,  19.99, 8.00,  0.200, 7, 2, '6901234567890', 'EAN-13'),
('Denim Jacket',           'CLTH-002', 'Classic denim jacket, unisex, indigo blue',                3,  5,  10,  59.99, 28.00, 0.800, 7, 2, '6901234567906', 'EAN-13'),
('Running Shoes (US 9)',   'CLTH-003', 'Lightweight running shoes, mesh upper, cushioned sole',   12,  10, 15,  89.99, 40.00, 0.350, 7, 2, '6901234567913', 'EAN-13'),
('Green Tea (50 bags)',    'FOOD-001', 'Organic Japanese green tea, 50 teabags per box',          200, 30, 100,  8.99,  3.50,  0.150, 3, 3, '4901234567894', 'EAN-13'),
('Sparkling Water Case',   'FOOD-002', '12-pack premium sparkling mineral water, 330ml cans',       60,  20, 50,  15.99,  7.00,  5.200, 3, 3, '4901234567900', 'EAN-13'),
('Dark Chocolate Bar',     'FOOD-003', '72% cacao dark chocolate, organic, 100g',                  5,  15, 30,   4.99,  2.00,  0.100, 3, 3, '4901234567917', 'EAN-13'),
('Ballpoint Pens (12pk)',  'OFFC-001', 'Blue ink ballpoint pens, medium tip, 12-pack',            500, 50, 200,  4.99,  1.50,  0.080, 4, NULL, '8801234567890', 'EAN-13'),
('A4 Paper (500 sheets)',  'OFFC-002', '80gsm multipurpose white A4 printer paper, 500 sheets',     30,  15, 30,   7.99,  3.80,  2.500, 4, NULL, '8801234567906', 'EAN-13'),
('Stapler',                'OFFC-003', 'Heavy-duty stapler, 50-sheet capacity, black',               4,  10, 15,  14.99,  6.00,  0.400, 4, NULL, '8801234567913', 'EAN-13');

-- ---------------------------------------------------------------------------
-- 5. sales_history (5 transaction headers)
-- ---------------------------------------------------------------------------
INSERT INTO sales_history (invoice_number, sale_date, total_amount, customer_name, payment_method, processed_by) VALUES
('INV-2026-0001', '2026-05-01 10:30:00',  42.97, 'Alice Johnson',   'card', 1),
('INV-2026-0002', '2026-05-03 14:15:00',  29.99, 'Bob Williams',    'cash', 1),
('INV-2026-0003', '2026-05-05 09:00:00',  35.97, 'Carol Davis',     'card', 2),
('INV-2026-0004', '2026-05-10 16:45:00',  59.99, 'David Miller',    'bank_transfer', 2),
('INV-2026-0005', '2026-05-15 11:20:00',  24.97, 'Eve Wilson',      'cash', 1);

-- ---------------------------------------------------------------------------
-- 5b. sales_history_items (11 line items across the 5 sales)
-- ---------------------------------------------------------------------------
INSERT INTO sales_history_items (sale_id, product_id, quantity, unit_price) VALUES
-- Sale 1: 2x USB-C Cable + 2x Green Tea
(1, 1, 2, 12.99),
(1, 7, 2,  8.99),
-- Sale 2: 1x Wireless Mouse
(2, 2, 1, 29.99),
-- Sale 3: 3x Pens + 2x Green Tea
(3, 10, 3, 4.99),
(3, 7,  2, 8.99),
-- Sale 4: 1x Denim Jacket
(4, 5, 1, 59.99),
-- Sale 5: 1x A4 Paper + 1x USB-C Cable + 1x Pens
(5, 11, 1, 7.99),
(5, 1,  1, 12.99),
(5, 10, 1, 4.99);

-- ---------------------------------------------------------------------------
-- 6. inventory_logs (14 stock movement records)
-- ---------------------------------------------------------------------------
-- Initial stock (one per product)
INSERT INTO inventory_logs (product_id, quantity_before, quantity_change, quantity_after, movement_type, reference_type, reason, performed_by) VALUES
(1,  0,   150,  150, 'initial_stock', 'setup',   'Initial inventory setup', 1),
(2,  0,   45,   45,  'initial_stock', 'setup',   'Initial inventory setup', 1),
(3,  0,   22,   22,  'initial_stock', 'setup',   'Initial inventory setup', 1),
(4,  0,   80,   80,  'initial_stock', 'setup',   'Initial inventory setup', 1),
(5,  0,   3,    3,   'initial_stock', 'setup',   'Initial inventory setup', 1),
(6,  0,   12,   12,  'initial_stock', 'setup',   'Initial inventory setup', 1),
(7,  0,   200,  200, 'initial_stock', 'setup',   'Initial inventory setup', 1),
(8,  0,   60,   60,  'initial_stock', 'setup',   'Initial inventory setup', 1),
(9,  0,   5,    5,   'initial_stock', 'setup',   'Initial inventory setup', 1),
(10, 0,   500,  500, 'initial_stock', 'setup',   'Initial inventory setup', 1),
(11, 0,   30,   30,  'initial_stock', 'setup',   'Initial inventory setup', 1),
(12, 0,   4,    4,   'initial_stock', 'setup',   'Initial inventory setup', 1),

-- Sale deduction (automatic from sale #1)
(1,  150, -2,  148,  'sale_out', 'sale', 'Sale INV-2026-0001', NULL),
(7,  200, -2,  198,  'sale_out', 'sale', 'Sale INV-2026-0001', NULL);

-- ---------------------------------------------------------------------------
-- 7. reorder_predictions (sample ML forecasts for 3 products × 7 days)
-- ---------------------------------------------------------------------------
INSERT INTO reorder_predictions (product_id, predicted_demand, confidence_score, forecast_date, model_version) VALUES
-- USB-C Cable: strong, steady demand
(1, 3.50, 0.92, '2026-05-26', 'v1.0'),
(1, 4.10, 0.91, '2026-05-27', 'v1.0'),
(1, 2.80, 0.89, '2026-05-28', 'v1.0'),
(1, 5.20, 0.88, '2026-05-29', 'v1.0'),
(1, 6.00, 0.85, '2026-05-30', 'v1.0'),
(1, 3.90, 0.90, '2026-05-31', 'v1.0'),
(1, 4.50, 0.91, '2026-06-01', 'v1.0'),

-- Denim Jacket: low, sporadic demand (already at risk)
(5, 0.50, 0.75, '2026-05-26', 'v1.0'),
(5, 0.30, 0.72, '2026-05-27', 'v1.0'),
(5, 1.00, 0.70, '2026-05-28', 'v1.0'),
(5, 0.80, 0.68, '2026-05-29', 'v1.0'),
(5, 0.40, 0.65, '2026-05-30', 'v1.0'),
(5, 0.60, 0.71, '2026-05-31', 'v1.0'),
(5, 0.90, 0.73, '2026-06-01', 'v1.0'),

-- Green Tea: steady everyday demand
(7, 8.00, 0.94, '2026-05-26', 'v1.0'),
(7, 7.50, 0.93, '2026-05-27', 'v1.0'),
(7, 9.20, 0.92, '2026-05-28', 'v1.0'),
(7, 6.80, 0.91, '2026-05-29', 'v1.0'),
(7, 10.50,0.90, '2026-05-30', 'v1.0'),
(7, 8.30, 0.93, '2026-05-31', 'v1.0'),
(7, 7.90, 0.94, '2026-06-01', 'v1.0');

-- ---------------------------------------------------------------------------
-- 8. iot_device_logs (6 sample hardware events)
-- ---------------------------------------------------------------------------
INSERT INTO iot_device_logs (device_id, device_type, event_type, product_id, barcode_data, rfid_epc, rssi, location, is_processed, raw_payload) VALUES
('SCANNER-WH001', 'barcode_scanner', 'scan',      1,  '5901234567897', NULL,         NULL,   'Warehouse-A', 0, '{"device":"SCANNER-WH001","timestamp":"2026-05-26T08:15:00Z","scan_value":"5901234567897","decoded":"USB-C Cable 1m"}'),
('SCANNER-WH001', 'barcode_scanner', 'scan',      7,  '4901234567894', NULL,         NULL,   'Warehouse-A', 0, '{"device":"SCANNER-WH001","timestamp":"2026-05-26T08:16:30Z","scan_value":"4901234567894","decoded":"Green Tea"}'),
('RFID-GATE-01',  'rfid_reader',     'tag_read',  10, NULL,            'E280689400004002', -68.5, 'Loading-Dock', 0, '{"device":"RFID-GATE-01","antenna":2,"tags":["E280689400004002"],"rssi":-68.5,"timestamp":"2026-05-26T09:00:00Z"}'),
('RFID-GATE-01',  'rfid_reader',     'tag_lost',  NULL,NULL,            'E280689400004002', -85.0, 'Loading-Dock', 0, '{"device":"RFID-GATE-01","antenna":2,"tag":"E280689400004002","rssi":-85.0,"event":"tag_lost","timestamp":"2026-05-26T09:00:12Z"}'),
('SCANNER-RT01',  'barcode_scanner', 'connect',   NULL,NULL,            NULL,         NULL,   'Retail-Floor', 0, '{"device":"SCANNER-RT01","event":"connect","firmware":"v2.3.1","battery":87.5,"timestamp":"2026-05-26T07:00:00Z"}'),
('TEMP-SENSOR-1', 'temperature_sensor','data',    NULL,NULL,            NULL,         NULL,   'Cold-Storage',0, '{"device":"TEMP-SENSOR-1","temperature_celsius":4.2,"humidity_pct":62,"timestamp":"2026-05-26T10:00:00Z"}');

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
