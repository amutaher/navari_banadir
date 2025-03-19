import frappe
from functools import reduce


def execute():
    data = get_journal_entries()
    for d in data:
        currency_conversion_doc = frappe.get_doc(
            {
                "doctype": "Currency Conversion",
                "date": d.posting_date,
                "from_currency": "USD",
                "from_amount": d.credit_in_account_currency,
                "to_currency": "INR",
                "to_amount": d.credit,
                "exchange_rate": d.exchange_rate,
            }
        )
        currency_conversion_doc.insert(ignore_if_duplicate=True)


def get_journal_entries():
    journal_entry_doc = frappe.qb.DocType("Journal Entry")
    Journal_entry_acc_doc = frappe.qb.DocType("Journal Entry Account")

    conditions = [
        journal_entry_doc.company == "Banadir Overseas PVT LTD",
        Journal_entry_acc_doc.party_type == "Customer",
        Journal_entry_acc_doc.party == "Banadir General Trading LLC",
    ]
    query = (
        frappe.qb.from_(Journal_entry_acc_doc)
        .join(journal_entry_doc)
        .on(Journal_entry_acc_doc.parent == journal_entry_doc.name)
        .select(
            journal_entry_doc.posting_date,
            Journal_entry_acc_doc.credit,
            Journal_entry_acc_doc.credit_in_account_currency,
            Journal_entry_acc_doc.exchange_rate,
        )
        .where(reduce(lambda x, y: x & y, conditions))
    )

    return query.run(as_dict=True)
