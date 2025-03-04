
from frappe.utils import flt
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months
from erpnext.accounts.utils import get_fiscal_year

import frappe
from frappe.utils import flt, getdate, add_months

def execute(filters=None):
    if not filters:
        filters = {}

    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value("Company", company, "default_currency")
    
    # Get the currency symbol instead of abbreviation
    currency_symbol = get_currency_symbol(presentation_currency)

    periodicity = filters.get("periodicity", "Yearly")

    columns = get_columns(from_date, to_date, periodicity)
    data = get_data(company, from_date, to_date, filters, presentation_currency, periodicity)
    
    total_income, total_expense, profit = calculate_totals(data, company)

    chart = get_profit_loss_chart(total_income, total_expense, profit, currency_symbol)
    data = append_profit_loss_row(data, company)
    # Summary Section (Single Line Format)
    report_summary = [
        {
            "label": _("Total Income"),
            "value": f"{currency_symbol} {flt(total_income, 2):,.2f}",
            "indicator": "Green",
        },
        {"type": "separator", "value": "-"},
        {
            "label": _("Total Expense"),
            "value": f"{currency_symbol} {flt(total_expense, 2):,.2f}",
            "indicator": "Red",
        },
        {"type": "separator", "value": "=", "color": "blue"},
        {
            "label": _("Profit"),
            "value": f"{currency_symbol} {flt(profit, 2):,.2f}",
            "indicator": "Blue" if profit >= 0 else "Red",
        }
    ]

    return columns, data, None, chart, report_summary


def get_currency_symbol(currency):
	return frappe.db.get_value("Currency", currency, "symbol") or currency

def append_profit_loss_row(data, company):
    profit_row = {"account": "Profit/Loss", "account_name": "<b style='color:red'>Profit for the Year</b>", "total": 0}
    income_total = 0
    expense_total = 0
    total_income, total_expense, profit = calculate_totals(data, company)
    # for row in data:
    #     account_doc = frappe.get_doc("Account", row["account"])
    #     if account_doc.root_type == "Income":
    #         for key in row:
    #             if key not in ["account", "account_name"]:
    #                 profit_row[key] = profit_row.get(key, 0) + row.get(key, 0)
    #                 income_total += row[key]
    #     elif account_doc.root_type == "Expense":
    #         for key in row:
    #             if key not in ["account", "account_name"]:
    #                 profit_row[key] = (profit_row.get(key, 0) or 0) - (row.get(key, 0) or 0)


    #                 expense_total += row[key]
    
    # profit_row["total"] = income_total - expense_total
    profit_row["total"] = total_income - total_expense
    data.append(profit_row)
    return data

def get_columns(from_date, to_date, periodicity):
    columns = [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 200},
        {"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 300},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 150, "hidden":1},  # Fixed fieldname
    ]
    
    periods = generate_periods(from_date, to_date, periodicity)
    for period in periods:
        columns.append({
            "label": _(period),
            "fieldname": period.lower().replace(" ", "_"),
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        })
    
    columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Currency","options":"currency", "width": 150})
    
    return columns


def generate_periods(from_date, to_date, periodicity):
    periods = []
    current_date = getdate(from_date)
    end_date = getdate(to_date)
    
    while current_date <= end_date:
        if periodicity == "Monthly":
            period_label = current_date.strftime("%b %Y")
            current_date = add_months(current_date, 1)
        elif periodicity == "Quarterly":
            quarter = (current_date.month - 1) // 3 + 1
            period_label = f"Q{quarter} {current_date.year}"
            current_date = add_months(current_date, 3)
        else:
            period_label = str(current_date.year)
            current_date = add_months(current_date, 12)
        
        periods.append(period_label)
    
    return periods

def get_data(company, from_date, to_date, filters=None, presentation_currency=None, periodicity=None):
    data = []
    accounts = get_accounts(company)
    
    gl_entries_by_account = get_gl_entries_by_account(company, from_date, to_date)
    periods = generate_periods(from_date, to_date, periodicity)
    
    for account in accounts:
        row = {"account": account.name, "account_name": account.account_name,"currency":presentation_currency, "total": 0}
        
        for period in periods:
            row[period.lower().replace(" ", "_")] = 0
        
        for entry in gl_entries_by_account.get(account.name, []):
            posting_period = get_period_label(entry["posting_date"], periodicity)
            
            # Fix: Income should be positive, Expense should be positive
            amount = entry["credit"] if account.root_type == "Income" else -entry["debit"]
            
            if presentation_currency:
                amount = convert_to_presentation_currency(amount, presentation_currency)
            
            if posting_period.lower().replace(" ", "_") not in row:
                row[posting_period.lower().replace(" ", "_")] = 0
                
            row[posting_period.lower().replace(" ", "_")] += amount
            row["total"] += amount

        if row["total"] or filters.get("show_zero_values"):
            data.append(row)
    
    return data

def calculate_totals(data, company):
    total_income = 0
    total_expense = 0
    
    for row in data:
        account_doc = frappe.get_doc("Account", row["account"])
        if account_doc.root_type == "Income":
            total_income += row["total"]
        elif account_doc.root_type == "Expense":
            total_expense += row["total"]
    
    profit = total_income - total_expense
    return total_income, total_expense, profit

def get_profit_loss_chart(total_income, total_expense, profit, currency):
    return {
        "data": {
            "labels": ["Total Income", "Total Expense", "Profit"],
            "datasets": [
                {
                    "values": [total_income, total_expense, profit]
                }
            ]
        },
        "type": "bar",  # Options: bar, line, percentage
        "colors": ["#007bff", "#dc3545", "#28a745"],  # Blue for Income, Red for Expense, Green for Profit
        "title": _("Profit & Loss Summary"),
        "summary": [
            {
                "label": _("Total Income This Year"),
                "value": f"{currency} {total_income:,.2f}",
                "indicator": "Blue"
            },
            {
                "label": _("Total Expense This Year"),
                "value": f"{currency} {total_expense:,.2f}",
                "indicator": "Red"
            },
            {
                "label": _("Profit This Year"),
                "value": f"{currency} {profit:,.2f}",
                "indicator": "Green"
            }
        ]
    }


def get_gl_entries_by_account(company, from_date, to_date):
    gl_entries = frappe.db.sql("""
        SELECT account, debit, credit, posting_date
        FROM `tabGL Entry`
        WHERE company=%s AND posting_date BETWEEN %s AND %s
    """, (company, from_date, to_date), as_dict=True)
    
    gl_entries_by_account = {}
    for entry in gl_entries:
        gl_entries_by_account.setdefault(entry.account, []).append(entry)
    
    return gl_entries_by_account

def get_accounts(company):
    return frappe.db.sql("""
        SELECT name, account_name, root_type FROM `tabAccount`
        WHERE company=%s
    """, (company,), as_dict=True)

def get_period_label(posting_date, periodicity):
    date_obj = getdate(posting_date)
    if periodicity == "Monthly":
        return date_obj.strftime("%b %Y")
    elif periodicity == "Quarterly":
        quarter = (date_obj.month - 1) // 3 + 1
        return f"Q{quarter} {date_obj.year}"
    return str(date_obj.year)

def convert_to_presentation_currency(amount, currency):
    return amount
