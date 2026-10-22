/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from MainActivity.java button/styleButton at PDF_Bookmarks_Android
 * b44ab5d14e547fef4b80e9469b7c8eb503e2302e; callbacks replace business actions.
 */
package cn.local.uicenter;

import android.content.Context;
import android.widget.Button;
import android.widget.LinearLayout;

/** Stacked actions remain readable with long translations and large Android font scales. */
public final class ActionGroup extends LinearLayout {
    private final Button primary, cancel;
    public ActionGroup(Context context, UiTheme theme, String primaryLabel,
                       Runnable onStart, Runnable onCancel) {
        super(context); setOrientation(VERTICAL);
        primary = new Button(context); primary.setText(primaryLabel); theme.button(primary, true);
        primary.setOnClickListener(view -> onStart.run()); addView(primary, new LayoutParams(-1, -2));
        cancel = new Button(context); cancel.setText("取消任务"); theme.button(cancel, false);
        cancel.setOnClickListener(view -> onCancel.run());
        LayoutParams params = new LayoutParams(-1, -2); params.topMargin = theme.dp(context, theme.space("sm"));
        addView(cancel, params); setRunning(false);
    }
    public void setRunning(boolean running) {
        primary.setEnabled(!running); cancel.setEnabled(running);
    }
    public Button primaryButton() { return primary; }
    public Button cancelButton() { return cancel; }
}
