# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

from typing import List, Dict

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_data(filters: Dict) -> List[Dict]:
    SalarySlip = DocType("Salary Slip")

    query = (
        frappe.qb.from_(SalarySlip)
        .select(
            SalarySlip.name,
            SalarySlip.branch,
            SalarySlip.employee,
            SalarySlip.employee_name,
            SalarySlip.posting_date,
            SalarySlip.currency,
            SalarySlip.net_pay,
            SalarySlip.journal_entry,
            IfNull(SalarySlip.journal_entry, "").as_("journal_entry"),
        )
        .where(SalarySlip.docstatus != 2)
    )

    query = apply_filters(query, SalarySlip, filters)

    results = query.run(as_dict=True)

    for row in results:
        row["payment_status"] = "Paid" if row.get("journal_entry") else "Unpaid"

    return results


def apply_filters(query, SalarySlip, filters: Dict):
    if filters.get("company"):
        query = query.where(SalarySlip.company == filters["company"])

    if filters.get("branch"):
        query = query.where(SalarySlip.branch == filters["branch"])

    if filters.get("employee"):
        query = query.where(SalarySlip.employee == filters["employee"])

    if filters.get("status") == "Paid":
        query = query.where(SalarySlip.journal_entry.isnotnull())
    elif filters.get("status") == "Unpaid":
        query = query.where(SalarySlip.journal_entry.isnull())

    if filters.get("from_date") and filters.get("to_date"):
        query = query.where(
            (SalarySlip.posting_date >= filters["from_date"])
            & (SalarySlip.posting_date <= filters["to_date"])
        )

    return query


def get_columns() -> List[Dict]:
    columns = [
        {
            "label": "Salary Slip",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Salary Slip",
            "width": 200,
        },
        {
            "label": "Branch",
            "fieldname": "branch",
            "fieldtype": "Link",
            "options": "Branch",
            "width": 150,
        },
        {
            "label": "Employee",
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 200,
        },
        {
            "label": "Employee Name",
            "fieldname": "employee_name",
            "fieldtype": "data",
            "width": 200,
        },
        {
            "label": "Posting Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Net Pay",
            "fieldname": "net_pay",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 180,
            "hidden": 1,
        },
        {
            "label": "Currency",
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
            "hidden": 1,
        },
        {
            "label": "Journal Entry",
            "fieldname": "journal_entry",
            "fieldtype": "Link",
            "options": "Journal Entry",
            "width": 180,
        },
        {
            "label": "Status",
            "fieldname": "payment_status",
            "fieldtype": "Data",
            "width": 100,
        },
    ]

    return columns
