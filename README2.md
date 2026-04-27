# Project Name: PawPal+ (Module 2 Project)

**PawPal+** is a Smart Care Management System. Its purpose is to create a Schedule of the User’s Pet’s Tasks. It gathers the User’s Data (User Info, Pet Info, Task Info, etc) and gathers that up to form a Schedule that matches the User’s Preferences.

# Project Artifact
https://docs.google.com/document/d/1qQ_9KtaRP4mS_quJHmuH_saC28Tj9gLEomJLMOA_rLk/edit?tab=t.0

# PawPal+ with AI Features:
Explain what the Project with the AI Features Does and why it matters.

The additional AI Feature **Agentic Workflow** is there as an Agent to fix the Problem regarding the Scheduler. This makes it that the User doesn't have to manually fix said problems. When the User hits the [Run AI Agent] Button, an Agentic Loop runs where it reads all of the inputs from the Current State, then decides what problem exists and the order to fix them, then calls the existing Scheduling Methods as the Tools to make the changes needed. Then it verifies but re-running the validation to confirm that the change works. It then writes a summary of the decisions made. Then lastly, the User reads the summary and clicks either [Accept] or [Reject] the changes. Now, the reason as to why this Agentic Workflow matters is because sometimes, Users forget necessary facts like a Task that was supposed to be done yesterday. With the Agent, it solves that problem by offering a solution, such as rescheduling it and such. Not only that, it asks the User if they prefer the changes in which they can either [Accept] or [Reject] the changes before it is saved.


# Architecture Overview:
A Short Explanation of the System.
1. pawpwal_system.py: Backbone of the App where it defines the classes (Task, Pet, Owner, and Schedule).
2. app.py: The App Overview.
3. test_pawpal.py: The Testing Site.
4. agent.py: It's where the Agentic Workflow lies. It calls the functions from the class of pawpal_system.py to the Gemini API.


# Setup Instructions:
A Step-by-step Directions to run the Code.
1. Run the App via "python -m streamlit run app.py"
2. Either Resume a Previous Session or Start a New One.
3. Complete all the Inputs from the [Owner], [Add a Pet], [Add a Task].
4. Then Generate the Schedule and if there is a conflict, run the [AI Agent] and the AI Agent will come and Fix the Problem for you.


# Sample Interactions:
Include at least 2-3 examples of Inputs and the resulting AI outputs to demonstrate the System is Functional.
Example 1:
- Available Time: 4.00 Hours
- Pet: Haru (Dog) and El Gato (Cat)
- Tasks:
     - Haru → Afternoon Walk, 15 Min Duration, Medium Priority.
     - El Gato → Afternoon Groom, 10 Min Duration, High Priority, Recurrence = Daily.
     - Both set at 10:00.
- [Generate Schedule] says 1 Scheduling Conflict.
- [Run AI Agent] gives Solutions that fits the Scheduling Time.

Example 2:
- Available Time: 5.00 Hours
- Pet: Wilson (Chicken)
- Tasks:
     - grooming, 45 Min Duration, Medium Priority, Due 2 Days Agp, Not Completed.
- [Run AI Agent] gives a solution to it by adjusting the time.



# Design Decisions:
Why it was built in this way, and what Trade-Odds been made.

It is designed to call Functions so that the Agent's Action could be more like fits appropriately. The Trade of is that it is a long code. A bit of a not so simple one. Also, after the Agent is done finding a Solution, it gives the User an Option to Accept or Decline it. However, it could also prevent Unintended Data Losses.

# Testing Summary:
What worked, What didn't, and Lesson learned.

Currently, 10 Tests Works but it gave me a warning and 5 not works. The Warning being that a Hidden Internal Python Feature will no longer be able to work since it would be removed in the Future, hence breaking the Code. For the 5 tests that did not pass, it is all about the Gemini API Quota being exceeded and such.

# Reflection:
What this Project taught me about AI and problem-solving.

All in all, this Project helped me expand more of my knowledge regarding Coding. Made me learn some new Topics that matter into Coding like Guardrails, Edge Cases and such. I also learned that for some Errors, or Edge Cases, sometimes it is better to fix them manually and sometimes add Guardrails to fix it. Now regarding AI, I've come to learn that the Loops require a sort of Exhaustion like the total Rounds they could do before exhausting them and such. And that I must not just blindly trust all the AI suggestions and take a look at them myself before proceeding.


[Walktrhough Videos]

[Before Minor Fixes]
<img src='Walkthorugh-Applied-AI-Before-Fixes.gif' title='Video Walkthrough' width='' alt='Video Walkthrough' />


[After After Fixes]
<img src='Walkthorugh-Applied-AI-After-Fixes.gif' title='Video Walkthrough' width='' alt='Video Walkthrough' />
