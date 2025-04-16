# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_datetime, flt


def execute(filters=None):
    columns = get_columns()

    data = ConsumptionTracker(filters).generate()

    data = format_data(data)

    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 120,
        },
        {
            "label": "Warehouse",
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 120,
        },
        {
            "label": "Avg Consumption Time (Days)",
            "fieldname": "avg_consumption_time",
            "fieldtype": "Float",
            "width": 180,
        },
        {
            "label": "Fastest Consumption (Days)",
            "fieldname": "fastest",
            "fieldtype": "Int",
            "width": 150,
        },
        {
            "label": "Slowest Consumption (Days)",
            "fieldname": "slowest",
            "fieldtype": "Int",
            "width": 150,
        },
    ]


def format_data(consumption_data):
    """Formats data into a report-friendly structure"""
    data = []

    for (item_code, warehouse), details in consumption_data.items():
        consumption_times = details["consumption_times"]

        if not consumption_times:
            continue  # Skip if no consumption records exist

        avg_consumption_time = flt(sum(consumption_times) / len(consumption_times), 2)
        fastest = min(consumption_times)
        slowest = max(consumption_times)

        data.append(
            {
                "item_code": item_code,
                "warehouse": warehouse,
                "avg_consumption_time": avg_consumption_time,
                "fastest": fastest,
                "slowest": slowest,
            }
        )

    return data


class ConsumptionTracker:
    """Tracks how long it takes to completely consume a stock item from when it was purchased or received"""

    def __init__(self, filters: dict | None = None, sle: list | None = None):
        self.item_details = {}
        self.filters = filters
        self.sle = sle

    def generate(self) -> dict:
        """
        Returns a dictionary structured as:
        Key = (Item, Warehouse)
        Value = List of consumption durations for different batches of stock
        """

        stock_ledger_entries = (
            self.sle if self.sle else self.__get_stock_ledger_entries()
        )

        for entry in stock_ledger_entries:
            key, fifo_queue = self.__init_key_store(entry)

            if entry.actual_qty > 0:
                self.__record_incoming_stock(entry, fifo_queue)
            else:
                self.record_outgoing_stock(entry, fifo_queue)

        return self.item_details

    def __init_key_store(self, row: dict) -> tuple:
        """Initialize the FIFO queue for each item and warehouse"""
        key = (row.item_code, row.warehouse)
        self.item_details.setdefault(key, {"fifo_queue": [], "consumption_times": []})
        fifo_queue = self.item_details[key]["fifo_queue"]

        return key, fifo_queue

    def __record_incoming_stock(self, row: dict, fifo_queue: list):
        """Record stock received with its date."""
        fifo_queue.append([row.actual_qty, row.posting_date])

    def record_outgoing_stock(self, row: dict, fifo_queue: list):
        """Track stock consumption and calculate consumption time."""
        if not fifo_queue:
            return

        qty_to_consume = abs(row.actual_qty)
        key = (row.item_code, row.warehouse)

        while qty_to_consume > 0 and fifo_queue:
            first_entry = fifo_queue[0]

            if first_entry[0] <= qty_to_consume:
                # If full batch is consumed, track duration
                consumption_time = (row.posting_date - first_entry[1]).days
                self.item_details[key]["consumption_times"].append(consumption_time)
                qty_to_consume -= first_entry[0]
                fifo_queue.pop(0)
            else:
                # If batch is partially consumed, update the batch quantity
                first_entry[0] -= qty_to_consume
                qty_to_consume = 0

    def __get_stock_ledger_entries(self) -> list:
        sle = frappe.qb.DocType("Stock Ledger Entry")
        item = self.__get_item_query()  # used as derived table in sle query
        to_date = get_datetime(self.filters.get("to_date") + " 23:59:59")

        sle_query = (
            frappe.qb.from_(sle)
            .from_(item)
            .select(
                sle.item_code,
                item.name,
                item.item_name,
                item.item_group,
                item.brand,
                item.description,
                item.stock_uom,
                item.has_serial_no,
                sle.actual_qty,
                sle.stock_value_difference,
                sle.posting_date,
                sle.voucher_type,
                sle.voucher_no,
                sle.serial_no,
                sle.batch_no,
                sle.qty_after_transaction,
                sle.serial_and_batch_bundle,
                sle.warehouse,
            )
            .where(
                (sle.item_code == item.name)
                & (sle.company == self.filters.get("company"))
                & (sle.posting_datetime <= to_date)
                & (sle.is_cancelled != 1)
            )
        )

        if self.filters.get("warehouse"):
            sle_query = self.__get_warehouse_conditions(sle, sle_query)
        elif self.filters.get("warehouse_type"):
            warehouses = frappe.get_all(
                "Warehouse",
                filters={
                    "warehouse_type": self.filters.get("warehouse_type"),
                    "is_group": 0,
                },
                pluck="name",
            )

            if warehouses:
                sle_query = sle_query.where(sle.warehouse.isin(warehouses))

        sle_query = sle_query.orderby(sle.posting_datetime, sle.creation)

        return sle_query.run(as_dict=True)

    def __get_item_query(self) -> str:
        item_table = frappe.qb.DocType("Item")

        item = frappe.qb.from_("Item").select(
            "name",
            "item_name",
            "description",
            "stock_uom",
            "brand",
            "item_group",
            "has_serial_no",
        )

        if self.filters.get("item_code"):
            item = item.where(item_table.item_code == self.filters.get("item_code"))

        if self.filters.get("brand"):
            item = item.where(item_table.brand == self.filters.get("brand"))

        return item

    def __get_warehouse_conditions(self, sle, sle_query) -> str:
        warehouse = frappe.qb.DocType("Warehouse")
        lft, rgt = frappe.db.get_value(
            "Warehouse", self.filters.get("warehouse"), ["lft", "rgt"]
        )

        warehouse_results = (
            frappe.qb.from_(warehouse)
            .select("name")
            .where((warehouse.lft >= lft) & (warehouse.rgt <= rgt))
            .run()
        )
        warehouse_results = [x[0] for x in warehouse_results]

        return sle_query.where(sle.warehouse.isin(warehouse_results))
