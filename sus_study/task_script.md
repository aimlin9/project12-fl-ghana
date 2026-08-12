# Guided Task Script (read aloud / hand to each participant)

Run this **before** handing over the SUS questionnaire. Takes about 10 minutes.
The dashboard should already be running (`python -m server.main` +
`npm run dev` in the `dashboard/` folder) and open at `http://localhost:3000`.

Say to the participant:

> "Imagine you're a district education officer checking in on how a student
> risk-prediction system is doing across your schools. I'll ask you to do a
> few things on this screen — just talk through what you're seeing as you go.
> There's no wrong answer, I'm testing the dashboard, not you."

## Tasks

1. **Orient.** "Take a look at the screen. What do you think this page is
   showing you?" *(Let them describe the District Officer View unprompted.)*

2. **Start a run.** "Go ahead and start a simulation." *(They click ▶ Start
   FL Simulation.)*

3. **Watch it progress.** "While that's running, tell me what the round
   counter and the F1-score card are showing you." *(Points at the metric
   cards updating live.)*

4. **Check a specific school.** "Now switch to the School Admin tab and tell
   me the status of one of the schools."

5. **Simulate a dropout.** "Try toggling one school offline, then look at
   what changes on screen."

6. **Read the completion summary.** Once the run finishes, the summary popup
   appears — "What does this tell you about how the run went?"

7. **Check the Configuration tab.** "Without changing anything, take a look
   at the Configuration tab — does it make sense what each setting does?"

Then say:

> "That's it — thanks. Now I'd like you to fill out a short 10-question
> survey about your experience just now. Answer honestly, first instinct is
> best — there's no preparation needed."

Hand them the SUS questionnaire (`sus_questionnaire.md` / the Google Form
link) next.
