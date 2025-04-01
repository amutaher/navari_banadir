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

    if data:
        average_exchange_rate = calculate_average_exchange_rate(data)

        if average_exchange_rate:
            data[-1]["average_exchange_rate"] = average_exchange_rate

    return columns, data


def get_columns() -> list[dict]:
    """Return columns for the report.

    One field definition per column, just like a DocType field definition.
    """
    return [
        {
            "label": _("Document Name"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Currency Conversion",
            "width": 200,
        },
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Amount(USD)"),
            "fieldname": "amount_usd",
            "fieldtype": "Currency",
            "options": "from_currency",
            "width": 200,
        },
        {
            "label": _("Amount(INR)"),
            "fieldname": "amount_inr",
            "fieldtype": "Currency",
            "options": "to_currency",
            "width": 200,
        },
        {
            "label": _("Exchange Rate"),
            "fieldname": "exchange_rate",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Average Exchange Rate"),
            "fieldname": "average_exchange_rate",
            "fieldtype": "Float",
            "width": 100,
        },
    ]


def get_data(filters) -> list[list]:
    """Return data for the report.

    The report data is a list of rows, with each row being a list of cell values.
    """
    currency_conversion_doc = frappe.qb.DocType("Currency Conversion")
    query = (
        frappe.qb.from_(currency_conversion_doc)
        .select(
            currency_conversion_doc.name,
            currency_conversion_doc.from_amount.as_("amount_usd"),
            currency_conversion_doc.to_amount.as_("amount_inr"),
            currency_conversion_doc.date,
            currency_conversion_doc.from_currency,
            currency_conversion_doc.to_currency,
            currency_conversion_doc.exchange_rate,
        )
        .where(
            (currency_conversion_doc.date >= filters.get("from_date"))
            & (currency_conversion_doc.date <= filters.get("to_date"))
        )
        .orderby(currency_conversion_doc.creation)
    )
    data = query.run(as_dict=True)

    data = format_data(data)

    return data


def format_data(data):
    for d in data:
        d["average_exchange_rate"] = None

    return data


def calculate_average_exchange_rate(data):
    totals_dict = {
        "is_total": 1,
        "name": "Total -> Average",
        "amount_usd": 0,
        "amount_inr": 0,
    }

    for item in data:
        if item.get("amount_usd"):
            totals_dict["amount_usd"] += item.get("amount_usd")
        if item.get("amount_inr"):
            totals_dict["amount_inr"] += item.get("amount_inr")

    averange_exchange_rate = totals_dict["amount_inr"] / totals_dict["amount_usd"]

    totals_dict["exchange_rate"] = averange_exchange_rate

    return averange_exchange_rate
