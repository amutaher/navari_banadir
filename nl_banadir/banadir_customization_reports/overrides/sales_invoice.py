from datetime import date

import frappe


def on_submit(doc, method=None) -> None:
    """
    Override on_submit doc event of the Sales Invoice to create Shipping Detail
    """

    book_sales_partner_commission(doc)

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


def book_sales_partner_commission(doc):
    if doc.sales_partner and doc.commission_amount > 0:
        frappe.log_error("Exectuted")
        try:
            accs = frappe.db.get_all(
                "Sales Partner Account",
                filters={"parent": doc.sales_partner, "company": doc.company},
                fields=["payable_account"],
            )

            if not accs:
                frappe.log_error("No Sales Partner Accounts found")
                return

            payable_acc = accs[0].payable_account
            journal_entry = frappe.new_doc("Journal Entry")
            journal_entry.voucher_type = "Journal Entry"
            journal_entry.company = doc.company
            journal_entry.posting_date = date.today()
            journal_entry.custom_company_group = doc.company_group
            journal_entry.sales_invoice = doc.name
            journal_entry.append(
                "accounts",
                {
                    "account": payable_acc,
                    "party_type": "Sales Partner",
                    "party": doc.sales_partner,
                    "credit_in_account_currency": doc.total_commission,
                    "company_group": doc.company_group,
                },
            )
            journal_entry.append(
                "accounts",
                {
                    "account": doc.commission_expense_account,
                    "debit_in_account_currency": doc.total_commission,
                    "company_group": doc.company_group,
                },
            )

            journal_entry.save()
            journal_entry.submit()
        except Exception:
            frappe.log_error(
                "Error while creating Journal Entry", frappe.get_traceback()
            )
