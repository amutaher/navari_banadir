// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Custom P & L Statement"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "periodicity",
            label: __("Periodicity"),
            fieldtype: "Select",
            options: ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
            default: "Monthly",
            reqd: 1
        },
        {
            fieldname: "presentation_currency",
            label: __("Currency"),
            fieldtype: "Select",
            options: erpnext.get_presentation_currency_list(),
        },
        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "finance_year",
            label: __("Finance Year"),
            fieldtype: "Link",
            options: "Finance Year",
            on_change: function (filters) {
                update_period_dates(filters);
            }
        },
        {
            fieldname: "fiscal_year",
            label: __("Fiscal Year"),
            fieldtype: "Link",
            options: "Fiscal Year"
        }
    ]
};

// Function to update from_date and to_date based on finance_year and company
function update_period_dates(filters) {
    let finance_year = frappe.query_report.get_filter_value("finance_year");
    let company = frappe.query_report.get_filter_value("company");
    if (finance_year && company) {
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Period Closing Voucher",
                filters: {
                    custom_finance_year: finance_year,
                    company: company
                },
                fields: ["period_start_date", "period_end_date"],
                limit_page_length: 1
            },
            callback: function (response) {
                if (response.message && response.message.length > 0) {
                    let record = response.message[0];
                    frappe.query_report.set_filter_value("from_date", record.period_start_date);
                    frappe.query_report.set_filter_value("to_date", record.period_end_date);
                } else {
                    frappe.msgprint({
                        title: __("Not Found"),
                        message: __("No Period Closing Voucher found for the selected Finance Year and Company."),
                        indicator: "red"
                    });
                    frappe.query_report.set_filter_value("from_date", "");
                    frappe.query_report.set_filter_value("to_date", "");
                }
            }
            
        });
    }
}
