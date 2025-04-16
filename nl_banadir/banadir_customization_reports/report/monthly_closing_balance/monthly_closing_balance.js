// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Closing Balance"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
      default: frappe.defaults.get_user_default("Company"),
    },
    {
      fieldname: "fiscal_year",
      label: __("Fiscal Year"),
      fieldtype: "Link",
      options: "Fiscal Year",
      default: erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
      reqd: 1,
      on_change: function (query_report) {
        var fiscal_year = query_report.get_values().fiscal_year;
        if (!fiscal_year) {
          return;
        }
        frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
          var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
          frappe.query_report.set_filter_value({
            from_date: fy.year_start_date,
            to_date: fy.year_end_date,
          });
        });
      },
    },
    {
      fieldname: "from_date",
      label: __("Start Date"),
      fieldtype: "Date",
      reqd: 1,
      default: erpnext.utils.get_fiscal_year(
        frappe.datetime.get_today(),
        true,
      )[1],
    },
    {
      fieldname: "to_date",
      label: __("End Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "periodicity",
      label: __("Periodicity"),
      fieldtype: "Select",
      options: ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
      default: "Monthly",
      hidden: 1,
      reqd: 1,
    },
    {
      fieldname: "presentation_currency",
      label: __("Currency"),
      fieldtype: "Select",
      options: erpnext.get_presentation_currency_list(),
    },
    {
      fieldname: "with_period_closing_entry_for_opening",
      label: __("With Period Closing Entry For Opening Balances"),
      fieldtype: "Check",
      default: 1,
    },
    {
      fieldname: "with_period_closing_entry_for_current_period",
      label: __("Period Closing Entry For Current Period"),
      fieldtype: "Check",
      default: 1,
    },
    {
      fieldname: "show_zero_values",
      label: __("Show zero values"),
      fieldtype: "Check",
    },
    {
      fieldname: "show_unclosed_fy_pl_balances",
      label: __("Show unclosed fiscal year's P&L balances"),
      fieldtype: "Check",
    },
    {
      fieldname: "include_default_book_entries",
      label: __("Include Default FB Entries"),
      fieldtype: "Check",
      default: 1,
    },
    {
      fieldname: "show_net_values",
      label: __("Show net values in opening and closing columns"),
      fieldtype: "Check",
      default: 1,
    },
  ],
  formatter: erpnext.financial_statements.formatter,
  tree: true,
  name_field: "account",
  parent_field: "parent_account",
  initial_depth: 3,
};
