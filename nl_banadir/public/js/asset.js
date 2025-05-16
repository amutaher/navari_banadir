frappe.ui.form.on("Asset", {
  custom_multi_currency: function (frm) {
    updateCompanyCurrencyAndExchangeRate(frm);
  },

  custom_transaction_currency: function (frm) {
    updateCompanyCurrencyAndExchangeRate(frm);
  },

  custom_company_currency: function (frm) {
    updateExchangeRate(frm);
  },

  custom_net_purchase_amounttransaction_currency: function (frm) {
    const exchange_rate = frm.doc.custom_transaction_exchange_rate;
    if (exchange_rate) {
      frm.doc.gross_purchase_amount =
        frm.doc.custom_net_purchase_amounttransaction_currency * exchange_rate;
      frm.refresh_fields("custom_net_purchase_amount");
    }
  },
});

// --- Helper Functions ---

function updateCompanyCurrencyAndExchangeRate(frm) {
  frappe.db.get_value("Company", frm.doc.company, "default_currency", (r) => {
    if (r && r.default_currency) {
      console.log("Default Currency: ", r.default_currency);
      frm.set_value("custom_company_currency", r.default_currency);
      frm.refresh_fields("custom_company_currency");
      updateExchangeRate(frm);
    } else {
      console.log("Default Currency not found");
    }
  });
}

function updateExchangeRate(frm) {
  const toCurrency = frm.doc.custom_company_currency;
  const fromCurrency = frm.doc.custom_transaction_currency;

  if (fromCurrency && toCurrency) {
    frappe.db.get_value(
      "Currency Exchange",
      {
        from_currency: fromCurrency,
        to_currency: toCurrency,
      },
      ["exchange_rate"],
      (response) => {
        frm.doc.custom_transaction_exchange_rate = response.exchange_rate;
        frm.refresh_fields("custom_transaction_exchange_rate");
      },
    );
  }
}
