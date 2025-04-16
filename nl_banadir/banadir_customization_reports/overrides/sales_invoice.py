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
    if doc.custom_is_export_sale:
        try:
            shipping_detail = frappe.get_doc("Shipping Detail", doc.name)
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

            shipping_detail.save(ignore_permissions=True)

            frappe.db.commit()

        except frappe.DoesNotExistError:
            frappe.log_error(f"Shipping Detail not found: {doc.name}")
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Error updating Shipping Detail for {doc.name}: {str(e)}",
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
