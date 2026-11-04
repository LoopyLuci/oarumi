package com.oarumi.app.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.oarumi.app.R
import com.oarumi.app.ui.theme.BadgeInfoBg
import com.oarumi.app.ui.theme.BadgeInfoFg
import com.oarumi.app.ui.theme.BadgeOkBg
import com.oarumi.app.ui.theme.BadgeOkFg
import com.oarumi.app.ui.theme.BadgeWarnBg
import com.oarumi.app.ui.theme.BadgeWarnFg

@Composable
fun OfflineBadge(offline: Boolean) {
    val (bg, fg) = if (offline) BadgeInfoBg to BadgeInfoFg else BadgeOkBg to BadgeOkFg
    val label = stringResource(if (offline) R.string.badge_offline else R.string.badge_online)
    Box(
        modifier =
            Modifier
                .clip(RoundedCornerShape(4.dp))
                .background(bg)
                .padding(horizontal = 8.dp, vertical = 2.dp),
    ) {
        Text(
            text = label,
            color = fg,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
fun DegradedBadge(visible: Boolean) {
    if (!visible) return
    Box(
        modifier =
            Modifier
                .clip(RoundedCornerShape(4.dp))
                .background(BadgeWarnBg)
                .padding(horizontal = 8.dp, vertical = 2.dp),
    ) {
        Text(
            text = stringResource(R.string.badge_degraded),
            color = BadgeWarnFg,
            fontSize = 11.sp,
            fontWeight = FontWeight.SemiBold,
        )
    }
}
