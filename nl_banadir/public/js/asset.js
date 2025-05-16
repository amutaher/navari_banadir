frappe.ui.form.on("Asset", {
  custom_multi_currency: function (frm) {
    frappe.db.get_value("Company", frm.doc.company, "default_currency", (r) => {
      if (r && r.default_currency) {
        console.log("Default Currency: ", r.default_currency);
        // You can use r.default_currency to set a field or for other logic
        frm.set_value("custom_company_currency", r.default_currency);
        frm.refresh_fields("custom_company_currency");
      } else {
        console.log("Default Currency not found");
      }
    });
    const toCurrency = frm.doc.custom_company_currency;

    if (toCurrency) {
      frappe.db.get_value(
        "Currency Exchange",
        {
          from_currency: frm.doc.custom_transaction_currency,
          to_currency: toCurrency,
        },
        ["exchange_rate"],
        (response) => {
          frm.doc.custom_transaction_exchange_rate = response.exchange_rate;
          frm.refresh_fields("custom_transaction_exchange_rate");
        },
      );
    }
  },
  custom_company_currency: function (frm) {
    const toCurrency = frm.doc.custom_company_currency;

    if (toCurrency) {
      frappe.db.get_value(
        "Currency Exchange",
        {
          from_currency: frm.doc.custom_transaction_currency,
          to_currency: toCurrency,
        },
        ["exchange_rate"],
        (response) => {
          frm.doc.custom_transaction_exchange_rate = response.exchange_rate;
          frm.refresh_fields("custom_transaction_exchange_rate");
        },
      );
    }
  },

  custom_net_purchase_amounttransaction_currency: function (frm) {
    exchange_rate = frm.doc.custom_transaction_exchange_rate;
    if (exchange_rate) {
      frm.doc.gross_purchase_amount =
        frm.doc.custom_net_purchase_amounttransaction_currency * exchange_rate;
      frm.refresh_fields("custom_net_purchase_amount");
    }
  },
});
