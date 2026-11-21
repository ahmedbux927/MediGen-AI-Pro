package com.medigen.aipro;

import android.Manifest;
import android.app.Activity;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** MediGen AI Pro — dukaan ke PC server ko phone par kholne wala saathi app.
 *  Pehli dafa server ka address (masalan http://192.168.1.100:5000) mangta hai,
 *  yaad rakh leta hai, aur phir seedha program khol deta hai. Load fail ho to
 *  address badalne ki screen khud ajati hai. */
public class MainActivity extends Activity {
    private WebView web;
    private LinearLayout setupBox;
    private EditText addrInput;
    private TextView errorText;
    private SharedPreferences prefs;
    private PermissionRequest pendingCamera;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("medigen", MODE_PRIVATE);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(10, 26, 47));

        setupBox = new LinearLayout(this);
        setupBox.setOrientation(LinearLayout.VERTICAL);
        setupBox.setPadding(48, 64, 48, 48);
        TextView title = new TextView(this);
        title.setText("MediGen AI Pro");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        setupBox.addView(title);
        TextView hint = new TextView(this);
        hint.setText("Dukaan ke PC ka address likhen (PC par program chala hona chahiye, aur phone usi Wi-Fi par ho):");
        hint.setTextColor(Color.rgb(180, 200, 220));
        hint.setPadding(0, 24, 0, 24);
        setupBox.addView(hint);
        addrInput = new EditText(this);
        addrInput.setHint("http://192.168.1.100:5000");
        addrInput.setText(prefs.getString("server", ""));
        addrInput.setSingleLine(true);
        setupBox.addView(addrInput);
        errorText = new TextView(this);
        errorText.setTextColor(Color.rgb(248, 150, 130));
        errorText.setPadding(0, 16, 0, 0);
        errorText.setVisibility(View.GONE);
        setupBox.addView(errorText);
        Button go = new Button(this);
        go.setText("Program kholen");
        go.setOnClickListener(v -> {
            String url = ServerAddress.normalize(addrInput.getText().toString());
            if (url == null) {
                showError("Address theek nahi. Dukaan ke PC ka local address likhen, masalan 192.168.1.100 (port khali chor dein to 5000).");
                return;
            }
            prefs.edit().putString("server", url).apply();
            openProgram(url);
        });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = 32;
        setupBox.addView(go, lp);
        root.addView(setupBox);

        web = new WebView(this);
        web.setVisibility(View.GONE);
        WebSettings ws = web.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        CookieManager.getInstance().setAcceptCookie(true);   // login session yaad rahe
        web.setWebViewClient(new WebViewClient() {
            @Override public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError err) {
                if (req.isForMainFrame()) {
                    showSetup();
                    showError("Server not reachable. PC par program chala hua hai? Phone usi Wi-Fi par hai? Phir dobara koshish karein.");
                }
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            // Web page ka camera barcode scan: sirf camera ki ijazat di jati hai.
            @Override public void onPermissionRequest(PermissionRequest request) {
                for (String res : request.getResources()) {
                    if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(res)) {
                        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                            request.grant(new String[]{res});
                        } else {
                            pendingCamera = request;
                            requestPermissions(new String[]{Manifest.permission.CAMERA}, 41);
                        }
                        return;
                    }
                }
                request.deny();
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(root);

        String saved = prefs.getString("server", "");
        if (saved.isEmpty()) showSetup(); else openProgram(saved);
    }

    private void showError(String msg) {
        errorText.setText(msg);
        errorText.setVisibility(View.VISIBLE);
    }

    @Override public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (code == 41 && pendingCamera != null) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
                pendingCamera.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
            } else {
                pendingCamera.deny();
            }
            pendingCamera = null;
        }
    }

    @Override protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();   // session cookie disk par mehfooz
    }

    private void showSetup() {
        web.setVisibility(View.GONE);
        setupBox.setVisibility(View.VISIBLE);
    }

    private void openProgram(String url) {
        setupBox.setVisibility(View.GONE);
        web.setVisibility(View.VISIBLE);
        web.loadUrl(url);
    }

    @Override public void onBackPressed() {
        if (web.getVisibility() == View.VISIBLE && web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
