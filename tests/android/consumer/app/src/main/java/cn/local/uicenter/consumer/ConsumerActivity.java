/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only */
package cn.local.uicenter.consumer;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Insets;
import android.view.View;
import android.view.WindowInsets;
import android.widget.LinearLayout;
import cn.local.uicenter.ActionGroup;
import cn.local.uicenter.TaskPanel;
import cn.local.uicenter.TaskState;
import cn.local.uicenter.UiTheme;

/** Minimal independent consumer. One deterministic synchronous fake step. */
public final class ConsumerActivity extends Activity {
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        UiTheme theme = UiTheme.fromAssets(this,false);
        TaskState state = new TaskState(); TaskPanel panel = new TaskPanel(this,theme);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.addView(new ActionGroup(this,theme,"运行消费示例",() -> {
            state.start("独立源码消费",1); state.advance("已成功调用复制组件"); panel.render(state);
        },() -> { }));
        root.addView(panel); panel.render(state);
        root.setOnApplyWindowInsetsListener((view,insets) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                view.setPadding(bars.left,bars.top,bars.right,bars.bottom);
            } else applyLegacyInsets(view,insets);
            return insets;
        });
        setContentView(root); root.requestApplyInsets(); theme.systemBars(this);
    }
    @SuppressWarnings("deprecation")
    private void applyLegacyInsets(View view,WindowInsets insets) {
        view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
    }
}
