# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

# import frappe

# travel_expense.py

import frappe
from frappe.utils import getdate


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
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
            "fieldname": "type_of_travel",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 100,
        },
        {
            "label": "Company Group",
            "fieldname": "company_group",
            "fieldtype": "Link",
            "options": "Company Group",
            "width": 150,
        },
        {"label": "Airline", "fieldname": "airline", "fieldtype": "Data", "width": 150},
        {
            "label": "Departure Date",
            "fieldname": "departure_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Departure Airport",
            "fieldname": "departure_airport",
            "fieldtype": "Data",
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
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Booked By",
            "fieldname": "booked_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 150,
        },
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("company_group"):
        conditions.append("ecd.company_group = %(company_group)s")
        values["company_group"] = filters["company_group"]

    if filters.get("booked_by"):
        conditions.append("ecd.custom_booked_by = %(booked_by)s")
        values["booked_by"] = filters["booked_by"]

    if filters.get("traveller_name"):
        conditions.append("ec.custom_traveller_name = %(traveller_name)s")
        values["traveller_name"] = filters["traveller_name"]

    if filters.get("type_of_travel"):
        conditions.append("ec.custom_travel_group = %(type_of_travel)s")
        values["type_of_travel"] = filters["type_of_travel"]

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
            ec.posting_date AS booking_date,
            ec.custom_traveller_name AS traveller_name,
            ec.custom_travel_group AS type_of_travel,
            ecd.amount AS amount,
            ecd.company_group AS company_group,
            ecd.custom_airlines AS airline,
            ecd.custom_date_of_travel AS departure_date,
            ecd.custom_departure_airport AS departure_airport,
            ecd.custom_date_of_arrival AS arrival_date,
            ecd.custom_arrival_airport AS arrival_airport,
            ecd.custom_booked_by AS booked_by
        FROM
            `tabExpense Claim Detail` ecd
        JOIN
            `tabExpense Claim` ec ON ec.name = ecd.parent
        {condition_str}
        ORDER BY ec.posting_date DESC
    """
    return frappe.db.sql(query, values, as_dict=True)
