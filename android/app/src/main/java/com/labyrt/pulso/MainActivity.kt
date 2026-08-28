package com.labyrt.pulso

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
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
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.updateAll
import com.labyrt.pulso.widget.PulsoWidget
import com.labyrt.pulso.widget.PulsoWidgetReceiver
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

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
        val requiredPermissions = androidPermissionsFor(request)
        if (requiredPermissions.all { grants[it] == true || checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }) {
            request.grant(request.resources)
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

        webView = WebView(this)
        setContentView(webView)
        configureWebView()
        configureBackNavigation()

        if (savedInstanceState == null) {
            openIntent(intent)
        } else {
            webView.restoreState(savedInstanceState)
        }
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
            userAgentString = "$userAgentString PULSO-Android/0.1"
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
                val missing = androidPermissionsFor(request)
                    .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
                if (missing.isEmpty()) {
                    request.grant(request.resources)
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

    private fun androidPermissionsFor(request: PermissionRequest): List<String> = buildList {
        if (request.resources.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE)) add(Manifest.permission.CAMERA)
        if (request.resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) add(Manifest.permission.RECORD_AUDIO)
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
        val path = intent.getStringExtra(EXTRA_PATH)?.takeIf { it.startsWith("/") } ?: "/app/"
        webView.loadUrl(BuildConfig.PULSO_BASE_URL + path)
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
        fun refreshWidget() {
            appScope.launch(Dispatchers.IO) {
                runCatching { PulsoWidget().updateAll(this@MainActivity) }
            }
        }

        @JavascriptInterface
        fun openWidgetSettings() {
            runCatching {
                startActivity(Intent(Settings.ACTION_HOME_SETTINGS))
            }
        }
    }

    companion object {
        const val EXTRA_PATH = "pulso_path"
    }
}
