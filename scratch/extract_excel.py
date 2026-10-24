"""Extract Term1 critical formulas and Transmutation table."""
import openpyxl, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

wb = openpyxl.load_workbook(
    r"C:\Users\KC\Downloads\EClass-2026-2027-blank Copy (1).xlsx",
    data_only=False
)

print("=== WORKSHEETS ===")
for name in wb.sheetnames:
    print(f"  {name}")

ws = wb["Term1"]

# Print rows 10-14 (headers + HPS + first student)
print("\n=== Term1: Rows 10-14, columns A-AH ===")
for r in range(10, 15):
    for c in range(1, 35):  # A to AH
        cell = ws.cell(row=r, column=c)
        if cell.value is not None:
            col_letter = openpyxl.utils.get_column_letter(c)
            print(f"  {col_letter}{r}: {repr(cell.value)}")

# Print specific formula columns from row 14
print("\n=== Term1 Row 14: All columns A-AH (formulas) ===")
for c in range(1, 35):
    cell = ws.cell(row=14, column=c)
    col_letter = openpyxl.utils.get_column_letter(c)
    print(f"  {col_letter}14: {repr(cell.value)}")

# Also check row 12 (HPS)
print("\n=== Term1 Row 12: HPS row ===")
for c in range(1, 35):
    cell = ws.cell(row=12, column=c)
    col_letter = openpyxl.utils.get_column_letter(c)
    if cell.value is not None:
        print(f"  {col_letter}12: {repr(cell.value)}")

# Transmutation worksheet
print("\n=== Transmutation WORKSHEET ===")
ws_t = wb["Transmutation"]
for r in range(1, 60):
    for c in range(1, 20):
        cell = ws_t.cell(row=r, column=c)
        if cell.value is not None:
            col_letter = openpyxl.utils.get_column_letter(c)
            try:
                print(f"  {col_letter}{r}: {repr(cell.value)}")
            except:
                print(f"  {col_letter}{r}: [unprintable]")

# Summary worksheet - check for final grade formulas
print("\n=== Summary WORKSHEET (rows 1-20) ===")
ws_s = wb["Summary"]
for r in range(1, 70):
    for c in range(1, 15):
        cell = ws_s.cell(row=r, column=c)
        if cell.value is not None:
            col_letter = openpyxl.utils.get_column_letter(c)
            try:
                print(f"  {col_letter}{r}: {repr(cell.value)}")
            except:
                print(f"  {col_letter}{r}: [unprintable]")
