

frappe.ui.form.on('Journal Entry', {
    onload: function(frm) {
        update_child_table(frm);
    },

    custom_branch: function(frm) {
        update_child_table(frm);
    },

    custom_marka: function(frm) {
        update_child_table(frm);
    }
});

frappe.ui.form.on('Journal Entry Account', {
    accounts_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.branch = frm.doc.custom_branch || '';
        row.marka = frm.doc.custom_marka || '';
        frm.refresh_field("accounts");
    }
});

function update_child_table(frm) {
    if (frm.doc.accounts && frm.doc.accounts.length > 0) {
        frm.doc.accounts.forEach(row => {
            row.branch = frm.doc.custom_branch || '';
            row.marka = frm.doc.custom_marka || '';
        });
        frm.refresh_field("accounts");
    }
}
