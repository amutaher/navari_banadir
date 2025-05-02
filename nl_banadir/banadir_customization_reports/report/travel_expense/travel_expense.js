// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Travel Expense"] = {
  filters: [
    {
      fieldname: "company_group",
      label: "Company Group",
      fieldtype: "Link",
      options: "Company Group",
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
      fieldname: "type_of_travel",
      label: "Type of Travel",
      fieldtype: "Select",
      options: "\nLocal\nInternational",
    },
    {
      fieldname: "traveller_name",
      label: "Traveller Name",
      fieldtype: "Link",
      options: "User",
    },
  ],
};
