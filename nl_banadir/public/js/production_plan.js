frappe.ui.form.on('Production Plan Item', {
    custom_split_no: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let idx = row.idx - 1; // idx is 1-based, convert to 0-based

        // Check if sub_assembly_items exists and has the same index
        if (frm.doc.sub_assembly_items && frm.doc.sub_assembly_items[idx]) {
            frappe.model.set_value(
                'Production Plan Sub Assembly Item',
                frm.doc.sub_assembly_items[idx].name,
                'custom_split_no',
                row.custom_split_no
            );
        }
    }
});

frappe.ui.form.on('Production Plan', {
    refresh: function(frm) {
            // Add a custom button to split items
            frm.add_custom_button(__('Split Items'), function() {
                // Ensure there's at least one item with a split number greater than 1
                let has_split = frm.doc.po_items.some(item => item.custom_split_no > 1);

                if (has_split) {
                    frappe.call({
                        method: "nl_banadir.banadir_customization_reports.controllers.production_plan.split_po_items",
                        args: {
                            production_plan: frm.doc.name
                        },
                        callback: function(r) {
                            if (r.message) {
                                frm.refresh();  // Refresh the form to show updated items
                            }
                        }
                    });
                } else {
                    frappe.msgprint(__('No items with a split number greater than 1.'));
                }
            });
        
    },
    custom_split_subassembly_item: function(frm){
        let has_subassembly_split = frm.doc.sub_assembly_items.some(item => item.custom_split_no > 1);
            
            if (has_subassembly_split) {
                frappe.call({
                    method: "nl_banadir.banadir_customization_reports.controllers.production_plan.split_prod_assembly",
                    args: {
                        production_plan: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frm.refresh();  
                        }
                    }
                });
            } else {
                frappe.msgprint(__('No sub-assembly items with a split number greater than 1.'));
            }
        
    }
});
