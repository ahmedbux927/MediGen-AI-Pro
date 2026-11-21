"""Importing this package registers every URL of the app."""
from . import auth  # noqa: F401
from . import dashboard  # noqa: F401
from . import medicines  # noqa: F401
from . import batches  # noqa: F401
from . import catalog  # noqa: F401
from . import sales  # noqa: F401
from . import purchase  # noqa: F401
from . import prescriptions  # noqa: F401
from . import reports  # noqa: F401
from . import users  # noqa: F401
from . import chatbot  # noqa: F401
from . import agent  # noqa: F401  (v72: agent confirm)
from . import customer_search  # noqa: F401  (v73: POS phone quick-pick)
from . import rx_scan  # noqa: F401  (v76: prescription photo intake)
from . import drip  # noqa: F401  (v77: drip and injection record)
from . import products  # noqa: F401  (v86: product sections and cart)
from . import profile  # noqa: F401
from . import records  # noqa: F401
from . import settings  # noqa: F401
from . import digest  # noqa: F401  (v96: daily digest)
from . import refills  # noqa: F401  (v97: refill reminders)
from . import clearance  # noqa: F401  (v97: expiry clearance)
from . import business  # noqa: F401
from . import errors  # noqa: F401
from . import supplier_returns  # noqa: F401
from . import api  # noqa: F401
from . import pwa  # noqa: F401
from . import pos_api  # noqa: F401  (v54: POS checkout API)
from . import sync_api  # noqa: F401  (v88.00: API token login + server info; phone snapshot removed)
from . import sync_conflicts  # noqa: F401  (v88.00: kept - admin data-quality page for short-sale conflicts, linked from Data Quality)
from . import purchase_suggest  # noqa: F401  (v86.24: purchase suggestions)
from . import data_quality  # noqa: F401  (v86.46: data quality report)
from . import supplier_ledger  # noqa: F401  (v86.47: supplier summary)
from . import stock_count  # noqa: F401  (v87.00: stock count screen)
from . import cold_chain  # noqa: F401  (v87.01: cold chain log screen)
from . import controlled_register  # noqa: F401  (v87.02: controlled drug register viewer)
from . import inspection_report  # noqa: F401  (Stage 3: inspection report Excel)
from . import margins  # noqa: F401  (v87.04: profit margin per item)
from . import purchase_drafts  # noqa: F401  (v87.05: purchase drafts from suggestions)
from . import interactions  # noqa: F401  (v87.07: drug interaction pairs, warnings only)
from . import purchase_forecast  # noqa: F401  (v87.12: seasonal purchase forecast, rules only)
from . import activity_log  # noqa: F401  (v86.49: activity log filter)
from . import cash_drawer  # noqa: F401  (v86.60: cash drawer)
from . import expenses  # noqa: F401  (v86.61: shop expenses)
from . import hubs  # noqa: F401  (v87.16: group hub pages behind the sidebar)
