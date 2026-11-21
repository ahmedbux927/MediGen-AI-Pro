"""v93.00: signature glassy layer, graphite sidebar, import rates fix. Base checks from v92 kept.
Source-level checks (mock suite, no MySQL)."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

passed = failed = 0
def ok(cond, label):
    global passed, failed
    if cond:
        passed += 1
        print('PASS', label)
    else:
        failed += 1
        print('FAIL:', label)

def read(rel):
    return open(os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

from config import Config
ok(Config.APP_VERSION == '101.03', 'version is 100.00 (one source)')

# ---- theme: corrected pairs, not one-sided overrides ----
base = read('templates/base.html'); login = read('templates/login.html')
ok('css/app.css' in base and '===== v92-theme.css =====' in read('static/css/app.css') and 'v92-theme.css' in login, 'v92 theme loaded on app pages (bundle) and login')
css = read('static/css/v92-theme.css')
ok('.sidebar-brand h4' in css and '#ffffff !important' in css, 'sidebar brand text forced white on the dark rail')
ok('page-heading{ display: block !important' in css.replace('  ', ' ') or 'page-heading' in css and 'display: block !important' in css,
   'light-mode page title restored (old shell hid it)')
ok('.dash .d-greet{ color: #ffffff !important' in css, 'welcome greeting white on the deep banner')
ok('.dash .d-welcome .d-chip' in css and 'rgba(255,255,255,.13)' in css, 'welcome chips are dark-glass with white text')
ok('d-welcome *' not in css, 'the harmful v90 blanket white-text rule is gone')

# ---- AI keys: settings storage + ai_client resolution ----
lib = read('pharmacy/lib.py')
ok("'gemini_api_key': ''" in lib and 'claude_api_key' not in lib and 'openai_api_key' not in lib, 'AI keys exist in setting defaults (Gemini only)')
ai = read('pharmacy/ai_client.py')
ok("def _gemini_key" in ai and "_settings_key('gemini_api_key')" in ai, 'ai_client reads keys from Settings first')
ok('def ai_status' in ai, 'ai_client exposes ai_status for the chat header')
ok(ai.count('Config.GEMINI_API_KEY') == 1 and 'OPENAI_API_KEY' not in ai,
   'env keys are only referenced inside _gemini_key')
st = read('pharmacy/routes/settings.py')
ok('gemini_api_key' in st and 'clear_' in st, 'settings route saves and clears AI keys')
ok("'api_key' not in k" in st, 'settings audit snapshot strips key values')
tpl = read('templates/settings.html')
ok('pane-ai' in tpl and 'data-tab="ai"' in tpl, 'settings page has the AI Assistant tab')
ok('ai_keys[field].mask' in tpl, 'settings page shows only a masked key hint')
ok('s.gemini_api_key' not in tpl and 's.claude_api_key' not in tpl and 's.openai_api_key' not in tpl,
   'settings page never renders a key value')

# ---- chatbot UI: Gemini-style, same JS contract ----
chat = read('templates/chatbot.html')
for el in ('id="chatBody"', 'id="chatForm"', 'id="questionInput"', 'id="micBtn"', 'id="sendBtn"', 'id="chips"'):
    ok(el in chat, f'chat keeps {el}')
ok('sug-card' in chat and 'chat-hero' in chat, 'chat has the welcome hero and suggestion cards')
ok("'.chip, .try, .sug-card'" in chat, 'suggestion cards send their question on click')
ok('data-theme="dark"] .chat-shell' in chat, 'chat supports dark mode')
ok('ai_online' in chat and 'ai_provider' in chat, 'chat header shows the AI connection status')
cb = read('pharmacy/routes/chatbot.py')
ok('ai_status' in cb, 'chat route passes the AI status to the page')

# ---- sale -> invoice traps fixed ----
sale_tpl = read('templates/new_sale.html')
ok('id="tenderVal"' in sale_tpl and 'id="tChange"' in sale_tpl, 'sale page has the cash-given + change calculator')
ok('Math.min(t, LAST_TOTAL)' in sale_tpl, 'cash given fills the paid amount capped at the bill total')
ok('drawer_open' in sale_tpl and 'cash drawer is' in sale_tpl, 'sale page warns up-front when the drawer is closed')
sales_py = read('pharmacy/routes/sales.py')
ok('drawer_open = CDR.open_session(cur) is not None' in sales_py, 'sale route passes the drawer state to the page')

# ---- v92: navy palette, top-bar squeeze, owner-KPI dark vars, AI diagnostics ----
ok('#0b1737' in css and '#1d4ed8' in css, 'brand palette is navy/sapphire (no green brand colour)')
ok('047857' not in css and '0d9488' not in css, 'old emerald brand colours are gone from the theme')
ok('.top-bar .page-heading h3{ white-space: nowrap' in css.replace('  ', ' ') or 'white-space: nowrap; overflow: hidden; text-overflow: ellipsis' in css,
   'top-bar heading can no longer be crushed by the user badge')
ok('html[data-theme="dark"] .dv{' in css.replace('  ', ' ') or 'html[data-theme="dark"] .dv' in css, 'dark mode redefines the dashboard dv variables')
ok('--ink: #e8eef7' in css, 'dark dv ink is light (owner KPI text readable)')
ok('def friendly_reason' in ai and 'def test_provider' in ai, 'ai_client can explain and live-test provider failures')
ok('settings_ai_test' in st and '/settings/ai/test' in st, 'settings has the AI test-connection route')
ok('testAiKey' in tpl and 'Test connection' in tpl, 'settings AI tab has Test connection buttons')
ok('did not answer' in lib and 'friendly_reason(_why)' in lib, 'chat explains why the online AI stayed silent')

# ---- v92 full-section audit fixes (screenshot-verified) ----
ok('html[data-theme="dark"] .bt-card .val' in css, 'dark mode: batch stat values readable')
ok('html[data-theme="dark"] .rstat .val' in css and 'html[data-theme="dark"] .report-tabs' in css,
   'dark mode: report values and tab bar paired')
ok('html[data-theme="dark"] .rxp-stat' in css and 'html[data-theme="dark"] .rxp-card' in css,
   'dark mode: prescription cards paired')
ok('html[data-theme="dark"] .ai-insights-card' in css and 'html[data-theme="dark"] .form-section' in css,
   'dark mode: profile cards paired')
ok('.col-md-3{' in css.replace(' ', '') or '.col-md-3' in css, 'grid shim restores the intended multi-column layout')
ok('.pf-tab.on{ background: var(--mg-grad)' in css.replace('  ', ' '), 'settings active tab uses the brand gradient')

# ---- screenshot-verified dark-mode pairs ----
ok('html[data-theme="dark"] .dv-action' in css, 'dark mode: dashboard quick actions readable')
ok('html[data-theme="dark"] .pf-card' in css and 'html[data-theme="dark"] .pf-input' in css,
   'dark mode: settings cards and inputs paired')
ok("replace(/_([^_]+)_/g, '<em>$1</em>')" in chat, 'chat renders _italic_ notes as italics')

# ---- v93.00: signature layer, graphite sidebar, bundled fonts, palette ----
ok('css/app.css' in base and '===== v100-theme.css =====' in read('static/css/app.css') and 'v100-theme.css' in login, 'v100 Nexus layer loaded on app pages (bundle) and login')
ok('fonts/fonts.css' in base, 'bundled local fonts stylesheet loaded (offline fonts)')
for w in ('Inter-400', 'Inter-600', 'Inter-700', 'PlusJakartaSans-700', 'PlusJakartaSans-800'):
    ok(os.path.exists(os.path.join(ROOT, 'static', 'fonts', w + '.woff2')), 'font file bundled: ' + w)
css93 = read('static/css/v100-theme.css')
ok('#0a1a2f' in css93 and '#14b8a6' in css93, 'sidebar Nexus navy + teal (owner ke bheje hue design par)')
ok('mg-pal-backdrop' in base and 'mgPalInput' in base, 'Ctrl+K command palette present in base')
ok('sales_hub' in base and 'finance_hub' in base, 'palette uses the real endpoint names')
ok('NEXUS LIGHT SYSTEM' in css93 and '#edf1f6' in css93, 'Nexus light system: halka canvas, safed cards')
ok('linear-gradient(135deg,#0d9488 0%,#0f766e 100%)' in css93, 'brand gradient Nexus teal')
ok('Welcome banner: LIGHT mode me halki patti' in css93, 'welcome banner light mode me halki hai (owner: black na karo)')
ok('live-bar' in css93 and 'pick-card' in css93, 'POS signature styles present (bill bar, product cards)')

# ---- v93.00: import lists carry rates (owner: stock + rates + category) ----
from pharmacy.services import product_sections as PS
_items, _errs, _warns = PS.parse_products_report(
    b"name,dosage_form,price,cost_price,stock\nTest Syrup,Syrup,180,140,25\nRate Syrup,Syrup,,,10\n", 'syrups')
ok(not _errs and len(_items) == 2, 'section CSV parses two rows')
ok(_items and _items[0].get('price') == 180.0 and _items[0].get('cost_price') == 140.0,
   'import reads the price and cost columns (pehle rate hamesha 0 aata tha)')
ok(_items and _items[0].get('qty') == 25, 'import reads the stock column')
_items2, _e2, _w2 = PS.parse_products_report(b"name,rate,stock\nLegacy Syrup,150,7\n", 'syrups')
ok(_items2 and _items2[0].get('price') == 150.0, "import also accepts a 'rate' column")
_recs = PS._table_records([['Name', 'Price', 'Stock'], ['Pdf Cream', '220', '15']], True)
ok(_recs and str(_recs[0].get('price')) == '220', 'PDF table conversion keeps the Price column')
ok('price' in PS.STD_COLS and 'cost_price' in PS.STD_COLS, 'PDF->CSV schema includes rates')




# ---- v94.00: wallets, WhatsApp share, QR, asal backup button ----
lib_s = read('pharmacy/lib.py')
ok("'JazzCash'" in lib_s and "'Easypaisa'" in lib_s and 'PAY_METHODS' in lib_s, 'JazzCash + Easypaisa payment methods')
ns = read('templates/new_sale.html')
ok('<option>JazzCash</option>' in ns and '<option>Easypaisa</option>' in ns, 'POS par wallet options')
th = read('templates/receipt_thermal.html'); iv = read('templates/invoice.html')
ok('wa.me' in th and 'wa.me' in iv, 'WhatsApp share dono invoice pages par')
ok('mg-tick' in th and 'Sale completed' in th, 'thermal par success tick animation')
ok('qrcode.min.js' in th and 'qrBox' in th, 'thermal par QR code')
ok(os.path.exists(os.path.join(ROOT, 'static', 'js', 'qrcode.min.js')), 'QR library bundled (offline)')
st_r = read('pharmacy/routes/settings.py')
ok('settings_backup_now' in st_r and 'backup_db.py' in st_r, 'settings me asal backup route (mysqldump, fake nahi)')
sth = read('templates/settings.html')
ok('settings_backup_now' in sth, 'settings Security tab me Backup card')
core_s = read('pharmacy/core.py')
ok("ENUM('Cash','Card','Online','JazzCash','Easypaisa')" in core_s, 'purane DB ki payment_method ENUM startup par widen hoti hai')
sch = read('database/schema.sql')
ok("enum('Cash','Card','Online','JazzCash','Easypaisa')" in sch, 'fresh install schema me wallets shamil')

ok('nav-btn' in th and "url_for('new_sale')" in th and "url_for('dashboard')" in th, 'thermal receipt par Back (New Sale) + Dashboard buttons — app band kiye baghair wapas')
# --- v100: Daily Digest + backup status ---
lib = read('pharmacy/lib.py')
ok('def backup_status' in lib, 'lib me backup_status helper')
ok(os.path.exists(os.path.join(ROOT, 'pharmacy', 'routes', 'digest.py')), 'digest route module mojood')
dg = read('pharmacy/routes/digest.py')
ok("'/digest'" in dg and "role_required('Admin')" in dg, 'digest sirf Admin ke liye')
ok('customers_with_dues' in dg and 'v_low_stock' in dg and 'backup_status' in dg, 'digest: udhaar + low stock + backup haalat')
ok('wa.me' in dg or 'wa_text' in dg, 'digest WhatsApp text tayyar hota hai')
dgt = read('templates/digest.html')
ok('Daily Digest' in dgt and 'Reminder' in dgt, 'digest template: khulasa + per-customer reminder')
ok('owner_whatsapp' in read('pharmacy/routes/settings.py') and 'owner_whatsapp' in sth, 'owner WhatsApp number Settings me save hota hai')
ok('backup.when' in sth or 'Aakhri backup' in sth, 'settings Backup card me aakhri backup ki haalat')
ri = read('pharmacy/routes/__init__.py')
ok('import digest' in ri, 'digest route registered')

# --- v100: refills + clearance + restore test ---
ok(os.path.exists(os.path.join(ROOT, 'pharmacy', 'services', 'refills.py')), 'refill service mojood')
rf = read('pharmacy/services/refills.py')
ok('def due_refills' in rf and 'avg_gap' in rf, 'refill due hisaab kharidari ke waqfay par')
rfr = read('pharmacy/routes/refills.py')
ok("'/refills'" in rfr, 'refills route')
rft = read('templates/refills.html')
ok('Reminder bhejen' in rft and 'wa.me' in rft, 'refill WhatsApp reminder button')
clr = read('pharmacy/routes/clearance.py')
ok("'/expiry-clearance'" in clr and '_suggestion' in clr, 'expiry clearance route + tajweez')
clt = read('templates/clearance.html')
ok('Expiry Clearance' in clt and 'phansi hui rakam' in clt, 'clearance template value-at-risk ke sath')
ok(os.path.exists(os.path.join(ROOT, 'scripts', 'restore_test.py')), 'restore_test.py script mojood')
rts = read('scripts/restore_test.py')
ok('medigen_restore_test' in rts and 'RESTORE TEST OK' in rts, 'restore test alag throwaway DB use karta hai')
ok('settings_restore_test' in st_r and 'restore_test.py' in st_r, 'settings me restore test route')
ok('settings_restore_test' in sth, 'settings Security tab me restore test button')
ok('due_refills' in read('pharmacy/routes/digest.py'), 'digest me refill strip')

# --- v100: security wrap + portal removal + logo ---
ok(not os.path.exists(os.path.join(ROOT, 'pharmacy', 'routes', 'customer_portal.py')), 'customer portal route hata diya (public surface kam)')
ok(not os.path.exists(os.path.join(ROOT, 'templates', 'portal_login.html')), 'portal templates bhi hata diye')
ri = read('pharmacy/routes/__init__.py')
ok('customer_portal' not in ri, 'portal registration bhi nahi')
ok(not os.path.exists(os.path.join(ROOT, 'pharmacy', 'routes', 'license.py')), 'v100: license system mukammal removed (owner decision)')
ok(not os.path.exists(os.path.join(ROOT, 'pharmacy', 'services', 'license.py')), 'v100: license service bhi removed')
aic = read('pharmacy/ai_client.py').lower().replace('licensed', '')
ok('openai' not in aic and 'anthropic' not in aic and 'api.anthropic' not in aic, 'v100: AI sirf Gemini (OpenAI/Claude code removed)')
cfg = read('config.py')
ok('OPENAI' not in cfg and 'CLAUDE_API' not in cfg, 'v100: config me bhi sirf Gemini settings')
ok(os.path.exists(os.path.join(ROOT, 'archive', 'routes', 'owner_home.py')), 'v100: owner_home archive me mehfooz (delete nahi)')
ok(os.path.exists(os.path.join(ROOT, 'archive', 'routes', 'branches.py')), 'v100: branches archive me mehfooz')
ok(os.path.exists(os.path.join(ROOT, 'START_MEDIGEN.bat')) and not os.path.exists(os.path.join(ROOT, 'START_DESKTOP.bat')), 'v100: sirf ek start file START_MEDIGEN.bat')
ok(os.path.exists(os.path.join(ROOT, 'android', 'app', 'AndroidManifest.xml')), 'v100: Android app source Server/android me mojood')
ok(os.path.exists(os.path.join(ROOT, 'CHANGELOG.md')), 'v100: ek hi CHANGELOG.md')
ok(os.path.exists(os.path.join(ROOT, 'static', 'logo.png')), 'naya MediGen logo static me mojood')
ok(os.path.exists(os.path.join(ROOT, 'static', 'icons', 'icon-512.png')), 'PWA icon 512 naya logo')
base = read('templates/base.html')
ok('logo.png' in base and 'favicon.png' in base, 'sidebar + favicon me naya logo')
ok('X-Frame-Options' in read('pharmacy/core.py') and 'nosniff' in read('pharmacy/core.py'), 'security headers mojood')
err = read('pharmacy/routes/errors.py')
ok('errorhandler(500)' in err or 'errorhandler(Exception)' in err, 'friendly error handlers mojood')
ok(os.path.exists(os.path.join(ROOT, 'scripts', 'restore_test.py')), 'restore test barqarar')

# ---------- v100.00: security + screenshot fixes ----------
ok('Content-Security-Policy' in read('pharmacy/core.py'), 'v100: CSP header set on responses')
ok('storage_path' in read('desktop.py'), 'v100: desktop window pins its WebView2 data folder (remember-me)')
ok('-webkit-autofill' in read('static/css/login.css'), 'v100: login autofill block removed (SS1 line)')
ok('FORM & CARD SYSTEM' in read('static/css/v100-theme.css'), 'v100: one form system for both modes in the theme')
ok('cash_opening' in read('pharmacy/routes/dashboard.py') and 'cash_opening' in read('templates/dashboard.html'), 'v100: dashboard cash card shows the drawer opening')
for vend in ('bootstrap/bootstrap.min.css', 'bootstrap/bootstrap.bundle.min.js',
             'bootstrap-icons/bootstrap-icons.css', 'chartjs/chart.umd.js'):
    ok(os.path.isfile(os.path.join(ROOT, 'static', 'vendor', *vend.split('/'))), 'v100: offline vendor file bundled: ' + vend)

print(f'done: {passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
