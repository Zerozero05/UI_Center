/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from MainActivity.java card/renderOutcome at PDF_Bookmarks_Android
 * b44ab5d14e547fef4b80e9469b7c8eb503e2302e; generic state-only rendering.
 */
package cn.local.uicenter;

import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Typeface;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

/** Progress and results are persistent inline text; color supplements explicit labels. */
public final class TaskPanel extends LinearLayout {
    private final UiTheme theme;
    private final TextView title, status;
    private final ProgressBar progress;
    private final LinearLayout rows;
    public TaskPanel(Context context, UiTheme theme) {
        super(context); this.theme = theme; setOrientation(VERTICAL);
        int padding = theme.dp(context, theme.space("lg")); setPadding(padding,padding,padding,padding);
        setBackground(theme.surface(context, "surface"));
        title = label("任务与结果", "heading"); title.setTypeface(null, Typeface.BOLD); addView(title);
        status = label("尚未开始", "body"); status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        addView(status);
        progress = new ProgressBar(context, null, android.R.attr.progressBarStyleHorizontal);
        progress.setProgressTintList(ColorStateList.valueOf(theme.color("accent")));
        addView(progress, new LayoutParams(-1, theme.dp(context, theme.space("lg"))));
        rows = new LinearLayout(context); rows.setOrientation(VERTICAL); addView(rows);
    }
    public void render(TaskState state) {
        title.setText(state.title());
        String summary;
        switch (state.phase()) {
            case RUNNING: summary = "处理中"; break;
            case SUCCEEDED: summary = "已完成"; break;
            case FAILED: summary = "处理失败；已完成项保留"; break;
            case CANCELLED: summary = "已取消；已完成项保留"; break;
            default: summary = "尚未开始";
        }
        status.setText(summary + (state.total() > 0 ? " · " + state.completed() + " / " + state.total() : ""));
        status.setTextColor(theme.color(state.phase() == TaskState.Phase.FAILED ? "error"
                : state.phase() == TaskState.Phase.SUCCEEDED ? "success" : "foreground"));
        progress.setVisibility(state.total() == 0 ? GONE : VISIBLE);
        progress.setMax(Math.max(1, state.total())); progress.setProgress(state.completed());
        progress.setContentDescription(summary + "，已完成 " + state.completed() + " 项，共 " + state.total() + " 项");
        rows.removeAllViews();
        for (TaskState.Result result : state.results()) {
            TextView row = label((result.success ? "已完成 · " : "失败 · ") + result.label, "body");
            row.setTextColor(theme.color(result.success ? "success" : "error"));
            row.setTextIsSelectable(true);
            int space = theme.dp(getContext(), theme.space("sm")); row.setPadding(0,space,0,space);
            rows.addView(row);
        }
    }
    private TextView label(String value, String role) {
        TextView label = new TextView(getContext()); label.setText(value); theme.text(label, role); return label;
    }
}
