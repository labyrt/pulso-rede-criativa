package com.labyrt.pulso.widget

import android.content.Context
import org.json.JSONObject

internal enum class WidgetConnectionState {
    READY,
    SIGNED_OUT,
    UNAVAILABLE,
}

internal data class WidgetSummary(
    val state: WidgetConnectionState,
    val messagesUnread: Int = 0,
    val activityUnread: Int = 0,
    val callsUnread: Int = 0,
    val latestActivityLabel: String? = null,
)

internal object WidgetSummaryClient {
    private const val PREFS = "pulso_widget_summary"
    private const val KEY_READY = "ready"
    private const val KEY_MESSAGES = "messages_unread"
    private const val KEY_ACTIVITY = "activity_unread"
    private const val KEY_CALLS = "calls_unread"
    private const val KEY_LATEST_LABEL = "latest_activity_label"
    private const val KEY_UPDATED_AT = "updated_at"
    private const val MAX_COUNT = 9_999
    private const val STALE_AFTER_MS = 6 * 60 * 60 * 1000L

    private val allowedLabels = setOf(
        "Nova conexão",
        "Nova curtida",
        "Novo comentário",
        "Novo compartilhamento",
        "Nova publicação",
        "Nova mensagem",
        "Nova ligação",
        "Nova atividade",
    )

    fun load(context: Context): WidgetSummary {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!prefs.getBoolean(KEY_READY, false)) {
            return WidgetSummary(WidgetConnectionState.SIGNED_OUT)
        }

        val updatedAt = prefs.getLong(KEY_UPDATED_AT, 0L)
        val stale = updatedAt <= 0L || System.currentTimeMillis() - updatedAt > STALE_AFTER_MS
        val storedLabel = prefs.getString(KEY_LATEST_LABEL, null)
        val label = if (stale) "Abra o PULSO para atualizar" else storedLabel

        return WidgetSummary(
            state = WidgetConnectionState.READY,
            messagesUnread = prefs.getInt(KEY_MESSAGES, 0).coerceIn(0, MAX_COUNT),
            activityUnread = prefs.getInt(KEY_ACTIVITY, 0).coerceIn(0, MAX_COUNT),
            callsUnread = prefs.getInt(KEY_CALLS, 0).coerceIn(0, MAX_COUNT),
            latestActivityLabel = label,
        )
    }

    fun save(context: Context, raw: String): Boolean = runCatching {
        val json = JSONObject(raw)
        val latest = json.optJSONObject("latest_activity")
        val label = latest
            ?.optString("label")
            ?.takeIf { it in allowedLabels }

        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_READY, true)
            .putInt(KEY_MESSAGES, json.optInt("messages_unread", 0).coerceIn(0, MAX_COUNT))
            .putInt(KEY_ACTIVITY, json.optInt("activity_unread", 0).coerceIn(0, MAX_COUNT))
            .putInt(KEY_CALLS, json.optInt("calls_unread", 0).coerceIn(0, MAX_COUNT))
            .putString(KEY_LATEST_LABEL, label)
            .putLong(KEY_UPDATED_AT, System.currentTimeMillis())
            .apply()
        true
    }.getOrDefault(false)

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .clear()
            .apply()
    }
}
