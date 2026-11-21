"""
MediGen AI - Chatbot Engine
---------------------------
* Works fully offline (no API key needed).
* Reads LIVE data from your MySQL database.
* Understands English and Roman Urdu.
* Finds medicine names even with spelling mistakes (e.g. "panadoll", "amoxcillin").
* Remembers the last medicine, so you can ask "and its price?".

Main function:  get_answer(cur, question, user, ctx)
    cur      -> MySQL DictCursor
    question -> text typed by the user
    user     -> dict: {"name": "...", "role": "Admin"|"Pharmacist"|"Cashier"}
    ctx      -> small dict kept in the session (memory of last medicine)
Returns:  (answer_text, suggestion_chips)
"""

import re
import difflib
import math
from datetime import date, datetime

# v90.00: built-in medicine knowledge base (offline). Guarded so the engine
# still works even if the knowledge file is missing.
try:
    import medicine_knowledge as _MK
except Exception:  # pragma: no cover
    _MK = None

# v90.00: what this software is and how it works (asked often, answered offline)
SOFTWARE_TEXT = (
    "**MediGen AI Pro** is a complete pharmacy management system (ERP + POS) for one shop, "
    "running on the shop PC.\n"
    "**How it runs:** a server program starts on the shop PC (START_DESKTOP.bat), the data is "
    "stored safely in a MySQL database, and staff use it in a browser - other PCs in the shop "
    "can open it on the local network.\n"
    "**What it does:**\n"
    "• **Sales & Billing (POS)** - fast billing, receipts (A4 and 80mm), discounts, returns, cash drawer\n"
    "• **Pharmacy Catalog** - medicines, barcodes, categories, prices\n"
    "• **Inventory** - batches, expiry tracking, low-stock and expiry alerts, stock counts\n"
    "• **Purchasing** - suppliers, purchase orders, suggestions and forecasts\n"
    "• **Customers** - customer records, udhaar (credit) and dues, prescriptions\n"
    "• **Finance** - expenses, daily closing, margins and reports (CSV, Excel, PDF, Word)\n"
    "• **AI Assistant** - ask me about stock, sales, any medicine, or how to do anything here\n"
    "**Roles:** Admin (everything), Pharmacist and Cashier (limited by design, for safety).\n"
    "Type **help** for example questions, or ask *how do I take a backup* style questions."
)

# v90.00: phrases that mean "tell me ABOUT this medicine" (not stock/price)
_KNOW_PHRASES = ("used for", "use for", "kis liye", "kis lie", "side effect", "side effects",
                 "what is", "kya hai", "kya hota", "kya hoti", "kis kaam", "kaam aati",
                 "use hoti", "use hota", "istemaal", "istamal", "fayda", "fayde",
                 "nuqsan", "nuksan", "ilaaj", "ilaj")
_KNOW_TOKENS = {"uses", "used", "benefits", "benefit", "dosage", "dose", "treats", "cures", "about"}

DEFAULT_CHIPS = ["Today sales", "Low stock", "Expiring soon", "Top selling", "Total customers", "Help"]

# ---- Pro keywords (English + Roman Urdu) ----
PROFIT_W = {"profit", "profits", "munafa", "nafa", "faida", "margin", "earning", "earnings"}
RETURN_W = {"return", "returns", "returned", "refund", "refunds", "wapas", "wapsi", "wapsy"}
DUES_W = {"udhaar", "udhar", "due", "dues", "balance", "credit", "baqi", "baki", "owes", "owe", "outstanding"}
SUPPLIER_W = {"supplier", "suppliers", "distributor", "distributors", "vendor", "vendors"}
REORDER_W = {"reorder", "mangwao", "mangwana", "kharidna", "khareedna", "buy", "restock", "order", "orders"}
ALLERGY_W = {"allergy", "allergic", "allergies", "alerji", "reaction", "contraindication"}
DISCOUNT_W = {"discount", "discounts", "offer", "offers", "tip", "tips", "suggest", "suggestion", "suggestions", "advice", "idea", "ideas"}

# ------------------------------------------------------------------
# Word lists (English + Roman Urdu)
# ------------------------------------------------------------------
GREET = {"hello", "hi", "hey", "salam", "salaam", "aoa", "assalam", "assalamualaikum", "slam", "hii", "hy", "morning", "evening"}
THANKS = {"thanks", "thank", "thankyou", "shukriya", "shukria", "jazakallah", "thx"}
BYE = {"bye", "goodbye", "allah", "khuda", "hafiz"}
HELP = {"help", "madad", "commands", "options", "menu"}
PRICE = {"price", "cost", "rate", "qeemat", "kimat", "keemat", "rates", "prices"}
STOCK = {"stock", "available", "availability", "quantity", "qty", "units", "maujood", "mojood", "inventory"}
LOW = {"low", "kam", "shortage", "reorder", "short", "running"}
EXPIRE = {"expiry", "expire", "expires", "expiring", "expired", "expiration", "mayad", "date"}
SALES = {"sale", "sales", "sell", "sold", "selling", "bikri", "bechi", "bechna", "invoice", "invoices",
         "revenue", "income", "earning", "earnings", "kamai", "business", "bill", "bills"}
TOP = {"top", "best", "popular", "bestselling", "zyada", "famous", "most"}
COUNTW = {"total", "how", "many", "count", "number", "kitne", "kitni", "kul", "tadad"}
RECENT = {"recent", "latest", "last", "new", "aakhri", "akhri"}
LISTW = {"list", "show", "all", "names", "dikhao", "sab", "saari", "sare"}
PRONOUN = {"it", "its", "uski", "uska", "iski", "iska", "uske", "iske", "isko", "usko"}
HOWW = {"how", "kaise", "kese", "kaisay", "where", "kahan", "kahaan", "steps", "guide"}

ENTITIES = {
    "customer": {"customer", "customers", "gahak", "client", "clients"},
    "supplier": {"supplier", "suppliers", "vendor", "vendors"},
    "medicine": {"medicine", "medicines", "dawai", "dawa", "dawaiyan", "drug", "drugs", "item", "items", "products"},
    "category": {"category", "categories"},
    "prescription": {"prescription", "prescriptions"},
    "user": {"user", "users", "staff", "employee", "employees"},
    "batch": {"batch", "batches"},
    "purchase": {"purchase", "purchases", "purchasing"},
}

GENERIC_STOP = {
    "a", "an", "the", "is", "are", "was", "of", "in", "on", "for", "me", "my", "to", "and", "or", "please", "pls",
    "show", "tell", "give", "what", "whats", "which", "who", "do", "does", "you", "we", "have", "has", "any", "with",
    "about", "info", "information", "details", "check", "find", "get", "can", "could", "se", "than", "there", "s",
    "hai", "hain", "ka", "ki", "ke", "ko", "me", "mein", "main", "kya", "batao", "bata", "dikhao", "do", "kaun",
    "aaj", "today", "todays", "yesterday", "week", "weekly", "month", "monthly", "days", "day", "now", "hafta", "mahina",
    "wala", "wali", "hota", "hoti", "kab", "ho", "gaya", "gayi", "gai", "hone", "wale", "wali", "soon", "out",
    "this", "that", "it", "its", "much", "very", "also", "too", "again", "more", "less", "than", "so", "ye", "yeh", "woh",
    "bhi", "aur", "or", "page", "system", "pharmacy", "medigen", "ai", "assistant", "bot",
}

ALL_KEYWORDS = set()
for _s in (GREET, THANKS, BYE, HELP, PRICE, STOCK, LOW, EXPIRE, SALES, TOP, COUNTW, RECENT, LISTW, PRONOUN, HOWW):
    ALL_KEYWORDS |= _s
for _s in ENTITIES.values():
    ALL_KEYWORDS |= _s
STOP = GENERIC_STOP | ALL_KEYWORDS

# How-to guide (short, step by step)
GUIDES = [
    ({"add", "medicine"}, "To add a medicine:\n• Open **Medicines** from the left menu\n• Click **Add Medicine**\n• Fill name, category, price, stock and reorder level\n• Click **Save**"),
    ({"make", "sale"}, "To make a sale:\n• Click **New Sale** in the left menu\n• Choose the customer (or leave empty for walk-in)\n• Add medicines and quantity\n• Choose payment method and save"),
    ({"new", "sale"}, "To make a new sale:\n• Click **New Sale** in the left menu\n• Choose the customer (or leave empty for walk-in)\n• Add medicines and quantity\n• Choose payment method and save\n• The receipt opens from the **Sales** page"),
    ({"make", "bill"}, "To make a bill:\n• Click **New Sale** in the left menu\n• Add medicines and quantity\n• Choose payment method and save\n• Open the receipt from the **Sales** page and click Print"),
    ({"add", "customer"}, "To add a customer:\n• Open **Customers** from the left menu\n• Click **Add Customer**\n• Fill the details and save"),
    ({"add", "supplier"}, "To add a supplier:\n• Open **Suppliers** (Admin / Pharmacist)\n• Click **Add Supplier**\n• Fill the details and save"),
    ({"add", "user"}, "To add a staff user (Admin only):\n• Open **Users**\n• Click **Add User**\n• Enter name, username, password and role, then save"),
    ({"purchase"}, "To record a purchase (Admin only):\n• Open **Purchases**\n• Click **New Purchase**\n• Pick the supplier, add medicines, quantity and price, then save"),
    ({"prescription"}, "To add a prescription:\n• Open **Prescriptions**\n• Click **Add Prescription**\n• Choose customer, doctor and medicines with dosage, then save"),
    ({"password"}, "To change your password:\n• Open **My Profile**\n• Use the **Change Password** section\n• Enter old and new password, then save"),
    ({"report"}, "Reports are in the **Reports** page (Admin only). Pick a start and end date to see daily sales, best sellers, low stock and expiry."),
    ({"backup"}, "To back up the database:\n• On the shop PC, open the Server folder\n• Run: python scripts/backup_db.py\n• The file is saved in the **backups** folder. A failed backup shows an error - it never claims success."),
    ({"export"}, "To export a report:\n• Open **Reports** (Admin only)\n• Pick the date range\n• Choose CSV, Excel, PDF or Word. CSV opens directly in Excel."),
    ({"return"}, "To take a return:\n• Open **Sales** and find the bill\n• Click **Return**\n• Enter the returned quantities and save\n• Stock goes back to the same batch it was sold from."),
    ({"barcode"}, "Barcodes:\n• Add or edit a medicine and type or scan its barcode\n• At **New Sale**, scan the barcode to add the medicine at once\n• One barcode can belong to only one medicine - duplicates are listed on the **Data Quality** page."),
    ({"remember"}, "Remember me:\n• Tick **Remember me** on the login page\n• This PC stays signed in for 30 days\n• Logging out ends it at once. Only use it on the shop's own PC."),
    ({"forgot", "password"}, "Forgot the password:\n• On the shop PC, open the Server folder\n• Run: python reset_password.py\n• Type the username and a new password (min 8 characters)."),
    ({"expiry"}, "Expiry:\n• The **Dashboard** shows batches expiring in 30, 60 and 90 days\n• The **Batches** page lists expired and expiring stock\n• Expired batches are never sold."),
    ({"discount"}, "Discounts:\n• At **New Sale** give a discount in percent or in rupees\n• A Cashier can give up to the limit set in **Settings** (ask a Pharmacist or Admin for more)."),
    ({"udhaar"}, "Udhaar (credit):\n• At **New Sale**, choose the customer when part of the bill stays unpaid\n• Customer dues are on the **Customers** page (Customer Dues)."),
    ({"tax"}, "Tax:\n• The tax rate is set in **Settings** (Money rules)\n• It is added to every sale and shown on the receipt and in the tax report."),
    ({"print", "receipt"}, "To print a receipt:\n• Open **Sales**, open the bill\n• **Print** gives the A4 receipt; **80mm receipt** gives the thermal size."),
    ({"settings"}, "Settings (Admin):\n• Open **Settings** for shop name, address, phone, receipt footer, tax rate and the cashier discount limit."),
    ({"start", "server"}, "To start MediGen:\n• Double-click **START_DESKTOP.bat** in the Server folder\n• It starts the server and opens the workbench in the browser\n• To stop it, use **STOP_MEDIGEN.bat**."),
]


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def _norm(text):
    text = (text or "").lower().replace("'", "")
    text = re.sub(r"[^a-z0-9\u0600-\u06ff\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def money(v):
    try:
        s = f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "Rs. 0"
    if s.endswith(".00"):
        s = s[:-3]
    return "Rs. " + s


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _stock_status(stock, reorder):
    stock = int(stock or 0)
    reorder = int(reorder or 0)
    if stock <= 0:
        return "Out of stock"
    if stock <= reorder:
        return "Low stock"
    return "In stock"


def _hit(tokens, words):
    return any(t in words for t in tokens)


def _entity(tokens):
    for name, words in ENTITIES.items():
        if any(t in words for t in tokens):
            return name
    return None


def _period(tokens, text):
    """Return (label, days_back_start, days_back_end) or None."""
    if "yesterday" in tokens or "kal" in tokens:
        return ("yesterday", 1, 1)
    if _hit(tokens, {"week", "weekly", "hafta", "haftay", "hafte"}) or "7 days" in text:
        return ("last 7 days", 6, 0)
    if _hit(tokens, {"month", "monthly", "mahina", "mahine"}) or "30 days" in text:
        return ("last 30 days", 29, 0)
    if _hit(tokens, {"today", "todays", "aaj"}):
        return ("today", 0, 0)
    return None


# ------------------------------------------------------------------
# Database helpers
# ------------------------------------------------------------------
def _all_medicines(cur):
    cur.execute("""
        SELECT m.medicine_id, m.name, m.price, m.stock_quantity, m.reorder_level, c.category_name
        FROM medicines m
        LEFT JOIN categories c ON m.category_id = c.category_id
    """)
    return cur.fetchall()


def _find_medicines(tokens, text, meds):
    """Find medicine(s) mentioned in the question. Tolerates spelling mistakes."""
    padded = f" {text} "
    exact = []
    for m in meds:
        n = _norm(m["name"])
        if n and f" {n} " in padded:
            exact.append((len(n), m))
    if exact:
        best = max(l for l, _ in exact)
        return [m for l, m in exact if l == best][:5]

    cand = [t for t in tokens if t not in STOP and len(t) >= 3 and not t.isdigit()]
    if not cand:
        return []

    scored = []
    for m in meds:
        parts = [p for p in _norm(m["name"]).split()
                 if len(p) >= 3 and not re.fullmatch(r"\d+(mg|ml|g|mcg|gm)?", p)]
        best = 0.0
        for p in parts[:2]:
            for t in cand:
                if t == p:
                    r = 1.0
                elif len(t) >= 4 and len(p) >= 4 and (p.startswith(t) or t.startswith(p)):
                    r = 0.92
                elif len(t) >= 4 and len(p) >= 4:
                    r = difflib.SequenceMatcher(None, t, p).ratio()
                else:
                    r = 0.0
                best = max(best, r)
        if best >= 0.84:
            scored.append((best, m))
    if not scored:
        return []
    top = max(s for s, _ in scored)
    return [m for s, m in scored if s >= top - 0.001][:5]


# ------------------------------------------------------------------
# Answer builders
# ------------------------------------------------------------------
def _medicine_card(cur, m, focus="info"):
    status = _stock_status(m["stock_quantity"], m["reorder_level"])
    name = m["name"]
    lines = [f"**{name}**"]

    if focus == "price":
        lines.append(f"• Price: {money(m['price'])} per unit")
        lines.append(f"• Stock: {m['stock_quantity']} units ({status})")
        return "\n".join(lines)

    if focus == "sold":
        cur.execute("SELECT IFNULL(SUM(quantity),0) AS s FROM sale_items WHERE medicine_id=%s", (m["medicine_id"],))
        total = cur.fetchone()["s"]
        cur.execute("""
            SELECT IFNULL(SUM(si.quantity),0) AS s
            FROM sale_items si JOIN sales s ON si.sale_id = s.sale_id
            WHERE si.medicine_id=%s AND DATE(s.sale_date) >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)
        """, (m["medicine_id"],))
        month = cur.fetchone()["s"]
        lines.append(f"• Sold in last 30 days: {int(month)} units")
        lines.append(f"• Sold all time: {int(total)} units")
        lines.append(f"• Stock left: {m['stock_quantity']} units ({status})")
        return "\n".join(lines)

    if focus == "expiry":
        cur.execute("""
            SELECT batch_number, expiry_date, quantity FROM batches
            WHERE medicine_id=%s AND quantity > 0 ORDER BY expiry_date ASC LIMIT 5
        """, (m["medicine_id"],))
        rows = cur.fetchall()
        if not rows:
            lines.append("• No active batch found for this medicine.")
            return "\n".join(lines)
        today = date.today()
        for r in rows:
            d = _to_date(r["expiry_date"])
            if d is None:
                tag = ""
            elif d < today:
                tag = " - EXPIRED"
            elif (d - today).days <= 90:
                tag = f" - expires in {(d - today).days} days"
            else:
                tag = ""
            lines.append(f"• Batch {r['batch_number']}: {r['expiry_date']} ({r['quantity']} units){tag}")
        return "\n".join(lines)

    # default: full info card
    lines.append(f"• Stock: {m['stock_quantity']} units ({status})")
    lines.append(f"• Price: {money(m['price'])} per unit")
    if m.get("category_name"):
        lines.append(f"• Category: {m['category_name']}")
    lines.append(f"• Reorder level: {m['reorder_level']}")
    cur.execute("""
        SELECT batch_number, expiry_date FROM batches
        WHERE medicine_id=%s AND quantity > 0 ORDER BY expiry_date ASC LIMIT 1
    """, (m["medicine_id"],))
    b = cur.fetchone()
    if b:
        lines.append(f"• Next expiry: {b['expiry_date']} (batch {b['batch_number']})")
    return "\n".join(lines)


def _sales_summary(cur, label, start, end):
    cur.execute("""
        SELECT COUNT(*) AS c, IFNULL(SUM(total_amount - returned_amount),0) AS t FROM sales
        WHERE DATE(sale_date) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)
    """, (start, end))
    d = cur.fetchone()
    lines = [f"**Sales ({label})**",
             f"• Invoices: {d['c']}",
             f"• Revenue: {money(d['t'])}"]
    if int(d["c"]) > 0:
        lines.append(f"• Average invoice: {money(float(d['t']) / int(d['c']))}")
        cur.execute("""
            SELECT m.name, SUM(si.quantity) AS sold
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN medicines m ON si.medicine_id = m.medicine_id
            WHERE DATE(s.sale_date) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY m.name ORDER BY sold DESC LIMIT 1
        """, (start, end))
        t = cur.fetchone()
        if t:
            lines.append(f"• Best seller: {t['name']} ({int(t['sold'])} sold)")
    return "\n".join(lines)


def _top_selling(cur, period):
    if period:
        label, start, end = period
        cur.execute("""
            SELECT m.name, SUM(si.quantity) AS sold, SUM(si.subtotal) AS revenue
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
            JOIN medicines m ON si.medicine_id = m.medicine_id
            WHERE DATE(s.sale_date) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY m.name ORDER BY sold DESC LIMIT 5
        """, (start, end))
    else:
        label = "all time"
        cur.execute("""
            SELECT m.name, SUM(si.quantity) AS sold, SUM(si.subtotal) AS revenue
            FROM sale_items si JOIN medicines m ON si.medicine_id = m.medicine_id
            GROUP BY m.name ORDER BY sold DESC LIMIT 5
        """)
    rows = cur.fetchall()
    if not rows:
        return f"No sales found for {label}."
    out = [f"**Top selling medicines ({label})**"]
    for i, r in enumerate(rows, 1):
        out.append(f"{i}. {r['name']} - {int(r['sold'])} sold ({money(r['revenue'])})")
    return "\n".join(out)


def _low_stock(cur):
    cur.execute("""
        SELECT name, stock_quantity, reorder_level FROM medicines
        WHERE stock_quantity <= reorder_level ORDER BY stock_quantity ASC LIMIT 10
    """)
    rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM medicines WHERE stock_quantity <= reorder_level")
    total = cur.fetchone()["c"]
    if not rows:
        return "Good news! All medicines are above their reorder level."
    out = [f"**Low stock medicines ({total})**"]
    for r in rows:
        out.append(f"• {r['name']}: {r['stock_quantity']} left (reorder at {r['reorder_level']})")
    if total > len(rows):
        out.append(f"...and {total - len(rows)} more. Open Reports for the full list.")
    return "\n".join(out)


def _out_of_stock(cur):
    cur.execute("SELECT name FROM medicines WHERE stock_quantity <= 0 ORDER BY name LIMIT 15")
    rows = cur.fetchall()
    if not rows:
        return "No medicine is out of stock right now."
    out = [f"**Out of stock ({len(rows)})**"]
    out += [f"• {r['name']}" for r in rows]
    return "\n".join(out)


def _expiring(cur, days):
    cur.execute("""
        SELECT m.name, b.batch_number, b.expiry_date, b.quantity
        FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
        WHERE b.quantity > 0 AND b.expiry_date >= CURDATE()
          AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
        ORDER BY b.expiry_date ASC LIMIT 10
    """, (days,))
    rows = cur.fetchall()
    if not rows:
        return f"No medicine is expiring in the next {days} days."
    out = [f"**Expiring in next {days} days**"]
    for r in rows:
        out.append(f"• {r['name']} (batch {r['batch_number']}): {r['expiry_date']} - {r['quantity']} units")
    return "\n".join(out)


def _expired(cur):
    cur.execute("""
        SELECT m.name, b.batch_number, b.expiry_date, b.quantity
        FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
        WHERE b.quantity > 0 AND b.expiry_date < CURDATE()
        ORDER BY b.expiry_date ASC LIMIT 10
    """)
    rows = cur.fetchall()
    if not rows:
        return "No expired stock found. Everything is fine."
    out = ["**Expired batches (remove from shelf!)**"]
    for r in rows:
        out.append(f"• {r['name']} (batch {r['batch_number']}): expired {r['expiry_date']} - {r['quantity']} units")
    return "\n".join(out)


def _count(cur, entity, tokens, user):
    role = user.get("role")
    if entity == "user" and role != "Admin":
        return "Sorry, staff information is only available for Admin."
    if entity == "purchase" and role != "Admin":
        return "Sorry, purchase information is only available for Admin."
    if entity == "supplier" and role not in ("Admin", "Pharmacist"):
        return "Sorry, supplier information is only available for Admin and Pharmacist."
    tables = {
        "customer": ("customers", "customers registered"),
        "supplier": ("suppliers", "suppliers"),
        "medicine": ("medicines", "medicines in the system"),
        "category": ("categories", "categories"),
        "prescription": ("prescriptions", "prescriptions"),
        "user": ("users", "staff users"),
        "batch": ("batches", "batches"),
        "purchase": ("purchase_orders", "purchase orders"),
    }
    table, label = tables[entity]
    cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
    n = cur.fetchone()["c"]
    text = f"There are **{n}** {label}."

    if _hit(tokens, LISTW):
        names = {
            "medicine": "SELECT name AS n FROM medicines ORDER BY name LIMIT 12",
            "category": "SELECT category_name AS n FROM categories ORDER BY category_name LIMIT 15",
            "customer": "SELECT name AS n FROM customers ORDER BY name LIMIT 10",
            "supplier": "SELECT name AS n FROM suppliers ORDER BY name LIMIT 10",
        }
        if entity in names:
            cur.execute(names[entity])
            rows = cur.fetchall()
            if rows:
                text += "\n" + "\n".join(f"• {r['n']}" for r in rows)
                if n > len(rows):
                    text += f"\n...and {n - len(rows)} more."
    return text


def _customer_lookup(cur, rest_tokens):
    like = f"%{rest_tokens[0]}%"
    cur.execute("SELECT name, contact_number FROM customers WHERE LOWER(name) LIKE %s ORDER BY name LIMIT 5", (like,))
    rows = cur.fetchall()
    if not rows:
        return None
    out = [f"**Customers matching '{rest_tokens[0]}'**"]
    for r in rows:
        out.append(f"• {r['name']} - {r['contact_number'] or 'no phone'}")
    return "\n".join(out)


def _recent_sales(cur):
    cur.execute("""
        SELECT s.sale_id, s.sale_date, s.total_amount, c.name AS customer_name
        FROM sales s LEFT JOIN customers c ON s.customer_id = c.customer_id
        ORDER BY s.sale_id DESC LIMIT 5
    """)
    rows = cur.fetchall()
    if not rows:
        return "No sales have been made yet."
    out = ["**Latest 5 sales**"]
    for r in rows:
        out.append(f"• #{r['sale_id']} - {r['customer_name'] or 'Walk-in'} - {money(r['total_amount'])} ({str(r['sale_date'])[:16]})")
    return "\n".join(out)


def _inventory_overview(cur):
    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN stock_quantity <= 0 THEN 1 ELSE 0 END) AS out_count,
               SUM(CASE WHEN stock_quantity > 0 AND stock_quantity <= reorder_level THEN 1 ELSE 0 END) AS low
        FROM medicines
    """)
    d = cur.fetchone()
    return ("**Stock overview**\n"
            f"• Total medicines: {d['total']}\n"
            f"• Low stock: {int(d['low'] or 0)}\n"
            f"• Out of stock: {int(d['out_count'] or 0)}\n"
            "Type a medicine name (for example **Panadol stock**) to see its stock.")


def _inventory_value(cur):
    cur.execute("SELECT IFNULL(SUM(price * stock_quantity),0) AS v FROM medicines")
    return f"Total stock value (price x quantity): **{money(cur.fetchone()['v'])}**"


def _medicines_in_category(cur, text, tokens):
    cur.execute("SELECT category_id, category_name FROM categories")
    cats = cur.fetchall()
    padded = f" {text} "
    for c in cats:
        n = _norm(c["category_name"])
        if n and (f" {n} " in padded or any(t == n for t in tokens)):
            cur.execute("SELECT name, stock_quantity FROM medicines WHERE category_id=%s ORDER BY name LIMIT 12", (c["category_id"],))
            rows = cur.fetchall()
            if not rows:
                return f"No medicines found in **{c['category_name']}**."
            out = [f"**{c['category_name']} medicines**"]
            out += [f"• {r['name']} ({r['stock_quantity']} in stock)" for r in rows]
            return "\n".join(out)
    return None



# ==================================================================
#  PRO FEATURES
# ==================================================================
ALLERGY_RULES = [
    (('penicillin', 'amoxicillin', 'augmentin'), ('amoxicillin', 'augmentin', 'amoxiclav', 'penicillin')),
    (('aspirin',), ('aspirin', 'disprin')),
    (('asthma', 'ulcer', 'gastric', 'kidney', 'renal'), ('ibuprofen', 'brufen', 'naproxen', 'diclofenac', 'aspirin', 'disprin')),
    (('sulfa', 'sulpha'), ('cotrimoxazole', 'bactrim', 'sulfa')),
]

def allergy_check(history, med_names):
    """Keyword check only (not medical advice). Returns a list of warning texts."""
    text = (history or '').lower()
    if not text.strip() or not med_names:
        return []
    out = []
    for name in med_names:
        first = (name.split() or [''])[0].lower()
        if len(first) >= 4 and first in text:
            out.append(f"History mentions {first.title()}: check with the doctor before giving {name}.")
    for triggers, words in ALLERGY_RULES:
        hit = next((t for t in triggers if t in text), None)
        if not hit:
            continue
        for name in med_names:
            if any(w in name.lower() for w in words):
                out.append(f"History mentions '{hit}': {name} may not be suitable.")
    unique = []
    for w in out:
        if w not in unique:
            unique.append(w)
    return unique

def _net_sales_cost(cur, start_days, end_days):
    """Net revenue (after returns) and cost of goods still sold, for a period in days back."""
    cur.execute("""SELECT IFNULL(SUM(total_amount - returned_amount), 0) AS net_revenue FROM sales
                   WHERE DATE(sale_date) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)""",
                (start_days, end_days))
    revenue = float(cur.fetchone()['net_revenue'] or 0)
    cur.execute("""SELECT si.quantity, si.unit_price,
                          IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri WHERE ri.sale_item_id = si.sale_item_id), 0) AS returned_qty,
                          COALESCE(b.purchase_price, m.cost_price, 0) AS unit_cost
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   JOIN medicines m ON si.medicine_id = m.medicine_id
                   LEFT JOIN batches b ON si.batch_id = b.batch_id
                   WHERE DATE(s.sale_date) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)""",
                (start_days, end_days))
    cost = 0.0
    for r in cur.fetchall():
        net = int(r['quantity']) - int(r['returned_qty'])
        if net > 0:
            cost += net * float(r['unit_cost'] or 0)
    return revenue, cost

def _profit_summary(cur, label, s, e):
    revenue, cost = _net_sales_cost(cur, s, e)
    profit = revenue - cost
    margin = (profit / revenue * 100) if revenue else 0.0
    return (f"**Profit ({label})**\\n"
            f"• Net sales: {money(revenue)}\\n"
            f"• Cost of goods sold: {money(cost)}\\n"
            f"• Profit: {money(profit)} (margin {margin:.1f}%)\\n"
            "• Returns are already removed. Tax, if any, is counted as profit.")

def _returns_summary(cur, label, s, e):
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(refund_amount), 0) AS v FROM sale_returns
                   WHERE DATE(created_at) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)""",
                (s, e))
    d = cur.fetchone()
    lines = [f"**Returns ({label})**",
             f"• Returns: {int(d['n'] or 0)}",
             f"• Value refunded: {money(d['v'])}"]
    if int(d['n'] or 0):
        cur.execute("""SELECT m.name, SUM(ri.quantity) AS q FROM sale_return_items ri
                       JOIN sale_returns r ON ri.return_id = r.return_id
                       JOIN medicines m ON ri.medicine_id = m.medicine_id
                       WHERE DATE(r.created_at) BETWEEN DATE_SUB(CURDATE(), INTERVAL %s DAY) AND DATE_SUB(CURDATE(), INTERVAL %s DAY)
                       GROUP BY m.name ORDER BY q DESC LIMIT 3""", (s, e))
        top = cur.fetchall()
        if top:
            lines.append("• Most returned: " + ", ".join(f"{t['name']} ({int(t['q'])})" for t in top))
    return "\\n".join(lines)

def _find_customer(cur, tokens):
    for t in tokens:
        if len(t) < 3:
            continue
        cur.execute("""SELECT customer_id, name, contact_number, medical_history FROM customers
                       WHERE LOWER(name) LIKE %s ORDER BY name LIMIT 1""", ('%' + t + '%',))
        row = cur.fetchone()
        if row:
            return row
    return None

def _customer_dues(cur, cust):
    cur.execute("""SELECT sale_id, sale_date, (total_amount - returned_amount - paid_amount) AS due_amount
                   FROM sales WHERE customer_id = %s AND (total_amount - returned_amount - paid_amount) > 0.004
                   ORDER BY sale_id ASC""", (cust['customer_id'],))
    rows = cur.fetchall()
    total = sum(float(r['due_amount']) for r in rows)
    if not rows:
        return f"**{cust['name']}** has no pending balance."
    lines = [f"**{cust['name']}: pending balance {money(total)}**"]
    for r in rows[:5]:
        lines.append(f"• Sale #{r['sale_id']} ({str(r['sale_date'])[:10]}): {money(r['due_amount'])} due")
    if len(rows) > 5:
        lines.append(f"...and {len(rows) - 5} more sale(s). Open Sales and filter 'Pending balance'.")
    return "\\n".join(lines)

def _dues_overview(cur):
    cur.execute("""SELECT c.name, SUM(s.total_amount - s.returned_amount - s.paid_amount) AS due_amount
                   FROM sales s JOIN customers c ON s.customer_id = c.customer_id
                   GROUP BY c.customer_id, c.name
                   HAVING SUM(s.total_amount - s.returned_amount - s.paid_amount) > 0.004
                   ORDER BY due_amount DESC LIMIT 10""")
    rows = cur.fetchall()
    if not rows:
        return "No customer has a pending balance. Good!"
    total = sum(float(r['due_amount']) for r in rows)
    lines = [f"**Credit (pending balances), top {len(rows)}**"]
    lines += [f"• {r['name']}: {money(r['due_amount'])}" for r in rows]
    lines.append(f"Total in this list: {money(total)}")
    return "\\n".join(lines)

def _supplier_list(cur):
    cur.execute("""SELECT s.name, s.contact,
                          (SELECT COUNT(*) FROM purchase_orders po WHERE po.supplier_id = s.supplier_id) AS orders,
                          (SELECT MAX(po.order_date) FROM purchase_orders po WHERE po.supplier_id = s.supplier_id) AS last_order
                   FROM suppliers s ORDER BY s.name LIMIT 15""")
    rows = cur.fetchall()
    if not rows:
        return "No suppliers saved yet."
    lines = [f"**Suppliers ({len(rows)})**"]
    for r in rows:
        last = str(r['last_order'])[:10] if r['last_order'] else 'no orders yet'
        lines.append(f"• {r['name']} - {r['contact'] or 'no phone'} - {int(r['orders'])} order(s), last: {last}")
    return "\\n".join(lines)

def _reorder_suggestions(cur):
    cur.execute("""SELECT medicine_id, name, stock_quantity, reorder_level FROM medicines
                   WHERE stock_quantity <= reorder_level ORDER BY stock_quantity ASC, name ASC LIMIT 15""")
    low = cur.fetchall()
    if not low:
        return "All medicines are above their reorder level. Nothing needs ordering now."
    cur.execute("""SELECT si.medicine_id, SUM(si.quantity) AS q FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   WHERE s.sale_date >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)
                   GROUP BY si.medicine_id""")
    sold30 = {r['medicine_id']: int(r['q'] or 0) for r in cur.fetchall()}
    lines = ["**Reorder suggestions** (based on the last 30 days of sales)"]
    for m in low:
        stock = int(m['stock_quantity'] or 0)
        reorder = int(m['reorder_level'] or 0)
        daily = sold30.get(m['medicine_id'], 0) / 30.0
        target = max(30 * daily, 2 * reorder)
        order = max(math.ceil(target) - stock, 1)
        tag = 'OUT of stock' if stock <= 0 else f'{stock} left'
        line = f"• {m['name']}: {tag}, reorder at {reorder}. Suggested order: {order} units"
        if daily > 0 and stock > 0:
            line += f" (about {stock / daily:.0f} day(s) of stock left)"
        lines.append(line)
    lines.append("This is only a suggestion. Check with your supplier before buying.")
    return "\\n".join(lines)

def _expiry_tips(cur):
    cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity
                   FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                   WHERE b.quantity > 0 AND b.expiry_date >= CURDATE()
                     AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 60 DAY)
                   ORDER BY b.expiry_date ASC LIMIT 10""")
    rows = cur.fetchall()
    if not rows:
        return "No batch expires in the next 60 days, so no clearance offer is needed."
    today = date.today()
    lines = ["**Expiry clearance ideas** (next 60 days)"]
    for r in rows:
        d = _to_date(r['expiry_date'])
        days = (d - today).days if d else 0
        idea = ("move it to the front shelf now and consider a 20-30% offer" if days <= 30
                else "start a 10-15% offer and suggest it to regular customers")
        lines.append(f"• {r['name']} (batch {r['batch_number']}): {int(r['quantity'])} units, {days} day(s) left. {idea[0].upper() + idea[1:]}.")
    lines.append("Check your pharmacy's pricing rules before giving any discount.")
    return "\\n".join(lines)

def _allergy_report(cur, cust, med_names):
    history = (cust.get('medical_history') or '').strip()
    lines = [f"**Patient: {cust['name']}**",
             f"• Recorded history: {history or 'none recorded'}"]
    if med_names:
        lines.append("• Medicines checked: " + ", ".join(med_names))
    warnings = allergy_check(history, med_names)
    if warnings:
        lines += [f"• {w}" for w in warnings]
    elif med_names:
        lines.append("• No warning found in the recorded history.")
    lines.append("This is a simple keyword check, not medical advice. The doctor or pharmacist decides.")
    return "\\n".join(lines)


def _greeting(user):
    h = datetime.now().hour
    part = "Good morning" if h < 12 else ("Good afternoon" if h < 17 else "Good evening")
    return (f"{part} {user.get('name', '')}! I am **MediGen AI Assistant**.\n"
            "Ask me about medicine stock, prices, expiry, sales, customers and more.")


PRO_HELP = (
    "\n**More things I can do:**\n"
    "• Profit (Admin): *Today profit*, *This month profit*\n"
    "• Returns: *Returns this week*\n"
    "• Credit: *Credit list*, *Ali balance*\n"
    "• Reorder (Admin / Pharmacist): *What should I order?*\n"
    "• Suppliers: *Supplier list*\n"
    "• Allergy check: *Allergy check Ali* or *Ali allergy Amoxicillin*\n"
    "• Expiry tips: *Expiry discount ideas*"
)

HELP_TEXT = (
    "**Here is what I can do:**\n"
    "• Medicine info: *Panadol stock*, *Brufen price*, *Panadol expiry*\n"
    "• Sales: *Today sales*, *This week revenue*, *Yesterday sales*, *Latest sales*\n"
    "• Top sellers: *Top selling medicines*\n"
    "• Alerts: *Low stock*, *Out of stock*, *Expiring soon*, *Expired medicines*\n"
    "• Counts: *Total customers*, *Total medicines*, *List categories*\n"
    "• Search: *Customer Ali*, *Antibiotic medicines*\n"
    "• Guides: *How to add medicine*, *How to make a sale*\n"
    "You can also type in Roman Urdu, for example *Panadol ka stock kitna hai?*"
)


# ------------------------------------------------------------------
# Main function
# ------------------------------------------------------------------
NOT_UNDERSTOOD = "Sorry, I did not understand that."


def get_answer(cur, question, user, ctx=None):
    if ctx is None:
        ctx = {}
    question = (question or "").strip()[:300]
    if not question:
        return "Please type a question.", DEFAULT_CHIPS

    text = _norm(question)
    tokens = text.split()
    if not tokens:
        return "I could not read that. Please type your question in simple words.", DEFAULT_CHIPS

    period = _period(tokens, text)
    entity = _entity(tokens)
    rest = [t for t in tokens if t not in STOP and not t.isdigit()]

    # ---- 1. Small talk ----
    if tokens[0] in GREET and len(tokens) <= 6 and all(t in GREET or t in GENERIC_STOP or t == "how" for t in tokens):
        return _greeting(user), DEFAULT_CHIPS
    if _hit(tokens, THANKS) and len(tokens) <= 4:
        return "You are welcome! Ask me anything else about the pharmacy.", DEFAULT_CHIPS
    if _hit(tokens, BYE) and len(tokens) <= 3:
        return "Goodbye! Stay blessed.", DEFAULT_CHIPS
    if _hit(tokens, HELP) or "what can you do" in text or "kya kar" in text:
        return HELP_TEXT + PRO_HELP, DEFAULT_CHIPS
    # v90.00: "what is this software / what does this program do / software features"
    if ("software" in tokens or "program" in tokens or "features" in tokens
            or ("medigen" in tokens and "what" in tokens)) \
            and _hit(tokens, {"what", "kya", "how", "features", "kaam", "kam", "does", "about", "hai"}):
        return SOFTWARE_TEXT, DEFAULT_CHIPS
    if "who am i" in text or "my role" in text or "mera role" in text:
        return f"You are logged in as **{user.get('name')}** with the role **{user.get('role')}**.", DEFAULT_CHIPS
    if ("time" in tokens or "date" in tokens) and not _hit(tokens, EXPIRE - {"date"}) \
            and not _hit(tokens, SALES | STOCK | PRICE):
        now = datetime.now()
        return f"Today is **{now.strftime('%A, %d %B %Y')}** and the time is **{now.strftime('%I:%M %p')}**.", DEFAULT_CHIPS

    # ---- 2. How-to guides ----
    # v90.00: the old gate needed the exact words "how to", so natural questions
    # like "How do I take a backup?" got "did not understand". Now a guide also
    # matches when its keywords are all present and the question is not clearly
    # a data question (a period, or sales/stock/price words). Longer (more
    # specific) guides are tried first.
    _how_gate = ("how" in tokens and "to" in tokens) or bool(_hit(tokens, HOWW - {"how"}))
    _data_block = bool(period) or bool(_hit(tokens, SALES | STOCK | PRICE))
    # single-word guides on data topics (udhaar list, expiry discount ideas...)
    # must not hijack the data answers - they need the how-gate like before
    _GUIDE_AMBIGUOUS = {"udhaar", "return", "discount", "expiry", "purchase"}
    if _how_gate or not _data_block:
        for needed, guide in sorted(GUIDES, key=lambda g: -len(g[0])):
            if not _how_gate and len(needed) == 1 and next(iter(needed)) in _GUIDE_AMBIGUOUS:
                continue
            if needed.issubset(set(tokens)) or all(any(n in t for t in tokens) for n in needed):
                return guide, DEFAULT_CHIPS

    # ---- 2c. Medicine knowledge (v90.00): "what is X used for / X kis liye hai /
    # side effects of X" - answered from the built-in knowledge base, even for
    # medicines the shop does not stock. A shop stock line is added when the
    # shop sells it. Plain stock/price questions keep the old behaviour. ----
    if _MK is not None:
        _kb = _MK.find_medicine(question)
        if _kb is not None:
            _strong = any(p in text for p in _KNOW_PHRASES if p not in ("what is", "kya hai", "about")) \
                or bool(_hit(tokens, _KNOW_TOKENS - {"about"}))
            _weak = any(p in text for p in ("what is", "kya hai")) or "about" in tokens
            _data_intent = bool(_hit(tokens, PRICE | STOCK | EXPIRE | SALES))
            _know_intent = _strong or (_weak and not _data_intent)
            # brand-aware shop match: the shop may sell it under a brand or generic name
            _aliases = {_MK._n(_kb["name"]).strip()} | {_MK._n(b).strip() for b in (_kb.get("brands") or [])}
            _shop_meds = _all_medicines(cur)
            _shop_hit = [m for m in _shop_meds if _MK._n(m.get("name") or "").strip() in _aliases] \
                or _find_medicines(tokens, text, _shop_meds)
            if _know_intent or (not _shop_hit and not _data_intent):
                if _shop_hit:
                    _m0 = _shop_hit[0]
                    _shop_line = (f"**In your shop:** {_m0['name']} - stock "
                                  f"{_m0.get('stock_quantity')} units, price Rs. {money(_m0.get('price'))} per unit.")
                else:
                    _shop_line = "_This medicine is not in your shop catalog right now._"
                return _MK.format_answer(_kb, _shop_line), \
                    [f"{_kb['name']} stock", "Low stock", "Today sales"]

    # ---- 2b. Allergy check (before medicine detection, so "Ali allergy Amoxicillin" works) ----
    if _hit(tokens, ALLERGY_W):
        rest_c = [t for t in tokens if t not in STOP and t not in ALLERGY_W and not t.isdigit()]
        cust = _find_customer(cur, rest_c)
        if not cust:
            return "Please write the patient name, for example: *allergy check Ali*.", DEFAULT_CHIPS
        found_meds = _find_medicines(tokens, text, _all_medicines(cur))
        return _allergy_report(cur, cust, [m['name'] for m in found_meds]), ["Total customers", "Low stock"]

    # ---- 3. A medicine is mentioned ----
    meds = _all_medicines(cur)
    found = _find_medicines(tokens, text, meds)
    if not found and not period and _hit(tokens, PRONOUN) and ctx.get("last_med_id"):
        found = [m for m in meds if m["medicine_id"] == ctx["last_med_id"]]

    if found:
        if _hit(tokens, PRICE):
            focus = "price"
        elif _hit(tokens, EXPIRE - {"date"}):
            focus = "expiry"
        elif _hit(tokens, {"sold", "sale", "sales", "sell", "selling", "bikri", "bechi"}):
            focus = "sold"
        else:
            focus = "info"
        ctx["last_med_id"] = found[0]["medicine_id"]
        ctx["last_med_name"] = found[0]["name"]
        cards = [_medicine_card(cur, m, focus) for m in found]
        name = found[0]["name"]
        chips = [f"{name} price", f"{name} expiry", f"{name} sold", "Low stock"]
        if focus == "price":
            chips = [f"{name} stock", f"{name} expiry", "Top selling"]
        elif focus == "expiry":
            chips = [f"{name} stock", f"{name} price", "Expiring soon"]
        return "\n\n".join(cards), chips

    # ---- 4a. Pro features ----
    if _hit(tokens, PROFIT_W):
        if user.get('role') != 'Admin':
            return "Sorry, profit information is only available for Admin.", DEFAULT_CHIPS
        label, s, e = period or ("last 30 days", 29, 0)
        return _profit_summary(cur, label, s, e), ["Today profit", "This month profit", "Reorder suggestions"]

    if _hit(tokens, RETURN_W):
        label, s, e = period or ("last 30 days", 29, 0)
        return _returns_summary(cur, label, s, e), ["Today sales", "Top selling"]

    if _hit(tokens, DUES_W):
        rest_d = [t for t in tokens if t not in STOP and t not in DUES_W and not t.isdigit()]
        cust = _find_customer(cur, rest_d) if rest_d else None
        if cust:
            return _customer_dues(cur, cust), ["Credit list", "Total customers"]
        return _dues_overview(cur), ["Total customers", "Today sales"]

    if _hit(tokens, SUPPLIER_W):
        if user.get('role') not in ('Admin', 'Pharmacist'):
            return "Sorry, supplier information is only available for Admin and Pharmacist.", DEFAULT_CHIPS
        return _supplier_list(cur), ["Reorder suggestions", "Low stock"]

    if _hit(tokens, REORDER_W) and not _hit(tokens, PRICE):
        if user.get('role') not in ('Admin', 'Pharmacist'):
            return "Sorry, reorder suggestions are only available for Admin and Pharmacist.", DEFAULT_CHIPS
        return _reorder_suggestions(cur), ["Out of stock", "Expiring soon", "Stock overview"]

    if _hit(tokens, DISCOUNT_W) and (_hit(tokens, EXPIRE - {"date"}) or _hit(tokens, {"clearance", "shelf"})):
        return _expiry_tips(cur), ["Expiring soon", "Expired medicines", "Low stock"]

    if "help more" in text or "more options" in text or "pro help" in text:
        return PRO_HELP, DEFAULT_CHIPS

    # ---- 4. Alerts ----
    if "out of stock" in text or "outofstock" in text or "zero stock" in text or "stock khatam" in text:
        return _out_of_stock(cur), ["Low stock", "Expiring soon", "Stock overview"]

    if _hit(tokens, EXPIRE - {"date"}):
        if "expired" in tokens or "expire ho gayi" in text:
            return _expired(cur), ["Expiring soon", "Low stock"]
        m = re.search(r"(\d{1,3})\s*(day|days|din)", text)
        days = int(m.group(1)) if m else 90
        return _expiring(cur, days), ["Expired medicines", "Low stock", "Top selling"]

    if (_hit(tokens, LOW) and (_hit(tokens, STOCK) or entity == "medicine" or "reorder" in tokens or "kam" in tokens)) \
            or "running out" in text or "reorder" in tokens or "shortage" in tokens:
        return _low_stock(cur), ["Out of stock", "Expiring soon", "Stock overview"]

    # ---- 5. Sales and revenue ----
    if _hit(tokens, TOP) and (_hit(tokens, SALES) or entity == "medicine" or "selling" in tokens):
        return _top_selling(cur, period), ["Today sales", "This week revenue", "Low stock"]

    if _hit(tokens, RECENT) and _hit(tokens, SALES):
        return _recent_sales(cur), ["Today sales", "Top selling"]

    if _hit(tokens, SALES) or (period and _hit(tokens, {"revenue", "income", "earning", "kamai"})):
        return _sales_summary(cur, *(period or ("today", 0, 0))), \
            ["Yesterday sales", "This week revenue", "This month revenue", "Top selling"]

    # ---- 6. Stock overview / inventory ----
    if ("value" in tokens or "worth" in tokens) and _hit(tokens, STOCK | {"medicine", "medicines"}):
        if user.get("role") != "Admin":
            return "Sorry, stock value is only available for Admin.", DEFAULT_CHIPS
        return _inventory_value(cur), ["Stock overview", "Low stock"]

    if _hit(tokens, STOCK) and entity in (None, "medicine"):
        return _inventory_overview(cur), ["Low stock", "Out of stock", "Expiring soon"]

    # ---- 7. Medicines of a category, counts, lists and lookups ----
    if not _hit(tokens, COUNTW) and entity in (None, "medicine", "category"):
        res = _medicines_in_category(cur, text, tokens)
        if res:
            return res, ["Low stock", "Top selling"]
    if entity == "customer" and rest and not _hit(tokens, COUNTW) and not _hit(tokens, LISTW):
        res = _customer_lookup(cur, rest)
        if res:
            return res, ["Total customers", "Today sales"]
    if entity == "supplier" and user.get("role") not in ("Admin", "Pharmacist"):
        return "Sorry, supplier information is only available for Admin and Pharmacist.", DEFAULT_CHIPS
    if entity:
        return _count(cur, entity, tokens, user), ["Total customers", "Total medicines", "Today sales"]

    # ---- 9. Not understood: try to suggest a medicine ----
    names = [m["name"] for m in meds]
    lower_map = {n.lower(): n for n in names}
    for t in rest:
        close = difflib.get_close_matches(t, list(lower_map.keys()), n=2, cutoff=0.6)
        if close:
            pick = lower_map[close[0]]
            return (f"I could not find that exactly. Did you mean **{pick}**?\n"
                    f"Try: *{pick} stock* or *{pick} price*."), [f"{pick} stock", f"{pick} price", "Help"]

    return (NOT_UNDERSTOOD + "\n"
            "Try: *Panadol stock*, *Today sales*, *Low stock*, *What is Augmentin used for?*, "
            "*How do I take a backup?* or type **help**."), DEFAULT_CHIPS
