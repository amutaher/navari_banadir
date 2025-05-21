# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

from typing import List, Dict

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull, Sum


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

    # Get paid amounts from JE
    paid_amounts = get_paid_amounts([row["name"] for row in results])

    for row in results:
        slip_name = row["name"]
        payable = row.get("net_pay", 0)
        paid = paid_amounts.get(slip_name, 0.0)
        row["payable_amount"] = payable
        row["paid_amount"] = paid
        row["balance"] = payable - paid
        row["payment_status"] = "Paid" if paid >= payable else "Unpaid"

    if filters.get("status") == "Paid":
        results = [row for row in results if row["payment_status"] == "Paid"]
    elif filters.get("status") == "Unpaid":
        results = [row for row in results if row["payment_status"] == "Unpaid"]

    return results


def apply_filters(query, SalarySlip, filters: Dict):
    if filters.get("company"):
        query = query.where(SalarySlip.company == filters["company"])

    if filters.get("branch"):
        query = query.where(SalarySlip.branch == filters["branch"])

    if filters.get("employee"):
        query = query.where(SalarySlip.employee == filters["employee"])

    if filters.get("from_date") and filters.get("to_date"):
        query = query.where(
            (SalarySlip.posting_date >= filters["from_date"])
            & (SalarySlip.posting_date <= filters["to_date"])
        )

    return query


def get_paid_amounts(salary_slips: List[str]) -> Dict[str, float]:
    if not salary_slips:
        return {}

    # Step 1: Get Salary Slip info (name, employee, payroll_entry)
    salary_slip_data = frappe.get_all(
        "Salary Slip",
        filters={"name": ["in", salary_slips]},
        fields=["name", "employee", "payroll_entry"],
    )

    # Build maps
    slip_map = {
        (d["employee"], d["payroll_entry"]): d["name"]
        for d in salary_slip_data
        if d["payroll_entry"]
    }
    payroll_entries = list(
        {d["payroll_entry"] for d in salary_slip_data if d["payroll_entry"]}
    )

    paid_amounts = {}

    # Step 2: Payments directly against Salary Slips
    JEA = DocType("Journal Entry Account")
    JE = DocType("Journal Entry")

    direct_slip_query = (
        frappe.qb.from_(JEA)
        .inner_join(JE)
        .on(JEA.parent == JE.name)
        .select(JEA.reference_name, Sum(JEA.credit).as_("credit_amount"))
        .where(
            (JEA.reference_type == "Salary Slip")
            & (JEA.reference_name.isin(salary_slips))
            & (JEA.party_type == "Employee")
            & (JE.docstatus == 1)
        )
        .groupby(JEA.reference_name)
    )

    for row in direct_slip_query.run(as_dict=True):
        paid_amounts[row["reference_name"]] = row["credit_amount"]

    # Step 3: Payments indirectly via Payroll Entry (actual payment JE)
    if payroll_entries:
        payroll_payment_query = (
            frappe.qb.from_(JEA)
            .inner_join(JE)
            .on(JEA.parent == JE.name)
            .select(
                JEA.party,
                JEA.reference_name.as_("payroll_entry"),
                Sum(JEA.debit).as_("paid_amount"),
            )
            .where(
                (JEA.reference_type == "Payroll Entry")
                & (JEA.reference_name.isin(payroll_entries))
                & (JEA.party_type == "Employee")
                & (JEA.debit > 0)  # actual payment to employee
                & (JE.docstatus == 1)
            )
            .groupby(JEA.party, JEA.reference_name)
        )

        for row in payroll_payment_query.run(as_dict=True):
            key = (row["party"], row["payroll_entry"])
            slip_name = slip_map.get(key)
            if slip_name and slip_name not in paid_amounts:
                paid_amounts[slip_name] = row["paid_amount"]

    return paid_amounts


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
        {
            "label": "Payable Amount",
            "fieldname": "payable_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": "Paid Amount",
            "fieldname": "paid_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": "Balance",
            "fieldname": "balance",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
    ]

    return columns
