import com.medigen.aipro.ServerAddress;

/** Plain-Java test for ServerAddress. No JUnit, no Android SDK needed:
 *  javac -d out app/src/com/medigen/aipro/ServerAddress.java tests/ServerAddressTest.java
 *  java -cp out ServerAddressTest
 */
public class ServerAddressTest {
    static int passed = 0, failed = 0;

    static void eq(String input, String expected) {
        String got = ServerAddress.normalize(input);
        if (expected == null ? got == null : expected.equals(got)) {
            passed++;
        } else {
            failed++;
            System.out.println("FAIL normalize(" + input + ") = " + got + ", expected " + expected);
        }
    }

    public static void main(String[] args) {
        eq("192.168.1.100", "http://192.168.1.100:5000");
        eq("192.168.1.100:5000", "http://192.168.1.100:5000");
        eq("http://192.168.0.25:5000", "http://192.168.0.25:5000");
        eq("http://192.168.0.25:5000/", "http://192.168.0.25:5000");
        eq("10.0.0.5", "http://10.0.0.5:5000");
        eq("172.16.3.4:8080", "http://172.16.3.4:8080");
        eq("172.31.255.255", "http://172.31.255.255:5000");
        eq("localhost", "http://localhost:5000");
        eq("127.0.0.1:5000", "http://127.0.0.1:5000");
        eq("  192.168.1.100  ", "http://192.168.1.100:5000");
        eq("8.8.8.8", null);                    // public IP: not a shop PC
        eq("172.32.0.1", null);                 // just outside 172.16/12
        eq("example.com", null);                // hostnames are not accepted
        eq("192.168.1.999", null);              // bad octet
        eq("192.168.1.1:0", null);              // bad port
        eq("192.168.1.1:abc", null);
        eq("", null);
        eq(null, null);
        eq("http://user@192.168.1.1", null);    // no credentials in the address
        System.out.println("ServerAddressTest: " + passed + " passed, " + failed + " failed");
        if (failed > 0) System.exit(1);
    }
}
