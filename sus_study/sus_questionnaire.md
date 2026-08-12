# System Usability Scale (SUS) — Brooke, 1996

Standard, widely-used 10-item instrument. Set this up as a Google Form (per
the proposal's D2 data collection plan) with each item as a 5-point Likert
scale: **1 = Strongly Disagree ... 5 = Strongly Agree**.

Keep the wording exactly as below — it's a validated instrument, and changing
the wording invalidates the standard scoring formula.

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to
   use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very
   quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this
    system.

## Setting up the Google Form

1. Create a new Google Form titled "Dashboard Usability Survey".
2. Add all 10 items above as **Linear Scale** questions, 1 to 5, with only
   the endpoints labeled ("Strongly Disagree" / "Strongly Agree" — don't
   label the middle values, that's standard SUS practice).
3. Make all 10 required.
4. Do **not** collect names or emails — keep it anonymous, per the consent
   form.
5. Once you have responses, go to the Form's **Responses → Google Sheets
   icon** to export a CSV.
6. Run `python scripts/score_sus.py path/to/exported.csv` (see that script
   for the exact expected column order) to get the SUS scores and the bar
   chart.
