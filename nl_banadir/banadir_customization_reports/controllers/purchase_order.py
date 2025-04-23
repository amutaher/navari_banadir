import frappe
from nl_banadir.banadir_customization_reports.controllers.work_order import (
    validate_insole_complete,
)


@frappe.whitelist()
def get_items_from_production_plan(production_plan):
    """
    Fetch items and quantities from all Work Orders associated with the given Production Plan.
    """
    work_orders = frappe.get_all(
        "Work Order",
        filters={"production_plan": production_plan},
        fields=["name", "production_item", "qty"],
    )

    items = []
    for work_order in work_orders:
        items.append(
            {
                "item_code": work_order.production_item,
                "quantity": work_order.qty,
                "work_order": work_order.name,
                "fg_item_qty": work_order.qty,
            }
        )
    frappe.response["message"] = items
    return items


"""I am against this method: how will we know 
the specific work order to get the quantity from?"""


@frappe.whitelist()
def get_qty_from_first_work_order(work_order):
    """
    Fetch items and quantities from the first Work Order associated with the given Production Plan.
    Additionally, fetch items from the 'required_materials' child table where 'item_code' contains 'UPPER'.
    """

    work_order = frappe.get_doc("Work Order", work_order)
    rate = get_job_charges_rate(work_order)

    required_materials = frappe.get_all(
        "Work Order Item",
        filters=[["parent", "=", work_order.name], ["item_code", "like", "%UPPER%"]],
        fields=["item_code"],
    )

    response = {
        "work_order_qty": work_order.qty,
        "upper_stock_items": [],
        "rate": rate,
    }

    if required_materials:
        response["upper_stock_items"] = required_materials[0]["item_code"]

    frappe.response["message"] = response


def get_job_charges_rate(work_order):
    """
    Fetch the job charges rate from the BOM associated with the given Work Order.
    """
    bom = frappe.get_doc("BOM", work_order.bom_no)
    return bom.custom_job_charges_rate or 0.0


def before_save(doc, method=None):
    validate_insole_complete(doc)
