# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "name",
            "label": "Name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "posting_date",
            "label": "Posting Date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "customer",
            "label": "Customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 150
        },
        {
            "fieldname": "grand_total",
            "label": "Grand Total",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "item_code",
            "label": "Item Code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 150
        },
        {
            "fieldname": "qty",
            "label": "Quantity",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "rate",
            "label": "Rate",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "amount",
            "label": "Amount",
            "fieldtype": "Currency",
            "width": 120
        }
    ]


def get_data(filters=None):
    # Fetch the last 20 invoices
    invoices = frappe.get_all(
        "Sales Invoice",
        fields=["name", "posting_date", "customer", "grand_total"],
        order_by="posting_date DESC",
        limit=20
    )

    data = []

    for invoice in invoices:
        # Add invoice row with indent 0
        data.append({
            "name": invoice.name,
            "posting_date": invoice.posting_date,
            "customer": invoice.customer,
            "grand_total": invoice.grand_total,
            "indent": 0,
            "is_group": 1
        })

        # Fetch items for the current invoice
        items = frappe.get_all(
            "Sales Invoice Item",
            filters={"parent": invoice.name},
            fields=["item_code", "qty", "rate", "amount"]
        )

        for item in items:
            # Add item row with indent 1
            data.append({
                "name": item.item_code,
                "item_code": item.item_code,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "indent": 1,
                "is_group": 0
            })

    return data