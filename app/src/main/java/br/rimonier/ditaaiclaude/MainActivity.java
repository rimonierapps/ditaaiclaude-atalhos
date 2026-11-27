package br.rimonier.ditaaiclaude;

import android.app.Activity;
import android.content.Context;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.HapticFeedbackConstants;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import android.net.wifi.WifiManager;

import java.io.InputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetSocketAddress;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.json.JSONObject;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.util.Collections;

/**
 * DitaAíClaude (atalhos): a tela inteira é a página assets/index.html
 * (a mesma que o servidor do PC entrega no navegador).
 */
public class MainActivity extends Activity {
    static final int PORTA = 8790, PORTA_ANUNCIO = 8791;
    WebView web;
    WifiManager.MulticastLock trava;
    DatagramSocket ouvido;
    volatile boolean ativo;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        // tela sempre acesa enquanto o app estiver aberto
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setStatusBarColor(0xFF11161D);
        getWindow().setNavigationBarColor(0xFF11161D);

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#11161D"));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setTextZoom(100);
        web.setHapticFeedbackEnabled(false);
        web.setLongClickable(false);
        web.setOnLongClickListener(v -> true);
        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(new Ponte(), "Android");
        web.loadUrl("file:///android_asset/index.html");
        setContentView(web);
    }

    @Override
    protected void onResume() {
        super.onResume();
        ativo = true;
        ouvirAnuncios();
        if (web != null) web.evaluateJavascript("window.sefReconectar && window.sefReconectar()", null);
    }

    @Override
    protected void onPause() {
        super.onPause();
        ativo = false;
        try { if (ouvido != null) ouvido.close(); } catch (Exception ignorado) { }
        try { if (trava != null && trava.isHeld()) trava.release(); } catch (Exception ignorado) { }
    }

    void avisarJs(String ip, int porta) {
        runOnUiThread(() -> web.evaluateJavascript(
                "window.sefAchouPc && window.sefAchouPc('" + ip + "'," + porta + ")", null));
    }

    /** Escuta o "estou aqui" que o servidor do PC manda pela rede. */
    void ouvirAnuncios() {
        try {
            WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null) {
                trava = wm.createMulticastLock("ditaaiclaude");
                trava.setReferenceCounted(false);
                trava.acquire();
            }
        } catch (Exception ignorado) { }
        new Thread(() -> {
            try {
                DatagramSocket s = new DatagramSocket(null);
                s.setReuseAddress(true);
                s.setBroadcast(true);
                s.bind(new InetSocketAddress(PORTA_ANUNCIO));
                ouvido = s;
                byte[] buf = new byte[512];
                while (ativo) {
                    DatagramPacket p = new DatagramPacket(buf, buf.length);
                    s.receive(p);
                    JSONObject j = new JSONObject(new String(p.getData(), 0, p.getLength(), "UTF-8"));
                    if (!"ditaaiclaude".equals(j.optString("app"))) continue;
                    avisarJs(p.getAddress().getHostAddress(), j.optInt("porta", PORTA));
                }
            } catch (Exception ignorado) { }
        }).start();
    }

    /** Plano B: testa todos os endereços da rede (x.x.x.1 a 254) ao mesmo tempo. */
    void varrerRede() {
        new Thread(() -> {
            String meu = new Ponte().ipLocal();
            AtomicBoolean achou = new AtomicBoolean(false);
            if (meu.isEmpty()) {
                runOnUiThread(() -> web.evaluateJavascript("window.sefFimBusca && window.sefFimBusca(false)", null));
                return;
            }
            String pre = meu.substring(0, meu.lastIndexOf('.') + 1);
            ExecutorService ex = Executors.newFixedThreadPool(48);
            for (int i = 1; i < 255; i++) {
                final String ip = pre + i;
                if (ip.equals(meu)) continue;
                ex.submit(() -> {
                    if (achou.get()) return;
                    HttpURLConnection c = null;
                    try {
                        c = (HttpURLConnection) new URL("http://" + ip + ":" + PORTA + "/ping").openConnection();
                        c.setConnectTimeout(600);
                        c.setReadTimeout(800);
                        InputStream in = c.getInputStream();
                        byte[] b = new byte[300];
                        int n = in.read(b);
                        if (n > 0 && new String(b, 0, n, "UTF-8").contains("ditaaiclaude")
                                && achou.compareAndSet(false, true)) {
                            avisarJs(ip, PORTA);
                        }
                    } catch (Exception ignorado) {
                    } finally {
                        if (c != null) c.disconnect();
                    }
                });
            }
            ex.shutdown();
            try { ex.awaitTermination(20, TimeUnit.SECONDS); } catch (InterruptedException ignorado) { }
            final boolean ok = achou.get();
            runOnUiThread(() -> web.evaluateJavascript("window.sefFimBusca && window.sefFimBusca(" + ok + ")", null));
        }).start();
    }

    @Override
    public void onBackPressed() {
        moveTaskToBack(true);
    }

    class Ponte {
        @JavascriptInterface
        public void vibrar(int ms) {
            try {
                Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v == null) return;
                v.vibrate(VibrationEffect.createOneShot(Math.max(1, ms), VibrationEffect.DEFAULT_AMPLITUDE));
            } catch (Exception ignorado) {
                runOnUiThread(() -> web.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY));
            }
        }

        @JavascriptInterface
        public void procurar() {
            varrerRede();
        }

        /** IP do celular no Wi-Fi, para procurar o PC na mesma rede. */
        @JavascriptInterface
        public String ipLocal() {
            try {
                for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                    if (!ni.isUp() || ni.isLoopback()) continue;
                    String nome = ni.getName();
                    if (!nome.startsWith("wlan") && !nome.startsWith("eth") && !nome.startsWith("ap")) continue;
                    for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                        if (a instanceof Inet4Address && a.isSiteLocalAddress()) return a.getHostAddress();
                    }
                }
            } catch (Exception ignorado) { }
            return "";
        }
    }
}
