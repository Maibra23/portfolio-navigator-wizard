# Risk Profiling System: Questionnaire, Gamified Scenario, Screening, and Scoring Logic

This document describes the full risk profiling system: screening questions, gamified (storyline) scenario, Modern Portfolio Theory (MPT) and Prospect Theory question pools, how they interact, and the mathematics used to produce a normalized risk score and category. It is written for both technical and non-technical readers.

---

## 1. Overview

The risk profiler has three stages:

1. **Screening** – Three non-scored questions (age, experience, knowledge) that determine which questions the user sees and in what form (gamified storyline vs. traditional MPT/Prospect mix).
2. **Questions** – Either 5 gamified storyline steps (under-19) or 12 traditional questions (19+) drawn from MPT and Prospect Theory pools according to a ratio.
3. **Result** – A single normalized risk score (0–100), optional MPT/Prospect sub-scores, and a risk category (very-conservative through very-aggressive).

Screening never contributes points. Only the questions selected in stage 2 are scored. Scoring uses 0-based normalization per question so that different scale lengths (e.g. 1–4 vs 1–5) are comparable.

---

## 2. Screening Questions (S1, S2, S3)

Screening questions are implemented in the UI only. They have no numeric scores (maxScore is not used for them in the scoring pipeline). They are used only for routing and question-set selection.

### 2.1 S1 – Age group

- **Question:** What is your age group?
- **Options:**
  - Under 19 years old → `ageGroup: 'under-19'`
  - 19 years old or above → `ageGroup: 'above-19'`
- **Role:** If `under-19`, the user sees the **gamified storyline** (5 fixed scenario steps) and no MPT/Prospect pool questions. If `above-19`, the user sees 12 questions from the MPT and Prospect pools, with the mix set by S2 and S3.

### 2.2 S2 – Investment experience

- **Question:** How many years of investing experience do you have?
- **Options:** 0–2 years, 3–5 years, 6–10 years, 10+ years  
- **Internal mapping (experience points):**  
  `0-2 → 0`, `3-5 → 1`, `6-10 → 2`, `10+ → 3`  
- **Role:** Combined with S3 into an “experience points” value that drives the MPT vs Prospect ratio for users 19+ (see Section 4).

### 2.3 S3 – Investment knowledge

- **Question:** How would you rate your investment knowledge?
- **Options:** Beginner, Intermediate, Advanced  
- **Internal mapping (knowledge points):**  
  `beginner → 0`, `intermediate → 1`, `advanced → 2`  
- **Role:** Added to experience points for 19+ users to determine question mix.

### 2.4 Experience points (for 19+ only)

- **Formula:**  
  `experiencePoints = experienceMap[S2] + knowledgeMap[S3]`  
  So: 0–5 (0+0 to 3+2).
- **Usage:** Drives MPT vs Prospect ratio together with age (Section 4). Screening answers are not sent to the scoring function; only the **selected question set** and **answers to those questions** are.

---

## 3. Gamified Questioning Scenario (Storyline)

### 3.1 When it is used

- **Condition:** S1 = “Under 19 years old”.
- **Effect:** The user does not see any MPT or Prospect pool questions. Instead they see exactly **5 storyline steps** in a fixed order. Each step is one scenario with 4 options. The system maps these steps to internal “questions” with `group: 'PROSPECT'`, `maxScore: 4`, and `construct: 'gamified_scenario'` so the same scoring pipeline can run.

### 3.2 How it works

- One scenario is shown at a time (story-1 → story-5).
- Each scenario has: scenario text, visual, avatar mood, 4 options (text, icon, consequence, score 1–4), and optional feedback.
- User picks one option. The **score** (1–4) of that option is what is used for scoring; the UI maps option index to value 1–4 so that the stored answer is in 1–4.
- After the choice, consequence/feedback is shown; then the flow moves to the next scenario (or to result after story-5).
- No branching: every user sees the same 5 scenarios in order. “Next scenario” text is narrative only; the next step is always the next node in the array.

### 3.3 Storyline nodes and options (all questions in the gamified path)

**Story 1 – Prize money (story-1)**  
Scenario: You just won $1,000 in a gaming tournament. Your friends are celebrating, but now you need to decide what to do with your prize money.  
- Option A: Cash out safely → Guaranteed $1,000 (score 1)  
- Option B: Buy streaming gear → Grow audience, potential future income (score 2)  
- Option C: Invest in gaming stocks → Market-dependent returns (score 3)  
- Option D: Fund indie game studio → High risk, huge potential (score 4)  

**Story 2 – Market drop (story-2)**  
Scenario: Your investment choice is working. Your $1,000 has grown to $1,500, but there is news of a big market drop coming.  
- Option A: Sell everything now → Lock in $500 profit (score 1)  
- Option B: Sell half, keep half → Balance safety and opportunity (score 2)  
- Option C: Wait and see → Ride out the storm (score 3)  
- Option D: Buy more on the dip → Double down (score 4)  

**Story 3 – Savings and goals (story-3)**  
Scenario: You have $2,000 saved. Your dream is to start your own business, but you also want to travel the world.  
- Option A: Put it all in savings → Safe, slow growth (score 1)  
- Option B: Use it for travel now → Experiences, no investment (score 2)  
- Option C: Start a small business → High risk, own boss (score 3)  
- Option D: Invest in crypto/startups → Maximum risk and potential (score 4)  

**Story 4 – Once-in-a-lifetime opportunity (story-4)**  
Scenario: Your choices paid off; you have $5,000. You discover a once-in-a-lifetime opportunity that requires all your money.  
- Option A: Too risky, keep my money (score 1)  
- Option B: Invest 25% (score 2)  
- Option C: Invest 50% (score 3)  
- Option D: Go all-in (score 4)  

**Story 5 – Advice to a friend (story-5)**  
Scenario: Your journey has taught you a lot. A friend just got $500. What advice would you give based on your experience?  
- Option A: Save it all safely (score 1)  
- Option B: Learn first, then invest (score 2)  
- Option C: Start small, grow gradually (score 3)  
- Option D: Take calculated risks (score 4)  

### 3.4 Interaction with the rest of the system

- **Scoring:** Each storyline step is treated as one question with `maxScore: 4`. The chosen option’s score (1–4) is the answer value. The same 0-based normalization and aggregate formula as for pool questions is applied (Section 6).
- **Sub-scores:** These steps have `group: 'PROSPECT'`, so they contribute only to the Prospect sub-score (and to the overall normalized score), not to MPT.
- **No MPT in gamified path:** Under-19 users have no MPT questions; their `normalized_mpt` is 0 (or N/A). The overall risk category is based on the single combined normalized score from the 5 storyline steps.

---

## 4. Question Selection (19+ only): Adaptive Branching System

For users 19 or older, the system uses an **adaptive branching** approach rather than random selection. Questions are presented in a fixed, phased sequence that adapts based on the user's responses.

### 4.1 Three-Phase Adaptive Flow

**Phase 1 – Anchor Questions (Always First)**
Four anchor questions are always asked first in a fixed order:
- M2 (time_horizon)
- M3 (volatility_tolerance)
- PT-2 (loss_aversion)
- PT-6 (drawdown_behavior)

These establish a baseline risk profile from which the system determines the next phase.

**Phase 2 – Adaptive Refinement**
Based on the Phase 1 responses, the system selects one of three question pools:
- **Conservative Confirming:** M5, M8, PT-1, PT-4 (for users showing conservative tendencies)
- **Aggressive Confirming:** M4, M11, PT-8, PT-10 (for users showing aggressive tendencies)
- **Discriminating/Moderate:** M6, M10, PT-3, PT-7 (for users with mixed responses)

**Phase 3 – Gap Filling and Consistency**
The system then:
1. Identifies any missing constructs and adds questions to cover them
2. Asks PT-13 if not already covered
3. Adds consistency-check pairs (reverse-coded questions like M3-R and PT-2-R) to verify response reliability

### 4.2 Answer Option Order

- **Under-19 (gamified path):** Options are shown in fixed source order
- **Above-19 (adaptive path):** Options are **randomized** per question using `sort(() => Math.random() - 0.5)` to prevent pattern memorization

### 4.3 Why Adaptive Branching?

The adaptive system provides several advantages over random selection:
- **More accurate profiling:** Questions are tailored to refine the user's specific risk tendencies
- **Consistency validation:** Reverse-coded questions detect unreliable responses
- **Efficient coverage:** Ensures all relevant constructs are assessed without redundancy
- **Deterministic behavior:** The question sequence is reproducible given the same responses

### 4.4 Scoring Independence

Scoring is **order-independent** and uses `answersMap[question.id]` for lookup. The adaptive question order does not affect final scores—only the selected questions and their answers matter.

---

## 5. All Questions in the Profiling System

Below are all questions that can appear: screening (no scoring), gamified (5 steps), MPT pool (15), Prospect pool (12). The gamified steps are listed in Section 3.3; here we list screening and the two pools.

### 5.1 Screening (no scoring, routing only)

| # | Question | Options |
|---|----------|--------|
| S1 | What is your age group? | Under 19 years old; 19 years old or above |
| S2 | How many years of investing experience do you have? | 0–2 years; 3–5 years; 6–10 years; 10+ years |
| S3 | How would you rate your investment knowledge? | Beginner; Intermediate; Advanced |

### 5.2 MPT question pool (15 questions, all 1–5 scale, maxScore 5 each)

| ID | Construct | Question | Scale (1–5) |
|----|-----------|----------|-------------|
| M1 | time_horizon | How would you prefer to allocate your investments over a long time horizon? | All stable → All growth |
| M2 | time_horizon | What is your preferred investment time horizon? | &lt;2 years → 20+ years |
| M3 | volatility_tolerance | How much volatility can you tolerate in your portfolio? | Very low → Very high |
| M4 | capital_allocation | What percentage of your total savings are you planning to invest? | &lt;10% → &gt;75% |
| M5 | income_requirement | How important is it that your investments provide steady income? | Extremely important → Not important (growth) |
| M6 | capital_preservation | What is your primary investment goal? | Capital preservation → Maximum growth |
| M7 | return_utilization | How do you plan to use your investment returns? | Immediate spending → Long-term wealth building |
| M8 | market_reaction | What is your reaction to market downturns? | Sell immediately → See as opportunity |
| M9 | diversification_preference | How many different types of investments would you prefer to hold? | 1–2 → As many as possible |
| M10 | liquidity_constraint | How quickly might you need access to your invested money? | Within days → Not for 5+ years |
| M11 | concentration_risk | What percentage of your portfolio would you put in your single best investment idea? | &lt;5% → &gt;40% |
| M12 | recovery_tolerance | If your investments dropped 20%, how long would you be willing to wait for recovery? | &lt;6 months → 5+ years |
| M13 | rebalancing_frequency | How often would you want to review and adjust your investments? | Daily/weekly → Rarely/never |
| M14 | tax_sensitivity | How important is minimizing taxes on your investment gains? | Extremely important → Not important |
| M15 | values_alignment | How much would you sacrifice returns to invest according to your values (ESG)? | Significant sacrifice → No sacrifice |

Total MPT maxScore sum = 15 × 5 = **75**.

### 5.3 Prospect Theory question pool (12 questions; 11 with maxScore 4, PT-8 with maxScore 5)

| ID | Construct | Question | Scale |
|----|-----------|----------|--------|
| PT-1 | certainty_effect | Guaranteed 5,000 SEK vs 75% chance at 7,000 SEK? | 1–4 |
| PT-2 | loss_aversion | Guaranteed loss 2,000 SEK vs 50% chance to lose 4,000 SEK? | 1–4 |
| PT-3 | regret_aversion | Portfolio gained 30%. Sell all / some / hold / invest more? | 1–4 |
| PT-4 | probability_weighting | Option A (90% +10%, 10% -5%) vs Option B (50% +20%, 50% -10%)? | 1–4 |
| PT-5 | sector_preference | One sector: Utilities / Consumer staples / Technology / Crypto? | 1–4 |
| PT-6 | drawdown_behavior | Investment lost 20% in one month: sell all / some / hold / buy more? | 1–4 |
| PT-7 | anchoring_bias | Bought at 1,000, now 800, analysts say 600: sell now / at 1,000 / hold / buy more? | 1–4 |
| PT-8 | disposition_effect | One up 30%, one down 30%; need cash: sell winner / overvalued / half each / analyze / sell loser? | 1–5 |
| PT-9 | overconfidence_bias | After 2 hours research, how confident in your decision? | 1–4 |
| PT-10 | herd_behavior | Everyone buying a trending investment: avoid / skeptical / research / join immediately? | 1–4 |
| PT-11 | representativeness_bias | Company had 5 great years. How likely is year 6 great? | 1–4 |
| PT-12 | endowment_effect | Inherited stock 50,000 SEK; you wouldn’t buy at this price. Keep or sell? | 1–4 |

Prospect maxScore sum = 11×4 + 1×5 = **49**.

---

## 6. Scoring Mathematics and Logic

### 6.1 Inputs

- **selectedQuestions:** List of questions that the user actually saw (either 5 storyline steps or 12 pool questions). Each has `id`, `group` ('MPT' or 'PROSPECT'), and `maxScore` (4 or 5).
- **answersMap:** Object mapping each question `id` to the user’s chosen option **value** (1 to maxScore). Unanswered questions have no key or undefined; they are treated as 0 for raw sum and excluded from the 0-based adjusted sum (see below).

Screening questions are not in `selectedQuestions`; they are never passed to the scoring function.

### 6.2 Exclusion rule

- Any question with `group === 'SCREENING'` or `maxScore === 0` is skipped in all scoring steps. In practice, screening is not in the selected set, so this applies to any future screening-style items if ever added.

### 6.3 Raw score (legacy)

- **Formula:** For each non-excluded question, add `answersMap[question.id]` (or 0 if missing).  
  `raw_score = sum over selected questions of (answer value or 0)`.
- **Note:** This sum mixes different scales (e.g. 1–4 and 1–5) and is not used for categorization. It is kept for compatibility.

### 6.4 0-based normalization (used for categories and sub-scores)

- **Idea:** Map each question to a 0–1 scale so that “minimum risk” = 0 and “maximum risk” = 1, regardless of whether the question uses 1–4 or 1–5.
- **Per-question adjusted value:**  
  `adjusted = max(0, answerValue - 1)`.  
  So for a 1–5 question, possible values are 0,1,2,3,4; for 1–4, they are 0,1,2,3.
- **Per-question maximum adjusted value:**  
  `maxAdjusted = max(0, maxScore - 1)`.  
  So 4 for maxScore 5, and 3 for maxScore 4.
- **Normalized contribution of one question (conceptually):**  
  `(answerValue - 1) / (maxScore - 1)`, clamped to [0, 1]. So each question contributes in [0, 1].

**Aggregate (over all selected, non-screening questions):**

- `rawAdj = sum of (answerValue - 1)` for answered questions (undefined → skip, no term).
- `maxAdj = sum of (maxScore - 1)` for all such questions.
- **Overall normalized score (0–100):**  
  `normalized_score = (rawAdj / maxAdj) * 100`,  
  clamped to [0, 100]. If `maxAdj === 0`, then `normalized_score = 0`.

**Sub-scores (same 0-based logic, but only for MPT or only for PROSPECT):**

- MPT: `rawAdjMPT` = sum of `(answerValue - 1)` for questions with `group === 'MPT'`; `maxAdjMPT` = sum of `(maxScore - 1)` for those questions.  
  `normalized_mpt = (rawAdjMPT / maxAdjMPT) * 100` (or 0 if `maxAdjMPT === 0`).
- Prospect: `rawAdjProspect` and `maxAdjProspect` analogously for `group === 'PROSPECT'`.  
  `normalized_prospect = (rawAdjProspect / maxAdjProspect) * 100` (or 0 if `maxAdjProspect === 0`).

So:

- **Gamified path:** Only PROSPECT questions (5 × maxScore 4). `normalized_mpt` is 0 (no MPT questions). Overall and Prospect sub-score use the same 5 questions.
- **Traditional path:** Both MPT and Prospect contribute to overall; `normalized_mpt` and `normalized_prospect` sum over their respective subsets.

### 6.5 Risk categories and thresholds

The **overall** risk category is determined only by `normalized_score` (the 0–100 value):

| normalized_score | risk_category      | color_code (hex) |
|------------------|--------------------|------------------|
| 0 ≤ score ≤ 20   | very-conservative  | #00008B          |
| 20 < score ≤ 40  | conservative      | #ADD8E6          |
| 40 < score ≤ 60  | moderate           | #008000          |
| 60 < score ≤ 80  | aggressive         | #FFA500          |
| 80 < score ≤ 100 | very-aggressive    | #FF0000          |

Boundaries are exclusive on the left (e.g. 20 is very-conservative, 20.01 is conservative).

### 6.6 Outputs of the scoring function

- **raw_score:** Sum of raw answer values (legacy).
- **normalized_score:** 0–100, used for category.
- **normalized_mpt:** 0–100, MPT subset only (0 if no MPT questions).
- **normalized_prospect:** 0–100, Prospect subset only (0 if no Prospect questions).
- **risk_category:** One of the five labels above.
- **color_code:** Associated hex color for UI.

---

## 7. End-to-end flow summary

1. **Screening:** User answers S1 (age), S2 (experience), S3 (knowledge). No points; only routing.
2. **Routing:**
   - If under 19 → select 5 gamified storyline steps in fixed order (story-1 through story-5, mapped to PROSPECT, maxScore 4).
   - If 19+ → enter the adaptive branching flow (Phase 1 → Phase 2 → Phase 3 as described in Section 4).
3. **Questions:** 
   - Under-19: Options shown in fixed order.
   - 19+: Options are **randomized** per question to prevent pattern memorization. Questions follow the adaptive sequence.
4. **Scoring:** For the selected set and answers: exclude screening; compute raw score (legacy); compute 0-based adjusted sums and max sums overall and per group; get normalized_score, normalized_mpt, normalized_prospect; map normalized_score to risk_category and color_code. Scoring is order-independent.
5. **Result:** Show risk category, description, and optionally MPT/Prospect sub-scores. The same pipeline supports both gamified and traditional paths because storyline steps are represented as PROSPECT questions with maxScore 4 and the same normalization is applied.

---

## 8. Summary table: what drives what

| Element           | Used in scoring? | Drives routing? | Drives mix (19+)? |
|-------------------|------------------|------------------|-------------------|
| S1 (age)          | No               | Yes (story vs 12) | No (age branch)  |
| S2 (experience)   | No               | No (only with S3) | Yes (experiencePoints) |
| S3 (knowledge)    | No               | No (only with S2) | Yes (experiencePoints) |
| Gamified steps    | Yes (as PROSPECT)| N/A              | N/A (only path for under-19) |
| MPT pool questions| Yes (if selected)| N/A              | Count from ratio   |
| Prospect pool questions | Yes (if selected) | N/A          | Count from ratio   |

This completes the description of the gamified scenario, screening questions, all questions in the system, and the math and logic of the risk profiling system.
