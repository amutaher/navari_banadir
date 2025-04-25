frappe.ui.form.on("Sales Invoice", {
  refresh(frm) {
    frm.set_query("commission_expense_account", function () {
      return {
        filters: {
          company: frm.doc.company,
          account_type: "Expense Account",
        },
      };
    });
  },
  commission_amount: function (frm) {
    if (frm.doc.commission_amount > 0) {
      const total_commission = frm.doc.total_qty * frm.doc.commission_amount;
      frm.set_value("total_commission", total_commission);
    }
  },
});
