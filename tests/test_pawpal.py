import pytest
from pawpal_system import Task, Pet


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
