# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

"""
Monthly Closing Balance Report
Shows complete monthly financial position with:
- Opening Balances
- Transaction Activity (Debit/Credit)
- Closing Balances
for each month in the selected period
"""

import frappe
from frappe import _
from frappe.utils import getdate, formatdate
from dateutil.relativedelta import relativedelta

import erpnext
from erpnext.accounts.report.trial_balance.trial_balance import (
    execute as trial_balance_execute,
)


def execute(filters=None):
    """
    Main report execution
    1. Inherits base functionality from standard Trial Balance report
    2. Adds monthly breakdown columns
    3. Processes monthly data
    """

    columns, data = trial_balance_execute(filters)

    company_currency = erpnext.get_company_currency(filters.company)
    presentation_currency = filters.presentation_currency or company_currency

    monthly_ranges = get_monthly_date_ranges(filters)

    columns = get_monthly_columns(columns, monthly_ranges, presentation_currency)

    monthly_data = process_monthly_data(
        data, filters, monthly_ranges, company_currency, presentation_currency
    )

    return columns, monthly_data


def get_monthly_date_ranges(filters):
    monthly_ranges = []
    current_date = getdate(filters.from_date)
    end_date = getdate(filters.to_date)

    while current_date <= end_date:
        month_start = current_date.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)

        if month_end > end_date:
            month_end = end_date

        monthly_ranges.append(
            {
                "start": month_start,
                "end": month_end,
                "label": formatdate(month_start, "MMM YYYY"),
            }
        )

        current_date = month_end + relativedelta(days=1)

    return monthly_ranges


def get_monthly_columns(original_columns, monthly_ranges, currency):
    columns = [
        original_columns[0],  # Account column
        {
            "fieldname": "account_currency",
            "label": _("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
            "hidden": 1,
        },
    ]

    for month in monthly_ranges:
        month_label = month["label"]
        columns.extend(
            [
                # Opening Balances
                {
                    "fieldname": f"{month_label}_opening_debit",
                    "label": _(f"{month_label} Open (DR)"),
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                },
                {
                    "fieldname": f"{month_label}_opening_credit",
                    "label": _(f"{month_label} Open (CR)"),
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                },
                # Period Activity
                {
                    "fieldname": f"{month_label}_debit",
                    "label": _(f"{month_label} Debit"),
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                },
                {
                    "fieldname": f"{month_label}_credit",
                    "label": _(f"{month_label} Credit"),
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                },
                # Closing Balances
                {
                    "fieldname": f"{month_label}_closing_debit",
                    "label": _(f"{month_label} Close (DR)"),
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                },
                {
                    "fieldname": f"{month_label}_closing_credit",
                    "label": _(f"{month_label} Close (CR)"),
                    "fieldtype": "Currency",
                    "options": "currency",
                    "width": 120,
                },
            ]
        )

    return columns


def process_monthly_data(
    original_data, filters, monthly_ranges, company_currency, presentation_currency
):
    """
    Process account data for monthly breakdown

    1. Initialize data structure for all accounts
    2. For each month:
        a. Run trial balance for that month
        b. Store opening, transaction, and closing values
        c. Carry forward closing balances to next month
    """

    monthly_account_data = {}

    # Initialize account structure
    for row in original_data:
        if row.get("account"):
            monthly_account_data[row["account"]] = {
                "account": row["account"],
                "account_name": row["account_name"],
                "account_currency": row.get("account_currency", company_currency),
                "parent_account": row.get("parent_account"),
                "indent": row.get("indent", 0),
                "currency": presentation_currency,
            }

            # Initialize all monthly fields
            for month in monthly_ranges:
                month_label = month["label"]
                monthly_account_data[row["account"]].update(
                    {
                        f"{month_label}_opening_debit": 0.0,
                        f"{month_label}_opening_credit": 0.0,
                        f"{month_label}_debit": 0.0,
                        f"{month_label}_credit": 0.0,
                        f"{month_label}_closing_debit": 0.0,
                        f"{month_label}_closing_credit": 0.0,
                    }
                )

    # Process each month sequentially
    for idx, month in enumerate(monthly_ranges):
        month_label = month["label"]
        month_filters = frappe._dict(filters.copy())
        month_filters.update(
            {
                "from_date": month["start"],
                "to_date": month["end"],
                "presentation_currency": presentation_currency,
            }
        )

        # Get monthly trial balance data
        _, month_data = trial_balance_execute(month_filters)

        for row in month_data:
            if not row.get("account") or not row.get("has_value"):
                continue

            account = monthly_account_data[row["account"]]

            # Set values from trial balance
            account.update(
                {
                    f"{month_label}_opening_debit": row["opening_debit"],
                    f"{month_label}_opening_credit": row["opening_credit"],
                    f"{month_label}_debit": row["debit"],
                    f"{month_label}_credit": row["credit"],
                    f"{month_label}_closing_debit": row["closing_debit"],
                    f"{month_label}_closing_credit": row["closing_credit"],
                }
            )

            # Carry forward closing to next month's opening
            if idx < len(monthly_ranges) - 1:
                next_month_label = monthly_ranges[idx + 1]["label"]
                monthly_account_data[row["account"]].update(
                    {
                        f"{next_month_label}_opening_debit": row["closing_debit"],
                        f"{next_month_label}_opening_credit": row["closing_credit"],
                    }
                )

    return list(monthly_account_data.values())
