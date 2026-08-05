"""
Data Loader Layer for Olist Brazilian E-Commerce Dataset.
Uses standard Python 'csv' module for zero dependencies and high performance.
Optimized for O(1) in-memory indexing and fast lookup.
"""

import os
import csv
from typing import Dict, List, Any, Optional


class DataLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.customer_orders: Dict[str, List[str]] = {}  # customer_unique_id -> list[order_id]
        self.order_items: Dict[str, List[Dict[str, Any]]] = {}  # order_id -> list[item]
        self.order_payments: Dict[str, List[Dict[str, Any]]] = {}  # order_id -> list[payment]
        self.products: Dict[str, Dict[str, Any]] = {}  # product_id -> product info
        self._is_loaded = False

    def load_data(self) -> None:
        """Load and index all CSV files into memory using standard csv.DictReader."""
        if self._is_loaded:
            return

        # 1. Load Customers
        cust_path = os.path.join(self.data_dir, "olist_customers_dataset.csv")
        if os.path.exists(cust_path):
            with open(cust_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cid = row["customer_id"].strip('"')
                    c_uniq = row["customer_unique_id"].strip('"')
                    cleaned_row = {k.strip('"'): v.strip('"') for k, v in row.items()}
                    self.customers[cid] = cleaned_row

        # 2. Load Orders
        orders_path = os.path.join(self.data_dir, "olist_orders_dataset.csv")
        if os.path.exists(orders_path):
            with open(orders_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {k.strip('"'): v.strip('"') for k, v in row.items()}
                    oid = cleaned_row["order_id"]
                    cid = cleaned_row["customer_id"]
                    self.orders[oid] = cleaned_row

                    if cid in self.customers:
                        c_uniq = self.customers[cid]["customer_unique_id"]
                        if c_uniq not in self.customer_orders:
                            self.customer_orders[c_uniq] = []
                        self.customer_orders[c_uniq].append(oid)

        # 3. Load Order Items
        items_path = os.path.join(self.data_dir, "olist_order_items_dataset.csv")
        if os.path.exists(items_path):
            with open(items_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {k.strip('"'): v.strip('"') for k, v in row.items()}
                    oid = cleaned_row["order_id"]
                    item_dict = {
                        "order_id": oid,
                        "order_item_id": int(cleaned_row["order_item_id"]),
                        "product_id": cleaned_row["product_id"],
                        "seller_id": cleaned_row["seller_id"],
                        "shipping_limit_date": cleaned_row["shipping_limit_date"],
                        "price": float(cleaned_row["price"]),
                        "freight_value": float(cleaned_row["freight_value"]),
                    }
                    if oid not in self.order_items:
                        self.order_items[oid] = []
                    self.order_items[oid].append(item_dict)

        # 4. Load Order Payments
        payments_path = os.path.join(self.data_dir, "olist_order_payments_dataset.csv")
        if os.path.exists(payments_path):
            with open(payments_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {k.strip('"'): v.strip('"') for k, v in row.items()}
                    oid = cleaned_row["order_id"]
                    pay_dict = {
                        "order_id": oid,
                        "payment_sequential": int(cleaned_row["payment_sequential"]),
                        "payment_type": cleaned_row["payment_type"],
                        "payment_installments": int(cleaned_row["payment_installments"]),
                        "payment_value": float(cleaned_row["payment_value"]),
                    }
                    if oid not in self.order_payments:
                        self.order_payments[oid] = []
                    self.order_payments[oid].append(pay_dict)

        # 5. Load Products
        products_path = os.path.join(self.data_dir, "olist_products_dataset.csv")
        if os.path.exists(products_path):
            with open(products_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {k.strip('"'): v.strip('"') for k, v in row.items()}
                    pid = cleaned_row["product_id"]
                    self.products[pid] = cleaned_row

        self._is_loaded = True

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.orders.get(order_id)

    def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        return self.customers.get(customer_id)

    def get_customer_unique_id(self, order_id: str) -> Optional[str]:
        order = self.get_order(order_id)
        if not order:
            return None
        cid = order.get("customer_id")
        if cid and cid in self.customers:
            return self.customers[cid].get("customer_unique_id")
        return None

    def get_related_orders(self, customer_unique_id: str, current_order_id: str) -> List[str]:
        if not customer_unique_id or customer_unique_id not in self.customer_orders:
            return []
        return [oid for oid in self.customer_orders[customer_unique_id] if oid != current_order_id]

    def get_items(self, order_id: str) -> List[Dict[str, Any]]:
        return self.order_items.get(order_id, [])

    def get_payments(self, order_id: str) -> List[Dict[str, Any]]:
        return self.order_payments.get(order_id, [])

    def get_product_category(self, product_id: str) -> Optional[str]:
        prod = self.products.get(product_id)
        if prod:
            cat = prod.get("product_category_name")
            return cat if cat and str(cat).strip() != "" else None
        return None

    def get_full_order_context(self, order_id: str) -> Dict[str, Any]:
        """Aggregate full context for a given order_id."""
        order = self.get_order(order_id)
        if not order:
            return {}

        cid = order.get("customer_id")
        customer = self.customers.get(cid, {}) if cid else {}
        customer_unique_id = customer.get("customer_unique_id")
        related_orders = self.get_related_orders(customer_unique_id, order_id) if customer_unique_id else []

        items = self.get_items(order_id)
        payments = self.get_payments(order_id)

        enriched_items = []
        sellers = []
        products = []
        categories = []

        for item in items:
            pid = item["product_id"]
            sid = item["seller_id"]
            cat = self.get_product_category(pid)

            if sid not in sellers:
                sellers.append(sid)
            if pid not in products:
                products.append(pid)
            if cat and cat not in categories:
                categories.append(cat)

            enriched_items.append({
                **item,
                "category_name": cat
            })

        return {
            "order": order,
            "customer": customer,
            "customer_unique_id": customer_unique_id,
            "related_order_ids": related_orders,
            "items": enriched_items,
            "payments": payments,
            "seller_ids": sellers,
            "product_ids": products,
            "category_names": categories
        }
