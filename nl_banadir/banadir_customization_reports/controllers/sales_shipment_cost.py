import frappe


def collect_sales_data(doc):
    """Collect sales document data and calculate container/carton totals"""
    sales_invoice_items = doc.purchase_receipts
    total_container_value = 0
    total_carton_value = 0
    sales_docs = {}
    item_container_map = {}

    for pr in sales_invoice_items:
        sales_type = pr.receipt_document_type
        sales_name = pr.receipt_document

        # Cache sales documents to avoid repeated database calls
        if sales_name not in sales_docs:
            sales_docs[sales_name] = frappe.get_doc(sales_type, sales_name)

        sales_doc = sales_docs[sales_name]

        for item in sales_doc.items:
            item_key = f"{item.item_code}_{item.qty}"
            item_container_map[item_key] = item
            total_container_value += item.custom_containers
            total_carton_value += item.custom_cartons

    # Calculate loss or profit
    loss_or_profit = 1 - total_container_value
    loss_or_profit_amount = loss_or_profit * doc.total_taxes_and_charges
    doc.profitloss_in_container_amount = loss_or_profit_amount

    return sales_docs, item_container_map, total_container_value, total_carton_value


def update_landed_cost_items(doc, item_container_map, total_container_value):
    """Update landed cost voucher items with new rates"""
    # docs_to_save = set()

    for lc_item in doc.items:
        item_key = f"{lc_item.item_code}_{lc_item.qty}"

        if item_key in item_container_map and total_container_value != 0:
            pr_item = item_container_map[item_key]
            pr_container_value = pr_item.custom_containers

            # Calculate applicable charges based on container ratio
            item_container_ratio = pr_container_value / total_container_value
            applicable_amount = item_container_ratio * doc.total_taxes_and_charges
            lc_item.applicable_charges = applicable_amount

            new_rate = (applicable_amount + lc_item.amount) / lc_item.qty
            lc_item.new_rate = new_rate
            pr_item.price_list_rate = lc_item.rate
            pr_item.rate = lc_item.rate

    return item_container_map


def update_sales_documents(
    sales_docs, item_container_map, total_container_value, total_carton_value
):
    """Update and save modified sales documents"""
    docs_to_save = set()

    # Identify documents that need to be saved
    for sales_name, sales_doc in sales_docs.items():
        if sales_doc.docstatus == 0:
            for item in sales_doc.items:
                item_key = f"{item.item_code}_{item.qty}"
                if item_key in item_container_map:
                    docs_to_save.add(sales_name)
                    break

    # Update and save all modified documents
    for sales_name in docs_to_save:
        sales_doc = sales_docs[sales_name]
        sales_doc.custom_total_containers = total_container_value
        sales_doc.custom_total_cartons = total_carton_value
        sales_doc.save()


def before_cancel(doc, method):
    if doc.distribute_charges_based_on == "Amount":
        sales_docs, item_container_map, total_container_value, total_carton_value = (
            collect_sales_data(doc)
        )
        item_container_map = update_landed_cost_items(
            doc, item_container_map, total_container_value
        )
        update_sales_documents(
            sales_docs, item_container_map, total_container_value, total_carton_value
        )
