package com.oarumi.app.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.oarumi.app.ui.theme.BorderSubtle
import com.oarumi.app.ui.theme.SurfaceElevated
import com.oarumi.app.ui.theme.TextMuted
import com.oarumi.app.ui.theme.TextPrimary

/** A rounded, bordered panel that groups related controls or results. */
@Composable
fun OarumiCard(
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit,
) {
    val shape = RoundedCornerShape(12.dp)
    Column(
        modifier =
            modifier
                .fillMaxWidth()
                .clip(shape)
                .background(SurfaceElevated)
                .border(1.dp, BorderSubtle, shape)
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        content()
    }
}

/** Large screen title with a one-line description under it. */
@Composable
fun ScreenHeader(
    title: String,
    subtitle: String,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            text = title,
            style = MaterialTheme.typography.displayLarge.copy(fontSize = 26.sp),
            color = TextPrimary,
        )
        Text(
            text = subtitle,
            style = MaterialTheme.typography.bodyLarge,
            color = TextMuted,
        )
    }
}
