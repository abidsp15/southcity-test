from decimal import Decimal

# Kolom yang namanya mengandung kata-kata ini dianggap nilai uang
MONEY_WORDS = [
    "amount", "debit", "credit", "total", "tunggakan", "sisa",
    "nilai", "tagihan", "bayar", "harga", "saldo",
]


def is_money_column(column_name):
    name = column_name.lower()
    return any(word in name for word in MONEY_WORDS)


def to_rupiah(value):
    """Contoh: 10500000 -> 'Rp 10.500.000'"""
    if value is None:
        return "-"

    value = Decimal(str(value))
    minus = value < 0
    text = f"{abs(value):,.2f}"           # '10,500,000.00'
    number, decimal = text.split(".")
    number = number.replace(",", ".")     # pemisah ribuan pakai titik

    result = f"Rp {number}"
    if decimal != "00":
        result += f",{decimal}"
    if minus:
        result = "-" + result
    return result


def format_rows(columns, rows):
    """Ubah hasil query jadi list of dict, kolom uang diformat Rupiah."""
    data = []
    for row in rows:
        item = {}
        for col, value in zip(columns, row):
            if is_money_column(col) and isinstance(value, (int, float, Decimal)):
                item[col] = to_rupiah(value)
            elif isinstance(value, Decimal):
                item[col] = float(value)
            elif value is None:
                item[col] = None
            else:
                item[col] = value if isinstance(value, (int, float, str)) else str(value)
        data.append(item)
    return data
