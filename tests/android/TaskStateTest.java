/* Copyright (C) 2026 Zerozero05. SPDX-License-Identifier: AGPL-3.0-only */
import cn.local.uicenter.TaskState;
import java.util.List;

/** Host JVM regression suite: no JUnit or Android runtime required. */
public final class TaskStateTest {
    private static int checks;
    private static void check(boolean value,String message) {
        checks++; if (!value) throw new AssertionError(message);
    }
    private static void rejects(Runnable action,String message) {
        boolean thrown = false;
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { thrown = true; }
        check(thrown,message);
    }
    public static void main(String[] args) {
        TaskState state = new TaskState();
        check(state.phase() == TaskState.Phase.IDLE && state.results().isEmpty(),"initial state");
        rejects(() -> state.start("",2),"blank title rejected");
        rejects(() -> state.start("sample",0),"zero steps rejected");
        state.start("中文任务",3); state.advance("first");
        List<TaskState.Result> snapshot = state.results();
        rejects(() -> state.start("overlap",2),"overlapping task rejected");
        state.cancel();
        check(state.phase() == TaskState.Phase.CANCELLED && state.completed() == 1,"cancel preserves progress");
        check(state.results().get(0).label.equals("first"),"cancel preserves earlier results");
        rejects(() -> state.advance("late callback"),"terminal state rejects late update");
        TaskState restored = TaskState.restore(state.title(),state.phase(),state.completed(),state.total(),state.results());
        check(restored.phase() == TaskState.Phase.CANCELLED && restored.completed() == 1,"cancel restore");
        state.start("retry",2); state.advance("retained"); state.fail("failure details");
        check(state.phase() == TaskState.Phase.FAILED && state.completed() == 1,"failure preserves partial progress");
        check(state.results().size() == 2 && !state.results().get(1).success,"failure detail retained");
        check(snapshot.size() == 1 && snapshot.get(0).label.equals("first"),"snapshots do not drift on retry");
        restored = TaskState.restore(state.title(),state.phase(),state.completed(),state.total(),state.results());
        check(restored.results().get(1).label.equals("failure details"),"failed restore");
        state.start("rotation",2); state.advance("one");
        restored = TaskState.restore(state.title(),state.phase(),state.completed(),state.total(),state.results());
        restored.advance("two");
        check(restored.phase() == TaskState.Phase.SUCCEEDED && restored.completed() == 2,"running restore resumes");
        check(state.phase() == TaskState.Phase.RUNNING && state.completed() == 1,"restored state is independent");
        rejects(() -> TaskState.restore("bad",TaskState.Phase.SUCCEEDED,1,2,state.results()),"incomplete success rejected");
        rejects(() -> TaskState.restore("bad",TaskState.Phase.CANCELLED,0,2,state.results()),"mismatched results rejected");
        System.out.println("TaskState: " + checks + " checks passed");
    }
}
