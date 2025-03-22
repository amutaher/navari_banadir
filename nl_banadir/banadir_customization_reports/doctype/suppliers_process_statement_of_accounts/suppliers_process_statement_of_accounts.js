// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Suppliers Process Statement Of Accounts", {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button(__("Send Emails"), function () {
        if (frm.is_dirty()) frappe.throw(__("Please save before proceeding."));
        frappe.call({
          method: "",
          args: {
            document_name: frm.doc.name,
          },
          callback: function (r) {
            if (r && r.message) {
              frappe.show_alert({
                message: __("Emails Queued"),
                indicator: "blue",
              });
            } else {
              frappe.msgprint(__("No Records for these settings."));
            }
          },
        });
      });
      frm.add_custom_button(__("Download"), function () {
        if (frm.is_dirty()) frappe.throw(__("Please save before proceeding."));
        let url = frappe.urllib.get_full_url(
          "/api/method/nl_banadir.banadir_customization_reports.doctype.suppliers_process_statement_of_accounts.suppliers_process_statement_of_accounts.download_statements?" +
            "document_name=" +
            encodeURIComponent(frm.doc.name)
        );
        $.ajax({
          url: url,
          type: "GET",
          success: function (result) {
            console.log("URL", url);
            if (jQuery.isEmptyObject(result)) {
              frappe.msgprint(__("No Records for these settings."));
            } else {
              window.location = url;
            }
          },
        });
      });
    }
  },

  onload: function (frm) {
    frm.set_query("currency", function () {
      return {
        filters: {
          enabled: 1,
        },
      };
    });
    frm.set_query("account", function () {
      return {
        filters: {
          company: frm.doc.company,
        },
      };
    });
    if (frm.doc.__islocal) {
      frm.set_value(
        "from_date",
        frappe.datetime.add_months(frappe.datetime.get_today(), -1)
      );
      frm.set_value("to_date", frappe.datetime.get_today());
    }
  },
  report: function (frm) {
    let filters = {
      company: frm.doc.company,
    };
    if (frm.doc.report == "Accounts Payable") {
      filters["account_type"] = "Payable";
    }
    frm.set_query("account", function () {
      return {
        filters: filters,
      };
    });
  },
  supplier_collection: function (frm) {
    frm.set_value("collection_name", "");
    if (frm.doc.supplier_collection) {
      frm.get_field("collection_name").set_label(frm.doc.supplier_collection);
    }
  },
  frequency: function (frm) {
    if (frm.doc.frequency != "") {
      frm.set_value("start_date", frappe.datetime.get_today());
    } else {
      frm.set_value("start_date", "");
    }
  },

  fetch_suppliers: function (frm) {
    if (frm.doc.collection_name) {
      frappe.call({
        method:
          "nl_banadir.banadir_customization_reports.doctype.suppliers_process_statement_of_accounts.suppliers_process_statement_of_accounts.fetch_suppliers",
        args: {
          supplier_collection: frm.doc.supplier_collection,
          collection_name: frm.doc.collection_name,
          primary_mandatory: frm.doc.primary_mandatory,
        },
        callback: function (r) {
          if (!r.exc) {
            if (r.message.length) {
              frm.clear_table("suppliers");
              for (const supplier of r.message) {
                var row = frm.add_child("suppliers");
                row.supplier = supplier.name;
                row.primary_email = supplier.primary_email;
                row.billing_email = supplier.billing_email;
              }
              frm.refresh_field("suppliers");
            } else {
              frappe.throw(__("No Suppliers found with selected options."));
            }
          }
        },
      });
    } else {
      frappe.throw("Enter " + frm.doc.supplier_collection + " name.");
    }
  },
});

frappe.ui.form.on("Process Statement Of Accounts Supplier", {
  supplier: function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (!row.supplier) {
      return;
    }
    frappe.call({
      method:
        "nl_banadir.banadir_customization_reports.doctype.suppliers_process_statement_of_accounts.suppliers_process_statement_of_accounts.get_supplier_emails",
      args: {
        supplier_name: row.supplier,
        primary_mandatory: frm.doc.primary_mandatory,
      },
      callback: function (r) {
        if (!r.exe) {
          if (r.message.length) {
            frappe.model.set_value(cdt, cdn, "primary_email", r.message[0]);
            frappe.model.set_value(cdt, cdn, "billing_email", r.message[1]);
          } else {
            return;
          }
        }
      },
    });
  },
});
