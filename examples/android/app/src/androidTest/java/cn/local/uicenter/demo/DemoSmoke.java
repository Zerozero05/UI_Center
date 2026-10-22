/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only */
package cn.local.uicenter.demo;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.res.Configuration;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.ScrollView;

/** Device smoke runner using only platform APIs. Invoke with adb shell am instrument -w. */
public final class DemoSmoke extends Instrumentation {
    private Activity activity;
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); start(); }
    @Override public void onStart() {
        Bundle result = new Bundle();
        try {
            activity = startActivitySync(new Intent(getTargetContext(),MainActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            waitForIdleSync();
            onMain(() -> {
                edit().setText(""); button("开始模拟任务（六步）").performClick();
                require(hasText("请输入任务名称。"),"empty input validation");
                button("切换为深色").performClick();
                require(hasText("请输入任务名称。"),"theme retains active validation");
            });
            onMain(() -> {
                require(edit().hasFocus(),"theme retains input focus after validation");
                button("切换为浅色").performClick();
                require(hasText("请输入任务名称。"),"second theme change retains validation");
                edit().setText("保留输入选择与焦点"); edit().requestFocus(); edit().setSelection(2,6);
                button("切换为深色").performClick();
            });
            onMain(() -> {
                require(edit().hasFocus(),"theme retains editing focus");
                require(edit().getSelectionStart() == 2 && edit().getSelectionEnd() == 6,"theme retains selection");
                button("切换为浅色").performClick();
                StringBuilder longTitle = new StringBuilder("旋转与长文本");
                for (int i = 0; i < 18; i++) longTitle.append(" · 中文参数与可访问界面");
                edit().setText(longTitle); button("开始模拟任务（六步）").performClick();
                require(!button("开始模拟任务（六步）").isEnabled(),"start disabled while busy");
                require(button("取消任务").isEnabled(),"cancel enabled while busy");
            });
            awaitText("第 1 项",3000);
            ActivityMonitor rotation = addMonitor(MainActivity.class.getName(),null,false);
            onMain(() -> activity.setRequestedOrientation(activity.getResources().getConfiguration().orientation
                    == Configuration.ORIENTATION_LANDSCAPE ? ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                    : ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE));
            Activity recreated = waitForMonitorWithTimeout(rotation,5000); removeMonitor(rotation);
            require(recreated != null,"rotation recreates Activity"); activity = recreated;
            waitForIdleSync();
            onMain(() -> {
                require(edit().getText().toString().startsWith("旋转与长文本"),"long input restored");
                button("取消任务").performClick();
                require(hasText("已取消"),"cancel status");
                require(hasText("第 1 项"),"partial results survive cancel/rotation");
                button("切换为深色").performClick(); require(hasText("切换为浅色"),"dark theme");
                require(hasText("已取消"),"theme preserves state");
                button("切换为浅色").performClick();
                checkbox().setChecked(true); button("开始模拟任务（六步）").performClick();
            });
            awaitText("模拟第三步失败",5000);
            onMain(() -> {
                require(button("开始模拟任务（六步）").isEnabled(),"retry after failure");
                checkbox().setChecked(false); button("开始模拟任务（六步）").performClick();
            });
            awaitText("已完成 · 6 / 6",7000);
            onMain(() -> {
                ScrollView scroll = (ScrollView)find(root(),view -> view instanceof ScrollView);
                scroll.scrollTo(0,80);
            });
            int[] scrollBefore = {0};
            onMain(() -> {
                scrollBefore[0] = ((ScrollView)find(root(),view -> view instanceof ScrollView)).getScrollY();
                require(scrollBefore[0] > 0,"long results provide nonzero scroll position");
                button("切换为深色").performClick();
            });
            onMain(() -> require(((ScrollView)find(root(),view -> view instanceof ScrollView)).getScrollY()
                    == scrollBefore[0],"theme retains scroll position"));
            result.putString("stream","UI Center Android device smoke passed: input, validation retention, selection, focus, scroll, long text, busy, rotation, cancel, themes, failure, retry, success.\n");
            finish(Activity.RESULT_OK,result);
        } catch (Throwable failure) {
            result.putString("stream","UI Center smoke FAILED: " + failure + "\n");
            finish(Activity.RESULT_CANCELED,result);
        } finally {
            if (activity != null) onMain(() -> activity.finish());
        }
    }
    private void onMain(Runnable action) { runOnMainSync(action); waitForIdleSync(); }
    private View root() { return activity.getWindow().getDecorView(); }
    private Button button(String label) {
        View found = find(root(),view -> view instanceof Button && ((Button)view).getText().toString().equals(label));
        require(found != null,"button exists: " + label); return (Button)found;
    }
    private EditText edit() { return (EditText)find(root(),view -> view instanceof EditText); }
    private CheckBox checkbox() { return (CheckBox)find(root(),view -> view instanceof CheckBox); }
    private boolean hasText(String value) {
        return find(root(),view -> view instanceof TextView && ((TextView)view).getText().toString().contains(value)) != null;
    }
    private interface Matcher { boolean matches(View view); }
    private View find(View view, Matcher matcher) {
        if (matcher.matches(view)) return view;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup)view;
            for (int i = 0; i < group.getChildCount(); i++) {
                View child = find(group.getChildAt(i),matcher); if (child != null) return child;
            }
        }
        return null;
    }
    private void awaitText(String value,long timeout) {
        long end = SystemClock.uptimeMillis() + timeout;
        while (SystemClock.uptimeMillis() < end) {
            boolean[] found = {false}; onMain(() -> found[0] = hasText(value));
            if (found[0]) return; SystemClock.sleep(100);
        }
        throw new AssertionError("Timed out waiting for: " + value);
    }
    private static void require(boolean condition,String message) {
        if (!condition) throw new AssertionError(message);
    }
}
