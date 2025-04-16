# Server script to synchronize custom_seq_id and continue from the last sequence in Production Plan Item
# Trigger: `on_save` of the Production Plan doctype
import frappe
from frappe.model.naming import make_autoname
from datetime import datetime
from frappe import _

def sync_sequence(doc, method):
    """
    Synchronize custom_seq_id between po_items and sub_assembly_items,
    ensuring sequence continues from the last value in Production Plan Item.
    """
    last_seq_id = frappe.db.sql("""
        SELECT MAX(custom_seq_id) 
        FROM `tabProduction Plan Item`
    """)[0][0] or 0  

    current_seq_id = last_seq_id + 1
    
    if len(doc.po_items) != len(doc.sub_assembly_items):
        frappe.throw(f"The number of items in <span style='color:red';>'Assembly Items'</span> and <span style='color:red';>'Sub Assembly Items'</span> must be equal(<b>{len(doc.po_items)}</b>)")

    for idx in range(len(doc.po_items)):
        doc.po_items[idx].custom_seq_id = current_seq_id
        doc.sub_assembly_items[idx].custom_seq_id = current_seq_id
        frappe.db.set_value("Production Plan Item", doc.po_items[idx].name, "custom_seq_id", current_seq_id)
        frappe.db.set_value("Production Plan Sub Assembly Item", doc.sub_assembly_items[idx].name, "custom_seq_id", current_seq_id)

        current_seq_id += 1
        
def auto_name(doc, method=None):
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if not company_abbr:
        frappe.throw(f"Company abbreviation not found for {doc.company}")

    current_year = datetime.now().year

    if doc.doctype == "Production Plan":
        base_name = make_autoname(f"PP-{company_abbr}-.####")
        doc.name = f"{base_name}-{current_year}"
    elif doc.doctype == "Work Order":
        base_name = make_autoname(f"WO-{company_abbr}-.#####")
        doc.name = f"{base_name}-{current_year}"
    else:
        frappe.throw(f"Unsupported doctype: {doc.doctype}")
        
    if doc.doctype=="Work Order":
        if doc.production_plan_item:
            doc.custom_seq_id = get_seq_id(doc.production_plan_item, "Production Plan Item")
        elif doc.production_plan_sub_assembly_item:
            doc.custom_seq_id = get_seq_id(doc.production_plan_sub_assembly_item, "Production Plan Sub Assembly Item")

def get_seq_id(_item, doc):
    """
    Get the sequence ID for the given Production Plan Item.
    """
    seq_id = frappe.db.get_value(
        doc,
        _item,
        "custom_seq_id"
    )
    return seq_id


def before_save(doc, method):
    if doc.is_new():
        validate_finished_insole(doc)
    
def validate_finished_insole(doc):
    if not hasattr(doc, 'po_items') or not hasattr(doc, 'sub_assembly_items'):
        frappe.throw("Both child tables (Production Plan Item and Sub Assembly Item) must exist")
    
    if len(doc.po_items) != len(doc.sub_assembly_items):
        frappe.throw(f"The number of items in <span style='color:red';>'Finished Goods Items'</span> and <span style='color:red';>'Sub Assembly Items'</span> must be equal (<b>{len(doc.po_items)}</b>)")

def split_sub_assembly(production_plan):
    """Split sub-assembly items based on custom_split_no"""
    plan_doc = frappe.get_doc("Production Plan", production_plan)
       
    # Process splitting
    items_to_split = get_items_to_split(plan_doc.sub_assembly_items)
    new_items = []
    
    for item in items_to_split:
        split_no = item.custom_split_no or 1
        split_result = calculate_split_quantities(item.qty, split_no)

        new_items.extend(create_split_items(item, split_result))
    
    # Update document
    remove_items_and_add_new(plan_doc, 'sub_assembly_items', items_to_split, new_items)
    reset_indices(plan_doc.po_items)
    plan_doc.save()
    plan_doc.reload()
    return plan_doc


def split_production_items(production_plan):
    """Split production items (po_items) based on custom_split_no"""
    plan_doc = frappe.get_doc("Production Plan", production_plan)
    items_to_split = get_items_to_split(plan_doc.po_items)
    new_items = []
    
    for item in items_to_split:
        split_no = item.custom_split_no or 1
        split_result = calculate_split_quantities(item.planned_qty, split_no)
        new_items.extend(create_production_split_items(item, split_result))
    
    remove_items_and_add_new(plan_doc, 'po_items', items_to_split, new_items)
    
    # Explicitly reset indices to ensure proper numbering
    reset_indices(plan_doc.po_items)
    
    plan_doc.save()
    plan_doc.reload()
    return plan_doc

def reset_indices(items):
    """Reset idx values for all items to ensure sequential numbering"""
    for i, item in enumerate(items, 1):
        item.idx = i
        
def get_initial_seq_id(doctype, fieldname):
    """Get the maximum existing seq_id + 1"""
    existing = frappe.get_all(doctype, fields=[fieldname])
    return max([x.get(fieldname) or 0 for x in existing], default=0) + 1

def get_items_to_split(items):
    """Filter items that need splitting (split_no > 1 and has quantity)"""
    return [item for item in items 
            if (item.custom_split_no or 1) > 1 
            and (item.get('qty') or item.get('planned_qty'))]

def calculate_split_quantities(total_qty, split_no):
    """Calculate split quantities and remainder"""
    split_qty = total_qty // split_no
    remainder = total_qty % split_no
    return {'split_qty': split_qty, 'remainder': remainder, 'split_no': split_no}

def create_split_items(original_item, split_result, seq_id=None):
    """Create new sub-assembly items after splitting"""
    new_items = []
    split_no = split_result['split_no']
    
    for i in range(split_no):
        qty = split_result['split_qty']
        if i == split_no - 1:
            qty += split_result['remainder']
            
        new_item = {
            **{field: original_item.get(field) for field in [
                'production_item', 'item_name', 'target_warehouse', 
                'finished_good', 'bom_no', 'uom', 'stock_uom'
            ]},
            'qty': qty,
            'custom_split_no': 1,
            'custom_seq_id': seq_id
        }
        new_items.append(new_item)
    
    return new_items

def create_production_split_items(original_item, split_result):
    """Create new production items after splitting"""
    new_items = []
    split_no = split_result['split_no']
    
    for i in range(split_no):
        qty = split_result['split_qty']
        if i == split_no - 1:
            qty += split_result['remainder']
            
        new_item = {
            **{field: original_item.get(field) for field in [
                'item_code', 'bom_no', 'stock_uom', 
                'planned_start_date'
            ]},
            'planned_qty': qty,
            'pending_qty': qty,
            'custom_split_no': 1
        }
        new_items.append(new_item)
    
    return new_items

def remove_items_and_add_new(doc, child_table, items_to_remove, new_items):
    """Remove original items and add new split items"""
    for item in items_to_remove:
        doc.get(child_table).remove(item)
    
    for item in new_items:
        doc.append(child_table, item)

@frappe.whitelist()
def split_po_items():
    production_plan = frappe.form_dict.get("production_plan")
    try:
        doc = split_production_items(production_plan)
        return {"success": True, "message": _("Production items split successfully"), "docname": doc.name}
    except Exception as e:
        frappe.log_error(_("Error splitting production items"), str(e))
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def split_prod_assembly():
    production_plan = frappe.form_dict.get("production_plan")
    try:
        doc = split_sub_assembly(production_plan)
        return {"success": True, "message": _("Sub-assembly items split successfully"), "docname": doc.name}
    except Exception as e:
        frappe.log_error(_("Error splitting sub-assembly items"), str(e))
        return {"success": False, "message": str(e)}