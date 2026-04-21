# Note: 
# Run "python -m streamlit run app.py" to see visuals.

import os
from datetime import date
import streamlit as st
from pawpal_system import Task, Pet, Owner, Schedule

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
owner_name = st.text_input("Owner name", value="Jordan")
time_available = st.number_input("Available time today (hours)", min_value=0.5, max_value=24.0, value=4.0, step=0.5)

if st.button("Set / Update Owner"):
    st.session_state.owner = Owner(owner_name, time_available)
    st.session_state.owner.save_to_json()
    # Clear schedule when owner changes
    st.session_state.pop("schedule", None)

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

st.divider()

# ── Add a Task ─────────────────────────────────────────────────────────────────
st.subheader("Add a Task")

PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
DONE_BADGE = {True: "✅", False: "⬜"}

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

    if st.button("Add Task"):
        recurrence_val = None if recurrence_input == "none" else recurrence_input
        new_task = Task(task_title, int(duration), priority,
                        recurrence=recurrence_val,
                        due_date=due_date_input)
        target_pet.addTask(new_task)
        owner.save_to_json()
        st.success(f"Task **{task_title}** added to **{target_pet_name}**.")

    all_tasks = owner.getAllTasks()
    if all_tasks:
        overdue = [t for t in all_tasks if t.isOverdue()]
        if overdue:
            st.error(f"⚠️ {len(overdue)} overdue task(s) need attention.")
            with st.expander("View overdue tasks"):
                for t in overdue:
                    pet_name = t.pet.getName() if t.pet else "—"
                    st.write(f"- **{t.getName()}** ({pet_name}) — due {t.due_date}")

        st.caption("All tasks across pets")
        task_rows = [
            {
                "Pet": t.pet.getName() if t.pet else "—",
                "Task": t.getName(),
                "Duration (min)": t.getDuration(),
                "Priority": PRIORITY_BADGE.get(t.getPriority(), t.getPriority()),
                "Recurrence": t.recurrence or "—",
                "Due Date": str(t.due_date),
                "Status": "⚠️ Overdue" if t.isOverdue() else ("✅ Done" if t.isCompleted() else "—"),
                "Done": t.isCompleted(),
            }
            for t in all_tasks
        ]
        edited_tasks = st.data_editor(
            task_rows,
            column_config={"Done": st.column_config.CheckboxColumn("Done", default=False)},
            disabled=["Pet", "Task", "Duration (min)", "Priority", "Recurrence", "Due Date", "Status"],
            use_container_width=True,
            hide_index=True,
            key="all_tasks_editor",
        )
        changed = False
        for i, row in enumerate(edited_tasks):
            if row["Done"] and not all_tasks[i].isCompleted():
                all_tasks[i].markCompleted()
                changed = True
        if changed:
            owner.save_to_json()
            st.rerun()

        st.caption("Edit or delete a task")
        task_labels = [
            f"{i + 1}. {t.pet.getName()} — {t.getName()} ({t.getDuration()} min)"
            for i, t in enumerate(all_tasks)
        ]
        selected_label = st.selectbox("Select task", task_labels, key="edit_select")
        selected_task = all_tasks[task_labels.index(selected_label)]

        with st.expander("Edit selected task"):
            edit_col1, edit_col2, edit_col3 = st.columns(3)
            with edit_col1:
                new_title = st.text_input("Title", value=selected_task.getName(), key="edit_title")
            with edit_col2:
                new_duration = st.number_input("Duration (min)", min_value=1, max_value=480,
                                               value=int(selected_task.getDuration()), key="edit_dur")
            with edit_col3:
                pri_options = ["low", "medium", "high"]
                new_priority = st.selectbox("Priority", pri_options,
                                            index=pri_options.index(selected_task.getPriority()),
                                            key="edit_pri")

            edit_col4, edit_col5 = st.columns(2)
            with edit_col4:
                recur_options = ["none", "daily", "weekly"]
                current_recur = selected_task.recurrence or "none"
                new_recurrence = st.selectbox("Recurrence", recur_options,
                                              index=recur_options.index(current_recur),
                                              key="edit_recur")
            with edit_col5:
                new_due_date = st.date_input("Due date", value=selected_task.due_date, key="edit_due")

            if st.button("Update Task"):
                selected_task.name = new_title
                selected_task.duration = int(new_duration)
                selected_task.priority = new_priority
                selected_task.recurrence = None if new_recurrence == "none" else new_recurrence
                selected_task.due_date = new_due_date
                owner.save_to_json()
                st.session_state.pop("schedule", None)
                st.success("Task updated.")
                st.rerun()

        if st.button("Delete Selected Task", type="secondary"):
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
                st.write(f"- **{a.getName()}** ({a_pet}) and **{b.getName()}** ({b_pet}) — both at `{a.time}`")

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
                "Time": t.time,
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
            st.success(f"Next available slot: **{slot}** — fits {int(slot_duration)} min")
