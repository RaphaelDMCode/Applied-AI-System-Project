# Note: 
# Run "python -m streamlit run app.py" to see visuals.

import os
from datetime import date
import streamlit as st
from pawpal_system import Task, Pet, Owner, Schedule
from agent import PawPalAgent

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ── Session choice prompt (only shown when saved data exists and no choice yet) ─
if "owner" not in st.session_state and "session_choice" not in st.session_state:
    if os.path.exists("data.json"):
        st.info("💾 A saved session was found. How would you like to continue?")
        col_resume, col_new = st.columns(2)
        if col_resume.button("▶ Resume Previous Session", use_container_width=True):
            st.session_state.session_choice = "resume"
            st.rerun()
        if col_new.button("🆕 Start New Session", use_container_width=True):
            st.session_state.session_choice = "new"
            st.rerun()
        st.stop()

# ── Owner setup ────────────────────────────────────────────────────────────────
st.subheader("Owner")
owner_name = st.text_input("Owner name", value="", placeholder="Input Name Here")
time_available = st.number_input("Available time today (hours)", min_value=0.5, max_value=24.0, value=4.0, step=0.5)

if st.button("Set / Update Owner"):
    st.session_state.owner = Owner(owner_name, time_available)
    st.session_state.owner.save_to_json()
    for _k in ("schedule", "agent_explanation", "agent_proposed", "agent_snapshot", "agent_schedule"):
        st.session_state.pop(_k, None)

# Load saved data only when the user chose to resume
if "owner" not in st.session_state and st.session_state.get("session_choice") == "resume":
    try:
        st.session_state.owner = Owner.load_from_json("data.json")
    except Exception as e:
        st.error(f"⚠️ Could not load saved session: {e}. Please set up a new owner below.")
        st.session_state.session_choice = "new"

if "owner" not in st.session_state:
    st.info("Set the owner above to get started.")
    st.stop()

owner: Owner = st.session_state.owner
st.success(f"Owner: **{owner.getName()}** — {owner.getTimeAvailability()}h available")

st.divider()

# ── Add a Pet ──────────────────────────────────────────────────────────────────
st.subheader("Add a Pet")
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with col3:
    preferences = st.text_input("Owner preferences", value="Prefers morning walks")

col4, col5, col6 = st.columns(3)
with col4:
    breed_input = st.text_input("Breed", value="Mixed")
with col5:
    age_input = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=1.0, step=0.5)
with col6:
    weight_input = st.number_input("Weight (lbs)", min_value=0.1, max_value=300.0, value=10.0, step=0.5)

if st.button("Add Pet"):
    existing_names = [p.getName() for p in owner.getPets()]
    if pet_name in existing_names:
        st.warning(f"A pet named **{pet_name}** is already added.")
    else:
        new_pet = Pet(pet_name, species, preferences,
                      breed=breed_input, age=age_input, weight=weight_input)
        owner.addPet(new_pet)
        owner.save_to_json()
        st.success(f"Added **{pet_name}** ({species}) to {owner.getName()}'s care list.")

pets = owner.getPets()
if pets:
    st.caption("Current pets")
    st.dataframe(
        [
            {
                "Name": p.getName(),
                "Type": p.getType(),
                "Breed": p.getBreed(),
                "Age (yrs)": p.getAge(),
                "Weight (lbs)": p.getWeight(),
                "Preferences": p.getPreferences(),
                "Tasks": len(p.getTasks()),
            }
            for p in pets
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.caption("Edit or remove a pet")
    pet_labels = [f"{p.getName()} ({p.getType()})" for p in pets]
    selected_pet_label = st.selectbox("Select pet", pet_labels, key="pet_edit_select")
    selected_pet = pets[pet_labels.index(selected_pet_label)]

    with st.expander("Edit selected pet"):
        ep_col1, ep_col2, ep_col3 = st.columns(3)
        with ep_col1:
            ep_name = st.text_input("Pet name", value=selected_pet.getName(), key="ep_name")
        with ep_col2:
            ep_species_opts = ["dog", "cat", "other"]
            ep_species = st.selectbox("Species", ep_species_opts,
                                      index=ep_species_opts.index(selected_pet.getType()) if selected_pet.getType() in ep_species_opts else 2,
                                      key="ep_species")
        with ep_col3:
            ep_prefs = st.text_input("Owner preferences", value=selected_pet.getPreferences(), key="ep_prefs")

        ep_col4, ep_col5, ep_col6 = st.columns(3)
        with ep_col4:
            ep_breed = st.text_input("Breed", value=selected_pet.getBreed(), key="ep_breed")
        with ep_col5:
            ep_age = st.number_input("Age (years)", min_value=0.0, max_value=30.0,
                                     value=float(selected_pet.getAge()), step=0.5, key="ep_age")
        with ep_col6:
            ep_weight = st.number_input("Weight (lbs)", min_value=0.1, max_value=300.0,
                                        value=max(0.1, float(selected_pet.getWeight())), step=0.5, key="ep_weight")

        if st.button("Update Pet"):
            selected_pet.name = ep_name
            selected_pet.type = ep_species
            selected_pet.ownerPreferences = ep_prefs
            selected_pet.breed = ep_breed
            selected_pet.age = ep_age
            selected_pet.weight = ep_weight
            owner.save_to_json()
            st.success(f"Updated **{ep_name}**.")
            st.rerun()

    if st.button("Remove Selected Pet", type="secondary", key="remove_pet_btn"):
        owner.removePet(selected_pet)
        owner.save_to_json()
        st.session_state.pop("schedule", None)
        st.success(f"Removed **{selected_pet.getName()}**.")
        st.rerun()

st.divider()

# ── Add a Task ─────────────────────────────────────────────────────────────────
st.subheader("Add a Task")

PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
DONE_BADGE = {True: "✅", False: "⬜"}

def _to_12h(t: str) -> str:
    try:
        h, m = map(int, t.split(":"))
        return f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    except Exception:
        return t

if not pets:
    st.info("Add at least one pet before scheduling tasks.")
else:
    pet_names = [p.getName() for p in pets]
    target_pet_name = st.selectbox("Assign task to pet", pet_names)
    target_pet = next(p for p in pets if p.getName() == target_pet_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5 = st.columns(2)
    with col4:
        recur_options = ["none", "daily", "weekly"]
        recurrence_input = st.selectbox("Recurrence", recur_options, index=0)
    with col5:
        due_date_input = st.date_input("Due date", value=date.today())

    use_preferred_time = st.checkbox("Set a preferred start time (optional)")
    preferred_time_str = "00:00"
    if use_preferred_time:
        import datetime as dt
        _time_opts = [
            f"{_h % 12 or 12}:{_m:02d} {'AM' if _h < 12 else 'PM'}"
            for _h in range(24) for _m in (0, 30)
        ]
        _selected_time = st.selectbox(
            "Preferred start time", _time_opts,
            index=_time_opts.index("8:00 AM"),
        )
        preferred_time_str = dt.datetime.strptime(_selected_time, "%I:%M %p").strftime("%H:%M")
        st.caption("The AI agent will try to honour this time when building your schedule.")

    if st.button("Add Task"):
        recurrence_val = None if recurrence_input == "none" else recurrence_input
        new_task = Task(task_title, int(duration), priority,
                        time=preferred_time_str,
                        has_preferred_time=use_preferred_time,
                        recurrence=recurrence_val,
                        due_date=due_date_input)
        try:
            target_pet.addTask(new_task)
            owner.save_to_json()
            st.success(f"Task **{task_title}** added to **{target_pet_name}**.")
        except ValueError as e:
            st.warning(str(e))

    all_tasks = owner.getAllTasks()
    if all_tasks:
        overdue = [t for t in all_tasks if t.isOverdue()]
        if overdue:
            st.error(f"⚠️ {len(overdue)} overdue task(s) need attention.")
            with st.expander("View overdue tasks"):
                for t in overdue:
                    pet_name = t.pet.getName() if t.pet else "—"
                    st.write(f"- **{t.getName()}** ({pet_name}) — due {t.due_date}")

        display_tasks = all_tasks

        if "task_editor_ver" not in st.session_state:
            st.session_state.task_editor_ver = 0

        st.caption("All tasks across pets")
        task_rows = [
            {
                "Pet": t.pet.getName() if t.pet else "—",
                "Task": t.getName(),
                "Duration (min)": t.getDuration(),
                "Priority": PRIORITY_BADGE.get(t.getPriority(), t.getPriority()),
                "Preferred Time": (
                    f"{int(t.time.split(':')[0]) % 12 or 12}:{t.time.split(':')[1]} "
                    f"{'AM' if int(t.time.split(':')[0]) < 12 else 'PM'}"
                    if t.has_preferred_time else "—"
                ),
                "Recurrence": t.recurrence or "—",
                "Due Date": str(t.due_date),
                "Status": "⚠️ Overdue" if t.isOverdue() else ("✅ Done" if t.isCompleted() else "—"),
                "Done": t.isCompleted(),
            }
            for t in display_tasks
        ]
        edited_tasks = st.data_editor(
            task_rows,
            column_config={"Done": st.column_config.CheckboxColumn("Done", default=False)},
            disabled=["Pet", "Task", "Duration (min)", "Priority", "Preferred Time", "Recurrence", "Due Date", "Status"],
            use_container_width=True,
            hide_index=True,
            key=f"all_tasks_editor_{st.session_state.task_editor_ver}",
        )
        changed = False
        for i, row in enumerate(edited_tasks):
            task = display_tasks[i]
            if row["Done"] and not task.isCompleted():
                task.completed = True
                changed = True
            elif not row["Done"] and task.isCompleted():
                task.completed = False
                changed = True
        if changed:
            owner.save_to_json()
            st.session_state.task_editor_ver += 1
            st.rerun()

        if display_tasks:
            import datetime as dt
            st.caption("Edit or delete a task")
            task_labels = [
                f"{i + 1}. {t.pet.getName()} — {t.getName()} ({t.getDuration()} min)"
                for i, t in enumerate(display_tasks)
            ]
            selected_label = st.selectbox("Select task", task_labels, key="edit_select")
            selected_idx = task_labels.index(selected_label)
            selected_task = display_tasks[selected_idx]
            _kp = f"e{selected_idx}"

            with st.expander("Edit selected task"):
                edit_col1, edit_col2, edit_col3 = st.columns(3)
                with edit_col1:
                    new_title = st.text_input("Title", value=selected_task.getName(), key=f"{_kp}_title")
                with edit_col2:
                    new_duration = st.number_input("Duration (min)", min_value=1, max_value=480,
                                                   value=int(selected_task.getDuration()), key=f"{_kp}_dur")
                with edit_col3:
                    pri_options = ["low", "medium", "high"]
                    new_priority = st.selectbox("Priority", pri_options,
                                                index=pri_options.index(selected_task.getPriority()),
                                                key=f"{_kp}_pri")

                edit_col4, edit_col5 = st.columns(2)
                with edit_col4:
                    recur_options = ["none", "daily", "weekly"]
                    current_recur = selected_task.recurrence or "none"
                    new_recurrence = st.selectbox("Recurrence", recur_options,
                                                  index=recur_options.index(current_recur),
                                                  key=f"{_kp}_recur")
                with edit_col5:
                    new_due_date = st.date_input("Due date", value=selected_task.due_date, key=f"{_kp}_due")

                _has_pref = selected_task.has_preferred_time
                edit_use_time = st.checkbox("Set preferred start time", value=_has_pref, key=f"{_kp}_use_time")
                new_time_for_update = "00:00"
                if edit_use_time:
                    edit_col6, _ = st.columns([2, 1])
                    with edit_col6:
                        _edit_time_opts = [
                            f"{_h % 12 or 12}:{_m:02d} {'AM' if _h < 12 else 'PM'}"
                            for _h in range(24) for _m in (0, 30)
                        ]
                        if selected_task.has_preferred_time:
                            _cur_h, _cur_m = map(int, selected_task.time.split(":"))
                            _cur_label = f"{_cur_h % 12 or 12}:{_cur_m:02d} {'AM' if _cur_h < 12 else 'PM'}"
                            _default_idx = _edit_time_opts.index(_cur_label) if _cur_label in _edit_time_opts else _edit_time_opts.index("8:00 AM")
                        else:
                            _default_idx = _edit_time_opts.index("8:00 AM")
                        new_time_label = st.selectbox(
                            "Preferred start time", _edit_time_opts,
                            index=_default_idx,
                            key=f"{_kp}_time",
                        )
                        new_time_for_update = dt.datetime.strptime(new_time_label, "%I:%M %p").strftime("%H:%M")

                if st.button("Update Task", key=f"{_kp}_update"):
                    selected_task.name = new_title
                    selected_task.duration = int(new_duration)
                    selected_task.priority = new_priority
                    selected_task.recurrence = None if new_recurrence == "none" else new_recurrence
                    selected_task.due_date = new_due_date
                    selected_task.time = new_time_for_update
                    selected_task.has_preferred_time = edit_use_time
                    owner.save_to_json()
                    st.session_state.pop("schedule", None)
                    st.success("Task updated.")
                    st.rerun()

            if st.button("Delete Selected Task", type="secondary", key=f"{_kp}_delete"):
                if selected_task.pet:
                    selected_task.pet.removeTask(selected_task)
                owner.save_to_json()
                st.session_state.pop("schedule", None)
                st.success(f"Deleted **{selected_task.getName()}**.")
                st.rerun()

st.divider()

# ── Generate Schedule ──────────────────────────────────────────────────────────
st.subheader("Build Schedule")

if st.button("Generate Schedule"):
    if not owner.getAllTasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        sched = Schedule(owner)
        sched.generateSchedule()
        st.session_state.schedule = sched
        for _k in ("agent_explanation", "agent_proposed", "agent_snapshot", "agent_schedule"):
            st.session_state.pop(_k, None)

if "schedule" in st.session_state:
    sched: Schedule = st.session_state.schedule

    # ── Availability banner ────────────────────────────────────────────────────
    if sched.canFitSchedule():
        st.success("All tasks fit within your available time.")
    else:
        st.error("Tasks exceed available time — consider removing lower-priority items.")

    # ── Conflict warnings via Schedule.getConflicts() ──────────────────────────
    if sched.hasConflicts():
        conflicts = sched.getConflicts()
        st.warning(f"{len(conflicts)} scheduling conflict(s) detected.")
        with st.expander("View conflicts"):
            for a, b in conflicts:
                a_pet = a.pet.getName() if a.pet else "?"
                b_pet = b.pet.getName() if b.pet else "?"
                st.write(f"- **{a.getName()}** ({a_pet}) and **{b.getName()}** ({b_pet}) — both at `{_to_12h(a.time)}`")

    # ── Overdue warnings via Schedule.getOverdueTasks() ───────────────────────
    overdue_sched = sched.getOverdueTasks()
    if overdue_sched:
        st.error(f"⚠️ {len(overdue_sched)} overdue task(s) in this schedule.")
        with st.expander("View overdue tasks"):
            for t in overdue_sched:
                pet_name = t.pet.getName() if t.pet else "—"
                st.write(f"- **{t.getName()}** ({pet_name}) — due {t.due_date}")

    # ── Summary metrics ────────────────────────────────────────────────────────
    total_min = sched.getTotalScheduledTime()
    avail_h = owner.getTimeAvailability()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total tasks", len(sched.getTasks()))
    m2.metric("Total time (min)", int(total_min))
    m3.metric("Available (h)", avail_h)
    m4.metric("High priority", len(sched.getTasksByPriority("high")))
    m5.metric("Overdue", len(overdue_sched))

    # ── Filter by pet via Schedule.filterTasks() ───────────────────────────────
    pet_options = ["All pets"] + [p.getName() for p in owner.getPets()]
    selected_pet = st.selectbox("Filter by pet", pet_options)

    filtered = (
        sched.filterTasks()
        if selected_pet == "All pets"
        else sched.filterTasks(pet_name=selected_pet)
    )

    # ── Table sorted by time via Schedule.sort_by_time() ──────────────────────
    sorted_tasks = sorted(filtered, key=lambda t: t.time)

    st.caption(f"{len(sorted_tasks)} task(s) — sorted by scheduled time")
    if sorted_tasks:
        sched_rows = [
            {
                "Time": _to_12h(t.time),
                "Pet": t.pet.getName() if t.pet else "—",
                "Task": t.getName(),
                "Duration (min)": t.getDuration(),
                "Priority": PRIORITY_BADGE.get(t.getPriority(), t.getPriority()),
                "Status": "⚠️ Overdue" if t.isOverdue() else ("✅ Done" if t.isCompleted() else "—"),
                "Done": t.isCompleted(),
            }
            for t in sorted_tasks
        ]
        edited_sched = st.data_editor(
            sched_rows,
            column_config={"Done": st.column_config.CheckboxColumn("Done", default=False)},
            disabled=["Time", "Pet", "Task", "Duration (min)", "Priority", "Status"],
            use_container_width=True,
            hide_index=True,
            key="schedule_editor",
        )
        changed = False
        for i, row in enumerate(edited_sched):
            if row["Done"] and not sorted_tasks[i].isCompleted():
                sorted_tasks[i].markCompleted()
                changed = True
            elif not row["Done"] and sorted_tasks[i].isCompleted():
                sorted_tasks[i].markIncomplete()
                changed = True
        if changed:
            owner.save_to_json()
            st.rerun()
    else:
        st.info("No tasks match the selected filter.")

    st.divider()

    # ── Next Available Slot finder ─────────────────────────────────────────────
    st.subheader("Find Next Available Slot")
    slot_duration = st.number_input(
        "Task duration to fit (minutes)", min_value=1, max_value=480, value=30, key="slot_dur"
    )
    if st.button("Find Slot"):
        slot = sched.findNextAvailableSlot(int(slot_duration))
        if slot == "No slot available today":
            st.error("No available slot today for that duration.")
        else:
            st.success(f"Next available slot: **{_to_12h(slot)}** — fits {int(slot_duration)} min")

st.divider()

# ── AI Schedule Agent ──────────────────────────────────────────────────────────
st.subheader("AI Schedule Agent")
st.caption(
    "The AI agent analyses your schedule, detects conflicts and overdue tasks, "
    "suggests fixes, and explains its reasoning. You decide whether to apply the changes."
)

if not owner.getAllTasks():
    st.info("Add at least one task before running the AI agent.")
else:
    _proposal_pending = "agent_explanation" in st.session_state
    if _proposal_pending:
        st.caption("Accept or reject the current proposal before running the agent again.")
    if st.button("Run AI Agent", type="primary", disabled=_proposal_pending):
        # Snapshot current task times so Reject can restore them
        st.session_state.agent_snapshot = {
            (t.pet.getName() if t.pet else "", t.getName()): t.time
            for t in owner.getAllTasks()
        }
        sched_agent = Schedule(owner)
        with st.spinner("AI agent is analysing your schedule..."):
            try:
                agent = PawPalAgent(sched_agent)
                explanation, proposed, steps = agent.run()
            except Exception as e:
                st.error(f"Agent error: {e}")
                st.stop()
        st.session_state.agent_explanation = explanation
        st.session_state.agent_proposed    = proposed
        st.session_state.agent_schedule    = sched_agent
        st.session_state.agent_steps       = steps
        st.rerun()

    if "agent_explanation" in st.session_state:
        # ── Reasoning trace ────────────────────────────────────────────────────
        agent_steps = st.session_state.get("agent_steps", [])
        if agent_steps:
            with st.expander(f"🔍 Agent reasoning steps ({len(agent_steps)} tool calls)", expanded=False):
                for s in agent_steps:
                    tool  = s["tool"]
                    args  = s["args"]
                    result = s["result"]

                    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items()) if args else ""
                    st.markdown(f"**Step {s['step']}: `{tool}({args_str})`**")

                    if tool == "generate_schedule":
                        n = result.get("total_tasks", 0)
                        rows = result.get("tasks", [])
                        st.caption(f"{n} task(s) scheduled")
                        if rows:
                            st.dataframe(
                                [{"Time": _to_12h(r["time"]), "Pet": r["pet"], "Task": r["task"],
                                  "Priority": r["priority"], "Duration (min)": r["duration_minutes"]}
                                 for r in rows],
                                use_container_width=True, hide_index=True,
                            )

                    elif tool == "get_conflicts":
                        n = result.get("count", 0)
                        if n == 0:
                            st.caption("No conflicts found.")
                        else:
                            st.caption(f"{n} conflict(s) detected:")
                            for c in result.get("conflicts", []):
                                st.write(f"- **{c['task_a']}** ({c['pet_a']}) vs **{c['task_b']}** ({c['pet_b']}) — both at `{_to_12h(c['shared_time'])}`")

                    elif tool == "get_overdue_tasks":
                        n = result.get("count", 0)
                        if n == 0:
                            st.caption("No overdue tasks.")
                        else:
                            st.caption(f"{n} overdue task(s):")
                            for t in result.get("overdue_tasks", []):
                                st.write(f"- **{t['task']}** ({t['pet']}) — due {t['due_date']}, priority: {t['priority']}")

                    elif tool == "check_capacity":
                        fits   = result.get("fits_within_availability")
                        used   = result.get("total_scheduled_minutes", 0)
                        avail  = result.get("available_minutes", 0)
                        over   = result.get("over_by_minutes", 0)
                        status = "✅ Fits" if fits else f"⚠️ Over by {over} min"
                        st.caption(f"{status} — {used} min used / {avail} min available")

                    elif tool == "find_next_slot":
                        slot = result.get("available_slot", "—")
                        dur  = result.get("duration_requested", 0)
                        st.caption(f"Next open slot for {dur} min: **{_to_12h(slot)}**")

                    elif tool == "reschedule_task":
                        if result.get("success"):
                            st.caption(
                                f"Moved **{result['task']}** ({result['pet']}) "
                                f"from `{_to_12h(result['moved_from'])}` → `{_to_12h(result['moved_to'])}`"
                            )
                        else:
                            st.caption(f"⚠️ {result.get('message', 'Reschedule failed.')}")

                    else:
                        st.json(result)

                    st.markdown("---")

        st.markdown("#### Agent's Report")
        st.info(st.session_state.agent_explanation)

        st.caption("Proposed schedule (read-only — accept or reject below)")
        st.dataframe(
            [
                {
                    "Time":           _to_12h(t["time"]),
                    "Pet":            t["pet"],
                    "Task":           t["task"],
                    "Priority":       PRIORITY_BADGE.get(t["priority"], t["priority"]),
                    "Duration (min)": t["duration_minutes"],
                }
                for t in sorted(st.session_state.agent_proposed, key=lambda t: t["time"])
            ],
            use_container_width=True,
            hide_index=True,
        )

        col_accept, col_reject = st.columns(2)

        if col_accept.button("Accept Changes", type="primary", use_container_width=True):
            owner.save_to_json()
            st.session_state.schedule = st.session_state.agent_schedule
            for key in ("agent_explanation", "agent_proposed", "agent_snapshot", "agent_schedule", "agent_steps"):
                st.session_state.pop(key, None)
            st.success("Schedule accepted and saved.")
            st.rerun()

        if col_reject.button("Reject Changes", use_container_width=True):
            snapshot = st.session_state.get("agent_snapshot", {})
            for t in owner.getAllTasks():
                key = (t.pet.getName() if t.pet else "", t.getName())
                if key in snapshot:
                    t.time = snapshot[key]
            for key in ("agent_explanation", "agent_proposed", "agent_snapshot", "agent_schedule", "agent_steps"):
                st.session_state.pop(key, None)
            st.info("Changes rejected. Original times restored.")
            st.rerun()
