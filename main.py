from datetime import date
from pawpal_system import Owner, Pet, Task, Schedule


# Temporary "Testing Ground"
# Verifies Logic Work in the Terminal


def main():
    owner = Owner(name="Alex", timeAvailability=6.0)

    pet1 = Pet(name="Bella", type="Dog", ownerPreferences="Daily walk and grooming")
    pet2 = Pet(name="Milo", type="Cat", ownerPreferences="Play and clean litter")

    owner.addPet(pet1)
    owner.addPet(pet2)

    # Tasks added out of order by time to demonstrate sort_by_time()
    # Durations are in minutes (matching the web app and scheduler)
    task1 = Task(name="Evening brush",    duration=30,  priority="low",    time="18:00")
    task2 = Task(name="Vet appointment",  duration=120, priority="medium", time="10:30")
    task3 = Task(name="Litter clean",     duration=15,  priority="high",   time="14:00")
    task4 = Task(name="Morning walk",     duration=60,  priority="high",   time="07:00")
    task5 = Task(name="Play session",     duration=30,  priority="low",    time="16:00")

    pet1.addTask(task1)
    pet1.addTask(task2)
    pet1.addTask(task4)
    pet2.addTask(task3)
    pet2.addTask(task5)

    # Mark one task complete to demonstrate filterTasks()
    task4.markCompleted()

    # Recurring task demo — daily task due today
    task_daily = Task(
        name="Feed Bella",
        duration=15,
        priority="high",
        time="08:00",
        recurrence="daily",
        due_date=date.today(),
    )
    pet1.addTask(task_daily)

    # Weekly task due today
    task_weekly = Task(
        name="Groom Milo",
        duration=30,
        priority="medium",
        time="11:00",
        recurrence="weekly",
        due_date=date.today(),
    )
    pet2.addTask(task_weekly)

    schedule = Schedule(owner)
    schedule.generateSchedule()

    print_pretty_schedule(schedule)
    print_sorted_by_time(schedule)
    print_filter_demo(schedule)
    print_recurrence_demo(pet1, pet2, task_daily, task_weekly)
    print_conflict_demo(schedule, pet1, pet2)


def print_pretty_schedule(schedule: Schedule) -> None:
    print("==== Today's Pet Care Schedule ====")
    print()

    by_pet = {}
    for task in schedule.getTasks():
        pet_name = task.pet.name if task.pet else "Unknown Pet"
        by_pet.setdefault(pet_name, []).append(task)

    for pet_name, tasks in by_pet.items():
        print(f"Pet: {pet_name}")
        print("  Task                 | Dur(min) | Priority | Status")
        print("  ---------------------+----------+----------+--------")
        for t in tasks:
            status = "[x]" if t.isCompleted() else "[ ]"
            print(f"  {t.name:<21} | {t.duration:>8.0f} | {t.priority:<8} | {status}")
        print()

    total_time = schedule.getTotalScheduledTime()
    available_time = schedule.owner.getTimeAvailability()
    fits = "[Fits]" if schedule.canFitSchedule() else "[Exceeds]"

    print("---- Summary ----")
    print(f"Total tasks : {len(schedule.getTasks())}")
    print(f"Total time  : {total_time:.0f}min")
    print(f"Available   : {available_time * 60:.0f}min")
    print(f"Capacity    : {fits}")
    print("============================")


def print_sorted_by_time(schedule: Schedule) -> None:
    print("==== Tasks Sorted by Time ====")
    print(f"  {'Time':<6} | {'Task':<21} | {'Pet':<8} | Status")
    print(f"  {'------':<6}-+-{'':-<21}-+-{'':-<8}-+--------")
    for t in schedule.sort_by_time():
        pet_name = t.pet.name if t.pet else "Unknown"
        status = "[x]" if t.isCompleted() else "[ ]"
        print(f"  {t.time:<6} | {t.name:<21} | {pet_name:<8} | {status}")
    print()


def print_filter_demo(schedule: Schedule) -> None:
    print("==== Filter: Incomplete Tasks ====")
    for t in schedule.filterTasks(completed=False):
        print(f"  [ ] {t.name} ({t.pet.name if t.pet else 'Unknown'})")
    print()

    print("==== Filter: Completed Tasks ====")
    for t in schedule.filterTasks(completed=True):
        print(f"  [x] {t.name} ({t.pet.name if t.pet else 'Unknown'})")
    print()

    print("==== Filter: Bella's Tasks Only ====")
    for t in schedule.filterTasks(pet_name="Bella"):
        status = "[x]" if t.isCompleted() else "[ ]"
        print(f"  {status} {t.name}")
    print()


def print_recurrence_demo(pet1: object, pet2: object, task_daily: object, task_weekly: object) -> None:
    print("==== Recurrence Demo ====")
    print(f"Completing daily task  : '{task_daily.name}' (due {task_daily.due_date})")
    task_daily.markCompleted()
    print(f"Completing weekly task : '{task_weekly.name}' (due {task_weekly.due_date})")
    task_weekly.markCompleted()
    print()

    print("  Bella's tasks after completion:")
    for t in pet1.getTasks():
        marker = "[x]" if t.isCompleted() else "[ ]"
        recur = f" [{t.recurrence}]" if t.recurrence else ""
        due = f" due {t.due_date}" if t.recurrence else ""
        print(f"    {marker} {t.name}{recur}{due}")
    print()

    print("  Milo's tasks after completion:")
    for t in pet2.getTasks():
        marker = "[x]" if t.isCompleted() else "[ ]"
        recur = f" [{t.recurrence}]" if t.recurrence else ""
        due = f" due {t.due_date}" if t.recurrence else ""
        print(f"    {marker} {t.name}{recur}{due}")
    print()


def print_conflict_demo(schedule: Schedule, pet1: Pet, pet2: Pet) -> None:
    print("==== Conflict Detection ====")

    # Two tasks deliberately scheduled at the same time across different pets
    task_same_time_1 = Task(name="Bath time",   duration=30, priority="medium", time="14:00")
    task_same_time_2 = Task(name="Feeding time", duration=15, priority="high",  time="14:00")

    pet1.addTask(task_same_time_1)
    pet2.addTask(task_same_time_2)

    warning1 = schedule.addTask(task_same_time_1)
    warning2 = schedule.addTask(task_same_time_2)

    for w in (warning1, warning2):
        if w:
            print(f"  {w}")
    print()

    print("  Full conflict list:")
    if not schedule.hasConflicts():
        print("    No scheduling conflicts found.")
    else:
        for task_a, task_b in schedule.getConflicts():
            pet_a = task_a.pet.name if task_a.pet else "Unknown"
            pet_b = task_b.pet.name if task_b.pet else "Unknown"
            print(f"    CONFLICT at {task_a.time}: '{task_a.name}' ({pet_a}) <-> '{task_b.name}' ({pet_b})")
    print()


if __name__ == "__main__":
    main()
