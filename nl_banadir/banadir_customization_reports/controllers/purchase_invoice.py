from datetime import datetime
from frappe.model.naming import make_autoname
import frappe

def auto_name(doc, method=None):
    if doc.company=="Banadir Steel LTD":
        company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
        if not company_abbr:
            frappe.throw(f"Company abbreviation not found for {doc.company}")

        current_year = datetime.now().year

        base_name = make_autoname(f"{company_abbr}-.####")
        doc.name = f"{base_name}-{current_year}"
    
# def get_taxes_and_charges(doc, method=None):
#     if doc.tax_id and doc.tax_id.startswith('06'):
       
#         doc.append('taxes', {
#             'charge_type': 'On Net Total',
#             'account_head': '2101 - VAT Payable',
#             'description': 'VAT 6%',
#             'tax_amount': doc.total * 0.06
#         },
#                    {
#             'charge_type': 'On Net Total',
#             'account_head': '2101 - VAT Payable',
#             'description': 'VAT 6%',
#             'tax_amount': doc.total * 0.06
#         })