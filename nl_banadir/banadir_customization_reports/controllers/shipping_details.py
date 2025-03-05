import frappe
from frappe import _

def sync_shipping_details(doc, method):
    """
    Enqueue the synchronization of shipping details to run in the background.
    Triggered on update_after_submit of Sales Invoice or Purchase Invoice.
    """
    frappe.enqueue(
        "nl_banadir.banadir_customization_reports.controllers.shipping_details.process_shipping_sync",
        queue="short",
        job_id=f"sync_shipping_details_for_{doc.doctype}_{doc.name}",
        doc=doc,
    )


def process_shipping_sync(doc):
    """
    Sync shipping details across all invoices linked by transit_no and update shipping status if needed.
    This runs in the background.
    """
    
    fields_to_sync = [
        "custom_container_no",
        "custom_port_of_loading",
        "custom_bill_of_landing",
        "custom_bil",
        "custom_estimated_date_of_departure",
        "custom_destination",
        "custom_port_of_discharge",
        "custom_container_quantity",
        "custom_estimated_date_of_arrival",
        "custom_actual_arrival_date",
        "custom_shipping_status",
    ]

    original_doc = frappe.get_doc(doc.doctype, doc.name, for_update=False)

    fields_changed = False
    for field in fields_to_sync:
        if doc.get(field) != original_doc.get(field):
            fields_changed = True
            break

    if not fields_changed:
        return

    # Get all transit numbers from the current invoice
    transit_numbers = [row.transit_no for row in doc.get("custom_transit_number")]

    if not transit_numbers:
        return

    # Find all related invoices (Sales and Purchase) with matching transit_no
    related_invoices = frappe.get_all(
        "Transit Numbers",
        filters={"transit_no": ["in", transit_numbers]},
        fields=["parent", "parenttype"],
        distinct=True
    )

    values_to_update = {field: doc.get(field) for field in fields_to_sync}

    if doc.get("custom_actual_arrival_date") and doc.get("custom_actual_arrival_date") != original_doc.get("custom_actual_arrival_date"):
        values_to_update["custom_shipping_status"] = "Completed"

    for inv in related_invoices:
        if inv.parent == doc.name and inv.parenttype == doc.doctype:
            continue

        frappe.db.set_value(
            inv.parenttype,
            inv.parent,
            values_to_update,
            update_modified=False
        )

        frappe.logger().info(f"Updated shipping details in {inv.parenttype} {inv.parent}")

    frappe.db.commit()