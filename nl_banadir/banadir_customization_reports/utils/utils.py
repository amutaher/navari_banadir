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
            _(
                "Branch <b>{0}</B> belongs to company <b>{1}</b>, but you are using company <b>{2}.</b>"
            ).format(doc.branch, branch_company, doc.company)
        )
    if not branch_company:
        frappe.throw(
            _("Branch <b>{0}</B> does not belong to any company.").format(doc.branch)
        )


def validate_branch_company_item_level(doc, method=None):
    """
    Validates that the branch belongs to the correct company at the item level.
    This applies to multiple doctypes like Sales Invoice, Purchase Invoice, etc.

    """

    for item in doc.accounts:
        if not item.branch:
            continue
        item_branch_company = frappe.get_value("Branch", item.branch, "custom_company")

        if item_branch_company and doc.company and item_branch_company != doc.company:
            frappe.throw(
                _(
                    "Branch <b>{0}</B> belongs to company <b>{1}</b>, but you are using company <b>{2}.</b>"
                ).format(item.branch, item_branch_company, doc.company)
            )
            break
        if not item_branch_company:
            frappe.throw(
                _("Branch <b>{0}</B> does not belong to any company.").format(
                    item.branch
                )
            )
            break


@frappe.whitelist()
def check_work_order_ops():
    work_order = frappe.form_dict.get("work_order")
    incomplete_ops = frappe.get_all(
        "Work Order Operations Item",
        filters={"parent": work_order, "status": ["!=", "Completed"]},
        pluck="name",
    )
    return {"all_completed": len(incomplete_ops) == 0}


def update_or_create_item_price(item_code, price_list, rate, currency):
    existing_item_price = frappe.db.exists(
        "Item Price", {"item_code": item_code, "price_list": price_list}
    )

    if existing_item_price:
        item_price_doc = frappe.get_doc("Item Price", existing_item_price)
        item_price_doc.price_list_rate = rate
        item_price_doc.currency = currency
        item_price_doc.save(ignore_permissions=True)
        frappe.db.commit()
    else:
        # Create a new Item Price
        frappe.get_doc(
            {
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": price_list,
                "price_list_rate": rate,
                "currency": currency,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()
    frappe.msgprint("Item Price updated success", alert=True)


def create_item_price(doc):
    if not doc.customer:
        return

    # Check if customer is internal
    is_internal = frappe.db.get_value("Customer", doc.customer, "is_internal_customer")

    if not is_internal:
        return

    price_list = doc.selling_price_list or "Standard Selling"

    for item in doc.items:
        update_or_create_item_price(
            item_code=item.item_code,
            price_list=price_list,
            rate=item.rate,
            currency=doc.currency,
        )


def before_save(doc, method=None):
    if not allow_update_customer():
        return
    create_item_price(doc)


def allow_update_customer():
    selling_settings = frappe.get_single("Selling Settings")
    if selling_settings.custom_update_item_price_internal_customer:
        return True
    return False
