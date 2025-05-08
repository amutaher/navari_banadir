// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Travel Expense"] = {
  filters: [
    {
      fieldname: "company",
      label: "Company",
      fieldtype: "Link",
      options: "Company",
      default: frappe.defaults.get_user_default("Company"),
      reqd: 1,
    },

    {
      fieldname: "company_group",
      label: "Company Group",
      fieldtype: "Link",
      options: "Company Group",
      reqd: 1,
    },
    {
      fieldname: "booked_by",
      label: "Booked By",
      fieldtype: "Link",
      options: "User",
    },
    {
      fieldname: "booking_date",
      label: "Date of Booking",
      fieldtype: "DateRange",
    },
    {
      fieldname: "travel_type",
      label: "Type of Travel",
      fieldtype: "Select",
      options: "\nOne Way\nReturn",
    },
    {
      fieldname: "traveller_name",
      label: "Traveller Name",
      fieldtype: "Link",
      options: "Traveller",
    },
  ],
};
