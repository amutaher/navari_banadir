import frappe


from frappe.model.naming import make_autoname
from frappe import _


def before_save(doc, method=None):
    if not doc.custom_subcontractors:
        currency = frappe.db.get_value("Company", doc.company, "default_currency")

        if doc.production_item:
            item_code = doc.production_item

            sub_operations = frappe.get_all(
                "Work Order Item Master",
                filters={"parent": item_code},
                fields=["operations", "item", "rate", "amount"],
                order_by="idx asc",
            )
            if not sub_operations:
                item_link = frappe.utils.get_link_to_form("Item", item_code)
                frappe.throw(f"No sub operations found for item code: {item_link}")
            for operation in sub_operations:
                doc.append(
                    "custom_subcontractors",
                    {
                        "operations": operation["operations"],
                        "rate": operation["rate"],
                        "amount": operation["amount"],
                        "item": operation["item"],
                        "currency": currency,
                    },
                )


def validate_rate(doc):
    if doc.custom_subcontractors:
        for row in doc.custom_subcontractors:
            if row.rate <= 0:
                frappe.throw(
                    _("Rate cannot be 0 or less for operation <b>{0}</b>").format(
                        row.operations
                    )
                )


def on_submit(doc, method=None):
    is_finished_good_work_order(doc)
    validate_source_warehouse(doc)
    validate_rate(doc)
    for operation in doc.custom_subcontractors:
        if (
            operation.status == "In Progress" or operation.status == "Completed"
        ) and operation.supplier is None:
            frappe.throw("Kindly enter the supplier in Sub-contractor table")


def generate_invoice_number(item_code, company_abbr):
    """
    Generate a custom invoice number in the format: item_code-company_abbreviation-series.
    """
    series = make_autoname(f"{company_abbr}-.####")
    return f"{item_code}-{series}"


def create_purchase_invoice(doc, operation, company, currency, custom_work_order):
    """
    Create a Purchase Invoice for the given operation.
    """
    company_abbr = frappe.db.get_value("Company", company, "abbr")
    if not company_abbr:
        frappe.throw(f"Company abbreviation not found for {company}")

    # Generate the custom invoice number
    custom_invoice_no = generate_invoice_number(operation.operations, company_abbr)

    # Create a new Purchase Invoice
    purchase_invoice = frappe.new_doc("Purchase Invoice")
    purchase_invoice.currency = currency
    purchase_invoice.supplier = operation.supplier
    purchase_invoice.company = company
    # purchase_invoice.set_warehouse = "Store - CW"
    purchase_invoice.update_stock = 0
    purchase_invoice.custom_work_order = custom_work_order
    purchase_invoice.custom_invoice_no = custom_invoice_no

    purchase_invoice.append(
        "items",
        {
            "item_code": operation.item,
            "qty": operation.completed_qty or 1,
            "rate": operation.rate,
            "amount": operation.amount,
            "expense_account": get_accounts(operation.item)
            if get_accounts(operation.item)
            else None,
        },
    )
    # frappe.throw(str(purchase_invoice.items))

    purchase_invoice.insert()
    # validate_accounts(purchase_invoice)
    purchase_invoice.submit()

    frappe.db.set_value(
        "Work Order Operations Item", operation.name, "invoice_created", 1
    )
    frappe.db.set_value(
        "Work Order Operations Item", operation.name, "invoice", purchase_invoice.name
    )
    doc.reload()

    return purchase_invoice


def get_accounts(item_code):
    """
    Fetch the default expense account and cost center for the given item code.
    """
    accounts = frappe.get_all(
        "Item Default",
        filters={"parenttype": "Item", "parent": item_code},
        fields=["expense_account", "buying_cost_center"],
    )

    if accounts:
        return (accounts[0].expense_account,)
    else:
        frappe.throw(f"No accounts found for item code: {item_code}")


def on_update(doc, method=None):
    """
    Main function to handle the creation of Purchase Invoices for completed operations.
    """
    validate_operations(doc)
    validate_operations_seq(doc)
    for operation in doc.custom_subcontractors:
        operation_doc = frappe.get_doc(
            "Work Order Operations Item", operation.get("name")
        )

        # Only consider operations with status "Completed" and invoice_created flag is 0
        if operation_doc.status == "Completed" and operation_doc.invoice_created == 0:
            create_purchase_invoice(
                doc=doc,
                operation=operation_doc,
                company=doc.company,
                currency=operation_doc.currency,
                custom_work_order=doc.name,
            )
            total_operation_cost(doc, operation_doc)

            frappe.msgprint(
                "Purchase Invoices successfully created for all suppliers with completed operations."
            )


def total_operation_cost(doc, operation_doc):
    current_total = doc.custom_total_operation_cost
    current_total += operation_doc.amount
    doc.custom_total_operation_cost = current_total
    frappe.db.set_value(
        "Work Order", doc.name, "custom_total_operation_cost", current_total
    )
    doc.reload()


def validate_operations(doc):
    """
    Validate the subcontractor operations in the custom_subcontractors table.
    """
    for operation in doc.custom_subcontractors:
        operation_doc = frappe.get_doc(
            "Work Order Operations Item", operation.get("name")
        )

        if (
            operation_doc.status == "In Progress" or operation_doc.status == "Completed"
        ) and operation_doc.supplier is None:
            frappe.throw("Kindly enter the supplier in the Sub-contractor table.")

        if operation_doc.status == "Completed" and (
            operation_doc.in_progress_date > operation_doc.completed_date
        ):
            frappe.throw(
                "<b>In Progress Date</b> cannot be greater than <b>Completed Date.</b>"
            )

        if operation_doc.status == "Completed" and operation_doc.completed_qty <= 0:
            frappe.throw(
                "Completed quantity must be greater than 0 for completed operations."
            )

        if operation_doc.status in ["In Progress", "Completed"]:
            if operation_doc.completed_qty > doc.qty:
                frappe.throw(
                    f"Completed quantity ({operation_doc.completed_qty}) for operation '{operation_doc.operations}' "
                    f"cannot exceed the quantity to manufacture ({doc.qty}) on this Work Order."
                )


def validate_dates(operation_doc):
    if operation_doc.in_progress_date > operation_doc.completed_date:
        frappe.throw("In Progress Date cannot be greater than Completed Date.")


def validate_operations_seq(doc, method=None):
    subcontractors = doc.custom_subcontractors or []

    for i in range(len(subcontractors)):
        current = subcontractors[i]
        if current.status == "Completed":
            if i > 0:
                previous = subcontractors[i - 1]
                if previous.status != "Completed":
                    frappe.throw(
                        f"Operation '{current.operations}' cannot be marked as Completed before '{previous.operations}' is completed."
                    )


def is_finished_work_order(doc):
    if (
        doc.production_plan_sub_assembly_item is None
        and doc.production_plan_item is not None
    ):
        return True
    else:
        return False


def is_finished_good_work_order(doc):
    if is_finished_work_order(doc):
        is_insole_complete(doc.custom_seq_id)
        validate_subcontracting_receipts(doc)
    else:
        False


def is_insole_work_order(doc):
    if not is_finished_work_order(doc):
        is_insole_complete(doc.custom_seq_id)


def is_insole_complete(seq_id):
    work_order = frappe.get_value(
        "Work Order",
        {"custom_seq_id": seq_id, "production_plan_sub_assembly_item": ["Is", "Set"]},
        "name",
    )

    if not work_order:
        return frappe.throw(
            f"No Work Order found for the given custom_seq_id: {seq_id}"
        )
    work_order_doc = frappe.get_doc("Work Order", work_order)
    if work_order_doc.status in ["Completed", "Closed"]:
        return True
    work_order_link = frappe.utils.get_link_to_form("Work Order", work_order)
    return frappe.throw(
        f"Insole Work Order {work_order_link} is not Completed or Closed."
    )


def validate_source_warehouse(doc):
    if doc.source_warehouse is None:
        frappe.throw("Kindly enter the <b>Source warehouse</b>")


# Purchase order validate insole complete
def validate_insole_complete(doc):
    for item in doc.items:
        if item.custom_work_order:
            work_order = frappe.get_doc("Work Order", item.custom_work_order)
            is_insole_complete(work_order.custom_seq_id)


def validate_subcontracting_receipts(doc):
    po_items = frappe.get_all(
        "Purchase Order Item",
        filters={"custom_work_order": doc.name},
        fields=["parent"],
    )
    if not po_items:
        frappe.throw(_("No Purchase Order Items found linked to this Work Order."))

    purchase_order_names = list(set([item.parent for item in po_items]))

    subcontracting_orders = frappe.get_all(
        "Subcontracting Order",
        filters={"purchase_order": ["in", purchase_order_names]},
        fields=["name"],
    )
    if not subcontracting_orders:
        frappe.throw(_("No Subcontracting Orders found for related Purchase Orders."))

    subcontracting_order_names = [so.name for so in subcontracting_orders]

    receipts = frappe.get_all(
        "Subcontracting Receipt Item",
        filters={
            "subcontracting_order": ["in", subcontracting_order_names],
            # "docstatus": 1,
        },
        limit=1,
    )
    if not receipts:
        frappe.throw(
            _(
                "At least one Subcontracting Receipt must be created before submitting this Work Order."
            )
        )


def update_is_finished(doc):
    if (
        doc.production_plan_sub_assembly_item is None
        and doc.production_plan_item is not None
    ):
        return True
    else:
        return False
