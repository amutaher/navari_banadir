import frappe
from frappe import _


def validate(doc, method=None):
    if doc.custom_sub_operations:
        validate_custom_sub_operations(doc)


def validate_custom_sub_operations(doc):
    for row in doc.custom_sub_operations:
        if row.operations:
            if row.rate <= 0:
                frappe.throw(
                    _("Rate cannot be 0 or less for operation <b>{0}</b>").format(
                        row.operations
                    )
                )
