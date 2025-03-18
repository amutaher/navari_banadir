// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Profit and Loss Statement"] = erpnext.financial_statements;

erpnext.utils.add_dimensions("Custom Profit and Loss Statement", 10);

frappe.query_reports["Custom Profit and Loss Statement"]["filters"].push({
	fieldname: "selected_view",
	label: __("Select View"),
	fieldtype: "Select",
	options: [
		{ value: "Report", label: __("Report View") },
		{ value: "Growth", label: __("Growth View") },
		{ value: "Margin", label: __("Margin View") },
	],
	default: "Report",
	reqd: 1,
});


frappe.query_reports["Custom Profit and Loss Statement"]["filters"].push({
	fieldname: "finance_year",
	label: __("Finance Year"),
	fieldtype: "Link",
	options: "Finance Year",
	on_change: function (filters) {
		update_period_dates(filters);
	}

});

frappe.query_reports["Custom Profit and Loss Statement"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Custom Profit and Loss Statement"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
});
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
                fields: ["period_start_date", "period_end_date"]
            },
            callback: function (response) {
                if (response.message && response.message.length > 0) {
                    let dates = response.message;

                    let from_date = dates.reduce((min, record) => 
                        record.period_start_date < min ? record.period_start_date : min, dates[0].period_start_date);

                    let to_date = dates.reduce((max, record) => 
                        record.period_end_date > max ? record.period_end_date : max, dates[0].period_end_date);

                    frappe.query_report.set_filter_value("filter_based_on", "Date Range");
                    frappe.query_report.set_filter_value("period_start_date", from_date);
                    frappe.query_report.set_filter_value("period_end_date", to_date);
                } else {
                    // If no Period Closing Voucher is found, get the last period_end_date of the company
                    frappe.call({
                        method: "frappe.client.get_list",
                        args: {
                            doctype: "Period Closing Voucher",
                            filters: {
                                company: company
                            },
                            fields: ["period_end_date"],
                            order_by: "period_end_date desc",
                            limit: 1
                        },
                        callback: function (response) {
                            let last_period_end_date = response.message && response.message.length > 0 ? 
                                response.message[0].period_end_date : null;

                            let period_start_date = last_period_end_date ? 
                                frappe.datetime.add_days(last_period_end_date, 1) : frappe.datetime.get_today();

                            let period_end_date = frappe.datetime.get_today();

                            frappe.query_report.set_filter_value("filter_based_on", "Date Range");
                            frappe.query_report.set_filter_value("period_start_date", period_start_date);
                            frappe.query_report.set_filter_value("period_end_date", period_end_date);
                        }
                    });
                }
            }
        });
    }
}

