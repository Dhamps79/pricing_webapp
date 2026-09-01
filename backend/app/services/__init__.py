import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

def generate_costing_excel(sheet_data: dict) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Costing Sheet"

    # Header Info
    ws.append(["Title:", sheet_data["title"]])
    ws.append(["Customer:", sheet_data.get("customer_name", "N/A")])
    ws.append(["Date:", str(sheet_data["created_at"])])
    ws.append([]) # Empty row

    # Table Headers
    headers = ["Item Name", "SKU", "Quantity", "Unit", "List Price", "Sell Price", "Discount %", "Net Total"]
    ws.append(headers)
    
    # Style Headers
    for cell in ws[5]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Add Line Items
    for line in sheet_data["lines"]:
        ws.append([
            line["name"],
            line["sku"],
            float(line["quantity"]),
            line["unit"],
            float(line["list_price"]),
            float(line["sell_price"]),
            float(line["discount_percent"]),
            float(line["line_net_total"])
        ])

    ws.append([]) # Empty row
    
    # Totals
    ws.append(["", "", "", "", "", "", "List Total:", float(sheet_data["list_total"])])
    ws.append(["", "", "", "", "", "", "Sheet Discount %:", float(sheet_data["discount_percent"])])
    ws.append(["", "", "", "", "", "", "Grand Total:", float(sheet_data["grand_total"])])

    # Save to memory stream
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream