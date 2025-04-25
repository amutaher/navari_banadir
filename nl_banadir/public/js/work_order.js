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
          "in_progress_date",
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

// For the Work Order main form
frappe.ui.form.on("Work Order", {
  refresh: function (frm) {
    // Initialize or refresh child table controls
    setup_subcontractor_controls(frm);
  },
  custom_subcontractors_add: function (frm, cdt, cdn) {
    // When a new row is added, set up its controls
    setup_subcontractor_row_controls(frm, cdt, cdn);
  },
});

// For the child table (Work Order Operations Item)
frappe.ui.form.on("Work Order Operations Item", {
  invoice_created: function (frm, cdt, cdn) {
    setup_subcontractor_row_controls(frm, cdt, cdn);
  },
  after_load: function (frm, cdt, cdn) {
    setup_subcontractor_row_controls(frm, cdt, cdn);
  },
});

// Common function to handle row controls
function setup_subcontractor_row_controls(frm, cdt, cdn) {
  const child_doc = locals[cdt][cdn];
  const row =
    frm.fields_dict["custom_subcontractors"].grid.grid_rows_by_docname[cdn];

  if (!row || !child_doc) return;

  const is_read_only = child_doc.invoice_created == 1;
  const fields = [
    "operations",
    "status",
    "qty_issued",
    "completed_qty",
    "in_progress_date",
    "completed_date",
    "supplier",
    "currency",
  ];

  fields.forEach((field) => {
    if (child_doc.hasOwnProperty(field)) {
      row.toggle_editable(field, is_read_only);
    }
  });
}

// Initialize all rows
function setup_subcontractor_controls(frm) {
  if (
    !frm.fields_dict["custom_subcontractors"] ||
    !frm.fields_dict["custom_subcontractors"].grid
  )
    return;

  Object.values(
    frm.fields_dict["custom_subcontractors"].grid.grid_rows_by_docname || {},
  ).forEach((row) => {
    if (row && row.doc) {
      setup_subcontractor_row_controls(frm, row.doc.doctype, row.doc.name);
    }
  });
}
