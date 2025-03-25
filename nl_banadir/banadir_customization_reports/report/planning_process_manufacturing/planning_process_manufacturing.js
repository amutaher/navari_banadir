// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Planning Process Manufacturing"] = {
    "filters": [
        {
            label: __("Company"),
            fieldname: "company",
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd:1,
        },
        {
            label: __("Production Plan"),
            fieldname: "production_plan",
            fieldtype: "Link",
            options: "Production Plan",
        },
        {
            label: __("Sales Order"),
            fieldname: "sales_order",
            fieldtype: "Link",
            options: "Sales Order",
        },
        {
            label: __("Item Name (Finished Goods)"),
            fieldname: "finished_goods_item",
            fieldtype: "Link",
            options: "Item",
        },
        {
            label: __("Item Name (Insole)"),
            fieldname: "insole_item",
            fieldtype: "Link",
            options: "Item",
        },
        {
            label: __("Status"),
            fieldname: "status",
            fieldtype: "Select",
            options: "\nDraft\nSubmitted\nCancelled\nCompleted",
        },
        {
            label: __("From Date"),
            fieldname: "from_date",
            fieldtype: "Date",
        },
        {
            label: __("To Date"),
            fieldname: "to_date",
            fieldtype: "Date",
        },
        {
            label: __("Remove Precision"),
            fieldname: "remove_precision",
            fieldtype: "Check",
            default: 1,
        }
    ],
    
  "formatter": function(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    
    const numericFields = [
        "order_pairs", "qty_issued", "cutting_pairs", "balance_to_cut",
        "qty_issued_printing", "printed_embossed_pairs", "balance_to_print_emboss",
        "insole_stock_qty", "quantity_issued", "received_quantity", "balance_quantity",
        "upper_stock", "qty_issued_machine", "fresh_qty_issued", "b_qty_issued",
        "rejected_qty_issued", "balance_to_issue"
    ];
    
    if (numericFields.includes(column.id) && value) {
        let numericString = value;
        
        if (typeof value === 'string' && value.includes('<')) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = value;
            numericString = tempDiv.textContent || tempDiv.innerText || '';
        }
        
        numericString = numericString.toString().replace(/[^0-9.-]/g, '');
        
        const numValue = parseFloat(numericString);
        
        if (!isNaN(numValue)) {
            const removePrecision = frappe.query_report && 
                                 frappe.query_report.get_filter_value && 
                                 frappe.query_report.get_filter_value("remove_precision");
            
            const formattedValue = numValue.toLocaleString('en-US', {
                maximumFractionDigits: removePrecision ? 0 : 2,
                minimumFractionDigits: removePrecision ? 0 : 2
            });
            
            return `<div style='text-align: right'>${formattedValue}</div>`;
        }
    }
    
    return value;
}
}