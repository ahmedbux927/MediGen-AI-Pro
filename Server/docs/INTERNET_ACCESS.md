# Use MediGen from the internet (mobile data, other WiFi)

The server stays on your laptop. A "tunnel" gives it a secure https address that works from anywhere.
The laptop must be on, the server must be running, and the internet must be on at the laptop.

## Option 1: quick test (5 minutes, easiest)

1. Install the tunnel program once. Open PowerShell and run:
       winget install --id Cloudflare.cloudflared
   Close PowerShell.
2. Make sure the MediGen server is running.
3. Double click `scripts\start_internet.bat`.
4. Wait a few seconds. Find the line with `https://` and ending in `trycloudflare.com`. Copy it.
5. On the phone, open MediGen (or any browser) and type that address. Test it on mobile data (WiFi off).

Limits (important):
- The address changes every time the tunnel starts. The phone app must be updated with the new address.
- The tunnel is for testing. It is not a promise of uptime, and Cloudflare does not recommend it for real customer data.
- Closing the window stops the link.

## Option 2: stable address for daily use (about 30 minutes, needs a domain)

This keeps the same address every day and runs the tunnel as a Windows service, so it starts with the laptop.
You need: a free Cloudflare account, and a domain name (for example from a domain seller; about a few dollars a year).
Ask for these steps when you are ready, and we will go through them one by one.

## Security checklist (do this before using the internet link)

- Use strong passwords for every user. The login locks after 5 wrong tries.
- Remove or disable users you do not need.
- Keep the .env file private. Never share the tunnel address in public.
- For internet use, set `HTTPS_ONLY=1` in `.env` and restart the server. Then login cookies are sent only over https.
  Note: with `HTTPS_ONLY=1`, the plain http WiFi address stops working for login. Use the https address on all devices.
- Turn on the phone screen lock (the MediGen app asks for it).
