package com.medigen.aipro;

/** Validates and normalises the shop server address typed by the user.
 *
 * LAN only, on purpose: the MediGen server runs on the shop PC, so the app
 * accepts localhost and private IPv4 ranges (10.x, 172.16-31.x, 192.168.x)
 * and nothing else - a public address can never be a shop PC on the local
 * Wi-Fi, and accepting one would send the login page to a stranger's server.
 *
 * Pure Java (no Android classes) so it can be unit tested on any JDK:
 * see android/tests/ServerAddressTest.java.
 */
public final class ServerAddress {
    public static final int DEFAULT_PORT = 5000;

    private ServerAddress() {}

    /** True when host is localhost or a private (LAN) IPv4 address. */
    public static boolean isLanHost(String host) {
        if (host == null) return false;
        String h = host.trim().toLowerCase();
        if (h.equals("localhost") || h.equals("127.0.0.1")) return true;
        String[] parts = h.split("\\.");
        if (parts.length != 4) return false;
        int[] n = new int[4];
        for (int i = 0; i < 4; i++) {
            try {
                n[i] = Integer.parseInt(parts[i]);
            } catch (NumberFormatException e) {
                return false;
            }
            if (n[i] < 0 || n[i] > 255) return false;
        }
        if (n[0] == 10) return true;                                   // 10.0.0.0/8
        if (n[0] == 172 && n[1] >= 16 && n[1] <= 31) return true;      // 172.16.0.0/12
        return n[0] == 192 && n[1] == 168;                             // 192.168.0.0/16
    }

    /** Returns the normalised base URL ("http://192.168.1.100:5000"), or
     *  null when the input is not a valid LAN server address. */
    public static String normalize(String raw) {
        if (raw == null) return null;
        String s = raw.trim();
        if (s.isEmpty()) return null;
        String scheme = "http";
        if (s.startsWith("https://")) { scheme = "https"; s = s.substring(8); }
        else if (s.startsWith("http://")) { s = s.substring(7); }
        int slash = s.indexOf('/');
        if (slash >= 0) s = s.substring(0, slash);          // no paths, no trailing slash needed
        if (s.isEmpty() || s.contains("@") || s.contains(" ")) return null;
        String host = s;
        int port = DEFAULT_PORT;
        int colon = s.lastIndexOf(':');
        if (colon >= 0) {
            host = s.substring(0, colon);
            try {
                port = Integer.parseInt(s.substring(colon + 1));
            } catch (NumberFormatException e) {
                return null;
            }
            if (port < 1 || port > 65535) return null;
        }
        if (!isLanHost(host)) return null;
        return scheme + "://" + host.toLowerCase() + ":" + port;
    }
}
