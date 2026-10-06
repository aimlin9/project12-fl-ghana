# Detailed narration notes — for live screen-recording over FL_Ghana_Demo_Run.mp4

This is the expanded version of `voiceover_script.md` — written for you to talk from
naturally while screen-recording the video playing, not to read word-for-word. Same
real timestamps (pulled from the actual video), but each section has the full
explanation so you're never stuck for what to say next. Pause the video if you need
more time on a section — you're recording a fresh take, not dubbing onto fixed audio.

---

## [0:00] Intro — District View, idle

**What's on screen:** The District View tab, nothing has run yet. A banner across the
top shows the centralised baseline numbers (F1 0.9377, Accuracy 0.9377, AUC 0.9799).
Six stat cards (Current Round, F1-score, Balanced Accuracy, Privacy Budget, Comm.
Overhead, School Nodes) are all empty dashes. Bottom-right says "School Nodes 3 / 3" —
all three are online before anything has started.

**What to explain:**
- This is the admin dashboard for the project: a privacy-preserving federated learning
  system where three simulated Ghanaian district schools — we call them alpha, beta,
  gamma — train a shared student at-risk prediction model *together*, without any
  school ever sending its raw student records anywhere.
- The baseline number at the top (F1 0.9377) is from a centralised model we trained
  separately, on all the pooled student data in one place — that's the number our
  federated model has to come close to, without ever pooling the data.
- Every school already shows as connected and idle. Nothing has trained yet — all the
  stat cards are blank. We're about to click Start.

---

## [0:05] Quick tour — Configuration and School Admin tabs

**What's on screen:** This happens fast in the recording — a flash through the
Configuration tab (toggles for Differential Privacy and Paillier Encryption, key size
dropdown, round/epoch settings) and the School Admin tab (three node cards, all idle),
before landing back on District View and clicking **Start FL simulation**.

**What to explain:**
- On the Configuration tab: both Differential Privacy (DP-SGD) and Paillier
  Homomorphic Encryption are switched on for this run — this is the full privacy
  stack, not a stripped-down demo.
- The Paillier key size is set to 512-bit here rather than our production target of
  2048-bit, purely so this live run finishes in about two minutes instead of ten-plus
  — the mechanism is identical either way, just slower at the bigger key size.
- Local epochs per round is set to 1 — each school does one pass over its own data per
  round before sending an update, which is the standard way federated learning is run
  (many communication rounds, light local training) rather than each node overfitting
  locally.
- On School Admin: this is the per-school view a headmaster or IT lead at an
  individual school would see — their own node's status, nothing about the other
  schools.
- Then we hit Start.

---

## [0:10] Round 1 begins — local training, DP-SGD, Paillier encryption

**What's on screen:** A green banner: "Simulation starting — waiting for school nodes
to connect," then "Simulation started — polling for updates." Round latency and
privacy-epsilon numbers start filling in per node on the School Admin cards as each
school finishes.

**What to explain:**
- Right now, each of the three schools is training a small neural network — an 8-input,
  two-hidden-layer MLP — *locally*, on its own SQLite database of student records.
  Nothing about those records ever leaves the school's machine.
- Before a school sends its trained update back, two privacy layers are applied:
  1. **Differential privacy (DP-SGD, via Opacus):** the gradients are clipped to a
     maximum norm and Gaussian noise is added during training. This gives a formal,
     mathematical privacy guarantee — even if someone intercepted the update, they
     couldn't reliably reconstruct any individual student's data from it. That's
     where the "Privacy Budget ε" number comes from — it's the quantified privacy
     cost of that round.
  2. **Paillier homomorphic encryption:** the (already DP-noised) model update is
     encrypted with a public key before it's sent anywhere. The key property of
     Paillier encryption is that the server can mathematically *add* encrypted
     numbers together without ever decrypting them individually — so it can combine
     all three schools' encrypted updates into one encrypted sum, and only decrypt
     that final aggregate. No individual school's update is ever visible in plaintext,
     not even to our own server.
- This whole process — train, clip and noise, encrypt, send — is what's happening
  during this quiet stretch while the latency numbers fill in per school.

---

## [0:40] Round 1 complete

**What's on screen:** Banner updates to "Round 1 of 5 completed — F1 0.929 · Acc
0.933." The District View's stat cards populate for the first time, and the first
point appears on the convergence chart.

**What to explain:**
- This is the server-side aggregation step finishing: it took the three encrypted
  updates, homomorphically summed them, decrypted only the combined result, and
  applied FedAvg — a weighted average where each school's contribution is scaled by
  how many students it has, so a bigger school doesn't unfairly dominate the model.
- The result: F1 of 0.929 after just one round — already within a hair of our
  centralised baseline of 0.9377. The green "within 5pp target" badge up top confirms
  that gap is comfortably inside the 5-percentage-point target from Objective 1 of
  the project.

---

## [1:00] Round 2 complete — convergence chart building

**What's on screen:** Banner: "Round 2 of 5 completed." Chart now shows two points
(R1, R2) for F1-score, balanced accuracy, AUC-ROC, and loss, all plotted against the
dashed baseline line.

**What to explain:**
- You can see the four series tracking almost flat against the baseline from round
  one onward — F1 and accuracy sitting right on the baseline line, loss staying low
  and steady.
- That's actually the headline finding of this run: the federated model isn't slowly
  climbing toward the baseline over many rounds — it's already there by round one and
  stays there. That's because the engineered features we use (quiz scores, assignment
  submission rates) are strongly predictive of the at-risk label by construction, so
  there isn't much more the model can learn after the first round. We verified this
  honestly — even changing training settings didn't produce a dramatically rising
  curve, so we're reporting the real result rather than engineering a nicer-looking
  one.

---

## [1:15] Round 3 complete — School Admin per-node view

**What's on screen:** Switches to the School Admin tab: three cards for alpha, beta,
gamma, each showing its own round latency, privacy epsilon, and rounds completed so
far, plus a line chart of cumulative privacy budget per round.

**What to explain:**
- This is the same per-school view from before, now live with real numbers. Each
  school has a different round latency — that's expected, it reflects each school's
  dataset size and local hardware.
- The cumulative privacy-budget chart is the two-layer privacy guarantee made
  concrete: epsilon per node, tracked round by round, staying flat and under control —
  this is literally the number a data-protection officer would want to see to confirm
  the system complies with something like Ghana's Data Protection Act.

---

## [1:35] Round 4 complete

**What's on screen:** Banner: "Round 4 of 5 completed." Communication-overhead bar
chart now has four bars (R1–R4), each a little over 2.5 MB.

**What to explain:**
- This chart is tracking how much encrypted data moves over the network each round —
  just the model weights, encrypted, never raw student data. Staying flat around 2.5
  MB per round per node means the encryption overhead is predictable and small enough
  to be practical even on a modest school network connection.

---

## [1:48] Round 5 complete — Simulation complete modal

**What's on screen:** A modal pops up: "Simulation complete — 5 rounds finished, 3/3
nodes participated." Final stats: F1 (macro) 0.9308, Balanced Accuracy 93.5%, AUC-ROC
0.9756, Max Privacy Budget ε 0.500, Total Comm. Overhead 12.65 MB, Config "DP ·
Paillier 512-bit." A green banner reads: "Within the 5pp target — federated F1
(0.9308) vs centralised baseline (0.9377), gap 0.0069."

**What to explain:**
- This is the full run summarised: five complete federated rounds, all three schools
  participating in every single one, final model performance within 0.7 percentage
  points of the centralised baseline we'd get from pooling everyone's data in one
  place — illegally, in this context, since that's exactly what we're avoiding.
- Total communication was 12.65 MB across the whole run, fully encrypted the entire
  time, with zero plaintext gradient exposure — that's the two objectives of this
  project demonstrated in one live run: performance parity with a centralised model,
  and a verified, encrypted, privacy-preserving training process to get there.

---

## [2:00] Final chart — wrap-up

**What's on screen:** Modal closed, back on District View. Full five-point convergence
chart and five-bar communication chart, status back to "Idle," ready to run again.

**What to explain:**
- That's the complete loop, end to end — three schools, five rounds, real OULAD
  student data, full encryption and differential privacy throughout, and a model that
  matches centralised performance without ever centralising the data.
- This is also exactly the audit trail a district education office would want: every
  round logged, every privacy budget tracked, every byte of the model update
  encrypted before it ever left a school.

---

*Tip: if you're talking for longer than the clip naturally allows at any point, pause
the video playback while you finish the thought, then resume — you're recording your
own screen capture, not syncing to fixed timestamps.*
