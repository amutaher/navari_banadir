# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from frappe import _


def execute(filters=None):
    columns = get_columns()

    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Expense Claim",
            "fieldname": "expense_claim",
            "fieldtype": "Link",
            "options": "Expense Claim",
            "width": 150,
        },
        {
            "label": "Date of Booking",
            "fieldname": "booking_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Traveller Name",
            "fieldname": "traveller_name",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Type of Travel",
            "fieldname": "travel_type",
            "fieldtype": "Select",
            "options": "\nOne Way\nReturn",
            "width": 120,
        },
        {
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 100,
        },
        {
            "label": " Amount(USD)",
            "fieldname": "amount_usd",
            "fieldtype": "Currency",
            "width": 100,
            "options": "USD",
        },
        {
            "label": "Company Group",
            "fieldname": "company_group",
            "fieldtype": "Link",
            "options": "Company Group",
            "width": 150,
        },
        {
            "label": "Airline",
            "fieldname": "airline",
            "fieldtype": "Link",
            "options": "Airlines",
            "width": 150,
        },
        {
            "label": "Departure Date",
            "fieldname": "departure_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Departure Airport",
            "fieldname": "departure_airport",
            "fieldtype": "Link",
            "options": "Airport",
            "width": 150,
        },
        {
            "label": "Arrival Date",
            "fieldname": "arrival_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Arrival Airport",
            "fieldname": "arrival_airport",
            "fieldtype": "Link",
            "options": "Airport",
            "width": 150,
        },
        {
            "label": "Booked By",
            "fieldname": "booked_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 150,
        },
        {
            "label": "Currency",
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 100,
            "hidden": 1,
        },
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("company"):
        conditions.append("ec.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("company_group"):
        conditions.append("ecd.company_group = %(company_group)s")
        values["company_group"] = filters["company_group"]

    if filters.get("booked_by"):
        conditions.append("ecd.custom_booked_by = %(booked_by)s")
        values["booked_by"] = filters["booked_by"]

    if filters.get("traveller_name"):
        conditions.append("ec.custom_traveller_name = %(traveller_name)s")
        values["traveller_name"] = filters["traveller_name"]

    if filters.get("travel_type"):
        conditions.append("ecd.custom_travel_type = %(travel_type)s")
        values["travel_type"] = filters["travel_type"]

    if filters.get("booking_date"):
        from_date, to_date = filters["booking_date"]
        conditions.append("ec.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = getdate(from_date)
        values["to_date"] = getdate(to_date)

    condition_str = " AND ".join(conditions)
    if condition_str:
        condition_str = "WHERE " + condition_str

    query = f"""
        SELECT
            ec.name AS expense_claim,
            ec.posting_date AS booking_date,
            ec.company AS company,
            ec.custom_traveller_name AS traveller_name,
            ec.custom_travel_group AS type_of_travel,
            ecd.amount AS amount,
            ecd.company_group AS company_group,
            ecd.custom_airlines AS airline,
            ecd.custom_date_of_travel AS departure_date,
            ecd.custom_departure_airport AS departure_airport,
            ecd.custom_date_of_arrival AS arrival_date,
            ecd.custom_arrival_airport AS arrival_airport,
            ecd.custom_booked_by AS booked_by,
            ecd.expense_type as expense_claim_type,
            ecd.custom_travel_type as travel_type
        FROM
            `tabExpense Claim Detail` ecd
        JOIN
            `tabExpense Claim` ec ON ec.name = ecd.parent
        {condition_str}
        ORDER BY ec.posting_date DESC
    """

    raw_data = frappe.db.sql(query, values, as_dict=True)
    company_currency = frappe.get_cached_value(
        "Company", filters.get("company"), "default_currency"
    )

    # Convert amounts to USD
    for row in raw_data:
        amount_kes = row["amount"] or 0
        date = row["booking_date"] or frappe.utils.nowdate()
        row["currency"] = company_currency
        row["amount_usd"] = convert_currency(amount_kes, company_currency, "USD", date)
    return raw_data


def convert_currency(amount, from_currency, to_currency, date):
    conversion_rate, conversion_date = get_conversion_rate(
        from_currency, to_currency, date
    )
    return amount * conversion_rate


def get_conversion_rate(from_currency, to_currency, date):
    if from_currency == to_currency:
        return 1, None

    conversion_rate = frappe.get_all(
        "Currency Exchange",
        filters={
            "from_currency": from_currency,
            "to_currency": to_currency,
            "date": ["<=", date],
        },
        fields=["exchange_rate", "date"],
        order_by="date desc",
        limit=1,
    )

    if conversion_rate:
        return conversion_rate[0]["exchange_rate"], conversion_rate[0]["date"]
    else:
        # Try fetching the inverse exchange rate
        inverse_conversion_rate = frappe.get_all(
            "Currency Exchange",
            filters={
                "from_currency": to_currency,
                "to_currency": from_currency,
                "date": ["<=", date],
            },
            fields=["exchange_rate", "date"],
            order_by="date desc",
            limit=1,
        )

        if inverse_conversion_rate:
            inverse_exchange_rate = inverse_conversion_rate[0]["exchange_rate"]
            return 1 / inverse_exchange_rate, inverse_conversion_rate[0]["date"]
        else:
            frappe.msgprint(
                _("Exchange rate not found for {0} to {1}").format(
                    from_currency, to_currency
                )
            )
            return 1, None
