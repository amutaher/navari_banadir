from datetime import datetime
from frappe.model.naming import make_autoname
import frappe


def auto_name(doc, method=None):
    if doc.company == "Banadir Steel LTD":
        if doc.custom_invoice_no:
            doc.name = doc.custom_invoice_no
            return
        company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
        if not company_abbr:
            frappe.throw(f"Company abbreviation not found for {doc.company}")

        current_year = datetime.now().year

        base_name = make_autoname(f"{company_abbr}-.####")
        doc.name = f"{base_name}-{current_year}"


def update_work_order_item(doc):
    work_order = doc.custom_work_order
    first_item_code = doc.items[0].item_code if doc.items else None
    if work_order:
        work_order_items = frappe.get_all(
            "Work Order Operations Item",
            filters={"parent": work_order, "item": first_item_code},
            fields=["name"],
        )

        for item in work_order_items:
            frappe.db.set_value(
                "Work Order Operations Item", item.name, "skip_invoice_creation", 1
            )

            # Reset the operation fields
            frappe.db.set_value(
                "Work Order Operations Item", item.name, "invoice_created", 0
            )
            frappe.db.set_value("Work Order Operations Item", item.name, "status", "")
            frappe.db.set_value(
                "Work Order Operations Item", item.name, "completed_date", None
            )

            # Update the work order's total operation cost
            work_order_doc = frappe.get_doc("Work Order", work_order)
            item_doc = frappe.get_doc("Work Order Operations Item", item.name)
            current_total = work_order_doc.custom_total_operation_cost or 0
            updated_total = current_total - item_doc.amount
            frappe.db.set_value(
                "Work Order", work_order, "custom_total_operation_cost", updated_total
            )

        frappe.db.commit()


def before_cancel(doc, method=None):
    update_work_order_item(doc)
