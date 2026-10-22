/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only */
package cn.local.uicenter.demo;

import android.app.Activity;
import android.content.res.ColorStateList;
import android.graphics.Insets;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowInsets;
import android.view.ViewTreeObserver;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import cn.local.uicenter.ActionGroup;
import cn.local.uicenter.TaskPanel;
import cn.local.uicenter.TaskState;
import cn.local.uicenter.UiTheme;
import java.util.ArrayList;

/** Fake task host. No files, network, permissions or original application dependencies. */
public final class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private TaskState state = new TaskState();
    private boolean dark, failDemo;
    private UiTheme theme;
    private EditText input;
    private CheckBox failure;
    private TextView validation;
    private TaskPanel panel;
    private ActionGroup actions;
    private Button themeButton;
    private ScrollView mainScroll;
    private String inputValue = "示例任务 · 支持中文与长文本";
    private String validationMessage = "", focusedRole = "";
    private int selectionStart = -1, selectionEnd = -1, scrollPosition;
    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (!state.isRunning()) return;
            if (failDemo && state.completed() == 2) state.fail("模拟第三步失败，请调整参数后重试。");
            else state.advance("第 " + (state.completed() + 1) + " 项：" + state.title());
            render();
            if (state.isRunning()) handler.postDelayed(this, 600);
        }
    };
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        if (saved != null) {
            dark = saved.getBoolean("dark"); failDemo = saved.getBoolean("failDemo");
            inputValue = saved.getString("input", inputValue);
            validationMessage = saved.getString("validation", "");
            focusedRole = saved.getString("focus", "");
            selectionStart = saved.getInt("selectionStart", -1); selectionEnd = saved.getInt("selectionEnd", -1);
            scrollPosition = saved.getInt("scrollPosition");
            ArrayList<String> labels = saved.getStringArrayList("results");
            boolean[] successes = saved.getBooleanArray("successes");
            ArrayList<TaskState.Result> results = new ArrayList<>();
            if (labels != null && successes != null)
                for (int i = 0; i < labels.size(); i++) results.add(new TaskState.Result(labels.get(i), successes[i]));
            state = TaskState.restore(saved.getString("title", "尚未开始"),
                    TaskState.Phase.valueOf(saved.getString("phase", "IDLE")),
                    saved.getInt("completed"), saved.getInt("total"), results);
        }
        buildUi();
    }
    @Override protected void onResume() {
        super.onResume(); if (state.isRunning()) handler.postDelayed(tick, 600);
    }
    @Override protected void onPause() {
        handler.removeCallbacks(tick); super.onPause();
    }
    @Override protected void onDestroy() {
        handler.removeCallbacks(tick); super.onDestroy();
    }
    @Override protected void onSaveInstanceState(Bundle saved) {
        captureUi();
        saved.putBoolean("dark", dark); saved.putBoolean("failDemo", failure.isChecked());
        saved.putString("input", inputValue); saved.putString("title", state.title());
        saved.putString("validation", validationMessage); saved.putString("focus", focusedRole);
        saved.putInt("selectionStart", selectionStart); saved.putInt("selectionEnd", selectionEnd);
        saved.putInt("scrollPosition", scrollPosition);
        saved.putString("phase", state.phase().name()); saved.putInt("completed", state.completed());
        saved.putInt("total", state.total()); ArrayList<String> labels = new ArrayList<>();
        boolean[] successes = new boolean[state.results().size()]; int index = 0;
        for (TaskState.Result result : state.results()) { labels.add(result.label); successes[index++] = result.success; }
        saved.putStringArrayList("results", labels); saved.putBooleanArray("successes", successes);
        super.onSaveInstanceState(saved);
    }
    private void buildUi() {
        setTheme(dark ? R.style.DemoTheme_Dark : R.style.DemoTheme);
        theme = UiTheme.fromAssets(this, dark);
        ScrollView scroll = new ScrollView(this); mainScroll = scroll; scroll.setFillViewport(true);
        scroll.setBackgroundColor(theme.color("background"));
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        int padding = theme.dp(this, theme.space("lg")); root.setPadding(padding,padding,padding,padding);
        scroll.addView(root);
        TextView heading = text("UI Center · Android Views", "heading"); heading.setTypeface(null,Typeface.BOLD);
        root.addView(heading);
        root.addView(text("所有数据均为虚构。示例只演示主次操作、主题与任务反馈。后台时暂停模拟进度；旋转后保留状态。", "body"));
        Button changeTheme = new Button(this); themeButton = changeTheme;
        changeTheme.setText(dark ? "切换为浅色" : "切换为深色");
        theme.button(changeTheme, false); add(root, changeTheme);
        changeTheme.setOnClickListener(view -> {
            captureUi(); dark = !dark;
            buildUi();
        });
        TextView inputLabel = text("任务名称（可粘贴长文本）", "body"); add(root,inputLabel);
        input = new EditText(this); input.setId(View.generateViewId()); inputLabel.setLabelFor(input.getId());
        input.setSingleLine(false); input.setMinLines(2); input.setMaxLines(5);
        input.setHint("请输入任务名称"); input.setText(inputValue); theme.input(input); add(root,input);
        failure = new CheckBox(this); failure.setText("模拟第三步失败"); failure.setChecked(failDemo);
        theme.text(failure,"body"); failure.setButtonTintList(ColorStateList.valueOf(theme.color("accent")));
        failure.setMinHeight(theme.dp(this,48)); add(root,failure);
        validation = text(validationMessage, "small"); validation.setTextColor(theme.color("error"));
        validation.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE); root.addView(validation);
        actions = new ActionGroup(this,theme,"开始模拟任务（六步）",this::startTask,this::cancelTask); add(root,actions);
        panel = new TaskPanel(this,theme); add(root,panel);
        TextView note = text("取消后已完成项仍可查看；完成或失败后可以再次开始。此状态只用于界面展示，真实任务的恢复与取消由应用负责。", "small");
        note.setTextColor(theme.color("muted")); add(root,note);
        // Insets are read after attachment. Never ask PhoneWindow for its controller before decor exists.
        scroll.setOnApplyWindowInsetsListener((view,insets) -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.ime());
                view.setPadding(bars.left,bars.top,bars.right,bars.bottom);
            } else applyLegacyInsets(view,insets);
            return insets;
        });
        setContentView(scroll); scroll.requestApplyInsets(); theme.systemBars(this); render();
        if (selectionStart >= 0 && selectionEnd >= 0) {
            int length = input.length(); input.setSelection(Math.min(selectionStart,length),Math.min(selectionEnd,length));
        }
        View focused = focusedRole.equals("input") ? input : focusedRole.equals("failure") ? failure
                : focusedRole.equals("primary") ? actions.primaryButton() : focusedRole.equals("cancel")
                ? actions.cancelButton() : focusedRole.equals("theme") ? themeButton : null;
        if (focused != null && focused.isEnabled()) focused.requestFocus();
        int savedScroll = scrollPosition;
        scroll.getViewTreeObserver().addOnGlobalLayoutListener(new ViewTreeObserver.OnGlobalLayoutListener() {
            @Override public void onGlobalLayout() {
                scroll.getViewTreeObserver().removeOnGlobalLayoutListener(this);
                scroll.scrollTo(0,savedScroll);
            }
        });
    }
    /** A theme change rebuilds only presentation; preserve the user's editing context. */
    private void captureUi() {
        inputValue = input.getText().toString(); failDemo = failure.isChecked();
        validationMessage = validation.getText().toString();
        selectionStart = input.getSelectionStart(); selectionEnd = input.getSelectionEnd();
        scrollPosition = mainScroll.getScrollY(); View focused = getCurrentFocus();
        focusedRole = focused == input ? "input" : focused == failure ? "failure"
                : focused == actions.primaryButton() ? "primary" : focused == actions.cancelButton()
                ? "cancel" : focused == themeButton ? "theme" : "";
    }
    @SuppressWarnings("deprecation")
    private void applyLegacyInsets(View view, WindowInsets insets) {
        view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
    }
    private TextView text(String value,String role) {
        TextView label = new TextView(this); label.setText(value); theme.text(label,role); return label;
    }
    private void add(LinearLayout parent,View child) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1,-2);
        params.topMargin = theme.dp(this,theme.space("md")); parent.addView(child,params);
    }
    private void startTask() {
        inputValue = input.getText().toString().trim();
        if (inputValue.isEmpty()) { validation.setText("请输入任务名称。"); input.requestFocus(); return; }
        validation.setText(""); failDemo = failure.isChecked(); state.start(inputValue,6); render();
        handler.postDelayed(tick,600);
    }
    private void cancelTask() {
        if (!state.isRunning()) return;
        handler.removeCallbacks(tick); state.cancel(); render();
    }
    private void render() {
        panel.render(state); actions.setRunning(state.isRunning());
        input.setEnabled(!state.isRunning()); failure.setEnabled(!state.isRunning());
    }
    @Override @SuppressWarnings("deprecation") public void onBackPressed() {
        if (state.isRunning()) cancelTask(); else super.onBackPressed();
    }
}
