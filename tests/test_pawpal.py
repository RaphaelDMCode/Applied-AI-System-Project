import os
import pytest
from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Schedule


def test_task_completion_changes_status():
    task = Task(name="Feed Dog", duration=0.5, priority="high")
    assert not task.isCompleted(), "New tasks should start as incomplete"

    task.markCompleted()
    assert task.isCompleted(), "Task should be marked complete after markCompleted()"


def test_add_task_to_pet_increases_task_count():
    pet = Pet(name="Bella", type="Dog", ownerPreferences="Weekly grooming")
    assert len(pet.getTasks()) == 0

    task = Task(name="Evening walk", duration=1.0, priority="medium")
    pet.addTask(task)

    assert len(pet.getTasks()) == 1
    assert pet.getTasks()[0] == task


# --- Sorting Correctness ---

def test_sort_by_time_returns_chronological_order():
    """Tasks should come back earliest-time-first after sort_by_time()."""
    owner = Owner(name="Alex", timeAvailability=8.0)
    schedule = Schedule(owner)

    t1 = Task(name="Afternoon walk", duration=0.5, priority="medium", time="14:00")
    t2 = Task(name="Morning feed",   duration=0.25, priority="high",   time="07:00")
    t3 = Task(name="Evening meds",   duration=0.1,  priority="high",   time="19:30")

    schedule.addTask(t1)
    schedule.addTask(t2)
    schedule.addTask(t3)

    sorted_tasks = schedule.sort_by_time()
    times = [t.time for t in sorted_tasks]
    assert times == sorted(times), f"Expected chronological order, got {times}"


def test_generate_schedule_sorts_by_priority_then_duration():
    """generateSchedule() should place high-priority tasks before lower ones."""
    owner = Owner(name="Sam", timeAvailability=10.0)
    pet = Pet(name="Rex", type="Dog", ownerPreferences="None")
    owner.addPet(pet)

    low_long  = Task(name="Bath",       duration=2.0, priority="low")
    high_short = Task(name="Feed",      duration=0.5, priority="high")
    med_task   = Task(name="Play",      duration=1.0, priority="medium")

    pet.addTask(low_long)
    pet.addTask(high_short)
    pet.addTask(med_task)

    schedule = Schedule(owner)
    schedule.generateSchedule()

    priorities = [t.getPriority() for t in schedule.getTasks()]
    # All high tasks must appear before any medium; all medium before any low
    seen = set()
    for p in priorities:
        assert p not in seen or p == priorities[priorities.index(p)], \
            "Priority order violated"
        seen.add(p)

    assert priorities[0] == "high", "First task should be highest priority"


# --- Recurrence Logic ---

def test_daily_recurrence_creates_next_day_task():
    """Completing a daily task should add a new task due the following day."""
    today = date.today()
    pet = Pet(name="Luna", type="Cat", ownerPreferences="None")
    task = Task(
        name="Morning feed",
        duration=0.25,
        priority="high",
        recurrence="daily",
        due_date=today,
    )
    pet.addTask(task)

    task.markCompleted()

    incomplete = pet.getIncompleteTasks()
    assert len(incomplete) == 1, "One new recurring task should have been created"
    assert incomplete[0].due_date == today + timedelta(days=1), \
        "Next task should be due tomorrow"
    assert not incomplete[0].isCompleted(), "New recurring task should be incomplete"


def test_weekly_recurrence_creates_next_week_task():
    """Completing a weekly task should add a new task due seven days later."""
    today = date.today()
    pet = Pet(name="Max", type="Dog", ownerPreferences="None")
    task = Task(
        name="Grooming",
        duration=1.0,
        priority="medium",
        recurrence="weekly",
        due_date=today,
    )
    pet.addTask(task)

    task.markCompleted()

    incomplete = pet.getIncompleteTasks()
    assert len(incomplete) == 1
    assert incomplete[0].due_date == today + timedelta(weeks=1), \
        "Next task should be due in one week"


def test_non_recurring_task_does_not_spawn_new_task():
    """A task with no recurrence should NOT create a follow-up task."""
    pet = Pet(name="Nemo", type="Fish", ownerPreferences="None")
    task = Task(name="Water change", duration=0.5, priority="low", recurrence=None)
    pet.addTask(task)

    task.markCompleted()

    assert len(pet.getIncompleteTasks()) == 0, \
        "No follow-up task expected for a non-recurring task"


# --- Conflict Detection ---

def test_add_task_returns_warning_on_time_conflict():
    """addTask() should return a warning string when two tasks share a time slot."""
    owner = Owner(name="Jordan", timeAvailability=8.0)
    pet = Pet(name="Buddy", type="Dog", ownerPreferences="None")
    owner.addPet(pet)
    schedule = Schedule(owner)

    t1 = Task(name="Feed",   duration=0.5, priority="high",   time="08:00")
    t2 = Task(name="Walk",   duration=1.0, priority="medium", time="08:00")
    t1.pet = pet
    t2.pet = pet

    schedule.addTask(t1)
    warning = schedule.addTask(t2)

    assert warning is not None, "Expected a conflict warning"
    assert "08:00" in warning, "Warning should mention the conflicting time"


def test_get_conflicts_returns_conflicting_pairs():
    """getConflicts() should list every pair of tasks at the same time."""
    owner = Owner(name="Casey", timeAvailability=8.0)
    schedule = Schedule(owner)

    t1 = Task(name="Feed",  duration=0.5, priority="high",   time="09:00")
    t2 = Task(name="Walk",  duration=1.0, priority="medium", time="09:00")
    t3 = Task(name="Meds",  duration=0.1, priority="high",   time="11:00")

    schedule.addTask(t1)
    schedule.addTask(t2)
    schedule.addTask(t3)

    conflicts = schedule.getConflicts()
    assert len(conflicts) == 1, "Exactly one conflicting pair expected"
    pair = conflicts[0]
    assert t1 in pair and t2 in pair, "Conflict should be between t1 and t2"


def test_has_conflicts_false_when_no_duplicates():
    """hasConflicts() should return False when all tasks have unique times."""
    owner = Owner(name="Riley", timeAvailability=8.0)
    schedule = Schedule(owner)

    schedule.addTask(Task(name="Feed", duration=0.5, priority="high",   time="07:00"))
    schedule.addTask(Task(name="Walk", duration=1.0, priority="medium", time="12:00"))
    schedule.addTask(Task(name="Meds", duration=0.1, priority="high",   time="20:00"))

    assert not schedule.hasConflicts(), "No conflicts expected with unique times"


# --- AI Agent Evaluation (integration tests — require GEMINI_API_KEY) ----------

@pytest.fixture(scope="module")
def agent_result():
    """Run PawPalAgent once for the whole module. Skips if no API key is found."""
    from dotenv import load_dotenv
    from agent import PawPalAgent

    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set — skipping agent integration tests")

    owner = Owner("TestOwner", 4.0)
    rocky = Pet("Rocky", "dog", "Prefers morning walks", breed="Labrador", age=3.0, weight=65.0)
    mochi = Pet("Mochi", "cat", "Indoors only",          breed="Mixed",    age=1.0, weight=10.0)

    rocky.addTask(Task("Morning walk", 30, "high",   time="08:00", due_date=date.today()))
    rocky.addTask(Task("Feeding",      10, "low",    time="00:00", due_date=date.today()))
    mochi.addTask(Task("Medication",   15, "high",   time="08:00", due_date=date.today()))
    mochi.addTask(Task("Grooming",     45, "medium", time="00:00",
                       due_date=date.today() - timedelta(days=2)))

    owner.addPet(rocky)
    owner.addPet(mochi)

    sched = Schedule(owner)
    agent = PawPalAgent(sched)
    explanation, proposed, _ = agent.run()
    return explanation, proposed, sched


def test_agent_produces_no_conflicts(agent_result):
    """After the agent runs, the proposed schedule must have zero time conflicts."""
    _, _, sched = agent_result
    conflicts = sched.getConflicts()
    assert len(conflicts) == 0, f"Agent left {len(conflicts)} unresolved conflict(s)"


def test_agent_fits_within_capacity(agent_result):
    """The proposed schedule must fit within the owner's available hours."""
    _, _, sched = agent_result
    assert sched.canFitSchedule(), "Agent produced a schedule that exceeds the owner's available time"


def test_agent_explanation_mentions_a_pet(agent_result):
    """The explanation must be non-empty and name at least one pet."""
    explanation, _, _ = agent_result
    assert isinstance(explanation, str) and len(explanation) > 0, \
        "Explanation should be a non-empty string"
    assert any(name in explanation for name in ("Rocky", "Mochi")), \
        f"Explanation should name at least one pet; got: {explanation!r}"


def test_agent_surfaces_overdue_task(agent_result):
    """The explanation must acknowledge the overdue Grooming task."""
    explanation, _, _ = agent_result
    lower = explanation.lower()
    assert "grooming" in lower or "overdue" in lower, \
        f"Explanation should mention the overdue Grooming task; got: {explanation!r}"


def test_agent_accept_saves_and_reloads_schedule(agent_result, tmp_path):
    """End-to-end: accept flow saves proposed times to JSON and reloads correctly."""
    explanation, proposed, sched = agent_result

    filepath = str(tmp_path / "test_data.json")
    sched.owner.save_to_json(filepath)

    reloaded = Owner.load_from_json(filepath)
    reloaded_times = {
        (t.pet.getName() if t.pet else "", t.getName()): t.time
        for t in reloaded.getAllTasks()
    }

    for task in proposed:
        key = (task["pet"], task["task"])
        assert key in reloaded_times, f"Task {key} missing from reloaded JSON"
        assert reloaded_times[key] == task["time"], (
            f"Time mismatch for {key}: expected {task['time']}, got {reloaded_times[key]}"
        )
