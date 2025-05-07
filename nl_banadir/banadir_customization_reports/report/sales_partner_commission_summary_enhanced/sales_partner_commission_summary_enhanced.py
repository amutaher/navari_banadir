# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _, msgprint


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_entries(filters)

    if filters.get("doctype") == "Sales Invoice":
        data = get_journal_entries(data)

    return columns, data


def get_columns(filters):
    if not filters.get("doctype"):
        msgprint(_("Please select the document type first"), raise_exception=1)

    columns = [
        {
            "label": _(filters["doctype"]),
            "options": filters["doctype"],
            "fieldname": "name",
            "fieldtype": "Link",
            "width": 140,
        },
        {
            "label": _("Customer"),
            "options": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "width": 140,
        },
        {
            "label": _("Territory"),
            "options": "Territory",
            "fieldname": "territory",
            "fieldtype": "Link",
            "width": 100,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Sales Partner"),
            "options": "Sales Partner",
            "fieldname": "sales_partner",
            "fieldtype": "Link",
            "width": 140,
        },
        {
            "label": _("Commission Rate %"),
            "fieldname": "commission_rate",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Total Commission"),
            "fieldname": "total_commission",
            "fieldtype": "Currency",
            "width": 120,
        },
    ]

    if filters.get("doctype") == "Sales Invoice":
        columns.append(
            {
                "label": _("Journal Entry"),
                "options": "Journal Entry",
                "fieldname": "journal_entry",
                "fieldtype": "Link",
                "width": 140,
            }
        )

    return columns


def get_entries(filters):
    date_field = (
        "transaction_date"
        if filters.get("doctype") == "Sales Order"
        else "posting_date"
    )

    conditions = get_conditions(filters, date_field)
    entries = frappe.db.sql(
        """
		SELECT
			name, customer, territory, {} as posting_date, base_net_total as amount,
			sales_partner, commission_rate, total_commission
		FROM
			`tab{}`
		WHERE
			{} and docstatus = 1 and sales_partner is not null
			and sales_partner != '' order by name desc, sales_partner
		""".format(
            date_field, filters.get("doctype"), conditions
        ),
        filters,
        as_dict=1,
    )

    return entries


def get_conditions(filters, date_field):
    conditions = "1=1"

    for field in ["company", "customer", "territory"]:
        if filters.get(field):
            conditions += f" and {field} = %({field})s"

    if filters.get("sales_partner"):
        conditions += " and sales_partner = %(sales_partner)s"

    if filters.get("from_date"):
        conditions += f" and {date_field} >= %(from_date)s"

    if filters.get("to_date"):
        conditions += f" and {date_field} <= %(to_date)s"

    return conditions


def get_journal_entries(data):
    je_doc = frappe.qb.DocType("Journal Entry")
    si_list = [x.name for x in data]

    query = (
        frappe.qb.from_(je_doc)
        .select(je_doc.name, je_doc.sales_invoice)
        .where(je_doc.sales_invoice.isin(si_list))
    )
    journal_entries = query.run(as_dict=True)

    if journal_entries:
        entry_lookup = {
            entry["sales_invoice"]: entry["name"] for entry in journal_entries
        }

        for x in data:
            if x["name"] in entry_lookup:
                x["journal_entry"] = entry_lookup[x["name"]]

        return data

    return data


# def execute(filters: dict | None = None):
# 	"""Return columns and data for the report.

# 	This is the main entry point for the report. It accepts the filters as a
# 	dictionary and should return columns and data. It is called by the framework
# 	every time the report is refreshed or a filter is updated.
# 	"""
# 	columns = get_columns()
# 	data = get_data()

# 	return columns, data


# def get_columns() -> list[dict]:
# 	"""Return columns for the report.

# 	One field definition per column, just like a DocType field definition.
# 	"""
# 	return [
# 		{
# 			"label": _("Column 1"),
# 			"fieldname": "column_1",
# 			"fieldtype": "Data",
# 		},
# 		{
# 			"label": _("Column 2"),
# 			"fieldname": "column_2",
# 			"fieldtype": "Int",
# 		},
# 	]


# def get_data() -> list[list]:
# 	"""Return data for the report.

# 	The report data is a list of rows, with each row being a list of cell values.
# 	"""
# 	return [
# 		["Row 1", 1],
# 		["Row 2", 2],
# 	]
