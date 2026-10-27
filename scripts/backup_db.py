"""
Database backup and restore (JSON snapshots).

Railway SSH is not usable from this machine and `mysqldump` is not installed,
so this is the backup path that actually runs. It works over any DATABASE_URL
the app itself can reach (Railway public proxy, or a local MySQL).

    python scripts/backup_db.py                      # backups/inventory-<utc>.json
    python scripts/backup_db.py --out D:\\dumps\\x.json
    python scripts/backup_db.py --restore D:\\dumps\\x.json --yes

Restore is destructive: it empties every table before reloading. It only runs
with --yes.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from sqlalchemy import DateTime, Date, Numeric, text  # noqa: E402

from app import create_app  # noqa: E402
from database import db  # noqa: E402


def _encode(value):
    if isinstance(value, (datetime, date)):
        return {"__type__": type(value).__name__, "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__type__": "Decimal", "value": str(value)}
    return value


def _decode(value):
    if isinstance(value, dict) and "__type__" in value:
        if value["__type__"] == "Decimal":
            return Decimal(value["value"])
        if value["__type__"] == "datetime":
            return datetime.fromisoformat(value["value"])
        if value["__type__"] == "date":
            return date.fromisoformat(value["value"])
    return value


def dump(out_path, app=None):
    app = app or create_app()
    with app.app_context():
        tables = list(db.metadata.sorted_tables)
        payload = {"created_at": datetime.now(timezone.utc).isoformat(), "tables": {}}
        total = 0
        for table in tables:
            rows = db.session.execute(table.select()).mappings().all()
            payload["tables"][table.name] = [
                {k: _encode(v) for k, v in row.items()} for row in rows
            ]
            total += len(rows)
            print(f"  {table.name:<24} {len(rows):>6} rows")
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
    print(f"\n{total} rows written to {out_path}")
    return payload


def restore(in_path, app=None):
    with open(in_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    app = app or create_app()
    with app.app_context():
        tables = list(db.metadata.sorted_tables)
        dialect = db.engine.dialect.name
        off = "SET FOREIGN_KEY_CHECKS=0" if dialect == "mysql" else "PRAGMA foreign_keys=OFF"
        on = "SET FOREIGN_KEY_CHECKS=1" if dialect == "mysql" else "PRAGMA foreign_keys=ON"
        db.session.execute(text(off))
        for table in reversed(tables):
            db.session.execute(table.delete())
        for table in tables:
            rows = payload["tables"].get(table.name, [])
            if rows:
                db.session.execute(
                    table.insert(),
                    [{k: _decode(v) for k, v in row.items()} for row in rows],
                )
        db.session.execute(text(on))
        db.session.commit()
    print(f"Restored {in_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(
        "backups", f"inventory-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"))
    parser.add_argument("--restore")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if args.restore:
        if not args.yes:
            sys.exit("Restore wipes every table. Re-run with --yes to confirm.")
        restore(args.restore)
    else:
        dump(args.out)
