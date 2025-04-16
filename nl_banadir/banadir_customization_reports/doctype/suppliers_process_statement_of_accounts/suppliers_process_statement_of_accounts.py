# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import copy
import frappe
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, today, add_months, format_date, add_days
from frappe.utils.pdf import get_pdf
from frappe.utils.jinja import validate_template

# nl_banadir.banadir_customization_reports.doctype.suppliers_process_statement_of_accounts.suppliers_process_statement_of_accounts.fetch_suppliers

from nl_banadir.banadir_customization_reports.overrides.process_of_statements import (
    get_html,
)

from erpnext import get_company_currency
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    execute as get_ar_soa,
)
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
    execute as get_ageing,
)
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa


class SuppliersProcessStatementOfAccounts(Document):
    def validate(self):
        if not self.subject:
            self.subject = "Statement of Accounts for {{ supplier.supplier_name }}"
        if not self.body:
            body_str = ""
            if self.report == "General Ledger":
                body_str = " from {{ doc.from_date }} to {{ doc.to_date }}."
            else:
                body_str = (
                    "Hello {{ supplier.supplier_name }},<br>PFA your Statement of Accounts"
                    + body_str
                )
            self.body = (
                "Hello {{ supplier.supplier_name }},<br>PFA your Statement Of Accounts"
                + body_str
            )
        if not self.pdf_name:
            self.pdf_name = "{{ supplier.supplier_name }}"

        validate_template(self.subject)
        validate_template(self.body)

        if not self.suppliers:
            frappe.throw(_("Suppliers not selected."))

        if self.enable_auto_email:
            if self.start_date and getdate(self.start_date) >= getdate(today()):
                self.to_date = self.start_date
                self.from_date = add_months(self.to_date, -1 * self.filter_duration)


def get_report_pdf(doc, consolidated=True):
    statement_dict = get_statement_dict(doc)
    if not bool(statement_dict):
        return False
    elif consolidated:
        delimiter = (
            '<div style="page-break-before: always;"></div>'
            if doc.include_break
            else ""
        )
        result = delimiter.join(list(statement_dict.values()))
        return get_pdf(result, {"orientation": doc.orientation})
    else:
        for supplier, statement_html in statement_dict.items():
            statement_dict[supplier] = get_pdf(
                statement_html, {"orientation": doc.orientation}
            )
        return statement_dict


def get_statement_dict(doc, get_statement_dict=False):
    statement_dict = {}
    ageing = ""

    for entry in doc.suppliers:
        if doc.include_ageing:
            ageing = set_ageing(doc, entry)

        tax_id = frappe.get_doc("Supplier", entry.supplier).tax_id
        presentation_currency = (
            get_party_account_currency("Supplier", entry.supplier, doc.company)
            or doc.currency
            or get_company_currency(doc.company)
        )

        filters = get_common_filters(doc)
        if doc.ignore_exchange_rate_revaluation_journals:
            filters.update({"ignore_err": True})

        # if doc.ignore_cr_dr_notes:
        #     filters.update({"ignore_cr_dr_notes": True})

        if doc.report == "General Ledger":
            filters.update(get_gl_filters(doc, entry, tax_id, presentation_currency))
            col, res = get_soa(filters)
            for x in [0, -2, -1]:
                res[x]["account"] = res[x]["account"].replace("'", "")
            if len(res) == 3:
                continue
        else:
            filters.update(get_ar_filters(doc, entry))
            ar_res = get_ar_soa(filters)
            col, res = ar_res[0], ar_res[1]
            if not res:
                continue

        statement_dict[entry.supplier] = (
            [res, ageing]
            if get_statement_dict
            else get_html(doc, filters, entry, col, res, ageing)
        )

    return statement_dict


def set_ageing(doc, entry):
    ageing_filters = frappe._dict(
        {
            "company": doc.company,
            "report_date": doc.posting_date,
            "ageing_based_on": doc.ageing_based_on,
            "range1": 30,
            "range2": 60,
            "range3": 90,
            "range4": 120,
            "party_type": "Supplier",
            "party": [entry.supplier],
        }
    )
    col1, ageing = get_ageing(ageing_filters)

    if ageing:
        ageing[0]["ageing_based_on"] = doc.ageing_based_on

    return ageing


def get_common_filters(doc):
    return frappe._dict(
        {
            "company": doc.company,
            "finance_book": doc.finance_book if doc.finance_book else None,
            "account": [doc.account] if doc.account else None,
            "cost_center": [cc.cost_center_name for cc in doc.cost_center],
            "show_remarks": doc.show_remarks,
        }
    )


def get_gl_filters(doc, entry, tax_id, presentation_currency):
    return {
        "from_date": doc.from_date,
        "to_date": doc.to_date,
        "party_type": "Supplier",
        "party": [entry.supplier],
        "party_name": [entry.supplier_name] if entry.supplier_name else None,
        "presentation_currency": presentation_currency,
        "group_by": doc.group_by,
        "currency": doc.currency,
        "project": [p.project_name for p in doc.project],
        "show_opening_entries": 0,
        "include_default_book_entries": 0,
        "tax_id": tax_id if tax_id else None,
        "show_net_values_in_party_account": doc.show_net_values_in_party_account,
    }


def get_ar_filters(doc, entry):
    return {
        "report_date": doc.posting_date if doc.posting_date else None,
        "party_type": "Supplier",
        "party": [entry.supplier],
        "supplier_name": entry.supplier_name if entry.supplier_name else None,
        "payment_terms_template": (
            doc.payment_terms_template if doc.payment_terms_template else None
        ),
        "based_on_payment_terms": doc.based_on_payment_terms,
        "report_name": "Accounts Payable",
        "ageing_based_on": doc.ageing_based_on,
        "range1": 30,
        "range2": 60,
        "range3": 90,
        "range4": 120,
    }


# def get_html(doc, filters, entry, col, res, ageing):
#     base_template_path = "frappe/www/printview.html"
#     template_path = (
#         "nl_banadir/templates/process_statement_of_accounts_suppliers.html"
#         if doc.report == "General Ledger"
#         else "nl_banadir/templates/process_statement_of_accounts_accounts_payable.html"
#     )

#     if doc.letter_head:
#         letter_head = get_letter_head(doc, 0)

#     html = frappe.render_template(
#         template_path,
#         {
#             "filters": filters,
#             "data": res,
#             "report": {"report_name": doc.report, "columns": col},
#             "ageing": ageing[0] if (doc.include_ageing and ageing) else None,
#             "letter_head": letter_head if doc.letter_head else None,
#             "terms_and_conditions": (
#                 frappe.db.get_value(
#                     "Terms and Conditions", doc.terms_and_conditions, "terms"
#                 )
#                 if doc.terms_and_conditions
#                 else None
#             ),
#         },
#     )

#     html = frappe.render_template(
#         base_template_path,
#         {
#             "body": html,
#             "css": get_print_style(),
#             "title": "Statement For " + entry.supplier,
#         },
#     )
#     return html


def get_suppliers_based_on_supplier_group(supplier_collection, collection_name):
    fields_dict = {
        "Supplier Group": "supplier_group",
    }
    collection = frappe.get_doc(supplier_collection, collection_name)
    selected = [
        supplier.name
        for supplier in frappe.get_list(
            supplier_collection,
            filters=[["lft", ">=", collection.lft], ["rgt", "<=", collection.rgt]],
            fields=["name"],
            order_by="lft asc, rgt desc",
        )
    ]
    return frappe.get_list(
        "Supplier",
        fields=["name", "supplier_name", "email_id"],
        filters=[
            ["disabled", "=", 0],
            [fields_dict[supplier_collection], "IN", selected],
        ],
    )


def get_recipients_and_cc(supplier, doc):
    recipients = []
    for clist in doc.suppliers:
        if clist.supplier == supplier:
            if clist.billing_email:
                for email in clist.billing_email.split(","):
                    recipients.append(email.strip())
            if doc.primary_mandatory and clist.primary_email:
                for email in clist.primary_email.split(","):
                    recipients.append(email.strip())
    cc = []
    if doc.cc_to != "":
        try:
            cc = [frappe.get_value("User", user.cc, "email") for user in doc.cc_to]
        except Exception:
            pass

    return recipients, cc


def get_context(supplier, doc):
    template_doc = copy.deepcopy(doc)
    del template_doc.suppliers
    template_doc.from_date = format_date(template_doc.from_date)
    template_doc.to_date = format_date(template_doc.to_date)
    return {
        "doc": template_doc,
        "supplier": frappe.get_doc("Supplier", supplier),
        "frappe": frappe.utils,
    }


@frappe.whitelist()
def fetch_suppliers(supplier_collection, collection_name, primary_mandatory):
    supplier_list = []
    suppliers = []

    suppliers = get_suppliers_based_on_supplier_group(
        supplier_collection, collection_name
    )

    for supplier in suppliers:
        primary_email = supplier.get("email_id") or ""
        billing_email = get_supplier_emails(supplier.name, 1, billing_and_primary=False)

        if int(primary_mandatory):
            if primary_email == "":
                continue

        supplier_list.append(
            {
                "name": supplier.name,
                "supplier_name": supplier.supplier_name,
                "primary_email": primary_email,
                "billing_email": billing_email,
            }
        )
    return supplier_list


@frappe.whitelist()
def get_supplier_emails(supplier_name, primary_mandatory, billing_and_primary=True):
    """Returns first email from Contact Email table as a Billing email
    when Is Billing Contact checked
    and Primary email- email with Is Primary checked"""

    billing_email = frappe.db.sql(
        """
		SELECT
			email.email_id
		FROM
			`tabContact Email` AS email
		JOIN
			`tabDynamic Link` AS link
		ON
			email.parent=link.parent
		JOIN
			`tabContact` AS contact
		ON
			contact.name=link.parent
		WHERE
			link.link_doctype='Supplier'
			and link.link_name=%s
			and contact.is_billing_contact=1
			{mcond}
		ORDER BY
			contact.creation desc
		""".format(mcond=get_match_cond("Contact")),
        supplier_name,
    )

    if len(billing_email) == 0 or (billing_email[0][0] is None):
        if billing_and_primary:
            frappe.throw(
                _("No billing email found for supplier: {0}").format(supplier_name)
            )
        else:
            return ""

    if billing_and_primary:
        primary_email = frappe.get_value("Supplier", supplier_name, "email_id")
        if primary_email is None and int(primary_mandatory):
            frappe.throw(
                _("No primary email found for supplier: {0}").format(supplier_name)
            )
        return [primary_email or "", billing_email[0][0]]
    else:
        return billing_email[0][0] or ""


@frappe.whitelist()
def download_statements(document_name):
    try:
        doc = frappe.get_doc("Suppliers Process Statement Of Accounts", document_name)

        report = get_report_pdf(doc)

        if report:
            frappe.local.response.filename = doc.name + ".pdf"
            frappe.local.response.filecontent = report
            frappe.local.response.type = "download"
        else:
            frappe.throw("No report generated")
    except Exception as e:
        frappe.logger().error(f"Error in download_statements: {str(e)}")
        frappe.throw("Failed to generate statement. Please check logs.")


@frappe.whitelist()
def send_emails(document_name, from_scheduler=False, posting_date=None):
    doc = frappe.get_doc("Suppliers Process Statement Of Accounts", document_name)
    report = get_report_pdf(doc, consolidated=False)

    if report:
        for supplier, report_pdf in report.items():
            context = get_context(supplier, doc)
            filename = frappe.render_template(doc.pdf_name, context)
            attachments = [{"fname": filename + ".pdf", "fcontent": report_pdf}]

            recipients, cc = get_recipients_and_cc(supplier, doc)
            if not recipients:
                continue

            subject = frappe.render_template(doc.subject, context)
            message = frappe.render_template(doc.body, context)

            if doc.sender:
                sender_email = frappe.db.get_value(
                    "Email Account", doc.sender, "email_id"
                )
            else:
                sender_email = frappe.session.user

            frappe.enqueue(
                queue="short",
                method=frappe.sendmail,
                recipients=recipients,
                sender=sender_email,
                cc=cc,
                subject=subject,
                message=message,
                now=True,
                reference_doctype="Suppliers Process Statement Of Accounts",
                reference_name=document_name,
                attachments=attachments,
                expose_recipients="header",
            )

        if doc.enable_auto_email and from_scheduler:
            new_to_date = getdate(posting_date or today())
            if doc.frequency == "Weekly":
                new_to_date = add_days(new_to_date, 7)
            else:
                new_to_date = add_months(
                    new_to_date, 1 if doc.frequency == "Monthly" else 3
                )
            new_from_date = add_months(new_to_date, -1 * doc.filter_duration)
            doc.add_comment(
                "Comment",
                "Emails sent on: " + frappe.utils.format_datetime(frappe.utils.now()),
            )
            if doc.report == "General Ledger":
                doc.db_set("to_date", new_to_date, commit=True)
                doc.db_set("from_date", new_from_date, commit=True)
            else:
                doc.db_set("posting_date", new_to_date, commit=True)
        return True
    else:
        return False


@frappe.whitelist()
def send_auto_email():
    selected = frappe.get_list(
        "Suppliers Process Statement Of Accounts",
        filters={"enable_auto_email": 1},
        or_filters={
            "to_date": format_date(today()),
            "posting_date": format_date(today()),
        },
    )
    for entry in selected:
        send_emails(entry.name, from_scheduler=True)
    return True
