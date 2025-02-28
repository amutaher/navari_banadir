import frappe
company_name = "CITYWALK FOOTWEAR PVT LTD"
start_date = "03-07-2024"
end_date = "04-07-2024"
finance_year_value = "2024"

# Fetch and update GL Entries
gl_entries = frappe.get_all(
    "GL Entry",
    filters={
        "company": company_name,
        "posting_date": ["between", [start_date, end_date]]
    },
    fields=["name"]
)

for gl in gl_entries:
    gl_entry = frappe.get_doc("GL Entry", gl["name"])  
    gl_entry.flags.ignore_permissions = True  
    gl_entry.finance_year = finance_year_value
    gl_entry.save()
    print(f"✅ Updated Finance Year in GL Entry: {gl['name']}")

print("✅ Finance Year updated for all matching GL Entries.")

#Ru the script on system console, choild table modification which will repost valuation
company_name = "CITYWALK FOOTWEAR PVT LTD"
start_date = "2024-01-01"
end_date = "2025-01-24"
finance_register_value = "2024" 

error_entries = [] 

journal_entries = frappe.get_all(
    "Journal Entry",
    filters={
        "company": company_name,
        "docstatus": 1,
        "posting_date": ["between", [start_date, end_date]]
    },
    fields=["name"]
)

for je in journal_entries:
    try:
        je_doc = frappe.get_doc("Journal Entry", je["name"])
        updated = False  

        for account in je_doc.accounts: 
            account.finance_year = finance_register_value 
            updated = True 

        if updated:
            je_doc.save() 
            frappe.db.commit()  
            print(f"✅ Updated Finance Register in Journal Entry: {je['name']}")

    except Exception as e:
        error_entries.append({"journal_entry": je["name"], "error": str(e)})
        print(f"❌ Error updating Journal Entry {je['name']}: {e}")

# Print all errors at the end
if error_entries:
    print("\n⚠️ The following Journal Entries had errors:")
    for error in error_entries:
        print(f"- {error['journal_entry']}: {error['error']}")
else:
    print("\n✅ All Journal Entries were updated successfully.")