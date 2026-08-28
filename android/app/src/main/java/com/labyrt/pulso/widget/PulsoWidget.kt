package com.labyrt.pulso.widget

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.DpSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.LocalSize
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.SizeMode
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.labyrt.pulso.MainActivity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class PulsoWidget : GlanceAppWidget() {
    override val sizeMode = SizeMode.Responsive(setOf(SMALL, WIDE))

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val summary = withContext(Dispatchers.IO) { WidgetSummaryClient.load(context) }
        provideContent { WidgetContent(context, summary) }
    }

    override suspend fun providePreview(context: Context, widgetCategory: Int) {
        provideContent {
            WidgetContent(
                context,
                WidgetSummary(
                    state = WidgetConnectionState.READY,
                    messagesUnread = 3,
                    activityUnread = 5,
                    callsUnread = 1,
                    latestActivityLabel = "Nova publicação",
                ),
            )
        }
    }

    companion object {
        private val SMALL = DpSize(180.dp, 96.dp)
        private val WIDE = DpSize(300.dp, 110.dp)
    }
}

@Composable
private fun WidgetContent(context: Context, summary: WidgetSummary) {
    val size = LocalSize.current
    val compact = size.width < 250.dp
    val openHome = actionStartActivity(openIntent(context, "/app/", "home"))

    Column(
        modifier = GlanceModifier
            .fillMaxSize()
            .background(INK)
            .clickable(openHome)
            .padding(if (compact) 12.dp else 14.dp),
    ) {
        Text(
            text = "PULSO",
            style = TextStyle(
                color = LIME,
                fontSize = if (compact) 16.sp else 18.sp,
                fontWeight = FontWeight.Bold,
            ),
        )
        Spacer(GlanceModifier.height(6.dp))

        when (summary.state) {
            WidgetConnectionState.READY -> ReadyContent(context, summary, compact)
            WidgetConnectionState.SIGNED_OUT -> StateMessage(
                title = "Conecte seu PULSO",
                copy = "Abra o app para entrar.",
            )
            WidgetConnectionState.UNAVAILABLE -> StateMessage(
                title = "Sem conexão agora",
                copy = "Toque para abrir o PULSO.",
            )
        }
    }
}

@Composable
private fun ReadyContent(context: Context, summary: WidgetSummary, compact: Boolean) {
    Row(modifier = GlanceModifier.fillMaxWidth()) {
        Metric(summary.messagesUnread, "mensagens")
        Spacer(GlanceModifier.width(if (compact) 12.dp else 22.dp))
        Metric(summary.activityUnread, "atividade")
        if (!compact && summary.callsUnread > 0) {
            Spacer(GlanceModifier.width(22.dp))
            Metric(summary.callsUnread, "ligações")
        }
    }

    Spacer(GlanceModifier.height(6.dp))
    if (!compact && !summary.latestActivityLabel.isNullOrBlank()) {
        Text(
            text = summary.latestActivityLabel,
            style = TextStyle(color = MUTED, fontSize = 11.sp),
        )
        Spacer(GlanceModifier.height(5.dp))
    }

    Row(modifier = GlanceModifier.fillMaxWidth()) {
        WidgetAction(context, "Mensagens", "/mensagens/", "messages")
        Spacer(GlanceModifier.width(14.dp))
        WidgetAction(context, "Atividade", "/notificacoes/", "activity")
        if (!compact) {
            Spacer(GlanceModifier.width(14.dp))
            WidgetAction(context, "+ Criar", "/app/?composer=1", "compose")
        }
    }
}

@Composable
private fun Metric(count: Int, label: String) {
    Column {
        Text(
            text = if (count > 99) "99+" else count.toString(),
            style = TextStyle(color = PAPER, fontSize = 18.sp, fontWeight = FontWeight.Bold),
        )
        Text(text = label, style = TextStyle(color = MUTED, fontSize = 10.sp))
    }
}

@Composable
private fun WidgetAction(context: Context, label: String, path: String, route: String) {
    Text(
        text = label,
        modifier = GlanceModifier
            .clickable(actionStartActivity(openIntent(context, path, route)))
            .padding(vertical = 3.dp),
        style = TextStyle(color = LIME, fontSize = 11.sp, fontWeight = FontWeight.Bold),
    )
}

@Composable
private fun StateMessage(title: String, copy: String) {
    Text(text = title, style = TextStyle(color = PAPER, fontSize = 14.sp, fontWeight = FontWeight.Bold))
    Spacer(GlanceModifier.height(4.dp))
    Text(text = copy, style = TextStyle(color = MUTED, fontSize = 11.sp))
}

private fun openIntent(context: Context, path: String, route: String): Intent =
    Intent(context, MainActivity::class.java).apply {
        data = Uri.parse("pulso://widget/$route")
        putExtra(MainActivity.EXTRA_PATH, path)
        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
    }

private val INK = ColorProvider(Color(0xFF0B0B0C))
private val PAPER = ColorProvider(Color(0xFFF7F6F2))
private val LIME = ColorProvider(Color(0xFFCAFF37))
private val MUTED = ColorProvider(Color(0xFFB8B8B6))
