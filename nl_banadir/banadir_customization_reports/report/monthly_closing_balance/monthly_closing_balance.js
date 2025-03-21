// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Closing Balance"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "from_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1]
		},
		{
			"fieldname": "to_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "periodicity",
			"label": __("Periodicity"),
			"fieldtype": "Select",
			"options": ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
			"default": "Monthly",
			"reqd": 1
		}
	]
};
