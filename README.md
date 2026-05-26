# Smart Inventory Management System

A full-stack inventory management system with predictive restocking, low-stock alerts, and IoT-ready architecture.

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MySQL 8.0
- **Frontend**: HTML, CSS, JavaScript
- **Prediction**: scikit-learn (Random Forest)

## Quick Start

### Prerequisites
- Python 3.11+
- MySQL 8.0
- (Optional) Docker & Docker Compose

### Setup (Manual)

```bash
# 1. Create database
mysql -u root -p < database/schema.sql

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 4. Seed sample data
python scripts/seed_data.py

# 5. Run
python backend/run.py
```

### Setup (Docker)

```bash
docker-compose up -d
```

### Generate Predictions

```bash
python scripts/run_predictions.py
```

## Default Login

- Username: `admin`
- Password: `admin123`

## Project Structure

```
smart-inventory/
├── backend/          # Flask application (models, routes, services)
├── frontend/         # HTML templates, CSS, JavaScript
├── prediction/       # ML prediction engine
├── iot/              # Barcode/RFID interface stubs
├── database/         # SQL schema and seed files
├── tests/            # Backend and prediction tests
├── scripts/          # Utility scripts
└── docs/             # Documentation
```

## License

MIT
