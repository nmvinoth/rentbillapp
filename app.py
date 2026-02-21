import datetime
from dataclasses import dataclass
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import re

# -----------------------------------
# SIMPLE ACCESS CODE (6 chars)
# -----------------------------------
# Best practice: store in Streamlit secrets, not hardcode in code.
# In Streamlit Cloud: Settings → Secrets → APP_ACCESS_CODE="A1B2C3"
APP_ACCESS_CODE = st.secrets["APP_ACCESS_CODE"] # fallback for local

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state.auth_ok:
    st.title("🔒 Access Required")
    code = st.text_input("Enter Access Code", type="password", max_chars=6)
    if st.button("Unlock"):
        if (code or "").strip() == str(APP_ACCESS_CODE).strip():
            st.session_state.auth_ok = True
            st.rerun()
        else:
            st.error("Invalid access code.")
    st.stop()
    
# -----------------------------------
# PAGE CONFIG
# -----------------------------------
st.set_page_config(page_title="Sulur Reliance Trends Rent Tax Invoice", layout="centered")


# -----------------------------------
# APP UI CSS (Streamlit page + KPI cards)
# -----------------------------------
APP_CSS = """
<style>
:root{
  --accent:#6FA8DC;
  --accent2:#9FC5E8;
  --muted:#6b7a99;
  --text:#1f2a44;
  --line:rgba(0,0,0,0.12);

  --kpi1:#EAF3FF;
  --kpi2:#EAFBF3;
  --kpi3:#FFF4EA;
  --kpi4:#F3EEFF;
}

.block-container{padding-top:1.25rem; padding-bottom:2rem;}

.kpi-grid{
  display:grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap:12px;
  margin-top:10px;
  margin-bottom:14px;
}
@media (max-width: 900px){
  .kpi-grid{grid-template-columns: repeat(2, minmax(0, 1fr));}
}
.kpi{
  border:1px solid var(--line);
  border-radius:16px;
  padding:14px;
  box-shadow: 0 8px 18px rgba(0,0,0,0.06);
}
.kpi .t{color:var(--muted); font-size:0.85rem; margin-bottom:6px;}
.kpi .v{color:var(--text); font-size:1.25rem; font-weight:900;}
.kpi.k1{background:linear-gradient(180deg, var(--kpi1), #ffffff);}
.kpi.k2{background:linear-gradient(180deg, var(--kpi2), #ffffff);}
.kpi.k3{background:linear-gradient(180deg, var(--kpi3), #ffffff);}
.kpi.k4{background:linear-gradient(180deg, var(--kpi4), #ffffff);}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

# -----------------------------------
# DOWNLOAD BUTTON CSS
# -----------------------------------
DOWNLOAD_BTN_CSS = """
<style>
div[data-testid="stDownloadButton"] > button {
    width: 100%;
    border-radius: 14px;
    padding: 0.75rem 1rem;
    font-weight: 800;
    font-size: 1.05rem;
    border: 1px solid rgba(0,0,0,0.10);
    background: linear-gradient(90deg, #6FA8DC, #9FC5E8);
    color: white;
    box-shadow: 0 10px 18px rgba(0,0,0,0.10);
    transition: transform 0.06s ease-in-out, filter 0.12s ease-in-out;
}

div[data-testid="stDownloadButton"] > button:hover {
    filter: brightness(0.98);
    transform: translateY(-1px);
}

div[data-testid="stDownloadButton"] > button:active {
    transform: translateY(0px);
    filter: brightness(0.96);
}
</style>
"""
st.markdown(DOWNLOAD_BTN_CSS, unsafe_allow_html=True)

# -----------------------------------
# DATA
# -----------------------------------
@dataclass
class Person:
    name: str
    address: str
    pan: str
    gst: str
    sac: str
    desc: str
    location: str
    state_code: str
    state_name: str
    default_rent: float


RECIPIENT = {
    "name": "Reliance Projects and Property Management Services Ltd",
    "address_lines": [
        "89, A1 Tower, Dr Radhakrishnan Salai",
        "Mylapore, Chennai - 600 004,",
        "Tamilnadu",
    ],
    "gstin": "33AAJCR6636B1ZJ",
}

PEOPLE = {
    "S.N.PREMA": Person(
        name="S.N.PREMA",
        address="10. RAMS APARTMENT, 181.TTK ROAD, ALWARPET, CHENNAI - 600018",
        pan="BXNPP2277D",
        gst="33BXNPP2277D1ZD",
        sac="997212",
        desc="Rental or leasing services involving own or leased non-residential property",
        location="SULUR, COIMBATORE DIST., TAMIL NADU",
        state_code="33",
        state_name="Tamilnadu",
        default_rent=194494.00,
    ),
    "S.N.Geetha": Person(
        name="S.N.Geetha",
        address="No.5, Third Main Road, Teesta Street, River View Housing Society, Manapakkam, Chennai - 600125",
        pan="ADAPG2263N",
        gst="33ADAPG2263N1ZQ",
        sac="997212",
        desc="Rental or leasing services involving own or leased non-residential property",
        location="SULUR, COIMBATORE DIST., TAMIL NADU",
        state_code="33",
        state_name="Tamilnadu",
        default_rent=194494.00,
    ),
    "N.RAJENDRAN": Person(
        name="N.RAJENDRAN",
        address="No.15, Subramaniam Layout, Ramanathapuram, Coimbatore - 641045",
        pan="BIFPR0499Q",
        gst="33BIFPR0499Q1ZI",
        sac="997212",
        desc="Rental or leasing services involving own or leased non-residential property",
        location="SULUR, COIMBATORE DIST., TAMIL NADU",
        state_code="33",
        state_name="Tamilnadu",
        default_rent=129662.00,
    ),
}


# -----------------------------------
# HELPERS
# -----------------------------------
ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

def _two_digits(n: int) -> str:
    if n < 20:
        return ONES[n]
    t = n // 10
    o = n % 10
    return (TENS[t] + (" " + ONES[o] if o else "")).strip()

def number_to_words_indian(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    crore = n // 10000000
    n %= 10000000
    lakh = n // 100000
    n %= 100000
    thousand = n // 1000
    n %= 1000
    hundred = n // 100
    n %= 100
    if crore: parts.append(f"{number_to_words_indian(crore)} Crore")
    if lakh: parts.append(f"{_two_digits(lakh)} Lakh")
    if thousand: parts.append(f"{_two_digits(thousand)} Thousand")
    if hundred: parts.append(f"{ONES[hundred]} Hundred")
    if n: parts.append(_two_digits(n))
    return " ".join([p for p in parts if p]).strip()

def format_money(x: float) -> str:
    return f"{x:,.2f}"

def invoice_seq_and_fy(dt: datetime.date):
    year, month = dt.year, dt.month
    fy_start = year if month >= 4 else year - 1
    fy_label = f"{fy_start}-{(fy_start + 1) % 100:02d}"
    seq = (month - 4 + 1) if month >= 4 else (month + 9)
    return seq, fy_label

def wrap_lines_pdf(c: canvas.Canvas, text: str, font_name: str, font_size: int, max_width: float):
    c.setFont(font_name, font_size)
    words = text.split()
    lines, cur = [], []
    for w in words:
        trial = (" ".join(cur + [w])).strip()
        if c.stringWidth(trial, font_name, font_size) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
                cur = [w]
            else:
                lines.append(w)
                cur = []
    if cur:
        lines.append(" ".join(cur))
    return lines

PINCODE_RE = re.compile(r"(?<!\d)(\d{3})\s*(\d{3})(?!\d)")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,\.])")

def format_indian_pincode(text: str, for_html: bool = False) -> str:
    """Ensures 6-digit Indian pin codes are shown as '123 456' (space after 3 digits).
       If for_html=True, uses non-breaking space so it doesn't wrap: '123&nbsp;456'
    """
    if not text:
        return text
    sep = "&nbsp;" if for_html else " "
    return PINCODE_RE.sub(rf"\1{sep}\2", text)

def normalize_text_for_display(text: str, for_html: bool = False) -> str:
    """
    - Removes spaces before comma/full stop so wrapping won't start a new line with ',' or '.'
    - Applies Indian pincode spacing.
    - If for_html=True, pincode uses non-breaking space to avoid messy wrap.
    """
    if not text:
        return text
    t = SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)                  # "Chennai ," -> "Chennai,"
    t = format_indian_pincode(t, for_html=for_html)             # "600125" -> "600&nbsp;125" (HTML) or "600 125" (PDF)
    return t
# -----------------------------------
# PDF (reduced margins + signature bottom-right)
# -----------------------------------
def make_invoice_pdf(
    person: Person,
    invoice_no: str,
    invoice_date: datetime.date,
    from_date: datetime.date,
    to_date: datetime.date,
    rent: float,
    sgst: float,
    cgst: float,
    total: float,
    amount_words: str,
) -> bytes:
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # --- Theme (match preview) ---
    accent = colors.HexColor("#6FA8DC")
    accent2 = colors.HexColor("#9FC5E8")
    accent3 = colors.HexColor("#2F5E8E")
    border = colors.HexColor("#BFC5CE") 
    soft_line = colors.HexColor("#C9D1DB")
    light_bg = colors.HexColor("#EEF5FF")
    text = colors.HexColor("#222222")

    # --- Page frame / usable area ---
    margin = 24
    left, right = margin, W - margin
    top, bottom = H - margin, margin

    # helpers
    def set_font(bold=False, size=10):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)

    def draw_txt(x, y, s, size=10, bold=False, col=text):
        c.setFillColor(col)
        set_font(bold, size)
        c.drawString(x, y, s)

    def draw_rtxt(x, y, s, size=10, bold=False, col=text):
        c.setFillColor(col)
        set_font(bold, size)
        c.drawRightString(x, y, s)

    def wrap(text_in, font_name, font_size, max_w):
        c.setFont(font_name, font_size)
        words = (text_in or "").split()
        lines, cur = [], []
        for w in words:
            trial = (" ".join(cur + [w])).strip()
            if c.stringWidth(trial, font_name, font_size) <= max_w:
                cur.append(w)
            else:
                if cur:
                    lines.append(" ".join(cur))
                    cur = [w]
                else:
                    lines.append(w)
                    cur = []
        if cur:
            lines.append(" ".join(cur))
        return lines

    # --- Outer frame ---
    c.setStrokeColor(border)
    c.setLineWidth(1.2)
    c.rect(left, bottom, right - left, top - bottom, stroke=1, fill=0)

    # Top / bottom bars (like preview)
    bar_h = 14
    c.setFillColor(accent)
    c.rect(left, top - bar_h, right - left, bar_h, stroke=0, fill=1)
    c.setFillColor(accent)
    c.rect(left, bottom, right - left, bar_h, stroke=0, fill=1)

    # --- Header layout: LEFT provider block + RIGHT title/meta block ---

    header_top = top - bar_h - 22  # was too tight
    header_left_x = left + 18
    header_right_w = 300
    header_right_x = right - 18 - header_right_w

    # Center title (so it never feels cramped)
    title_y = header_top
    draw_txt((left + right) / 2 - 55, title_y, "TAX INVOICE", size=20, bold=True, col=colors.HexColor("#42526b"))

    # Keep note top-right with a bit more padding
    draw_rtxt(right - 18, title_y + 2, "Original for Recipient", size=10, bold=False, col=colors.HexColor("#666666"))

    # Meta box slightly lower (more breathing space under title)
    meta_h = 56
    meta_y = header_top - 78   # push down a bit more than before
    c.setStrokeColor(border)
    c.setFillColor(colors.white)
    c.roundRect(header_right_x, meta_y, header_right_w, meta_h, 10, stroke=1, fill=1)

    draw_txt(header_right_x + 14, meta_y + 34, f"Invoice No.   {invoice_no}", size=10, bold=True)
    draw_txt(header_right_x + 14, meta_y + 16, f"Date: {invoice_date.strftime('%d/%m/%Y')}", size=10, bold=True)

    # Left provider name/address
    # --- Provider name/address (header left block) ---
    addr_y = header_top - 45  # starting point below title

    draw_txt(header_left_x, addr_y, f"Name: {person.name}", size=12, bold=True)

    addr_y -= 20  # spacing after name

    provider_addr = normalize_text_for_display(person.address)
    for ln in wrap(provider_addr, "Helvetica", 10, (header_right_x - 24) - header_left_x):
        draw_txt(header_left_x, addr_y, ln, size=10)
        addr_y -= 16  # increased line height

    # extra breathing space after address block
    addr_y -= 8
    
    # START main vertical cursor
    y = addr_y

    # Divider under header
    y -= 10
    c.setStrokeColor(soft_line)
    c.setLineWidth(1.1)
    c.line(left + 14, y, right - 14, y)

    # --- Body starts ---
    y -= 22

    # Recipient section (LEFT) - no duplicate meta box here
    draw_txt(left + 18, y, RECIPIENT["name"], size=10, bold=True)
    y -= 16   # more gap after bold name

    for line in RECIPIENT["address_lines"]:
        draw_txt(left + 18, y, normalize_text_for_display(line), size=10)
        y -= 15   # was 12 → more vertical air

    y -= 8   # space before GSTIN line

    draw_txt(left + 18, y, "GSTIN of recipient :", size=10, bold=False)
    draw_txt(left + 170, y, RECIPIENT['gstin'], size=10, bold=True)

    y -= 18  # more space before next divider

    # Divider
    c.setStrokeColor(soft_line)
    c.setLineWidth(1.1)
    c.line(left + 14, y, right - 14, y)
    y -= 18

    # Provider detail KV grid (3 columns: label : value)
    label_x = left + 18
    colon_x = left + 310
    value_x = left + 325
    max_val_w = right - 18 - value_x

    def kv(label, value, extra_after=6):
        nonlocal y
        draw_txt(label_x, y, label, size=10, bold=False)
        draw_txt(colon_x, y, ":", size=10, bold=False, col=colors.HexColor("#666666"))

        lines = wrap(value, "Helvetica", 10, max_val_w)
        for ln in lines:
            draw_txt(value_x, y, ln, size=10, bold=False)
            y -= 14  # slightly more row height

        y -= extra_after  # bigger spacing after each field

    # PAN (bold value)
    draw_txt(label_x, y, "Pan Number of Service Provider", size=10, bold=False)
    draw_txt(colon_x, y, ":", size=10, bold=False, col=colors.HexColor("#666666"))
    draw_txt(value_x, y, person.pan, size=10, bold=True)
    y -= 18
    
    # GST Registration (bold value)
    draw_txt(label_x, y, "GST Registration Number of service provider", size=10, bold=False)
    draw_txt(colon_x, y, ":", size=10, bold=False, col=colors.HexColor("#666666"))
    draw_txt(value_x, y, person.gst, size=10, bold=True)
    y -= 18
    kv("Service Accounting Code (SAC)", person.sac, extra_after=8)

    # Add bigger gap after this long description to consume empty space nicely
    kv("Description of Service Accounting Code (SAC)", person.desc, extra_after=16)

    kv("Location of service provided", person.location, extra_after=10)
    kv("State code of service location", person.state_code, extra_after=10)
    kv("State name of service location", person.state_name, extra_after=12)

    y -= 8

    # --- Amount table (match preview proportions) ---
    table_x = left + 18
    table_w = right - 18 - table_x
    header_h = 30
    row_h = 30
    table_h = header_h + 4 * row_h

    # Table container
    c.setStrokeColor(border)
    c.roundRect(table_x, y - table_h, table_w, table_h, 10, stroke=1, fill=0)

    # Header fill
    c.setFillColor(accent)
    c.roundRect(table_x, y - header_h, table_w, header_h, 10, stroke=0, fill=1)
    c.setFillColor(colors.white)
    set_font(True, 10)
    c.drawString(table_x + 12, y - 20, "Particulars")
    c.drawRightString(table_x + table_w - 12, y - 20, "Amt Rs")

    # Rows
    c.setFillColor(text)
    set_font(False, 10)

    rent_desc = f"RENT FOR THE PERIOD {from_date.strftime('%d/%m/%Y')} TO {to_date.strftime('%d/%m/%Y')}"
    c.drawString(table_x + 12, y - header_h - 20, rent_desc)
    c.drawRightString(table_x + table_w - 12, y - header_h - 20, format_money(rent))

    # SGST row
    sgst_y = y - header_h - row_h
    c.drawRightString(table_x + table_w - 80, sgst_y - 20, "SGST @ 9%")
    c.drawRightString(table_x + table_w - 12, sgst_y - 20, format_money(sgst))

    # CGST row
    cgst_y = y - header_h - 2 * row_h
    c.drawRightString(table_x + table_w - 80, cgst_y - 20, "CGST @ 9%")
    c.drawRightString(table_x + table_w - 12, cgst_y - 20, format_money(cgst))

    # Total row (light bg)
    total_y = y - header_h - 3 * row_h
    c.setFillColor(light_bg)
    c.rect(table_x, total_y - row_h, table_w, row_h, stroke=0, fill=1)
    c.setFillColor(text)
    set_font(True, 10)
    c.drawString(table_x + 12, total_y - 20, "Total")
    c.drawRightString(table_x + table_w - 12, total_y - 20, format_money(total))

    y = y - table_h - 18

    # ---------------- Amount in words + Signature (no overlap) ----------------
    sig_width = 260
    gap = 20

    left_col_x = table_x
    left_col_w = table_w - sig_width - gap   # reserve space on the right for signature
    right_col_x = table_x + left_col_w + gap

    # Amount in words (full width is fine since signature is bottom)
    set_font(False, 10)
    for ln in wrap(f"Amount in words: {amount_words}", "Helvetica", 10, table_w):
        draw_txt(table_x, y, ln, size=10, bold=False)
        y -= 13

    # --- Signature anchored bottom-right (do NOT move up) ---
    sig_width = 260
    sig_x = right - 18 - sig_width
    sig_y = bottom + bar_h + 26  # fixed anchor above bottom blue bar

    # --- Signature anchored bottom-right (balanced spacing) ---
    sig_width = 260
    sig_x = right - 18 - sig_width
    sig_y = bottom + bar_h + 26  # fixed anchor above bottom blue bar

    # Signature label
    draw_txt(sig_x, sig_y + 60, "Signature:", size=10, bold=True)

    # Medium signing space (reduced from previous)
    # Optional light signing line
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.line(sig_x, sig_y + 44, sig_x + 200, sig_y + 44)

    # Name
    draw_txt(sig_x, sig_y + 22, "Name :", size=10, bold=True)

    # Move designation further right
    draw_txt(sig_x + 90, sig_y + 4, "Authorised Signatory", size=9, bold=True)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------
# UI
# -----------------------------------
st.title("🏠 Sulur Trends Rent Invoice Generator")

st.sidebar.header("View Settings")
desktop_layout = st.sidebar.toggle("Desktop Layout (2 columns)", value=False)

if desktop_layout:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_name = st.selectbox("Select Name", list(PEOPLE.keys()))
    with col2:
        from_date = st.date_input(
            "From Date",
            value=datetime.date.today().replace(day=1),
            format="DD/MM/YYYY"
        )
    with col3:
        to_date = st.date_input(
            "To Date",
            value=datetime.date.today(),
            format="DD/MM/YYYY"
        )
else:
    selected_name = st.selectbox("Select Name", list(PEOPLE.keys()))
    col1, col2 = st.columns(2)
    with col1:
        from_date = st.date_input(
            "From Date",
            value=datetime.date.today().replace(day=1),
            format="DD/MM/YYYY"
        )
    with col2:
        to_date = st.date_input(
            "To Date",
            value=datetime.date.today(),
            format="DD/MM/YYYY"
        )

if to_date < from_date:
    st.warning("To Date is earlier than From Date. Please correct it.")

person = PEOPLE[selected_name]

# Invoice date = 1st of month of From Date
invoice_date = from_date.replace(day=1)
seq, fy_label = invoice_seq_and_fy(invoice_date)
default_invoice_no = f"{seq:02d} / {fy_label}"

st.subheader("Invoice Inputs")
rent = st.number_input("Rent Amount (Rs)", min_value=0.0, value=float(person.default_rent), step=100.0, format="%.2f")
invoice_no = st.text_input("Invoice Number", value=default_invoice_no)

sgst = round(rent * 0.09, 2)
cgst = round(rent * 0.09, 2)
total = round(rent + sgst + cgst, 2)
amount_words = f"{number_to_words_indian(int(round(total)))} Only"

# KPI Cards (colored)
st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi k1"><div class="t">Rent</div><div class="v">Rs {format_money(rent)}</div></div>
      <div class="kpi k2"><div class="t">SGST (9%)</div><div class="v">Rs {format_money(sgst)}</div></div>
      <div class="kpi k3"><div class="t">CGST (9%)</div><div class="v">Rs {format_money(cgst)}</div></div>
      <div class="kpi k4"><div class="t">Total</div><div class="v">Rs {format_money(total)}</div></div>
    </div>
    """,
    unsafe_allow_html=True
)

st.subheader("Preview (should match PDF)")

# IMPORTANT FIX: embed CSS INSIDE the iframe so preview isn’t plain
preview_css = """
<style>
  :root{ --accent:#6FA8DC; --accent2:#9FC5E8; --accent3:#2F5E8E; }
  body{ margin:0; padding:0; background:#fff; font-family: Arial, sans-serif; }
  .preview-frame{ border:2px solid rgba(47,94,142,0.20); border-radius:16px; overflow:hidden; background:white; }
  .inv-bar{ height:14px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .inv-top{ padding:14px 18px; display:flex; justify-content:space-between; gap:18px; }
  .inv-top-left{ font-size:12px; line-height:1.6; color:#333; }
  .inv-top-right{ text-align:right; min-width:320px; }
  .inv-title{ font-size:22px; font-weight:900; letter-spacing:0.8px; color:#42526b; }
  .inv-note{ font-size:11px; color:#666; margin-top:4px; }
  .inv-meta{ margin-top:10px; border:1px solid #d9d9d9; border-radius:10px; overflow:hidden; }
  .inv-meta-row{ display:flex; justify-content:space-between; padding:10px 12px; border-top:1px solid #e6e6e6; font-size:12px; background:#fbfdff; }
  .inv-meta-row:first-child{ border-top:none; }
  .inv-meta-row b{ color:#2a3b57; }
  .inv-body{ padding:14px 18px 18px 18px; }
  .section{ margin-top:12px; }
  .section-title{ font-size:12px; font-weight:900; color:var(--accent3); margin-bottom:8px; }
  .lines{ font-size:12px; line-height:1.6; color:#333; }
  .hr{ height:1px; background:#ededed; margin:14px 0; }
  .kv-grid{ display:grid; grid-template-columns: 240px 14px 1fr; row-gap:8px; font-size:12px; line-height:1.5; }
  .kv-grid .c{ text-align:center; color:#666; }
  .table{ margin-top:14px; border:1px solid #d9d9d9; border-radius:10px; overflow:hidden; }
  .thead{ display:flex; justify-content:space-between; background: linear-gradient(90deg, var(--accent), var(--accent2)); color:white; font-weight:900; font-size:12px; }
  .thead div{ padding:10px 12px; }
  .trow{ display:flex; justify-content:space-between; gap:12px; border-top:1px solid #eee; font-size:12px; }
  .trow:nth-child(odd){ background:#f7faff; }
  .trow div{ padding:10px 12px; }
  .wdesc{ flex:1 1 auto; }
  .wamt{ width:180px; text-align:right; white-space:nowrap; }
  .rightlabel{ text-align:right; padding-right:30px; font-weight:700; color:#2a3b57; }
  .totalrow{ background:#eef5ff; font-weight:900; }
  .amountwords{ margin-top:12px; font-size:12px; line-height:1.6; }
  .signature{ margin-top:26px; display:flex; justify-content:flex-end; }
  .sigbox{ width:300px; font-size:12px; line-height:1.8; }
  .sigbox b{ color:#2a3b57; }
</style>
"""
person_address_preview = normalize_text_for_display(person.address)
recipient_lines_preview = "<br>".join(normalize_text_for_display(x, for_html=True) for x in RECIPIENT["address_lines"])
address_preview = normalize_text_for_display(person.address, for_html=True)

if person.name == "S.N.Geetha":
    # Keep this phrase unbreakable
    address_preview = address_preview.replace(
        "River View Housing Society",
        "River&nbsp;View&nbsp;Housing&nbsp;Society"
    )
    # Force a clean break so "Chennai - 600 125" starts on next line
    address_preview = address_preview.replace(", Chennai", ",<br>Chennai")

preview_html = f"""
<!doctype html>
<html>
<head>{preview_css}</head>
<body>
<div class="preview-frame">
  <div class="inv-bar"></div>

  <div class="inv-top">
    <div class="inv-top-left">
      <div><b>Name: {person.name}</b></div>
      <div>{address_preview}</div>
    </div>

    <div class="inv-top-right">
      <div class="inv-title">TAX INVOICE</div>
      <div class="inv-note">Original for Recipient</div>
      <div class="inv-meta">
        <div class="inv-meta-row"><b>Invoice No.</b><span>{invoice_no}</span></div>
        <div class="inv-meta-row"><b>Date</b><span>{invoice_date.strftime("%d/%m/%Y")}</span></div>
      </div>
    </div>
  </div>

  <div class="inv-body">
    <div class="section">
      <div class="section-title">Name & Address of service recipient</div>
      <div class="lines"><b>{RECIPIENT["name"]}</b><br>
        {recipient_lines_preview}
      </div>
      <div class="lines" style="margin-top:10px;">   <b>GSTIN of recipient :</b> <b>{RECIPIENT["gstin"]}</b> </div>
    </div>

    <div class="hr"></div>

    <div class="section">
      <div class="kv-grid">
        <div><b>Pan Number of Service Provider</b></div><div class="c">:</div><div><b>{person.pan}</b></div>
        <div><b>GST Registration Number of service provider</b></div><div class="c">:</div><div><b>{person.gst}</b></div>
        <div><b>Service Accounting Code (SAC)</b></div><div class="c">:</div><div>{person.sac}</div>
        <div><b>Description of Service Accounting Code (SAC)</b></div><div class="c">:</div><div>{person.desc}</div>
        <div><b>Location of service provided</b></div><div class="c">:</div><div>{person.location}</div>
        <div><b>State code of service location</b></div><div class="c">:</div><div>{person.state_code}</div>
        <div><b>State name of service location</b></div><div class="c">:</div><div>{person.state_name}</div>
      </div>
    </div>

    <div class="table">
      <div class="thead"><div>Particulars</div><div>Amt Rs</div></div>

      <div class="trow">
        <div class="wdesc">RENT FOR THE PERIOD {from_date.strftime("%d/%m/%Y")} TO {to_date.strftime("%d/%m/%Y")}</div>
        <div class="wamt">{format_money(rent)}</div>
      </div>
      <div class="trow">
        <div class="wdesc rightlabel">SGST @ 9%</div>
        <div class="wamt">{format_money(sgst)}</div>
      </div>
      <div class="trow">
        <div class="wdesc rightlabel">CGST @ 9%</div>
        <div class="wamt">{format_money(cgst)}</div>
      </div>
      <div class="trow totalrow">
        <div class="wdesc">Total</div>
        <div class="wamt">{format_money(total)}</div>
      </div>
    </div>

    <div class="amountwords"><b>Amount in words:</b> {amount_words}</div>

    <div class="signature">
      <div class="sigbox">
        <div><b>Signature:</b></div>
        <div style="margin-top:18px;"><b>Name :</b> Name</div>
        <div><b>Authorised Signatory</b></div>
      </div>
    </div>
  </div>

  <div class="inv-bar"></div>
</div>
</body>
</html>
"""

components.html(preview_html, height=920, scrolling=True)

# PDF
pdf_bytes = make_invoice_pdf(
    person=person,
    invoice_no=invoice_no,
    invoice_date=invoice_date,
    from_date=from_date,
    to_date=to_date,
    rent=rent,
    sgst=sgst,
    cgst=cgst,
    total=total,
    amount_words=amount_words,
)

file_name = f"TaxInvoice_{person.name.replace(' ', '_')}_{invoice_date.strftime('%Y%m')}.pdf"
st.download_button(
    "⬇️ Download PDF",
    data=pdf_bytes,
    file_name=file_name,
    mime="application/pdf",
    use_container_width=True

)
















