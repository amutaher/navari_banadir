import frappe


def on_submit(doc, method=None) -> None:
    """
    Override on_submit doc event of the Sales Invoice to create Shipping Detail
    """

    if doc.custom_is_export_sale:
        if frappe.db.exists("Shipping Detail", doc.name):
            return

        try:
            shipping_detail = frappe.new_doc("Shipping Detail")
            shipping_detail.sales_invoice_no = doc.name
            shipping_detail.company = doc.company
            shipping_detail.customer = doc.customer
            shipping_detail.container_no = doc.custom_container_no
            shipping_detail.port_of_loading = doc.custom_port_of_loading
            shipping_detail.estimated_date_of_departure = (
                doc.custom_estimated_date_of_departure
            )
            shipping_detail.estimated_date_of_arrival = (
                doc.custom_estimated_date_of_arrival
            )
            shipping_detail.actual_arrival_date = doc.custom_actual_arrival_date
            shipping_detail.destination = doc.custom_destination
            shipping_detail.port_of_discharge = doc.custom_port_of_discharge

            shipping_detail.insert(ignore_permissions=True)
            shipping_detail.submit()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), str(e))


def update_shipping_details_on_save_after_submit(doc, method=None) -> None:
    """
    Update shipping details when the Sales Invoice is updated after submit.
    """
    fields_to_update = [
        "container_no",
        "port_of_loading",
        "estimated_date_of_departure",
        "destination",
        "port_of_discharge",
        "estimated_date_of_arrival",
        "actual_arrival_date",
    ]

    values_to_update = {field: doc.get(f"custom_{field}") for field in fields_to_update}

    frappe.db.set_value(
        "Shipping Detail", doc.name, values_to_update, update_modified=True
    )


def on_cancel(doc, method=None) -> None:
    """
    Delete Shipping Detail when the Sales Invoice is cancelled.
    """
    try:
        shipping_detail_name = frappe.db.get_value(
            "Shipping Detail", {"sales_invoice_no": doc.name}
        )

        if shipping_detail_name:
            frappe.delete_doc(
                "Shipping Detail", shipping_detail_name, ignore_permissions=True
            )

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            f"Error deleting Shipping Detail for {doc.name}: {str(e)}",
        )


# nl_banadir.banadir_customization_reports.overrides.sales_invoice.on_submit


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
        distinct=True,
    )

    values_to_update = {field: doc.get(field) for field in fields_to_sync}

    if doc.get("custom_actual_arrival_date") and doc.get(
        "custom_actual_arrival_date"
    ) != original_doc.get("custom_actual_arrival_date"):
        values_to_update["custom_shipping_status"] = "Completed"

    for inv in related_invoices:
        if inv.parent == doc.name and inv.parenttype == doc.doctype:
            continue

        frappe.db.set_value(
            inv.parenttype, inv.parent, values_to_update, update_modified=True
        )
