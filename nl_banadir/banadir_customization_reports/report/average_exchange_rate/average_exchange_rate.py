# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
    """Return columns and data for the report.

    This is the main entry point for the report. It accepts the filters as a
    dictionary and should return columns and data. It is called by the framework
    every time the report is refreshed or a filter is updated.
    """
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns() -> list[dict]:
    """Return columns for the report.

    One field definition per column, just like a DocType field definition.
    """
    return [
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
        },
        {
            "label": _("Amount(USD)"),
            "fieldname": "amount_usd",
            "fieldtype": "Currency",
        },
        {
            "label": _("Amount(INR)"),
            "fieldname": "amount_inr",
            "fieldtype": "Currency",
        },
        {
            "label": _("Exchange Rate"),
            "fieldname": "exchange_rate",
            "fieldtype": "Data",
        },
    ]


def get_data(filters) -> list[list]:
    """Return data for the report.

    The report data is a list of rows, with each row being a list of cell values.
    """
    currency_conversion_doc = frappe.qb.DocType("Currency Conversion")
    query = (
        frappe.qb.from_(currency_conversion_doc)
        .select("date", "exchange_rate")
        .where(
            (currency_conversion_doc.date >= filters.get("from_date"))
            & (currency_conversion_doc.date <= filters.get("to_date"))
        )
        .orderby(currency_conversion_doc.creation)
    )
    data = query.run(as_dict=True)

    return data
