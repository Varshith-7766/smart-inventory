import importlib.util
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "backup_db.py")
_spec = importlib.util.spec_from_file_location("backup_db", _SCRIPT)
backup_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backup_db)


def test_dump_and_restore_round_trip(app, db, tmp_path):
    """A backup that cannot be restored is not a backup."""
    from models import Category, Product

    cat = Category(name="BackupCat", user_id=1)
    db.session.add(cat)
    db.session.commit()
    db.session.add(Product(
        name="Backed Up", sku="BKP-001", unit_price=Decimal("12.34"),
        category_id=cat.id, category="BackupCat", user_id=1,
    ))
    db.session.commit()

    out = tmp_path / "snapshot.json"
    backup_db.dump(str(out), app=app)
    assert out.exists()

    db.session.query(Product).delete()
    db.session.query(Category).delete()
    db.session.commit()
    assert db.session.query(Product).count() == 0

    backup_db.restore(str(out), app=app)

    product = db.session.query(Product).filter_by(sku="BKP-001").one()
    assert product.name == "Backed Up"
    # Decimal is what MySQL NUMERIC comes back as; it must survive the trip.
    assert product.unit_price == Decimal("12.34")
    assert db.session.query(Category).filter_by(name="BackupCat").count() == 1
