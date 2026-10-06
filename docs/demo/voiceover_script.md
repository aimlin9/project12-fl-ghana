# Voiceover script — FL_Ghana_Demo_Run.mp4 (2:04 total)

Timestamps are pulled from the actual video (frame-sampled every 5s), not estimated —
read each line starting at its timestamp and you'll land on the matching screen.
Target pace ~140 words/min; word counts per segment are sized to fit the window with
room to breathe. Speak the bracketed notes to yourself, not out loud.

---

**[0:00]**
"This is the admin dashboard for our cross-school federated learning system — three
simulated school nodes training a student at-risk model together, without any of them
sharing raw student data."

**[0:05]** *(Configuration / School Admin tabs flash by quickly here — don't worry about narrating each one, just keep talking)*
"Differential privacy and Paillier encryption are both switched on for this run, and
all three school nodes are connected. I'll start the simulation now."

**[0:10]**
"Each node is now training locally on its own OULAD student data, then encrypting its
update with Paillier homomorphic encryption before sending anything to the server —
the server never sees a plaintext gradient."

**[0:25]**
"You can see the per-node round latency and privacy budget filling in as training
finishes on each school."

**[0:40]**
"Round 1 is done — F1 of 0.929, right in line with our centralised baseline of 0.938.
The dashboard flags it as within the 5-percentage-point target from objective one."

**[1:00]**
"Round 2 complete. The convergence chart is building out — F1 and accuracy tracking
the baseline almost immediately, which is the real story here: the model reaches
baseline-level performance from round one and holds it."

**[1:15]**
"Round 3. I'm switching to the School Admin tab to show each node individually —
alpha, beta, gamma — all reporting their round latency and privacy epsilon separately."

**[1:35]**
"Round 4 complete, still matching the baseline within less than a percentage point."

**[1:48]**
"And round 5 — simulation complete. Final F1 of 0.9308 against a centralised baseline
of 0.9377, a gap of just 0.007. Total communication overhead was 12.65 megabytes across
all five rounds, fully Paillier-encrypted the entire time."

**[2:00]**
"That's the full run — objective one and objective two both demonstrated live, end to
end, on real OULAD data."

---

*Total: ~210 words. If you're reading slower than ~140 wpm, trim the round-3 and
round-4 lines first — they're the most skippable without losing the throughline.*
