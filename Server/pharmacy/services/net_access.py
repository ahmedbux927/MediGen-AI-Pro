"""Which network may open the app (v79). No Flask.

ALLOWED_NETWORKS in .env is a comma list, for example:
    ALLOWED_NETWORKS=192.168.0.0/16,100.64.0.0/10
- 192.168.0.0/16  = the shop WiFi / LAN
- 100.64.0.0/10   = Tailscale VPN addresses (owner's phone or laptop, from anywhere)
Empty = no limit (the old behaviour). This PC (127.0.0.1) is always allowed.
Only the connecting address counts. Do not put a proxy in front of the app unless you also set it up.
"""
import ipaddress


def parse_networks(text):
    """Returns (networks, problems). Bad entries are reported, not silently used."""
    nets, problems = [], []
    for part in (text or '').split(','):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            problems.append(part)
    return nets, problems


def is_allowed(ip_text, networks):
    """True when no list is set, when the address is this PC, or when it is inside a listed network."""
    if not networks:
        return True
    try:
        ip = ipaddress.ip_address((ip_text or '').strip())
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    return any(ip in n for n in networks)
