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
            "label": "Voucher No",
            "fieldname": "voucher_no",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "Addition Expense Claim",
            "fieldname": "additional_expense",
            "fieldtype": "Link",
            "options": "Expense Claim",
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


def get_conditions(filters):
    conditions = ["(ec.custom_is_addition = 0 OR ec.custom_is_addition IS NULL)"]
    values = {}

    if filters.get("company"):
        conditions.append("ec.company = %(company)s")
        values["company"] = filters["company"]

    if filters.get("company_group"):
        conditions.append("ec.company_group = %(company_group)s")
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

    return condition_str, values


def fetch_expense_claims(condition_str, values):
    return frappe.db.sql(
        f"""
        SELECT
            ec.name AS expense_claim,
            ecd.expense_date AS booking_date,
            ec.company AS company,
            ec.custom_traveller_name AS traveller_name,
            ec.custom_travel_group AS type_of_travel,
            ecd.amount AS amount,
            ec.company_group AS company_group,
            ecd.custom_airlines AS airline,
            ecd.custom_date_of_travel AS departure_date,
            ecd.custom_departure_airport AS departure_airport,
            ecd.custom_date_of_arrival AS arrival_date,
            ecd.custom_arrival_airport AS arrival_airport,
            ecd.custom_booked_by AS booked_by,
            ecd.expense_type as expense_claim_type,
            ecd.custom_travel_type as travel_type,
            ecd.custom_voucher_no as voucher_no
        FROM
            `tabExpense Claim Detail` ecd
        JOIN
            `tabExpense Claim` ec ON ec.name = ecd.parent
        {condition_str}
        ORDER BY ec.posting_date DESC
        """,
        values,
        as_dict=True,
    )


def fetch_additional_claims_map():
    additions = frappe.db.sql(
        """
        SELECT
            ecd.amount,
            ecd.parent AS expense_claim,
            ecd.custom_voucher_no AS voucher_no,
            ec.custom_original_expense_claim AS original_expense_claim
        FROM
            `tabExpense Claim Detail` ecd
        JOIN
            `tabExpense Claim` ec ON ec.name = ecd.parent
        WHERE
            ec.custom_is_addition = 1
        """,
        as_dict=True,
    )
    additions_map = {}
    for add in additions:
        original = add.get("original_expense_claim")
        if original:
            additions_map.setdefault(original, []).append(add)
    return additions_map


def get_data(filters):
    condition_str, values = get_conditions(filters)
    original_claims = fetch_expense_claims(condition_str, values)
    additions_map = fetch_additional_claims_map()

    company_currency = frappe.get_cached_value(
        "Company", filters.get("company"), "default_currency"
    )

    for row in original_claims:
        claim_name = row["expense_claim"]
        additions = additions_map.get(claim_name, [])

        additional_total = sum(a["amount"] for a in additions)
        additional_refs = ", ".join(a["expense_claim"] for a in additions)

        row["amount"] += additional_total
        row["additional_expense"] = additional_refs if additional_refs else None
        row["voucher_no"] = ", ".join(
            filter(
                None, [row.get("voucher_no")] + [a.get("voucher_no") for a in additions]
            )
        )
        row["currency"] = company_currency
        row["amount_usd"] = convert_currency(
            row["amount"], company_currency, "USD", row["booking_date"]
        )

    return original_claims


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
