import frappe
from frappe import _

def validate_branch_company(doc, method):
    """
    Validates that the branch belongs to the correct company before saving.
    This applies to multiple doctypes like Sales Invoice, Purchase Invoice, etc.
    """
    if not doc.branch:
        return 

    branch_company = frappe.get_value("Branch", doc.branch, "custom_company")
    if branch_company and doc.company and branch_company != doc.company:
        frappe.throw(
            _("Branch <b>{0}</B> belongs to company <b>{1}</b>, but you are using company <b>{2}.</b>")
            .format(doc.branch, branch_company, doc.company)
        )

def validate_branch_company_item_level(doc , method):
    """
    Validates that the branch belongs to the correct company at the item level.
    This applies to multiple doctypes like Sales Invoice, Purchase Invoice, etc.
    """

    for item in doc.accounts:
        item_branch_company = frappe.get_value("Branch", item.branch, "custom_company")

        if item_branch_company and doc.company and item_branch_company != doc.company:
            frappe.throw(
                _("Branch <b>{0}</B> belongs to company <b>{1}</b>, but you are using company <b>{2}.</b>")
                .format(item.branch, item_branch_company, doc.company)
            )
            break