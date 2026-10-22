/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only
 * Adapted from PDF_Bookmarks_Android TaskOutcome.java at
 * b44ab5d14e547fef4b80e9469b7c8eb503e2302e; generic UI state, no file operations.
 */
package cn.local.uicenter;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/** Main-thread owned display state. The host owns work, cancellation and persistence. */
public final class TaskState {
    public enum Phase { IDLE, RUNNING, SUCCEEDED, FAILED, CANCELLED }
    public static final class Result {
        public final String label;
        public final boolean success;
        public Result(String label, boolean success) {
            this.label = Objects.requireNonNull(label, "label"); this.success = success;
        }
    }
    private String title = "尚未开始";
    private Phase phase = Phase.IDLE;
    private int completed;
    private int total;
    private final ArrayList<Result> results = new ArrayList<>();

    public String title() { return title; }
    public Phase phase() { return phase; }
    public boolean isRunning() { return phase == Phase.RUNNING; }
    public int completed() { return completed; }
    public int total() { return total; }
    public List<Result> results() { return Collections.unmodifiableList(new ArrayList<>(results)); }

    public void start(String title, int total) {
        if (isRunning()) throw new IllegalStateException("A task is already running");
        if (title == null || title.trim().isEmpty() || total < 1)
            throw new IllegalArgumentException("A title and positive total are required");
        this.title = title; this.total = total; completed = 0;
        results.clear(); phase = Phase.RUNNING;
    }
    public void advance(String result) {
        requireRunning();
        results.add(new Result(result, true)); completed++;
        if (completed == total) phase = Phase.SUCCEEDED;
    }
    public void fail(String message) {
        requireRunning(); results.add(new Result(message, false)); phase = Phase.FAILED;
    }
    public void cancel() {
        requireRunning(); phase = Phase.CANCELLED;
    }
    /** Restore a UI snapshot after the host has restored or reconciled its actual task. */
    public static TaskState restore(String title, Phase phase, int completed, int total,
                                    List<Result> results) {
        Objects.requireNonNull(title, "title"); Objects.requireNonNull(phase, "phase");
        Objects.requireNonNull(results, "results");
        if (completed < 0 || total < 0 || completed > total
                || (phase != Phase.IDLE && total == 0)
                || (phase == Phase.RUNNING && completed == total)
                || (phase == Phase.SUCCEEDED && completed != total)
                || (phase == Phase.IDLE && (total != 0 || completed != 0 || !results.isEmpty())))
            throw new IllegalArgumentException("Invalid task snapshot");
        int successes = 0, failures = 0;
        for (Result result : results) {
            if (Objects.requireNonNull(result, "result").success) successes++; else failures++;
        }
        if (successes != completed || failures != (phase == Phase.FAILED ? 1 : 0))
            throw new IllegalArgumentException("Results do not match task progress");
        TaskState state = new TaskState(); state.title = title; state.phase = phase;
        state.completed = completed; state.total = total; state.results.addAll(results); return state;
    }
    private void requireRunning() {
        if (!isRunning()) throw new IllegalStateException("Task is not running");
    }
}
