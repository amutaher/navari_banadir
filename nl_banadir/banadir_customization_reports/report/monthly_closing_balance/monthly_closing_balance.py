# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
import json
import os
from datetime import datetime, date
from decimal import Decimal
from frappe import _
from frappe.utils import flt, getdate, add_months, add_days

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
	get_dimension_with_children,
)
from ..general_ledger_report.general_ledger_report import (
	initialize_gle_map,
    get_accountwise_gle,
    get_gl_entries,
	get_data_with_opening_closing
)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()  # Convert to string format (YYYY-MM-DD)
    raise TypeError(f"Type {type(obj)} not serializable")

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters=None):
    columns = [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "width": 300},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 150, "hidden": 1},
        {"label": _("Indent"), "fieldname": "indent", "fieldtype": "Int", "width": 50, "hidden": 1},
    ]
    
    periods = generate_periods(filters.from_date, filters.to_date, filters.periodicity)
    for period in periods:
        # Since periods now returns tuples (label, start_date, end_date), use only the label (first element)
        period_label = period[0] if isinstance(period, tuple) else period
        columns.extend([
            {
                "label": _(f"{period_label} Opening"),
                "fieldname": f"{period_label.lower().replace(' ', '_')}_opening",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150
            },
            {
                "label": _(f"{period_label} Debit"),
                "fieldname": f"{period_label.lower().replace(' ', '_')}_debit",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150,
                # "hidden": 1
            },
            {
                "label": _(f"{period_label} Credit"),
                "fieldname": f"{period_label.lower().replace(' ', '_')}_credit",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150,
                # "hidden": 1
            },
            {
                "label": _(f"{period_label} Closing"),
                "fieldname": f"{period_label.lower().replace(' ', '_')}_closing",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150
            }
        ])

    return columns

def generate_periods(from_date, to_date, periodicity):
    periods = []
    current_date = getdate(from_date)
    end_date = getdate(to_date)
    
    while current_date <= end_date:
        if periodicity == "Monthly":
            period_label = current_date.strftime("%b %Y")
            start_date = current_date
            current_date = add_months(current_date, 1)
            end_date_period = add_days(current_date, -1)
        elif periodicity == "Quarterly":
            quarter = (current_date.month - 1) // 3 + 1
            period_label = f"Q{quarter} {current_date.year}"
            start_date = current_date
            current_date = add_months(current_date, 3)
            end_date_period = add_days(current_date, -1)
        else:  # Yearly
            period_label = str(current_date.year)
            start_date = current_date
            current_date = add_months(current_date, 12)
            end_date_period = add_days(current_date, -1)
        
        periods.append((period_label, start_date, end_date_period))
    
    return periods

def get_accounts_with_hierarchy(company, root_type=None):
    query = """
        SELECT 
            name,
            account_name,
            parent_account,
            is_group,
            root_type,
            lft,
            rgt,
            account_currency as currency
        FROM `tabAccount`
        WHERE company=%s
    """
    
    parameters = [company]
    
    if root_type:
        query += " AND root_type=%s"
        parameters.append(root_type)
    
    query += " ORDER BY lft"
    
    accounts = frappe.db.sql(query, parameters, as_dict=True)
    
    parent_dict = {}
    for account in accounts:
        parent_dict[account.name] = account.parent_account
    
    for account in accounts:
        indent = 0
        parent = account.parent_account
        while parent:
            indent += 1
            parent = parent_dict.get(parent)
        account.indent = indent
    
    return accounts


def get_data(filters=None):
    data = []
    periods = generate_periods(filters.from_date, filters.to_date, filters.periodicity)
    accounts = get_accounts_with_hierarchy(filters.company)
    accounting_dimensions = get_accounting_dimensions()

    account_balances = {account["name"]: {
        "account": account["account_name"],
        "currency": account["currency"],
        "indent": account["indent"],
    } for account in accounts}

    for period_label, period_start, period_end in periods:
        period_filters = filters.copy()
        period_filters.update({
            "from_date": period_start,
            "to_date": period_end,
            "periodicity": "Monthly"
        })

        gl_entries = get_gl_entries(period_filters, accounting_dimensions)
        period_data = get_data_with_opening_closing(period_filters, accounts, accounting_dimensions, gl_entries)

        current_directory = os.getcwd()
        file_path = os.path.join(current_directory, "myfile.json")

        with open(file_path, 'a', encoding='utf8') as json_file:
            json.dump(period_data, json_file, ensure_ascii=True, indent=4, default=json_serial)
            json_file.write("\n")

        print(f"Period: {period_label}, Data: {json.dumps(period_data, indent=4,default=json_serial)}")

        for record in period_data:
            account_name = record.get("account")
            if account_name in account_balances:
                # Store balances under dynamically named keys for each month
                account_balances[account_name][f"{period_label.lower().replace(' ', '_')}_opening"] = record.get("opening", {}).get("debit", 0) - record.get("opening", {}).get("credit", 0)
                account_balances[account_name][f"{period_label.lower().replace(' ', '_')}_debit"] = record.get("debit", 0)
                account_balances[account_name][f"{period_label.lower().replace(' ', '_')}_credit"] = record.get("credit", 0)
                account_balances[account_name][f"{period_label.lower().replace(' ', '_')}_closing"] = account_balances[account_name][f"{period_label.lower().replace(' ', '_')}_opening"] + record.get("debit", 0) - record.get("credit", 0)


    data = list(account_balances.values())

    return data