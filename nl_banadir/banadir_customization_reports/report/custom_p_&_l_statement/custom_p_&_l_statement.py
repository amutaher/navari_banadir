from frappe.utils import flt
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months
from erpnext.accounts.utils import get_fiscal_year

from frappe.query_builder import DocType


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
    
    total_income, total_expense, profit = calculate_totals(data)

    chart = get_profit_loss_chart(total_income, total_expense, profit, currency_symbol)
    data = append_profit_loss_row(data, total_income, total_expense)
    
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

def append_profit_loss_row(data, total_income, total_expense):
    profit = total_income - total_expense
    profit_row = {
 "account":  "<b style='color:red'>Profit for the Year</b>", 
 "warn_if_negative": True,
  "total": profit, 
        "indent": 0
    }
    data.append(profit_row)
    return data

def get_columns(from_date, to_date, periodicity):
    columns = [
        {"label": _("Account"), "fieldname": "account", "fieldtype": "Data", "options": "Account", "width": 300},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 150, "hidden": 1},
        {"label": _("Indent"), "fieldname": "indent", "fieldtype": "Int", "width": 50, "hidden": 1},
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
    
    columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "options": "currency", "width": 150})
    
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
        else:  # Yearly
            period_label = str(current_date.year)
            current_date = add_months(current_date, 12)
        
        periods.append(period_label)
    
    return periods
def get_data(company, from_date, to_date, filters=None, presentation_currency=None, periodicity=None):
    data = []
    gl_entries_by_account = get_gl_entries_by_account(company, from_date, to_date)
    periods = generate_periods(from_date, to_date, periodicity)
    
    # Process Income section
    income_accounts = get_accounts_with_hierarchy(company, "Income")
    income_data = process_account_category(
        income_accounts, 
        gl_entries_by_account, 
        periods, 
        presentation_currency, 
        periodicity, 
        filters,
        "Income"
    )
    
    # Calculate Income total using only leaf (non-group) accounts to avoid double counting
    income_total = calculate_category_total(income_data)
    
    # Add section header for Income
    income_header = {
        "account": "<b style='color:green'>Income</b>",
        "indent": 0,
        "currency": presentation_currency,
        "total": income_total
    }
    
    # Initialize period values for the header
    for period in periods:
        period_key = period.lower().replace(" ", "_")
        # Calculate period totals from non-group accounts
        period_total = 0
        for row in income_data:
            # Check if it's not a group account (doesn't have <b> tag)
            if "<b>" not in row.get("account", ""):
                period_total += row.get(period_key, 0)
        income_header[period_key] = period_total
    
    # Process Expense section
    expense_accounts = get_accounts_with_hierarchy(company, "Expense")
    expense_data = process_account_category(
        expense_accounts, 
        gl_entries_by_account, 
        periods, 
        presentation_currency, 
        periodicity, 
        filters,
        "Expense"
    )
    
    # Calculate Expense total using only leaf accounts to avoid double counting
    expense_total = calculate_category_total(expense_data)
    
    # Add section header for Expense
    expense_header = {
        "account": "<b style='color:red'>Expense</b>",
        "indent": 0,
        "currency": presentation_currency,
        "total": expense_total
    }
    
    # Initialize period values for the header
    for period in periods:
        period_key = period.lower().replace(" ", "_")
        # Calculate period totals from non-group accounts
        period_total = 0
        for row in expense_data:
            # Check if it's not a group account
            if "<b>" not in row.get("account", ""):
                period_total += row.get(period_key, 0)
        expense_header[period_key] = period_total
    
    # Combine all data with section headers
    if income_data:
        data.append(income_header)
        data.extend(income_data)
    
    if expense_data:
        data.append(expense_header)
        data.extend(expense_data)
    
    return data

def calculate_category_total(category_data):
    """Calculate the total of a category by only summing leaf accounts (not group accounts)"""
    total = 0
    for row in category_data:
        # Check if this is not a group account (bold text indicates group)
        if "<b>" not in row.get("account", ""):
            total += row.get("total", 0)
    return total


def process_account_category(accounts, gl_entries_by_account, periods, presentation_currency, periodicity, filters, root_type):
    """Process a single category of accounts (Income or Expense)"""
    data = []
    processed_parents = set()
    account_dict = {account.name: account for account in accounts}
    
    # Process top-level accounts first
    top_level_accounts = [acc for acc in accounts if acc.parent_account is None or acc.parent_account not in account_dict]
    
    for account in top_level_accounts:
        if account.name in processed_parents:
            continue
            
        account_rows = process_account_with_children(
            account, 
            accounts, 
            gl_entries_by_account, 
            periods, 
            presentation_currency, 
            periodicity, 
            filters, 
            account.indent, 
            processed_parents,
            root_type
        )
        
        data.extend(account_rows)
    
    return data

def process_account_with_children(account, all_accounts, gl_entries, periods, presentation_currency, periodicity, filters, indent, processed_parents, root_type):
    """Process an account and all its children recursively"""
    result_rows = []
    
    # Mark this account as processed
    processed_parents.add(account.name)
    
    # Create row for this account
    row = {
        "account": account.account_name, # Use account_name instead of name
        "currency": presentation_currency,
        "indent": indent,
        "root_type": root_type,
        "total": 0
    }
    
    # Format parent account name in bold
    if account.is_group:
        row["account"] = f"<b>{account.account_name}</b>"
    
    # Initialize period values
    for period in periods:
        row[period.lower().replace(" ", "_")] = 0
    
    # Get direct GL entries for this account
    if account.name in gl_entries:
        entries = gl_entries[account.name]
        for entry in entries:
            posting_period = get_period_label(entry["posting_date"], periodicity)
            period_key = posting_period.lower().replace(" ", "_")
            
            # Calculate amount with correct sign for account type
            if root_type == "Income":
                # For Income accounts: Credit - Debit (credits increase income)
                amount = entry["credit"]
            else:
                # For Expense accounts: Debit - Credit (debits increase expenses)
                amount = entry["debit"] - entry["credit"]
            
            if presentation_currency:
                amount = convert_to_presentation_currency(amount, presentation_currency)
            
            if period_key not in row:
                row[period_key] = 0
                
            row[period_key] += amount
            row["total"] += amount
    
    # Process children if this is a group account
    children = [acc for acc in all_accounts if acc.parent_account == account.name]
    
    if children:
        child_rows = []
        for child in children:
            child_row_set = process_account_with_children(
                child, 
                all_accounts, 
                gl_entries, 
                periods, 
                presentation_currency, 
                periodicity, 
                filters, 
                indent + 1, 
                processed_parents,
                root_type
            )
            
            child_rows.extend(child_row_set)
            
            # Rollup child totals to parent
            for child_row in child_row_set:
                row["total"] += child_row.get("total", 0)
                
                for period in periods:
                    period_key = period.lower().replace(" ", "_")
                    if period_key in child_row and period_key in row:
                        row[period_key] += child_row[period_key]
    
    # Add row if it has value or show_zero_values is enabled
    has_value = row["total"] != 0
    
    if has_value or filters.get("show_zero_values"):
        result_rows.append(row)
        
        # Add child rows if this is a group account
        if children:
            child_rows = []
            for child in children:
                child_processed_parents = set()
                child_row_set = process_account_with_children(
                    child, 
                    all_accounts, 
                    gl_entries, 
                    periods, 
                    presentation_currency, 
                    periodicity, 
                    filters, 
                    indent + 1, 
                    child_processed_parents,
                    root_type
                )
                
                # Only add child rows with values or if showing zero values
                for cr in child_row_set:
                    if cr.get("total", 0) != 0 or filters.get("show_zero_values"):
                        child_rows.append(cr)
                
            result_rows.extend(child_rows)
    
    return result_rows

def calculate_totals(data):
    """Calculate the total income, expense and profit"""
    total_income = 0
    total_expense = 0
    
    for row in data:
        account = row.get("account", "").strip()
        if "<b style='color:green'>Income</b>" in account:
            total_income = row.get("total", 0)
        elif "<b style='color:red'>Expense</b>" in account:
            total_expense = row.get("total", 0)
    
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
        "type": "bar",
        "colors": ["#28a745", "#dc3545", "#007bff"],  # Green for Income, Red for Expense, Blue for Profit
        "title": _("Profit & Loss Summary"),
        "summary": [
            {
                "label": _("Total Income"),
                "value": f"{currency} {total_income:,.2f}",
                "indicator": "Green"
            },
            {
                "label": _("Total Expense"),
                "value": f"{currency} {total_expense:,.2f}",
                "indicator": "Red"
            },
            {
                "label": _("Profit"),
                "value": f"{currency} {profit:,.2f}",
                "indicator": "Blue" if profit >= 0 else "Red"
            }
        ]
    }

def get_gl_entries_by_account(company, from_date, to_date, ignore_opening_entries=False):
    gl_entry = DocType("GL Entry")

    query = (
        frappe.qb.from_(gl_entry)
        .select(
            gl_entry.account,
            gl_entry.debit,
            gl_entry.credit,
            gl_entry.debit_in_account_currency,
            gl_entry.credit_in_account_currency,
            gl_entry.account_currency,
            gl_entry.posting_date,
            gl_entry.is_opening,
            gl_entry.fiscal_year
        )
        .where(gl_entry.company == company)
        .where(gl_entry.posting_date.between(from_date, to_date))
        .where(gl_entry.is_cancelled == 0)
    )

    if ignore_opening_entries:
        query = query.where(gl_entry.is_opening == "No")

    gl_entries = query.run(as_dict=True)

    # Group entries by account
    gl_entries_by_account = {}
    for entry in gl_entries:
        gl_entries_by_account.setdefault(entry["account"], []).append(entry)
    
    return gl_entries_by_account

def get_accounts_with_hierarchy(company, root_type=None):
    """Get accounts with hierarchy information, filtered by root_type if specified"""
    query = """
        SELECT 
            name, 
            account_name, 
            parent_account, 
            is_group, 
            root_type, 
            lft, 
            rgt
        FROM `tabAccount`
        WHERE company=%s
    """
    
    parameters = [company]
    
    if root_type:
        query += " AND root_type=%s"
        parameters.append(root_type)
    
    query += " ORDER BY lft"
    
    accounts = frappe.db.sql(query, parameters, as_dict=True)
    
    # Create a dictionary to store parent-child relationships
    parent_dict = {}
    for account in accounts:
        parent_dict[account.name] = account.parent_account
    
    # Calculate indent level for each account
    for account in accounts:
        indent = 0
        parent = account.parent_account
        
        # Traverse up the parent chain to determine level
        while parent:
            indent += 1
            parent = parent_dict.get(parent)
        
        account.indent = indent
    
    return accounts

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