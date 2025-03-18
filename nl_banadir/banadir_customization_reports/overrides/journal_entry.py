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
                        "date": doc.posting_date,
                        "from_currency": "USD",
                        "from_amount": account.credit_in_account_currency,
                        "to_currency": "INR",
                        "to_amount": account.credit,
                        "exchange_rate": account.exchange_rate,
                    }
                )

                cc_doc.insert()
