// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Salary Slip Payment Status"] = {
  filters: [
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
    },
    {
      fieldname: "branch",
      label: "Branch",
      fieldtype: "Link",
      options: "Branch",
    },
    {
      fieldname: "employee",
      label: "Employee",
      fieldtype: "Link",
      options: "Employee",
    },
    {
      fieldname: "status",
      label: "Payment Status",
      fieldtype: "Select",
      options: ["", "Paid", "Unpaid"],
    },
    {
      fieldname: "from_date",
      label: "From Date",
      fieldtype: "Date",
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
    },
    {
      fieldname: "to_date",
      label: "To Date",
      fieldtype: "Date",
      default: frappe.datetime.get_today(),
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (column.fieldname === "payment_status") {
      if (value === "Paid") {
        value = `<span style="color: green; font-weight: bold;">${value}</span>`;
      } else if (value === "Unpaid") {
        value = `<span style="color: red; font-weight: bold;">${value}</span>`;
      }
    }

    return value;
  },
};
