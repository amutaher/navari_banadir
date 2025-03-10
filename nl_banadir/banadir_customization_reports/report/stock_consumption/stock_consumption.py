# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_datetime, flt


def execute(filters=None):
	columns = get_columns()

	tracker = ConsumptionTracker(filters)
	consumption_data = tracker.generate()

	data = format_data(consumption_data)

	# frappe.throw(str(data))

	return columns, data


def get_columns():
    """Define report columns"""
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 120},
        {"label": "Avg Consumption Time (Days)", "fieldname": "avg_consumption_time", "fieldtype": "Float", "width": 180},
        {"label": "Fastest Consumption (Days)", "fieldname": "fastest", "fieldtype": "Int", "width": 150},
        {"label": "Slowest Consumption (Days)", "fieldname": "slowest", "fieldtype": "Int", "width": 150},
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

        data.append({
            "item_code": item_code,
            "warehouse": warehouse,
            "avg_consumption_time": avg_consumption_time,
            "fastest": fastest,
            "slowest": slowest,
        })

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

		stock_ledger_entries = self.sle if self.sle else self.__get_stock_ledger_entries()

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
		"""Get stock ledger entries based on filters"""
		sle = frappe.qb.DocType("Stock Ledger Entry")
		return(
			frappe.qb.from_(sle)
			.select(
				sle.name,
				sle.item_code,
				sle.warehouse,
				sle.actual_qty,
				sle.posting_date
			)
			.where(
				(sle.company == self.filters.get("company"))
				& (sle.is_cancelled != 1)
			)
			.orderby(sle.posting_date)
			.run(as_dict=True)		
		)
