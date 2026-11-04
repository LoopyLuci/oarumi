package com.oarumi.app.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.oarumi.app.ui.theme.BorderSubtle
import com.oarumi.app.ui.theme.SurfaceInset
import com.oarumi.app.ui.theme.TextMuted

@Composable
fun OarumiStatusBar(
    offline: Boolean,
    degraded: Boolean,
    auditTail: String,
    onRefreshAudit: () -> Unit,
) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(32.dp)
                .background(SurfaceInset)
                .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OfflineBadge(offline = offline)
        DegradedBadge(visible = degraded)
        Text(
            text = auditTail,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.labelSmall,
            color = TextMuted,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        IconButton(onClick = onRefreshAudit, modifier = Modifier.size(24.dp)) {
            Icon(
                imageVector = Icons.Filled.Refresh,
                contentDescription = "Refresh audit tail",
                tint = BorderSubtle,
            )
        }
    }
}
