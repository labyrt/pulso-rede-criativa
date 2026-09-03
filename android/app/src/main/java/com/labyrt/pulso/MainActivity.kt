package com.labyrt.pulso

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.util.Base64
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.addCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.updateAll
import com.labyrt.pulso.widget.PulsoWidget
import com.labyrt.pulso.widget.PulsoWidgetReceiver
import com.labyrt.pulso.widget.WidgetSummaryClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.security.MessageDigest
import java.security.SecureRandom

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private var fileChooserCallback: ValueCallback<Array<Uri>>? = null
    private var pendingMediaRequest: PermissionRequest? = null

    private val fileChooserLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val uris = WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data)
        fileChooserCallback?.onReceiveValue(uris)
        fileChooserCallback = null
    }

    private val mediaPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        val request = pendingMediaRequest ?: return@registerForActivityResult
        pendingMediaRequest = null
        val approvedResources = approvedWebResources(request)
        if (approvedResources.isEmpty()) {
            request.deny()
            return@registerForActivityResult
        }
        val requiredPermissions = androidPermissionsFor(approvedResources)
        if (requiredPermissions.all { grants[it] == true || checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }) {
            request.grant(approvedResources)
        } else {
            request.deny()
            Toast.makeText(
                this,
                "Câmera e microfone precisam de permissão para chamadas.",
                Toast.LENGTH_LONG,
            ).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Android 15/16 render target-SDK 35+ apps edge-to-edge. Handle the
        // insets explicitly so the WebView never disappears under the status
        // or navigation bars on gesture and three-button navigation devices.
        WindowCompat.setDecorFitsSystemWindows(window, false)
        webView = WebView(this)
        setContentView(webView)
        configureSystemInsets()
        configureWebView()
        configureBackNavigation()

        if (savedInstanceState == null) {
            openIntent(intent)
        } else {
            webView.restoreState(savedInstanceState)
        }
    }

    private fun configureSystemInsets() {
        ViewCompat.setOnApplyWindowInsetsListener(webView) { view, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout(),
            )
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(webView)
    }

    private fun configureBackNavigation() {
        onBackPressedDispatcher.addCallback(this) {
            if (webView.canGoBack()) {
                webView.goBack()
            } else {
                isEnabled = false
                onBackPressedDispatcher.onBackPressed()
            }
        }
    }

    private fun configureWebView() {
        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            javaScriptCanOpenWindowsAutomatically = false
            mediaPlaybackRequiresUserGesture = false
            userAgentString = "$userAgentString PULSO-Android/0.2.1"
        }

        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, false)
        }

        webView.addJavascriptInterface(NativeBridge(), "PulsoAndroid")
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val uri = request?.url ?: return false
                if (isPulsoUri(uri)) return false
                startActivity(Intent(Intent.ACTION_VIEW, uri))
                return true
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                if (url?.startsWith(BuildConfig.PULSO_BASE_URL) == true) {
                    appScope.launch(Dispatchers.IO) {
                        runCatching { PulsoWidget().updateAll(this@MainActivity) }
                    }
                }
            }
        }
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?,
            ): Boolean {
                fileChooserCallback?.onReceiveValue(null)
                fileChooserCallback = filePathCallback
                val chooserIntent = runCatching { fileChooserParams?.createIntent() }.getOrNull()
                    ?: Intent(Intent.ACTION_GET_CONTENT).apply {
                        type = "image/*"
                        addCategory(Intent.CATEGORY_OPENABLE)
                    }
                return try {
                    fileChooserLauncher.launch(chooserIntent)
                    true
                } catch (_: Exception) {
                    fileChooserCallback?.onReceiveValue(null)
                    fileChooserCallback = null
                    false
                }
            }

            override fun onPermissionRequest(request: PermissionRequest) {
                val approvedResources = approvedWebResources(request)
                if (approvedResources.isEmpty()) {
                    request.deny()
                    return
                }
                val missing = androidPermissionsFor(approvedResources)
                    .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
                if (missing.isEmpty()) {
                    request.grant(approvedResources)
                } else {
                    pendingMediaRequest?.deny()
                    pendingMediaRequest = request
                    mediaPermissionLauncher.launch(missing.toTypedArray())
                }
            }

            override fun onPermissionRequestCanceled(request: PermissionRequest?) {
                if (pendingMediaRequest == request) pendingMediaRequest = null
            }
        }
    }

    private fun approvedWebResources(request: PermissionRequest): Array<String> =
        request.resources.filter {
            it == PermissionRequest.RESOURCE_VIDEO_CAPTURE ||
                it == PermissionRequest.RESOURCE_AUDIO_CAPTURE
        }.toTypedArray()

    private fun androidPermissionsFor(resources: Array<String>): List<String> = buildList {
        if (resources.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE)) add(Manifest.permission.CAMERA)
        if (resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) add(Manifest.permission.RECORD_AUDIO)
    }

    private fun isPulsoUri(uri: Uri): Boolean {
        val base = Uri.parse(BuildConfig.PULSO_BASE_URL)
        return uri.scheme == "https" && uri.host == base.host
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        openIntent(intent)
    }

    private fun openIntent(intent: Intent) {
        val callback = intent.data
        if (callback?.scheme == "pulso" && callback.host == "auth") {
            consumeNativeAuthCallback(callback)
            return
        }
        val path = intent.getStringExtra(EXTRA_PATH)?.takeIf { it.startsWith("/") } ?: "/app/"
        webView.loadUrl(BuildConfig.PULSO_BASE_URL + path)
    }

    private fun consumeNativeAuthCallback(uri: Uri) {
        val code = uri.getQueryParameter("code")?.takeIf { NATIVE_CODE.matches(it) }
        val prefs = getSharedPreferences(NATIVE_AUTH_PREFS, Context.MODE_PRIVATE)
        val verifier = prefs.getString(NATIVE_AUTH_VERIFIER, null)?.takeIf { NATIVE_VERIFIER.matches(it) }
        if (code == null || verifier == null) {
            Toast.makeText(this, "Não foi possível concluir o login social.", Toast.LENGTH_LONG).show()
            webView.loadUrl("${BuildConfig.PULSO_BASE_URL}/entrar/")
            return
        }

        prefs.edit().remove(NATIVE_AUTH_VERIFIER).apply()
        val body = "code=$code&verifier=$verifier".toByteArray(Charsets.UTF_8)
        webView.postUrl("${BuildConfig.PULSO_BASE_URL}/native-auth/consume/", body)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        pendingMediaRequest?.deny()
        pendingMediaRequest = null
        fileChooserCallback?.onReceiveValue(null)
        fileChooserCallback = null
        appScope.cancel()
        webView.removeJavascriptInterface("PulsoAndroid")
        webView.destroy()
        super.onDestroy()
    }

    private inner class NativeBridge {
        @JavascriptInterface
        fun requestPinWidget() {
            appScope.launch {
                val sent = runCatching {
                    GlanceAppWidgetManager(this@MainActivity).requestPinGlanceAppWidget(
                        receiver = PulsoWidgetReceiver::class.java,
                        preview = PulsoWidget(),
                    )
                }.getOrDefault(false)
                if (!sent) {
                    Toast.makeText(
                        this@MainActivity,
                        "Seu launcher não aceitou a fixação automática. Use o seletor de widgets do Android.",
                        Toast.LENGTH_LONG,
                    ).show()
                }
            }
        }

        @JavascriptInterface
        fun updateWidgetSummary(rawJson: String) {
            if (!WidgetSummaryClient.save(this@MainActivity, rawJson)) return
            appScope.launch(Dispatchers.IO) {
                runCatching { PulsoWidget().updateAll(this@MainActivity) }
            }
        }

        @JavascriptInterface
        fun clearWidgetSummary() {
            WidgetSummaryClient.clear(this@MainActivity)
            appScope.launch(Dispatchers.IO) {
                runCatching { PulsoWidget().updateAll(this@MainActivity) }
            }
        }

        @JavascriptInterface
        fun refreshWidget() {
            appScope.launch(Dispatchers.IO) {
                runCatching { PulsoWidget().updateAll(this@MainActivity) }
            }
        }

        @JavascriptInterface
        fun startSocialLogin(provider: String) {
            if (provider !in NATIVE_SOCIAL_PROVIDERS) return
            val verifierBytes = ByteArray(32).also { SecureRandom().nextBytes(it) }
            val verifier = base64Url(verifierBytes)
            val challenge = base64Url(MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII)))
            getSharedPreferences(NATIVE_AUTH_PREFS, Context.MODE_PRIVATE)
                .edit()
                .putString(NATIVE_AUTH_VERIFIER, verifier)
                .apply()

            val target = Uri.parse("${BuildConfig.PULSO_BASE_URL}/native-auth/start/$provider/")
                .buildUpon()
                .appendQueryParameter("challenge", challenge)
                .build()
            appScope.launch {
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, target)) }
                    .onFailure {
                        Toast.makeText(
                            this@MainActivity,
                            "Não encontrei um navegador para concluir o login social.",
                            Toast.LENGTH_LONG,
                        ).show()
                    }
            }
        }

        @JavascriptInterface
        fun openWidgetSettings() {
            runCatching {
                startActivity(Intent(Settings.ACTION_HOME_SETTINGS))
            }
        }
    }

    private fun base64Url(bytes: ByteArray): String = Base64.encodeToString(
        bytes,
        Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING,
    )

    companion object {
        const val EXTRA_PATH = "pulso_path"
        private const val NATIVE_AUTH_PREFS = "pulso_native_auth"
        private const val NATIVE_AUTH_VERIFIER = "verifier"
        private val NATIVE_SOCIAL_PROVIDERS = setOf("google", "github", "linkedin", "instagram", "adobe")
        private val NATIVE_CODE = Regex("^[A-Za-z0-9_-]{32,128}$")
        private val NATIVE_VERIFIER = Regex("^[A-Za-z0-9_-]{43,128}$")
    }
}
