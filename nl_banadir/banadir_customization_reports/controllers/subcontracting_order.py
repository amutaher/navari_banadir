import frappe
from frappe import _
from nl_banadir.banadir_customization_reports.controllers.work_order import get_accounts, validate_insole_complete


def validate_operations(doc):
    po = frappe.get_doc("Purchase Order", doc.purchase_order)
    validate_insole_complete(po)
    
    
def before_save(doc, method=None):
    """
    Validate the operations before saving the document.
    """
    validate_operations(doc)
