frappe.ui.form.on("Work Order", {
  refresh: function (frm) {
    if (frm.doc.docstatus === 1) {
      setTimeout(() => {
        frappe.call({
          method:
            "nl_banadir.banadir_customization_reports.utils.utils.check_work_order_ops",
          args: {
            work_order: frm.doc.name,
          },
          callback: function (r) {
            if (r.message && !r.message.all_completed) {
              frm.remove_custom_button("Finish");
              frm.remove_custom_button("Material Consumption");
            }
          },
        });
      }, 10);
    }

    editable(frm);

    if (frm.doc.custom_subcontractors) {
      frm.doc.custom_subcontractors.forEach((row) => {
        const fields_to_update = [
          "status",
          "item",
          "rate",
          "supplier",
          "in_progress",
          "completed_date",
        ];
        if (row.invoice_created == 1) {
          fields_to_update.forEach((field) => {
            frappe.meta.get_docfield(
              "Work Order Operations Item",
              field,
              frm.doc.name,
            ).read_only = 1;
            frappe.meta.get_docfield(
              "Work Order Operations Item",
              field,
              frm.doc.name,
            ).allow_on_submit = 0;
          });
        } else {
          fields_to_update.forEach((field) => {
            frappe.meta.get_docfield(
              "Work Order Operations Item",
              field,
              frm.doc.name,
            ).read_only = 0;
            frappe.meta.get_docfield(
              "Work Order Operations Item",
              field,
              frm.doc.name,
            ).allow_on_submit = 1;
          });
        }
      });
      frm.refresh_field("custom_subcontractors");
    }
  },
});

frappe.ui.form.on("Work Order Operations Item", {
  operations: function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    if (frm.doc.company) {
      frappe.db.get_value(
        "Company",
        frm.doc.company,
        "default_currency",
        (r) => {
          if (r && r.default_currency) {
            frappe.model.set_value(cdt, cdn, "currency", r.default_currency);
          }
        },
      );
    } else {
      frappe.msgprint(__("Please select a company in the Work Order."));
    }
  },
  in_progress_date: function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (
      row.in_progress_date &&
      row.in_progress_date != null &&
      row.completed_date == null
    ) {
      frappe.model.set_value(cdt, cdn, "status", "In Progress");
    }
  },
  completed_date: function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.completed_date && row.completed_date != null) {
      frappe.model.set_value(cdt, cdn, "status", "Completed");
    }
  },
  completed_qty: function (frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    if (row.qty_issued == 0.0) {
      frappe.throw(
        "Please issue the material before completing the operation.",
      );
      frappe.model.set_value(cdt, cdn, "completed_qty", 0);
      return; // stops further execution
    }

    frm.refresh_field("custom_subcontractors");
  },
});

function editable(frm) {
  const is_submitted = frm.doc.docstatus === 1;
  frm.set_df_property("custom_subcontractors", "read_only", !is_submitted);

  frm.set_df_property("custom_subcontractors", "hidden", !is_submitted);
}
