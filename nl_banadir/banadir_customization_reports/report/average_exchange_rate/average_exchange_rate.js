// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Average Exchange Rate"] = {
  filters: [
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
      reqd: 1,
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
      reqd: 1,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (data && data.is_total) {
      value = `<b>${value}</b>`;
    }
    return value;
  },
};
