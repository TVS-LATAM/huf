import frappe
from frappe import _

@frappe.whitelist()
def create_quotation_v2(customer_name: str, items, **kwargs):
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

        # Ensure each item is a dict
        formatted_items = []
        for item in items:
            if isinstance(item, str):
                formatted_items.append({"item_code": item, "qty": 1.0})
            elif isinstance(item, dict):
                formatted_items.append(item)
        
        # Enforce ERPNext logic
        doc_data = {
            "doctype": "Quotation",
            "quotation_to": "Customer",
            "party_name": customer_name,
            "items": formatted_items
        }
        
        # Optional: pull in other kwargs if they exist and are valid fields
        meta = frappe.get_meta("Quotation")
        for key, value in kwargs.items():
            if meta.has_field(key) and key not in ["quotation_to", "party_name", "items", "doctype"]:
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
