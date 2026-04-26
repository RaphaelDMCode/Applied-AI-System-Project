import os
from datetime import date, timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pawpal_system import Owner, Pet, Task, Schedule

load_dotenv()

MODEL = "gemini-2.5-flash"

# Shared schedule reference - set via set_schedule() before running the agent
_schedule: Schedule | None = None


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Add it to your .env file.")
    return genai.Client(api_key=api_key)


def set_schedule(schedule: Schedule) -> None:
    """Point all tool functions at the current schedule instance."""
    global _schedule
    _schedule = schedule


# -- Tool 1 --------------------------------------------------------------------

def generate_schedule() -> dict:
    """Generate an optimized schedule sorted by priority (high first) then by
    duration (shortest first). Call this first to produce the initial plan
    before checking for problems."""
    _schedule.generateSchedule()
    tasks = [
        {
            "task":             t.getName(),
            "pet":              t.pet.getName() if t.pet else "unknown",
            "time":             t.time,
            "priority":         t.getPriority(),
            "duration_minutes": int(t.getDuration()),
        }
        for t in _schedule.getTasks()
    ]
    return {"tasks": tasks, "total_tasks": len(tasks)}


# -- Tool 2 --------------------------------------------------------------------

def get_conflicts() -> dict:
    """Return every pair of tasks that share the same scheduled time slot.
    Use this after generating the schedule to detect collisions."""
    pairs = _schedule.getConflicts()
    result = [
        {
            "task_a":      a.getName(),
            "pet_a":       a.pet.getName() if a.pet else "unknown",
            "task_b":      b.getName(),
            "pet_b":       b.pet.getName() if b.pet else "unknown",
            "shared_time": a.time,
        }
        for a, b in pairs
    ]
    return {"conflicts": result, "count": len(result)}


# -- Tool 3 --------------------------------------------------------------------

def get_overdue_tasks() -> dict:
    """Return all tasks whose due date has already passed and that are not yet
    completed. Use this to surface missed or forgotten pet care items."""
    overdue = _schedule.getOverdueTasks()
    result = [
        {
            "task":     t.getName(),
            "pet":      t.pet.getName() if t.pet else "unknown",
            "due_date": str(t.due_date),
            "priority": t.getPriority(),
        }
        for t in overdue
    ]
    return {"overdue_tasks": result, "count": len(result)}


# -- Tool 4 --------------------------------------------------------------------

def find_next_slot(duration_minutes: int) -> dict:
    """Find the earliest open time window in today's schedule that can fit a
    task of the requested length.

    Args:
        duration_minutes: How many minutes the task needs.
    """
    slot = _schedule.findNextAvailableSlot(duration_minutes)
    return {"available_slot": slot, "duration_requested": duration_minutes}


# -- Tool 5 --------------------------------------------------------------------

def check_capacity() -> dict:
    """Check whether the total time of all scheduled tasks fits within the
    owner's available hours today. Use this to detect over-scheduling."""
    fits      = _schedule.canFitSchedule()
    total     = _schedule.getTotalScheduledTime()
    available = _schedule.owner.getTimeAvailability() * 60
    return {
        "fits_within_availability": fits,
        "total_scheduled_minutes":  int(total),
        "available_minutes":        int(available),
        "over_by_minutes":          int(max(0, total - available)),
    }


# -- Tool 6 --------------------------------------------------------------------

def reschedule_task(task_name: str, pet_name: str, new_time: str) -> dict:
    """Move a specific task to a new start time to resolve a conflict or
    honour a time preference.

    Args:
        task_name: Exact name of the task to move.
        pet_name:  Name of the pet this task belongs to.
        new_time:  New start time in HH:MM format (e.g. '10:30').
    """
    for task in _schedule.getTasks():
        if task.getName() == task_name and task.pet and task.pet.getName() == pet_name:
            old_time  = task.time
            try:
                _h, _m = map(int, new_time.split(":"))
                new_time = f"{_h:02d}:{_m:02d}"
            except (ValueError, AttributeError):
                pass
            task.time = new_time
            return {
                "success":    True,
                "task":       task_name,
                "pet":        pet_name,
                "moved_from": old_time,
                "moved_to":   new_time,
            }
    return {
        "success": False,
        "message": f"Task '{task_name}' for pet '{pet_name}' was not found.",
    }


# List passed to Gemini in Step 3
PAWPAL_TOOLS = [
    generate_schedule,
    get_conflicts,
    get_overdue_tasks,
    find_next_slot,
    check_capacity,
    reschedule_task,
]


# -- Step 3: Agent Loop --------------------------------------------------------

SYSTEM_PROMPT = """You are PawPal+, a smart pet care scheduling assistant.
Your job is to analyse the owner's pet care schedule, detect any problems
(scheduling conflicts, overdue tasks, over-capacity), fix them using the
available tools, verify the fixes, then write a short plain-English summary
for the owner explaining what you found and what you changed.

Rules:
- Always call generate_schedule first to produce the initial plan.
- Always call get_conflicts and get_overdue_tasks to check for problems.
- Always call check_capacity to verify the schedule fits the owner's day.
- Use reschedule_task to fix conflicts; prefer moving lower-priority tasks.
- Use find_next_slot to find a safe open time before rescheduling.
- After fixing conflicts, call get_conflicts again to confirm they are gone.
- End with a clear, friendly summary (under 150 words) that names the specific
  pets and tasks you changed and why."""


class PawPalAgent:
    """Agentic loop: Observe -> Plan -> Act -> Check -> Report."""

    MAX_ROUNDS = 12

    def __init__(self, schedule: Schedule):
        self.client = get_gemini_client()
        set_schedule(schedule)
        self._schedule = schedule

    def run(self) -> tuple[str, list[dict], list[dict]]:
        """Run the agent loop. Returns (explanation, proposed_tasks, steps)."""
        user_prompt = (
            "Here is today's pet care situation:\n\n"
            + self._build_context()
            + "\n\nPlease optimise the schedule, fix any problems, "
            "and explain what you did."
        )

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
        ]

        steps: list[dict] = []
        response = None
        for _ in range(self.MAX_ROUNDS):
            response = self.client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=PAWPAL_TOOLS,
                ),
            )

            calls = response.function_calls or []
            if not calls:
                break

            # Append model turn so history is consistent
            contents.append(response.candidates[0].content)

            # Execute every tool call, collect results, and record trace
            fn_parts = []
            for fc in calls:
                result = self._dispatch(fc.name, dict(fc.args))
                steps.append({
                    "step":   len(steps) + 1,
                    "tool":   fc.name,
                    "args":   dict(fc.args),
                    "result": result,
                })
                fn_parts.append(
                    types.Part.from_function_response(name=fc.name, response=result)
                )

            # Return all results in one user turn
            contents.append(types.Content(role="user", parts=fn_parts))

        exhausted = bool(response is not None and (response.function_calls or []))

        if exhausted:
            explanation = (
                "⚠️ The agent reached its step limit before finishing all fixes. "
                "The schedule may still have unresolved issues — try running the agent again."
            )
        else:
            explanation = "Schedule has been optimised."
            if response is not None:
                try:
                    txt = response.text
                    if txt:
                        explanation = txt
                except Exception:
                    pass

        return explanation, self._snapshot(), steps

    # -- helpers ---------------------------------------------------------------

    def _build_context(self) -> str:
        owner = self._schedule.owner
        lines = [
            f"Owner: {owner.getName()}, available {owner.getTimeAvailability()} hours today.",
            "Tasks:",
        ]
        for pet in owner.getPets():
            for task in pet.getTasks():
                due  = f", due {task.due_date}" if task.due_date else ""
                pref = (
                    f", preferred start {task.time}"
                    if task.has_preferred_time
                    else ""
                )
                lines.append(
                    f"  {pet.getName()} ({pet.getType()}): {task.getName()} "
                    f"[{task.getPriority()}, {int(task.getDuration())}min{pref}{due}]"
                )
        return "\n".join(lines)

    def _dispatch(self, name: str, args: dict):
        table = {fn.__name__: fn for fn in PAWPAL_TOOLS}
        fn = table.get(name)
        if fn is None:
            return {"error": f"Unknown tool: {name}"}
        return fn(**args)

    def _snapshot(self) -> list[dict]:
        return [
            {
                "task":             t.getName(),
                "pet":              t.pet.getName() if t.pet else "unknown",
                "time":             t.time,
                "priority":         t.getPriority(),
                "duration_minutes": int(t.getDuration()),
            }
            for t in self._schedule.getTasks()
        ]


# -- Step 2 verification - call every tool manually and check the output -------

if __name__ == "__main__":
    # Build a test scenario with a deliberate conflict and an overdue task
    owner = Owner("Alex", 4.0)

    rocky = Pet("Rocky", "dog", "Prefers morning walks", breed="Labrador", age=3.0, weight=65.0)
    mochi = Pet("Mochi", "cat", "Indoors only",          breed="Mixed",    age=1.0, weight=10.0)

    # Both tasks have preferred time 08:00 -> conflict after generateSchedule
    rocky.addTask(Task("Morning walk", 30, "high",   time="08:00", due_date=date.today()))
    rocky.addTask(Task("Feeding",      10, "low",    time="00:00", due_date=date.today()))
    mochi.addTask(Task("Medication",   15, "high",   time="08:00", due_date=date.today()))
    # Overdue: due 2 days ago
    mochi.addTask(Task("Grooming",     45, "medium", time="00:00", due_date=date.today() - timedelta(days=2)))

    owner.addPet(rocky)
    owner.addPet(mochi)

    sched = Schedule(owner)
    set_schedule(sched)

    sep = "-" * 52

    # Tool 1 - generate_schedule
    print(sep)
    print("TOOL 1 - generate_schedule()")
    result = generate_schedule()
    for t in result["tasks"]:
        print(f"  {t['time']}  {t['pet']:<8}  {t['task']:<20}  {t['priority']:<6}  {t['duration_minutes']}min")

    # Tool 2 - get_conflicts
    print(sep)
    print("TOOL 2 - get_conflicts()")
    result = get_conflicts()
    print(f"  Conflicts found: {result['count']}")
    for c in result["conflicts"]:
        print(f"  {c['task_a']} ({c['pet_a']}) vs {c['task_b']} ({c['pet_b']}) at {c['shared_time']}")

    # Tool 3 - get_overdue_tasks
    print(sep)
    print("TOOL 3 - get_overdue_tasks()")
    result = get_overdue_tasks()
    print(f"  Overdue tasks: {result['count']}")
    for t in result["overdue_tasks"]:
        print(f"  {t['task']} ({t['pet']}) - due {t['due_date']}")

    # Tool 4 - check_capacity
    print(sep)
    print("TOOL 4 - check_capacity()")
    result = check_capacity()
    print(f"  Fits: {result['fits_within_availability']}")
    print(f"  {result['total_scheduled_minutes']}min used / {result['available_minutes']}min available")
    if result["over_by_minutes"]:
        print(f"  Over by: {result['over_by_minutes']} minutes")

    # Tool 5 - find_next_slot
    print(sep)
    print("TOOL 5 - find_next_slot(20)")
    result = find_next_slot(20)
    print(f"  Next available 20-min slot: {result['available_slot']}")

    # Tool 6 - reschedule_task
    print(sep)
    print("TOOL 6 - reschedule_task('Morning walk', 'Rocky', '09:00')")
    result = reschedule_task("Morning walk", "Rocky", "09:00")
    print(f"  Success: {result['success']}")
    if result["success"]:
        print(f"  Moved '{result['task']}' from {result['moved_from']} to {result['moved_to']}")

    # Confirm conflict is now gone after the reschedule
    print(sep)
    print("Re-check get_conflicts() after reschedule:")
    result = get_conflicts()
    print(f"  Conflicts remaining: {result['count']}")
    print(sep)

    # -- Step 3 - PawPalAgent live API call ------------------------------------
    print("STEP 3 - PawPalAgent.run()  (live Gemini API call)")

    owner2 = Owner("Alex", 4.0)
    rocky2 = Pet("Rocky", "dog", "Prefers morning walks", breed="Labrador", age=3.0, weight=65.0)
    mochi2 = Pet("Mochi", "cat", "Indoors only",          breed="Mixed",    age=1.0, weight=10.0)

    rocky2.addTask(Task("Morning walk", 30, "high",   time="08:00", due_date=date.today()))
    rocky2.addTask(Task("Feeding",      10, "low",    time="00:00", due_date=date.today()))
    mochi2.addTask(Task("Medication",   15, "high",   time="08:00", due_date=date.today()))
    mochi2.addTask(Task("Grooming",     45, "medium", time="00:00", due_date=date.today() - timedelta(days=2)))

    owner2.addPet(rocky2)
    owner2.addPet(mochi2)

    sched2 = Schedule(owner2)
    agent  = PawPalAgent(sched2)
    explanation, proposed, steps = agent.run()

    print("\nAgent reasoning steps:")
    for s in steps:
        args_str = ", ".join(f"{k}={v!r}" for k, v in s["args"].items()) if s["args"] else ""
        print(f"  Step {s['step']}: {s['tool']}({args_str}) → {s['result']}")

    print("\nAgent explanation:")
    print(explanation)
    print("\nProposed schedule:")
    for t in proposed:
        print(f"  {t['time']}  {t['pet']:<8}  {t['task']:<20}  {t['priority']:<6}  {t['duration_minutes']}min")
    print(sep)
