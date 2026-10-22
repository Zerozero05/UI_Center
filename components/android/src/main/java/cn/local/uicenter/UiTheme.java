/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from PDF_Bookmarks_Android UiAppearance.java at
 * b44ab5d14e547fef4b80e9469b7c8eb503e2302e. Token mapping replaces its palette.
 */
package cn.local.uicenter;

import android.app.Activity;
import android.content.Context;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.graphics.drawable.StateListDrawable;
import android.os.Build;
import android.view.View;
import android.view.WindowInsetsController;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/** Reads the packaged design-tokens.json. No global theme or preference mutation. */
public final class UiTheme {
    private final JSONObject colors, spacing, typography;
    private final int radius;
    public final boolean dark;
    private UiTheme(JSONObject tokens, boolean dark) throws JSONException {
        this.dark = dark;
        colors = tokens.getJSONObject("themes").getJSONObject(dark ? "dark" : "light");
        spacing = tokens.getJSONObject("spacing"); typography = tokens.getJSONObject("typography");
        radius = tokens.getJSONObject("radii").getInt("control");
    }
    public static UiTheme fromAssets(Context context, boolean dark) {
        try (InputStream input = context.getAssets().open("design-tokens.json")) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] block = new byte[4096]; int count;
            while ((count = input.read(block)) != -1) bytes.write(block, 0, count);
            return new UiTheme(new JSONObject(bytes.toString(StandardCharsets.UTF_8.name())), dark);
        } catch (IOException | JSONException e) {
            throw new IllegalStateException("Package tokens/design-tokens.json as an Android asset", e);
        }
    }
    public int color(String role) {
        try { return Color.parseColor(colors.getString(role)); }
        catch (JSONException e) { throw new IllegalArgumentException("Unknown color role: " + role, e); }
    }
    public int space(String role) {
        try { return spacing.getInt(role); }
        catch (JSONException e) { throw new IllegalArgumentException("Unknown spacing role: " + role, e); }
    }
    public float textSp(String role) {
        try { return (float) typography.getJSONObject(role).getDouble("android_sp"); }
        catch (JSONException e) { throw new IllegalArgumentException("Unknown type role: " + role, e); }
    }
    public int dp(Context context, int value) {
        return Math.round(context.getResources().getDisplayMetrics().density * value);
    }
    public GradientDrawable surface(Context context, String role) {
        GradientDrawable drawable = new GradientDrawable(); drawable.setColor(color(role));
        drawable.setCornerRadius(dp(context, radius)); return drawable;
    }
    public void text(TextView view, String role) {
        view.setTextSize(textSp(role));
        view.setTextColor(new ColorStateList(new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}},
                new int[]{color("disabled"),color("foreground")}));
        view.setHighlightColor(color("selected_background"));
    }
    public void input(EditText input) {
        text(input, "body"); input.setHintTextColor(color("muted"));
        input.setBackgroundTintList(new ColorStateList(new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}},
                new int[]{color("disabled"),color("accent")}));
        input.setMinimumHeight(dp(input.getContext(), 48));
    }
    public void button(Button button, boolean primary) {
        Context context = button.getContext();
        GradientDrawable normal = surface(context, primary ? "accent" : "surface");
        if (!primary) normal.setStroke(dp(context, 1), color("border"));
        GradientDrawable focused = surface(context, primary ? "accent_active" : "hover");
        focused.setStroke(dp(context, 2), color(primary ? "selected_foreground" : "focus"));
        GradientDrawable disabled = surface(context, "hover");
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[]{-android.R.attr.state_enabled}, disabled);
        states.addState(new int[]{android.R.attr.state_focused}, focused);
        states.addState(new int[]{}, normal);
        button.setBackgroundTintList(null);
        button.setBackground(new RippleDrawable(ColorStateList.valueOf(color("border")), states, null));
        button.setTextColor(new ColorStateList(new int[][]{new int[]{-android.R.attr.state_enabled},new int[]{}},
                new int[]{color("disabled"),color(primary ? "selected_foreground" : "accent")}));
        button.setAllCaps(false); button.setTextSize(textSp("body"));
        button.setMinHeight(dp(context, 48)); button.setMinimumHeight(dp(context, 48));
        int horizontal = dp(context, space("md")), vertical = dp(context, space("sm"));
        button.setPadding(horizontal, vertical, horizontal, vertical); button.setStateListAnimator(null);
    }
    @SuppressWarnings("deprecation")
    public void systemBars(Activity activity) {
        View decor = activity.getWindow().getDecorView();
        if (Build.VERSION.SDK_INT < 35) {
            activity.getWindow().setStatusBarColor(color("background"));
            activity.getWindow().setNavigationBarColor(color("background"));
        }
        decor.post(() -> {
            if (Build.VERSION.SDK_INT >= 30) {
                WindowInsetsController controller = decor.getWindowInsetsController();
                if (controller != null) {
                    int flags = WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                            | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS;
                    controller.setSystemBarsAppearance(dark ? 0 : flags, flags);
                }
            } else {
                int flags = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                decor.setSystemUiVisibility(dark ? decor.getSystemUiVisibility() & ~flags
                        : decor.getSystemUiVisibility() | flags);
            }
        });
    }
}
