"""
Export the Defense Q&A Study Guide to a Word document.
==========================================================
Generates FL_Ghana_Defense_QA_Study_Guide.docx at the project root — a
downloadable, shareable version of the same content published as the HTML
Defense Q&A Study Guide artifact, for group members who'd rather have a
Word file than a link.

Usage:
    python scripts/export_qa_guide_docx.py
"""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x0F, 0x34, 0x60)
INDIGO = RGBColor(0x4F, 0x46, 0xE5)
BODY_GRAY = RGBColor(0x33, 0x33, 0x33)
MUTED = RGBColor(0x6B, 0x72, 0x80)
AMBER_TEXT = RGBColor(0x92, 0x40, 0x0E)

FILL_INDIGO = "F8F9FF"
FILL_AMBER = "FFFBEB"


def shade_cell(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def set_cell_border_left(cell, hex_color, size=24):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(size))
    left.set(qn("w:color"), hex_color)
    borders.append(left)
    tc_pr.append(borders)


def add_qa(doc, question, answer_paragraphs, honesty=False):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    shade_cell(cell, FILL_AMBER if honesty else FILL_INDIGO)
    set_cell_border_left(cell, "F59E0B" if honesty else "6366F1", size=28)

    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(("[Honest answer] " if honesty else "Q  ") + question)
    run.bold = True
    run.font.size = Pt(11.5)
    run.font.color.rgb = AMBER_TEXT if honesty else INDIGO

    for i, para_text in enumerate(answer_paragraphs):
        ap = cell.add_paragraph()
        ap.paragraph_format.space_before = Pt(4 if i == 0 else 6)
        ap.paragraph_format.space_after = Pt(2)
        ar = ap.add_run(para_text)
        ar.font.size = Pt(10.5)
        ar.font.color.rgb = BODY_GRAY

    doc.add_paragraph().paragraph_format.space_after = Pt(2)  # small gap after each QA


def add_stack_table(doc, caption, rows):
    cap = doc.add_paragraph()
    cr = cap.add_run(caption.upper())
    cr.bold = True
    cr.font.size = Pt(10)
    cr.font.color.rgb = INDIGO
    cap.paragraph_format.space_before = Pt(6)
    cap.paragraph_format.space_after = Pt(4)

    table = doc.add_table(rows=1 + len(rows), cols=2)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text = "Component"
    hdr[1].text = "Role & why it was chosen"
    for cell in hdr:
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9.5)
    for i, (name, role) in enumerate(rows, start=1):
        cells = table.rows[i].cells
        cells[0].text = name
        cells[1].text = role
        for p in cells[0].paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9.5)
                r.font.color.rgb = NAVY
        for p in cells[1].paragraphs:
            for r in p.runs:
                r.font.size = Pt(9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_note(doc, text):
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    shade_cell(cell, "EFF6FF")
    set_cell_border_left(cell, "3B82F6", size=28)
    p = cell.paragraphs[0]
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = BODY_GRAY
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_fact_strip(doc, facts):
    table = doc.add_table(rows=1, cols=len(facts))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, (label, value) in zip(table.rows[0].cells, facts):
        shade_cell(cell, FILL_INDIGO)
        p1 = cell.paragraphs[0]
        r1 = p1.add_run(label.upper())
        r1.font.size = Pt(8)
        r1.font.color.rgb = MUTED
        r1.bold = True
        p2 = cell.add_paragraph()
        r2 = p2.add_run(value)
        r2.font.size = Pt(13)
        r2.bold = True
        r2.font.color.rgb = NAVY
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_section(doc, number, title, subtitle):
    doc.add_page_break() if number > 1 else None
    h = doc.add_heading(level=1)
    h.paragraph_format.space_before = Pt(6)
    hr = h.add_run(f"{number}.  {title}")
    hr.font.color.rgb = NAVY
    hr.font.size = Pt(17)
    sub = doc.add_paragraph()
    sr = sub.add_run(subtitle)
    sr.italic = True
    sr.font.size = Pt(10)
    sr.font.color.rgb = MUTED
    sub.paragraph_format.space_after = Pt(10)


def build():
    doc = Document()

    # Base style
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    for section in doc.sections:
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)

    # ---- Title page ----
    eyebrow = doc.add_paragraph()
    er = eyebrow.add_run("GROUP 7  ·  PROJECT 12")
    er.font.size = Pt(9)
    er.font.color.rgb = MUTED
    er.bold = True

    title = doc.add_paragraph()
    tr = title.add_run("Defense Q&A Study Guide")
    tr.font.size = Pt(26)
    tr.bold = True
    tr.font.color.rgb = NAVY

    subtitle = doc.add_paragraph()
    sr = subtitle.add_run(
        "Cross-School Federated Learning for Privacy-Preserving Student Progress "
        "Tracking — every question we prepared for, and the answer to give."
    )
    sr.font.size = Pt(11.5)
    sr.font.color.rgb = BODY_GRAY
    subtitle.paragraph_format.space_after = Pt(14)

    howto_table = doc.add_table(rows=1, cols=1)
    cell = howto_table.rows[0].cells[0]
    shade_cell(cell, FILL_AMBER)
    p = cell.paragraphs[0]
    r1 = p.add_run("How to use this:  ")
    r1.bold = True
    r1.font.color.rgb = AMBER_TEXT
    r1.font.size = Pt(10)
    r2 = p.add_run(
        "read each answer in your own words before the presentation — don't "
        "memorise verbatim. The amber-highlighted questions show the tone to use "
        "when something wasn't tested yet: state clearly what we tested, what we "
        "didn't, and why. That reads as more credible than guessing."
    )
    r2.font.size = Pt(10)
    r2.font.color.rgb = BODY_GRAY

    # ---- Section 1: Overview ----
    add_section(doc, 1, "What This Project Is — Technical Framing",
                "Say this first if asked to summarise the project — it's precise, not just descriptive.")

    add_qa(doc, "In one technically precise sentence, what is this project?", [
        "A cross-silo federated learning system that trains a shared binary classifier for student at-risk "
        "prediction across multiple data-owning institutions (simulated schools), using FedAvg for parameter "
        "aggregation, DP-SGD for a formal per-round privacy guarantee, and Paillier partial homomorphic encryption "
        "for secure aggregation — so no institution's raw data or unencrypted model update ever leaves its own "
        "boundary."
    ])
    add_qa(doc, 'What makes this "federated learning" specifically, and not just "distributed training"?', [
        "Distributed training (e.g. multi-GPU data-parallel training) assumes the orchestrator can see and shuffle "
        "the data across workers freely — the data is centrally owned, just physically spread out for speed. "
        "Federated learning assumes the opposite: each participant's data is privately owned, non-IID (school_gamma "
        "is 57% at-risk, school_beta is 49%), and must never leave that participant's boundary.",
        "We're specifically doing cross-silo FL — a small number (3-5) of reliable, always-available institutional "
        "participants — as opposed to cross-device FL (Google's original use case: millions of unreliable mobile "
        "phones). Cross-silo FL is why we can afford synchronous rounds and don't need client-selection sampling "
        "strategies designed for device churn."
    ])
    add_qa(doc, "What's the underlying systems constraint that makes FL the right architecture here, not just a stylistic choice?", [
        "Data sovereignty, enforced legally: the Ghana Data Protection Act 2012 (Act 843) prohibits transfer of "
        "personal data — including academic records — between institutions without explicit consent and adequate "
        "security measures. That means centralised training is not just undesirable but legally infeasible. FL is "
        "the systems-level solution because it achieves the same ML objective — one globally-optimised shared "
        "model — under a hard data-locality constraint the centralised approach cannot satisfy."
    ])
    add_qa(doc, 'How does this actually improve the education system — concretely, not just "it helps"?', [
        "Three concrete mechanisms: (1) Early-warning capability without new data infrastructure — district "
        "education offices get a shared predictive signal across their schools without GES needing to build or "
        "fund a centralised student-records database. (2) Legal compliance is structural, not procedural — "
        "privacy isn't a policy added after the fact, it's enforced by the architecture itself (DP-SGD's formal "
        "(ε,δ) guarantee, Paillier's cryptographic guarantee).",
        "(3) The architecture generalises beyond education — the same FL + DP-SGD + partial-homomorphic-secure-"
        "aggregation stack applies to any regulated, multi-institutional setting where data can't be centralised: "
        "hospital consortia training diagnostic models, banks doing joint fraud detection, inter-agency government "
        "analytics. This maps to SDG 4 (Quality Education, Target 4.1) and SDG 16 (Target 16.10) directly."
    ])

    # ---- Section 2: Dataset ----
    add_section(doc, 2, "The Dataset (OULAD)",
                "Real data, not synthetic — one of the strongest parts of the project to lean on.")
    add_fact_strip(doc, [("Total records", "32,593"), ("Real quarters", "4"), ("Features engineered", "8")])

    add_qa(doc, "Why OULAD and not real Ghanaian student data?", [
        "OULAD is the same substitution strategy used by the FL-education papers we cite — Salehi et al. used it too. "
        "It's public, real, and anonymised, and large enough (32,593 records) to simulate realistic non-IID school "
        "variation, without the ethical and access barriers of collecting real Ghanaian student records for a course "
        "project. We partition it by real registration quarter (2013B/2013J/2014B/2014J) to simulate distinct school "
        "intakes, rather than generating synthetic data from scratch."
    ])
    add_qa(doc, 'OULAD doesn\'t have "attendance" or "course difficulty" fields — how did you get those?', [
        "We engineered them as documented proxies from the raw VLE (virtual learning environment) click logs and "
        "assessment records — for example, attendance_rate is the fraction of days a student had any VLE activity, "
        "and course_difficulty is a per-module pass-rate ranking. This is disclosed explicitly in our methodology, "
        "not hidden — it's a standard technique when adapting a dataset built for one purpose to a different "
        "modelling task."
    ])
    add_qa(doc, "Why do quarters map to only 4 school nodes when your proposal says 3–5?", [
        "OULAD genuinely only has 4 real registration quarters. For the 5-node configuration, we split the largest "
        "quarter (2014J, 11,260 students) by course-module group into two further nodes, which we document "
        "explicitly as a necessary adaptation — we didn't quietly force a 5th node that doesn't reflect real data "
        "structure."
    ])
    add_qa(doc, "What's the at_risk label based on?", [
        "at_risk = 1 if the student's real OULAD final result was Withdrawn or Fail, 0 otherwise — a standard "
        "convention already used in the FL-education literature we cite. Nothing invented; it comes straight from "
        "the real outcome field."
    ])

    # ---- Section 3: Training pipeline ----
    add_section(doc, 3, "Model Training Pipeline",
                'The full, precise answer to "what did you use to train the model" — walk through this layer by layer.')

    add_qa(doc, "What did you use to train the model — full technical answer?", [
        "Architecture: a fully-connected feedforward network (StudentMLP in PyTorch) — Linear(8->64) -> ReLU -> "
        "Linear(64->32) -> ReLU -> Linear(32->1), emitting a raw logit. 2,689 trainable parameters total.",
        "Loss: BCEWithLogitsLoss — combines sigmoid activation and binary cross-entropy into one numerically "
        "stable log-sum-exp computation, avoiding the float overflow/underflow a separate sigmoid-then-BCELoss "
        "pipeline risks. A pos_weight term (derived from each partition's class-imbalance ratio, capped at 10x) "
        "penalises missed at-risk predictions more heavily than false positives.",
        "Optimiser: Adam, learning rate 0.01, default beta coefficients — re-instantiated fresh each round per "
        "client (no persisted optimiser state across rounds, the standard FedAvg assumption).",
        "Local training loop: 3 local epochs per communication round, mini-batch SGD via Adam, batch size 32, "
        "executed entirely client-side on that school's own data only.",
        "Aggregation: FedAvg. Each client computes a parameter delta dw_i = w_i(local) - w(global), the server "
        "computes the weighted mean dw = sum((n_i/N) * dw_i) where n_i is client i's sample count, and updates "
        "w(global) <- w(global) + dw."
    ])
    add_qa(doc, "Walk through exactly how DP-SGD modifies that training loop, mechanically.", [
        "Opacus wraps the model in a GradSampleModule, which hooks the backward pass to materialise per-sample "
        "gradients (via a vectorised Jacobian technique) instead of the batch-averaged gradient PyTorch computes "
        "by default. Each per-sample gradient is clipped to L2 norm <= C (C=1.0), Gaussian noise sampled from "
        "N(0, sigma^2*C^2*I) is added to the clipped sum (sigma=1.1), and the noisy sum is averaged before the "
        "optimiser step.",
        "Privacy loss is tracked with a Renyi Differential Privacy (RDP) accountant, which composes the per-step "
        "privacy cost across all steps in a round and converts to a reportable (epsilon, delta)-DP guarantee "
        "(delta fixed at 1e-5, epsilon computed empirically via get_privacy_spent())."
    ])
    add_qa(doc, "Where does encryption fit relative to training — before, during, or after?", [
        "Strictly after. Training (including DP-SGD's clipping and noise injection) happens entirely in plaintext, "
        "locally, inside PyTorch. Only once the final parameter delta for that round is computed does it get "
        "Paillier-encrypted, element-wise, immediately before serialisation and network transmission."
    ])

    # ---- Section 4: Tech stack ----
    add_section(doc, 4, "Technology Stack — Frontend & Backend",
                "Name the library, know why it was chosen — that combination is what reads as technical fluency.")

    add_stack_table(doc, "Backend", [
        ("Python 3.11.9", "Pinned specifically for Opacus 1.4.0 compatibility"),
        ("Flower 1.8.0", "gRPC-based FL orchestration framework — provides ClientManager, the Strategy abstraction "
                          "(overridden as PaillierFedAvg), and the round-scheduling state machine"),
        ("PyTorch 2.3.0", "Tensor/autograd engine for the MLP; integrates natively with Opacus"),
        ("Opacus 1.4.0", "DP-SGD instrumentation — GradSampleModule + RDP accountant"),
        ("python-paillier (phe) 1.5.0", "Paillier partial homomorphic cryptosystem implementation (2048-bit modulus)"),
        ("FastAPI 0.111.0", "ASGI-based async REST API — serves /api/*, runs the FL simulation as a background task"),
        ("SQLite3", "Embedded, file-based relational store — one file per school partition, so data isolation is "
                     "enforced at the filesystem level"),
        ("scikit-learn 1.5.0", "Evaluation metrics — F1, balanced accuracy, AUC-ROC, ROC-curve-derived Youden's J"),
        ("threading (stdlib)", "The Flower gRPC server and all school clients run as concurrent threads inside one "
                                "Python process for the simulation"),
    ])
    add_stack_table(doc, "Frontend", [
        ("React 18.3.1", "Component-based SPA — functional components with hooks; no external state library needed"),
        ("Vite 5", "ESBuild-based dev server/bundler — near-instant hot-module-reload"),
        ("Chart.js 4 (react-chartjs-2)", "Canvas-based (not SVG) charting — chosen for rendering performance on "
                                          "charts that redraw every 3 seconds during a live run"),
        ("CSS Modules", "Locally-scoped component styling, avoids global CSS namespace collisions"),
    ])
    add_note(doc,
        "Two distinct network protocols run concurrently: Flower's FL protocol runs over gRPC (binary, HTTP/2-"
        "based) on port 8088; the dashboard's API runs over REST/JSON on port 8000. The dashboard polls (fetch() "
        "every 3000ms) rather than using WebSockets — a deliberate simplicity/robustness tradeoff, reasonable "
        "given FL updates arrive on a round-based cadence (tens of seconds), not sub-second."
    )

    # ---- Section 5: Privacy ----
    add_section(doc, 5, "Privacy Design — DP-SGD + Paillier",
                "Two layers, protecting against two different threats — the distinction lecturers probe hardest.")

    add_qa(doc, "Why do you need both DP-SGD and Paillier? Isn't one enough?", [
        "They protect against different threats. DP-SGD protects against someone analysing the content of a model "
        "update to infer facts about individual students, even if they can see the update. Paillier protects "
        "against the server itself (or anyone intercepting network traffic) seeing the update at all.",
        'Put another way: DP-SGD answers "is this update statistically safe to reveal?" Paillier answers "who is '
        'allowed to look at it at all?" Genuinely separate questions — you could have one without the other, but '
        "then you're only covered against one kind of attacker."
    ])
    add_qa(doc, "If DP-SGD already protects individual students, why bother encrypting the update with Paillier too?", [
        "DP noise makes the update statistically safe to reveal — it's still the actual number being transmitted. "
        "Without Paillier, the server (or anyone sniffing the network) sees each school's real, DP-noised update in "
        "the clear. With Paillier, they only ever see ciphertext."
    ])
    add_qa(doc, "What does epsilon (ε) actually mean, in plain terms?", [
        "It bounds how much any single student's presence or absence could change the model's output. Smaller ε "
        "means a stronger guarantee. We target ε ≤ 3.0 per round, and our privacy-accuracy sweep shows F1 stays "
        "strong (roughly 0.91–0.94) even down to ε≈0.07 — the strongest privacy setting we tested — so the accuracy "
        "cost of strong privacy here is genuinely small."
    ])
    add_qa(doc, "Doesn't Paillier decryption on the server defeat the purpose — the server still learns the combined model?", [
        "Yes, by design — the server is meant to learn the aggregated global model; that's the whole point of "
        "federated learning. What it must never learn is any individual school's raw update. Paillier's homomorphic "
        "addition means the server only ever decrypts the already-combined sum, never a single school's "
        "contribution in isolation."
    ])
    add_qa(doc, "What stops the server from analysing the encrypted update anyway?", [
        "Semantic security — Paillier ciphertexts don't leak anything about the plaintext even to someone with "
        "unlimited computation on the ciphertext alone. The server can only produce meaningful output by "
        "decrypting, and by construction it only ever decrypts the already-aggregated sum across all schools that "
        "round."
    ])
    add_qa(doc, "What actually happens on the wire when Paillier is on — describe it precisely.", [
        "Each of the 2,689 model parameters gets encrypted individually into its own Paillier ciphertext, "
        "serialized to a big integer string, sent as JSON. The server multiplies each school's ciphertext-array by "
        "that school's FedAvg weight — Paillier supports this as scalar multiplication on ciphertext — then adds "
        "all schools' weighted ciphertext-arrays together element-wise, still encrypted. Only that single combined "
        "result gets decrypted."
    ])
    add_qa(doc, "Couldn't a malicious school lie about how many students it has, to game the FedAvg weighting?", [
        "Honestly — yes, and we don't defend against that. FedAvg trusts each client's reported sample count. It's "
        "a known open problem in federated learning generally (robust aggregation against malicious clients is its "
        "own research area). Our threat model here is privacy-preserving collaboration between honest-but-curious "
        "schools, not defense against an actively malicious participant."
    ], honesty=True)

    # ---- Section 3: Results ----
    add_section(doc, 6, "Results & Statistical Proof",
                "This is the section with real evidence behind it — use the actual numbers, don't round them off.")
    add_fact_strip(doc, [("Baseline F1", "0.9386"), ("Paired t-test p", "0.9156"), ("Cohen's d", "-0.05")])

    add_qa(doc, "Is a small percentage-point difference between federated and centralised F1 actually meaningful, or just noise?", [
        "We ran 5 independent bootstrap resamples of the train/test split, training both a centralised and "
        "federated model on each. A paired t-test gave p = 0.9156 — nowhere near the 0.05 significance threshold — "
        "meaning we cannot say federated and centralised performance differ at all. Cohen's d was -0.05, a "
        "negligible effect size. The small differences you see round to round are resampling noise, not a real "
        "performance gap."
    ])
    add_qa(doc, 'Your proposal says "5 independent random partitions" for the statistical test — but you only have 4 real quarters. How did you resolve that?', [
        "We reframed it: instead of drawing 5 random school partitions (impossible with only 4 real quarters), we "
        "drew 5 independent random train/test splits within the same fixed real-quarter school assignment, and ran "
        "the full centralised-vs-federated comparison on each. That gives 5 genuinely independent paired "
        "observations for the significance test, while still using 100% real data throughout."
    ])
    add_qa(doc, "Why did you disable DP and Paillier for that statistical test?", [
        "That test validates Objective 1 specifically — federated accuracy parity with centralised training. "
        "Objective 2 (the encryption guarantee) is a separate, already-validated claim via the cryptographic audit "
        "log. Mixing DP noise into the parity test would conflate two different questions — \"does FL work as well "
        "as centralised training\" and \"what does privacy cost you\" — so we isolated them."
    ])
    add_qa(doc, "Does the same F1 parity hold at 4 or 5 nodes, not just 3?", [
        "We smoke-tested the full pipeline at 4 and 5 nodes and confirmed it runs correctly end-to-end with strong "
        "F1 (~0.93 in both cases), but the formal 5-seed statistical significance test was only run at 3 nodes. "
        "Extending it to 4/5-node configs would be a natural next step, not something we've formally claimed yet."
    ], honesty=True)

    # ---- Section 4: Systems ----
    add_section(doc, 7, "Systems & Architecture",
                "The infrastructure decisions — why Flower, why this model size, what happens when a school drops out.")

    add_qa(doc, "Why Flower specifically, not a custom solution?", [
        "It handles the client/server communication protocol, round scheduling, and client sampling out of the "
        "box, and exposes a Strategy interface we could override to inject Paillier aggregation — PaillierFedAvg "
        "in server/strategy.py. Writing that networking layer from scratch would be infrastructure work orthogonal "
        "to the actual research contribution."
    ])
    add_qa(doc, "What happens if a school goes offline mid-round?", [
        "The server samples only the schools actually online for that round — client_manager tracks who's "
        "registered, and a school marked offline never gets asked to train. Its status shows \"OFFLINE — queued\" "
        "on the dashboard, and training continues with the remaining schools. For real deployment (not just the "
        "live demo toggle), a separate nightly cron sync daemon queues a school's update locally if it's genuinely "
        "disconnected, and retransmits it automatically the next time it's online."
    ])
    add_qa(doc, "Why is the MLP so small — only two hidden layers?", [
        "The proposal spec fixes this architecture (8→64→32→1) specifically so training is fast enough to run many "
        "FL rounds on constrained hardware like a Pi 4 — the research contribution here is the federated/privacy "
        "infrastructure, not squeezing out extra accuracy from a bigger model. Given the baseline already hits F1 "
        "0.94 and AUC 0.98 on this architecture, there wasn't a compelling case to complicate it."
    ])
    add_qa(doc, "Has this actually run on a Raspberry Pi, like the proposal specifies?", [
        "Not yet — the code and deployment script (deploy_client.sh) are ready and correct, and comm overhead / "
        "latency are already logged automatically every round, but real Pi hardware benchmarking (latency, energy "
        "via UM25C, packet-loss testing) hasn't been run. It's the one proposal objective still unproven on "
        "physical hardware rather than in simulation."
    ], honesty=True)

    # ---- Section 5: Metrics ----
    add_section(doc, 8, "Reading the Metrics Right",
                "These trip people up because the numbers look similar but answer different questions.")

    add_qa(doc, 'What does "Balanced Accuracy" mean, and why isn\'t it the same as AUC?', [
        "Balanced accuracy is the average of sensitivity (catching real at-risk students) and specificity "
        "(correctly leaving safe students alone) — computed at one specific decision threshold the model commits "
        "to. AUC measures something different: the model's ability to rank at-risk above not-at-risk students "
        "correctly, across every possible threshold at once.",
        "AUC is the ceiling — the model's full separating potential. Balanced accuracy is how much of that ceiling "
        "gets realised once you force one concrete yes/no decision per student. AUC is always ≥ balanced accuracy "
        "at any single threshold; a big gap between them would be the thing worth investigating, not a small one."
    ])
    add_qa(doc, "What threshold does the model actually use — is it 0.5?", [
        "No — the code never uses a fixed 0.5. Every evaluation computes its own cutoff via Youden's J statistic "
        "(the point on the ROC curve that maximises true-positive rate minus false-positive rate), recomputed per "
        "school, per round, from that round's own data. In one real run this came out to 0.5821, not 0.5 — a "
        "genuinely different, evidence-based number each time."
    ])
    add_qa(doc, "How would you actually identify a specific at-risk student?", [
        "Two different questions get conflated here. The actual count of at-risk students is just the real label "
        "already in the data (e.g. school_gamma is 57% at-risk) — nothing to do with the model. Spotting one "
        "specific student means feeding their features through the trained model to get a probability, then "
        "comparing it against that round's threshold.",
        "Important point for the defense: our dashboard deliberately never does this for individual students. "
        "Per-student predictions would only ever happen locally, inside a school's own system, on that school's "
        "own roster — never surfaced to the district-level dashboard, which only ever shows aggregated numbers. "
        "That's not a missing feature, it's the actual privacy guarantee working as designed."
    ])

    # ---- Section 6: Dashboard ----
    add_section(doc, 9, "Walking Through the Dashboard",
                "If asked to explain what's on screen during the live demo, here's the tour.")

    add_qa(doc, "What do the header badges and the six metric cards mean?", [
        "Header badges show the live config for the current run: Flower version, Paillier key size, DP-SGD status, "
        "and Idle/Running state.",
        "The six cards: Current Round (progress through the configured total); F1-Score (macro) (primary "
        "evaluation metric); Balanced Accuracy + AUC (see Section 5); Privacy Budget ε (worst case across all "
        "schools that round); Comm. Overhead (encrypted MB transmitted per round — target <50MB); School Nodes "
        "(how many participated vs how many are offline)."
    ])
    add_qa(doc, "Why does the Privacy-Accuracy chart show data before you even start a simulation, but the Convergence chart doesn't?", [
        "They pull from two different places. The Privacy-Accuracy chart reads a pre-computed file "
        "(results/privacy_accuracy_tradeoff.json) generated once offline by privacy_accuracy_sweep.py — it shows "
        "up immediately because the file already exists. The Convergence and Comm. Overhead charts read live "
        'telemetry from an actual running simulation, so they correctly show "No data yet" until you click Start.'
    ])
    add_qa(doc, "What's the completion summary popup for?", [
        "When a run finishes, a modal automatically summarises the final F1, balanced accuracy, AUC, max privacy "
        "budget, total communication overhead, active config, and — most usefully for the demo — a direct "
        'pass/fail line against the centralised baseline ("✓ Within the 5pp target"), which is Objective 1 '
        "confirmed live, on screen, the moment a round finishes."
    ])

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(24)
    fr = footer.add_run(
        "Cross-School Federated Learning — Group 7 — Defense Q&A Study Guide\n"
        "Compiled for presentation preparation — share freely within the group"
    )
    fr.font.size = Pt(9)
    fr.font.color.rgb = MUTED

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "FL_Ghana_Defense_QA_Study_Guide.docx",
    )
    doc.save(out_path)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    build()
