import frappe
from frappe import _

@frappe.whitelist()
def create_quotation_custom(customer_name: str, items, plate: str, project_name: str, **kwargs):
    """
    Robust wrapper for creating Sales Quotations.
    Ensures quotation_to and party_name are set correctly for ERPNext.
    
    Args:
        customer_name: Name of the Customer
        items: List of quotation items (or a string to be parsed)
    """
    try:
        # Debugging: log the incoming request
        frappe.logger().info(f"[ERPNext Tools] Creating quotation for: {customer_name}")
        
        # Robust items handling
        if isinstance(items, str):
            try:
                import json
                items = json.loads(items)
            except:
                # If it's just a string like "3 units of DIAREP0001"
                # This is a fallback to prevent crash, though parsing might be imperfect
                import re
                qty_match = re.search(r'(\d+)', items)
                qty = qty_match.group(1) if qty_match else 1
                
                # Try to find something that looks like an item code (uppercase/numbers)
                code_match = re.search(r'([A-Z0-9_-]{3,})', items)
                code = code_match.group(1) if code_match else items
                
                items = [{"item_code": code, "qty": float(qty)}]
        
        if not isinstance(items, list):
            items = [items] if items else []

        # Ensure each item is a dict and has mandatory qty
        formatted_items = []
        for item in items:
            if isinstance(item, str):
                frappe.throw(_("Quantity (qty) is mandatory for item {0}").format(item))
            elif isinstance(item, dict):
                if not item.get("qty"):
                    frappe.throw(_("Quantity (qty) is mandatory for item {0}").format(item.get("item_code", "unknown")))
                formatted_items.append(item)
        
        # Enforce ERPNext logic
        doc_data = {
            "doctype": "Quotation",
            "quotation_to": "Customer",
            "party_name": customer_name,
            "plate": plate,
            "project_name": project_name,
            "items": formatted_items
        }
        
        # Optional: pull in other kwargs if they exist and are valid fields
        meta = frappe.get_meta("Quotation")
        for key, value in kwargs.items():
            if meta.has_field(key) and key not in ["quotation_to", "party_name", "items", "doctype", "plate", "project_name"]:
                doc_data[key] = value
        
        doc = frappe.get_doc(doc_data)
        doc.insert()
        
        # Return structured result
        return {
            "success": True,
            "name": doc.name,
            "message": _("Quotation {0} created successfully for {1}").format(doc.name, customer_name)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Create Quotation V2 Failed"))
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def update_quotation_custom(quotation_id: str, items=None, plate=None, project_name=None, **kwargs):
    """
    Robust wrapper for updating Sales Quotations.
    Preserves existing quantities if not provided.
    """
    try:
        frappe.logger().info(f"[ERPNext Tools] Updating quotation: {quotation_id}")
        
        doc = frappe.get_doc("Quotation", quotation_id)
        
        if plate: doc.plate = plate
        if project_name: doc.project_name = project_name

        # Update flat fields
        meta = frappe.get_meta("Quotation")
        for key, value in kwargs.items():
            if meta.has_field(key) and key not in ["items", "doctype", "name", "plate", "project_name"]:
                doc.set(key, value)
        
        # Handle Items (Smart Update/Merge)
        if items:
            if isinstance(items, str):
                try:
                    import json
                    items = json.loads(items)
                except:
                    # If it's just a string and we don't have qty, we must throw error per user
                    frappe.throw(_("Items must be a list of objects with at least item_code and qty."))
            
            if not isinstance(items, list):
                items = [items]

            # Map existing items by item_code for easy lookup
            # Note: This handles the case where item_code is unique in the quotation.
            # If there are duplicates, it will update the first one found.
            existing_items = {d.item_code: d for d in doc.items}
            
            for item_data in items:
                if not isinstance(item_data, dict):
                    continue
                    
                ic = item_data.get("item_code")
                if not ic: continue
                
                if ic in existing_items:
                    # Update existing row - fields provided by AI override existing ones
                    # Qty is preserved if not in item_data
                    row = existing_items[ic]
                    for field, val in item_data.items():
                        if field != "item_code":
                            row.set(field, val)
                else:
                    # New item - qty is mandatory
                    if not item_data.get("qty"):
                        frappe.throw(_("Quantity (qty) is mandatory for new item {0}").format(ic))
                    doc.append("items", item_data)
        
        doc.save()
        
        return {
            "success": True,
            "name": doc.name,
            "message": _("Quotation {0} updated successfully").format(doc.name)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Update Quotation V2 Failed"))
        return {
            "success": False,
            "error": str(e)
        }
