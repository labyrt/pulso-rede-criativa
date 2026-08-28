package com.labyrt.pulso.widget

import android.content.Context
import android.webkit.CookieManager
import com.labyrt.pulso.BuildConfig
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

internal enum class WidgetConnectionState {
    READY,
    SIGNED_OUT,
    UNAVAILABLE,
}

internal data class WidgetSummary(
    val state: WidgetConnectionState,
    val displayName: String = "PULSO",
    val messagesUnread: Int = 0,
    val activityUnread: Int = 0,
    val callsUnread: Int = 0,
    val latestActivityLabel: String? = null,
)

internal object WidgetSummaryClient {
    fun load(@Suppress("UNUSED_PARAMETER") context: Context): WidgetSummary {
        val cookie = CookieManager.getInstance().getCookie(BuildConfig.PULSO_BASE_URL)
        if (cookie.isNullOrBlank()) return WidgetSummary(WidgetConnectionState.SIGNED_OUT)

        val connection = (URL("${BuildConfig.PULSO_BASE_URL}/api/v1/widget/summary/").openConnection() as HttpURLConnection)
        return try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 5_000
            connection.readTimeout = 6_000
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Cookie", cookie)
            connection.setRequestProperty("User-Agent", "PULSO-Android-Widget/0.1")

            when (connection.responseCode) {
                HttpURLConnection.HTTP_OK -> parse(connection.inputStream.bufferedReader().use { it.readText() })
                HttpURLConnection.HTTP_UNAUTHORIZED,
                HttpURLConnection.HTTP_FORBIDDEN,
                HttpURLConnection.HTTP_MOVED_TEMP,
                HttpURLConnection.HTTP_MOVED_PERM -> WidgetSummary(WidgetConnectionState.SIGNED_OUT)
                else -> WidgetSummary(WidgetConnectionState.UNAVAILABLE)
            }
        } catch (_: Exception) {
            WidgetSummary(WidgetConnectionState.UNAVAILABLE)
        } finally {
            connection.disconnect()
        }
    }

    private fun parse(raw: String): WidgetSummary {
        val json = JSONObject(raw)
        val latest = json.optJSONObject("latest_activity")
        return WidgetSummary(
            state = WidgetConnectionState.READY,
            displayName = json.optString("display_name").ifBlank { "PULSO" },
            messagesUnread = json.optInt("messages_unread", 0).coerceAtLeast(0),
            activityUnread = json.optInt("activity_unread", 0).coerceAtLeast(0),
            callsUnread = json.optInt("calls_unread", 0).coerceAtLeast(0),
            latestActivityLabel = latest?.optString("label")?.takeIf { it.isNotBlank() },
        )
    }
}
