import frappe


def on_submit(doc, method=None):
    if doc.company == "Banadir Overseas PVT LTD":
        for account in doc.accounts:
            if (
                account.party_type == "Customer"
                and account.party == "Banadir General Trading LLC"
                and account.account_currency == "USD"
                and account.exchange_rate
            ):
                cc_doc = frappe.get_doc(
                    {
                        "doctype": "Currency Conversion",
                        "from_currency": "USD",
                        "to_currency": "INR",
                        "exchange_rate": account.exchange_rate,
                    }
                )

                cc_doc.insert()
