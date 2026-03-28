from pawpal_system import Owner, Pet, Task, Schedule


# Temporary "Testing Ground"
# Verifies Logic Work in the Terminal


def main():
    owner = Owner(name="Alex", timeAvailability=6.0)

    pet1 = Pet(name="Bella", type="Dog", ownerPreferences="Daily walk and grooming")
    pet2 = Pet(name="Milo", type="Cat", ownerPreferences="Play and clean litter")

    owner.addPet(pet1)
    owner.addPet(pet2)

    task1 = Task(name="Morning walk", duration=1.0, priority="high")
    task2 = Task(name="Vet appointment", duration=2.0, priority="medium")
    task3 = Task(name="Play session", duration=0.5, priority="low")

    pet1.addTask(task1)
    pet1.addTask(task2)
    pet2.addTask(task3)

    schedule = Schedule(owner)
    schedule.generateSchedule()

    print_pretty_schedule(schedule)


def print_pretty_schedule(schedule: Schedule) -> None:
    print("==== Today's Pet Care Schedule ====")
    print()

    by_pet = {}
    for task in schedule.getTasks():
        pet_name = task.pet.name if task.pet else "Unknown Pet"
        by_pet.setdefault(pet_name, []).append(task)

    for pet_name, tasks in by_pet.items():
        print(f"Pet: {pet_name}")
        print("  Task                 | Duration | Priority | Status")
        print("  ---------------------+----------+----------+--------")
        for t in tasks:
            status = "✓" if t.isCompleted() else "✗"
            print(f"  {t.name:<21} | {t.duration:>8.2f} | {t.priority:<8} | {status}")
        print()

    total_time = schedule.getTotalScheduledTime()
    available_time = schedule.owner.getTimeAvailability()
    fits = "✓ Fits" if schedule.canFitSchedule() else "✗ Exceeds"

    print("---- Summary ----")
    print(f"Total tasks : {len(schedule.getTasks())}")
    print(f"Total time  : {total_time:.2f}h")
    print(f"Available   : {available_time:.2f}h")
    print(f"Capacity    : {fits}")
    print("============================")


if __name__ == "__main__":
    main()
