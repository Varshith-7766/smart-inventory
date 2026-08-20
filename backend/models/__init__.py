"""
Models Package
==============
Every database table has a corresponding Python class.

Importing this package makes all models available at once:
    from models import Product, Sale, Supplier, User
"""

from models.product import Product
from models.sale import Sale, SaleItem
from models.supplier import Supplier
from models.user import User
from models.category import Category
from models.inventory_log import InventoryLog
from models.iot_device import IoTDeviceLog, IoTDevice
from models.reorder_prediction import ReorderPrediction
from models.alert_resolution import AlertResolution

__all__ = [
    "Product", "Sale", "SaleItem", "Supplier", "User",
    "Category", "InventoryLog", "IoTDeviceLog", "IoTDevice",
    "ReorderPrediction", "AlertResolution",
]
