import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months
from erpnext.accounts.utils import get_fiscal_year

def execute(filters=None):
    if not filters:
        filters = {}
    
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    presentation_currency = filters.get("presentation_currency")
    periodicity = filters.get("periodicity", "Yearly")
    
    columns = get_columns(from_date, to_date, periodicity)
    data = get_data(company, from_date, to_date, filters, presentation_currency, periodicity)
    
    data = append_profit_loss_row(data, company)
    
    return columns, data

def get_columns(from_date, to_date, periodicity):
    columns = [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 200},
        {"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 300}
    ]
    
    periods = generate_periods(from_date, to_date, periodicity)
    for period in periods:
        columns.append({
            "label": _(period),
            "fieldname": period.lower().replace(" ", "_"),
            "fieldtype": "Currency",
            "width": 150
        })
    
    columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 150})
    
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
        row = {"account": account.name, "account_name": account.account_name, "total": 0}
        
        for period in periods:
            row[period.lower().replace(" ", "_")] = 0
        
        for entry in gl_entries_by_account.get(account.name, []):
            posting_period = get_period_label(entry["posting_date"], periodicity)
            amount = entry["credit"] - entry["debit"] if account.root_type == "Income" else entry["debit"] - entry["credit"]
            
            if presentation_currency:
                amount = convert_to_presentation_currency(amount, presentation_currency)
            
            row[posting_period.lower().replace(" ", "_")] += amount
            row["total"] += amount
        
        if row["total"] or filters.get("show_zero_values"):
            data.append(row)
    
    return data

def append_profit_loss_row(data, company):
    profit_row = {"account": "Profit/Loss", "account_name": "<b style='color:red'>Profit for the Year</b>", "total": 0}
    income_total = 0
    expense_total = 0
    
    for row in data:
        account_doc = frappe.get_doc("Account", row["account"])
        if account_doc.root_type == "Income":
            for key in row:
                if key not in ["account", "account_name"]:
                    profit_row[key] = profit_row.get(key, 0) + row[key]
                    income_total += row[key]
        elif account_doc.root_type == "Expense":
            for key in row:
                if key not in ["account", "account_name"]:
                    profit_row[key] = profit_row.get(key, 0) - row[key]
                    expense_total += row[key]
    
    profit_row["total"] = income_total - expense_total
    data.append(profit_row)
    return data

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
