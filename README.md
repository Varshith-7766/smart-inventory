# Smart Inventory Management System

A comprehensive inventory management solution with predictive analytics, IoT readiness, and multi-tenant data isolation.

## Project Overview

The Smart Inventory Management System is a full-stack web application designed to help businesses track inventory, manage sales, and leverage predictive analytics for optimal stock levels. The system features role-based access control, real-time data visualization, and extensible architecture for IoT device integration.

## Objectives

- Provide an intuitive interface for inventory and sales management
- Implement robust data isolation for multi-tenant security
- Offer predictive restocking capabilities using statistical demand forecasting
- Design an extensible architecture for IoT device integration
- Ensure data integrity and security through proper validation and CSRF protection
- Deliver a responsive web application accessible across devices

## Features

### Core Functionality
- **Product Management**: Add, edit, and organize products with SKU, barcode, categories, and suppliers
- **Sales Processing**: Record sales transactions with multiple payment methods and customer details
- **Inventory Tracking**: Real-time stock level updates with low-stock alerts
- **Supplier Management**: Maintain supplier information and contact details
- **User Authentication**: Secure login/logout with role-based access (viewer/manager/admin)
- **Data Export**: Generate reports for inventory and sales data

### Advanced Features
- **Predictive Restocking**: Statistical demand forecasts (moving averages, consumption rates, trend analysis) drive reorder points
- **IoT-Ready Architecture**: Modular design for barcode scanners, RFID readers, and weight sensors
- **Multi-Tenant Isolation**: Each user sees only their own data (products, sales, categories, devices)
- **Responsive Design**: Mobile-friendly interface with custom CSS
- **RESTful API**: Well-documented endpoints for integration
- **Audit Trail**: Inventory change logs for accountability

### Security Features
- CSRF protection on all state-changing endpoints
- Input validation and sanitization (backend) and HTML-escaping on the frontend (stored-XSS safe)
- Password hashing for user credentials (min length 8 enforced)
- Session-based authentication with HttpOnly, SameSite cookies
- Client-supplied roles are never trusted — new accounts are always created as viewer
- Weak/default secret keys are rejected and replaced with generated keys
- Role-based access control: viewer (read-only), manager, admin
- IoT devices authenticate with per-device API keys (no anonymous ingest)
- Data isolation per user

## Tech Stack

### Backend
- **Python 3.11+**: Core programming language (Docker image uses 3.11-slim)
- **Flask**: Web framework for RESTful API
- **SQLAlchemy**: ORM for database interactions
- **MySQL**: Primary database (SQLite fallback for quick local runs)
- **Flask-WTF**: CSRF protection
- **NumPy/Pandas**: Data processing for demand forecasting

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Custom styling (design tokens, no CSS framework)
- **JavaScript (ES6)**: Client-side interactivity
- **Feather Icons**: Icon library
- **Chart.js**: Dashboard sales charts

### DevOps & Tools
- **Git**: Version control
- **Docker**: Containerization (Dockerfile & docker-compose.yml provided)
- **pytest**: Testing framework
- **Postman**: API testing (collection included)

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   Frontend      │    │     Backend      │    │     Database       │
│  (SPA/Pages)    │◄──►│  (Flask API)     │◄──►│  (MySQL/PostgreSQL)│
└─────────────────┘    └──────────────────┘    └────────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   IoT Devices   │    │  Predictive     │    │   File Storage     │
│ (Barcode/RFID)  │◄──►│   Analytics     │◄──►│   (Logs/Exports)   │
└─────────────────┘    └──────────────────┘    └────────────────────┘
```

### Key Components
1. **Presentation Layer**: Responsive web pages served by Flask templates
2. **Application Layer**: Flask blueprints separating concerns (auth, products, sales, etc.)
3. **Service Layer**: Business logic encapsulated in service functions
4. **Data Access Layer**: SQLAlchemy models with proper relationships
5. **Integration Layer**: API endpoints for external systems and IoT devices

## Database Design

### Core Tables
- **users**: Authentication and role information (viewer/manager/admin)
- **products**: Inventory items with SKU, barcode, pricing, and stock levels (per-user unique SKU/barcode)
- **categories**: Product categorization (user-specific)
- **suppliers**: Vendor information (user-specific)
- **sales**: Transaction headers with customer and payment details
- **sale_items**: Line items linking sales to products
- **inventory_logs**: Audit trail of stock movements
- **reorder_predictions**: Cached demand forecasts and reorder suggestions
- **iot_devices**: Registered devices with per-device API keys
- **iot_device_logs**: Sensor readings from connected devices
- **alert_resolutions**: Record of resolved low-stock alerts

### Relationships
- Users 1:M Products, Suppliers, Categories, InventoryLogs, IoTDevices
- Products 1:M SaleItems, InventoryLogs
- Sales 1:M SaleItems
- Categories 1:M Products (through product.category_id)
- Suppliers 1:M Products

### Indexes
- Primary keys on all ID columns
- Foreign key constraints for referential integrity
- Unique constraints (user_id, sku) and (user_id, barcode) on products
- Unique constraints (user_id, device_id) and api_key on iot_devices
- Indexes on frequently queried columns (sale_date, processed_by, user_id)

## API Documentation

### Authentication
- `POST /api/auth/register` - Create account (role always "viewer"; password min 8 chars)
- `POST /api/auth/login` - Authenticate user
- `POST /api/auth/logout` - End session
- `GET /api/auth/me` - Current user info
- `GET /api/auth/csrf-token` - Retrieve CSRF token (send as `X-CSRFToken` header on mutations)

### Products
- `GET /api/products/` - List products (search/filter/pagination)
- `GET /api/products/<id>` - Get single product
- `GET /api/products/low-stock` - Products below reorder level
- `POST /api/products/` - Create product (manager/admin)
- `PUT /api/products/<id>` - Update product (manager/admin)
- `DELETE /api/products/<id>` - Delete product (manager/admin)
- `GET /api/products/categories` - List user categories
- `POST /api/products/categories` - Create category (manager/admin)

### Sales
- `GET /api/sales/` - List sales history (pagination)
- `GET /api/sales/<id>` - Get sale with line items
- `POST /api/sales/` - Record new sale (manager/admin; client-supplied prices ignored — current product price is used)
- `DELETE /api/sales/<id>` - Void sale (manager/admin)

### Stock
- `GET /api/stock/alerts` - Low-stock alerts (with resolved state)
- `PATCH /api/stock/alerts/resolve` - Mark an alert resolved (persisted in alert_resolutions)
- `POST /api/stock/adjust` - Adjust stock with audit log (manager/admin; cannot go below zero)
- `GET /api/stock/movements` - Paginated inventory movement history

### Dashboard
- `GET /api/dashboard/stats` - Key performance indicators
- `GET /api/dashboard/recent-sales` - Latest transactions
- `GET /api/dashboard/low-stock` - Products below reorder level

### IoT
- `POST /api/iot/devices/register` - Register a device, receives an API key (manager/admin)
- `POST /api/iot/events` - Ingest an event; authenticate with `X-Device-Key` header (no session required)
- `GET /api/iot/events` - List events (filter by device_id/type/unprocessed)
- `PATCH /api/iot/events/<id>/process` - Mark an event processed (scan events adjust stock + audit log)
- `GET /api/iot/devices` - Device summary (event counts, last seen, avg battery)
- `GET /api/iot/stats` - Per-user IoT statistics
- `POST /api/iot/simulator/start` / `POST /api/iot/simulator/stop` / `GET /api/iot/simulator/status` - Built-in simulator (requires `IOT_API_KEY`)

### Misc
- `GET /health` - Health check

## Predictive Restocking Explanation

The predictive restocking system uses historical sales data to forecast future demand and recommend optimal reorder points.

### How It Works
1. **Data Collection**: The system collects daily sales quantities for each product over time
2. **Demand Baseline**: A 7-day simple moving average (SMA) smooths daily demand and handles gaps
3. **Consumption Rate**: Daily consumption rate (DCR) estimates average units sold per day
4. **Trend Analysis**: Compares recent vs. older consumption to detect rising or falling demand
5. **Reorder Calculation**: Combines predicted demand with lead time and safety stock to calculate reorder points
6. **Stockout Prediction**: Estimates days until stockout at current demand; negative values trigger restock alerts

### Benefits
- Reduces stockouts by anticipating demand spikes
- Minimizes excess inventory carrying costs
- Adapts to seasonal trends and promotions
- Provides data-driven purchasing decisions
- Reduces manual forecasting effort

### Implementation
- Located in `/prediction/` (pure pandas/numpy — no heavy ML dependencies)
- Key functions: `analyze_product()`, `run_for_product()`, `run_for_all_products()`, `generate_restock_alerts()`
- Runs on demand via the dashboard; interval controlled by `PREDICTION_INTERVAL_DAYS`
- Forecasts are cached in the `reorder_predictions` table

## IoT-Ready Architecture Explanation

The system is designed with extensibility in mind for seamless IoT device integration.

### Architecture Principles
1. **Modular Design**: IoT handlers in `/iot` directory with clear interfaces
2. **Event-Driven**: Device data triggers inventory updates through standardized endpoints
3. **Protocol Agnostic**: Supports MQTT, HTTP, and serial connections
4. **Data Normalization**: Converts device-specific formats to internal inventory events
5. **Fault Tolerance**: Graceful handling of device disconnections and malformed data

### Supported Devices
- **Barcode Scanners**: USB/HID or Bluetooth scanners input as keyboard wedge
- **RFID Readers**: Fixed or handheld readers for bulk inventory counts
- **Weight Sensors**: Smart shelves that detect weight changes
- **Environmental Sensors**: Temperature/humidity for perishable goods
- **Camera Systems**: Computer vision for automated stock counting

### Integration Flow
1. Device is registered via `POST /api/iot/devices/register` and receives an API key
2. Device detects event (scan, weight change, etc.)
3. Device sends data to `POST /api/iot/events` with `X-Device-Key` header
4. Backend validates the key, binds the event to the device owner, and normalizes the data
5. Unauthenticated or unregistered clients are rejected (401)
6. Processing a scan event creates an inventory log entry and updates stock in real-time
7. Frontend reflects changes via polling

### Extension Points
- Add new device types in `/iot/` directory
- Implement new parsers in device handler files
- Register devices and issue keys via `iot.py` routes
- Extend database schema for specialized device data

## Installation Steps

### Prerequisites
- Python 3.11+ (tested up to 3.14)
- Git
- (Optional) Docker and Docker Compose
- (Optional) MySQL/PostgreSQL for production (SQLite works out of the box)

### Local Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/smart-inventory.git
   cd smart-inventory
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Set Environment Variables**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize Database**
   ```bash
   python scripts/migrate_db.py
   python scripts/seed_data.py
   ```

6. **Run the Application**
   ```bash
   python backend/app.py
   ```
   - Access at: http://localhost:5000
   - Default admin: admin / admin123 (created by seed_data.py)

7. **Run Tests**
   ```bash
   python -m pytest tests -q
   python scripts/test_api.py          # live-DB API smoke tests
   python scripts/test_edge_cases.py   # 56 edge-case checks
   python scripts/test_iot.py          # IoT device key flow + simulator
   ```

### Docker Installation

1. **Build and Run**
   ```bash
   docker-compose up --build
   ```
   - Application: http://localhost
   - Adminer (DB admin): http://localhost:8080

2. **Manage Containers**
   ```bash
   docker-compose ps        # View status
   docker-compose logs -f   # View logs
   docker-compose down      # Stop containers
   ```

## Future Enhancements

### Short-Term (1-3 Months)
- [ ] WebSocket integration for real-time UI updates
- [ ] Advanced reporting with charts and graphs
- [ ] CSV import/export for bulk product updates
- [ ] Multi-warehouse/inventory location support
- [ ] barcode generation and printing module
- [ ] Supplier price history and purchase order management

### Medium-Term (3-6 Months)
- [ ] Mobile application (React Native/Ionic)
- [ ] Advanced machine learning models (LSTM for time series)
- [ ] Integration with accounting software (QuickBooks, Xero)
- [ ] Role-based permissions beyond admin/user
- [ ] Automated reorder purchasing workflow
- [ ] Dark mode and theme customization

### Long-Term (6+ Months)
- [ ] AI-powered demand forecasting with external data (weather, trends)
- [ ] Autonomous drone inventory counting for warehouses
- [ ] Blockchain-based supply chain transparency
- [ ] Augmented reality picking assistance
- [ ] Multi-language support (i18n)
- [ ] Advanced analytics dashboard with customizable widgets

## Conclusion

The Smart Inventory Management System provides a solid foundation for modern inventory control with room for growth into advanced analytics and IoT integration. Its modular architecture, security-conscious design, and developer-friendly structure make it suitable for both small businesses looking to digitize their operations and enterprises seeking a customizable inventory solution.

The system successfully balances immediate usability with extensibility, ensuring that as business needs evolve, the platform can adapt without requiring a complete rewrite. Whether used as-is or as a starting point for further customization, this system delivers value through improved inventory accuracy, reduced carrying costs, and data-driven decision-making capabilities.

---

*Documentation updated on: August 20, 2026*