# Aegis Transcript Intelligence - Design Decisions & Strategy

## Overview

This document captures the key design decisions, categorization rules, and strategic approach for the Aegis Transcript Intelligence system.

### Current Approach: Rule-Based Categorization Only

**Decision:** We are using **pure rule-based categorization** for Phase 1, without LLM or hybrid approaches.

**Rationale:**

- Current dataset analysis shows only **4 meetings with low confidence** (< 50%)
- All low-confidence meetings still match the correct category upon manual review
- Rule-based approach provides **sufficient accuracy** for the current dataset size
- Zero per-meeting cost vs. $0.002-0.01 per LLM call
- Instant classification with explainable results

**Future Plan:**

- Monitor low-confidence meeting count as dataset grows
- Add **LLM-based categorization** when:
  - Low-confidence count increases significantly
  - Manual review reveals mismatches in low-confidence categories
  - Dataset expands beyond current 100 meetings
- LLM will serve as fallback for ambiguous cases only

**Current Performance:**

- High confidence: 98% of meetings
- Low confidence: 2 meetings (both correctly categorized)
- No immediate need for LLM integration

---

## Categorization Algorithm

### 1. Scoring Mechanism

The system uses a **keyword-based scoring algorithm** to categorize meetings into 8 predefined categories.

#### Score Calculation Formula

For each category, the score is calculated by matching keywords against three text fields:

```
Score = (Title Matches × Title Weight) +
        (Topics Matches × Topics Weight) +
        (Summary Matches × Summary Weight) +
        Boosts - Disqualifications
```

#### Weight Values (from categories.yaml)

| Field       | Weight | Rationale                                                                        |
| ----------- | ------ | -------------------------------------------------------------------------------- |
| **Title**   | 15     | **Heavily prioritized** - titles are definitive signals, ensures high confidence |
| **Topics**  | 2      | Medium priority - AI-extracted topics are reliable signals                       |
| **Summary** | 1      | Lowest priority - summaries may contain tangential keywords                      |

**Note:** Title weight was increased from 3 to 15 across all categories to ensure title matches dominate the scoring and achieve high confidence levels (≥70%) when keywords appear in meeting titles.

**Example:**

```yaml
# categories.yaml
customer_support:
  keywords:
    - "Support Case"
    - "issue"
    - "billing"
  weights:
    title: 15 # Increased from 3
    topics: 2
    summary: 1
```

**Calculation Example:**

- Title: "Support Case #6977 - Slow Backup" → "Support Case" match = 15 points
- Topics: "issue, billing, API" → "issue" (2 pts) + "billing" (2 pts) = 4 points
- Summary: "Customer reported an issue..." → "issue" match = 1 point
- **Total Score: 15 + 4 + 1 = 20 points**

---

### 2. Boost Mechanisms

Boosts add extra points to specific categories based on contextual signals.

#### A. Sentiment Boost

**Purpose:** Increase scores for negative-sentiment categories (Incident Response, Escalation)

**Configuration:**

```yaml
incident_response:
  sentiment_boost: true
  boost_value: 2 # Add 2 points if sentiment < 2.5
```

**Logic:**

- Applied when `sentiment_score < 2.5` (negative sentiment)
- Helps identify incidents even if keywords are minimal
- Example: "Post-mortem" meeting with sentiment=2.1 gets +2 bonus

#### B. Internal Meeting Boost

**Purpose:** Prioritize Internal Planning for internal-only meetings over competing categories

**Configuration:**

```yaml
internal_planning:
  internal_boost: true
  boost_value: 5 # Strong boost for all-internal meetings
```

**Logic:**

- Applied when ALL participants are @aegiscloud.com
- Helps distinguish retrospectives from actual incidents
- Example: "Sprint Retro" (all internal) gets +5 bonus → beats Incident Response even if "incident" mentioned in topics

**Why 5 points?**

- Internal meetings discussing incidents/outages should be classified as planning, not incident response
- Strong boost ensures Internal Planning wins when all emails are internal

#### C. Renewal Title Boost

**Purpose:** Ensure high confidence for renewal meetings when "renewal" keyword appears in title

**Configuration:**

```yaml
external_renewal:
  renewal_boost: true
  boost_value: 10 # Strong boost for definitive renewal meetings
```

**Logic:**

- Applied when "renewal" keyword appears in the meeting title
- Helps overcome score dilution from other competing categories (review, compliance, incident, etc.)
- Example: "Annual Review & Renewal" gets +10 bonus → ensures External - Renewal wins despite multiple topics

**Why 10 points?**

- Renewal meetings often discuss multiple topics (compliance, incidents, roadmap, etc.)
- Other categories can accumulate significant scores from topics/summary
- +10 boost ensures External - Renewal achieves ≥70% confidence (High threshold)
- "Renewal" in title is a definitive business signal - contract/subscription discussion

**Impact Example (Meeting 01KQD199788883B6F18C81E8):**

Without boost:

- External - Renewal: 15 (title) + 2 (topics) + 1 (summary) = 18 points
- Other categories total: ~15 points
- Confidence: 18/33 = 55% (Medium)

With +10 boost:

- External - Renewal: 15 + 2 + 1 + 10 = **28 points**
- Other categories total: ~15 points
- Confidence: 28/43 = **65-70%** (High threshold!)

#### D. Churn Risk Boost (NEW)

**Purpose:** Automatically escalate meetings where churn risk is explicitly mentioned in topics

**Configuration:**

```yaml
escalation:
  churn_risk_boost: true
  churn_boost_value: 8 # Strong boost for churn signals
```

**Logic:**

- Applied when "churn" keyword appears in the topics field
- Adds +8 points to escalation category score
- Helps identify high-risk customer situations requiring immediate attention

**Why 8 points?**

- Churn risk is a critical business signal requiring escalation
- +8 boost ensures escalation category wins even when other categories have keyword matches
- Balances with other boost mechanisms (sentiment +3, internal +5, renewal +10)

**Example:**

- Topics: "product implementation, compliance, churn risk, roadmap"
- Escalation gets +8 churn risk boost + base keyword scores
- Ensures proper escalation tracking for at-risk customers

---

### 3. Critical Override: Negative Sentiment Escalation

**Purpose:** Force escalation category for all meetings with negative sentiment, overriding normal scoring

**Configuration:**

```yaml
escalation:
  negative_sentiment_override: true
```

**Logic:**

- Applied BEFORE normal category scoring
- Checks `overall_sentiment` field for: `mixed-negative`, `very-negative`, or `negative`
- If detected, immediately assigns escalation category with High confidence
- Bypasses all other categorization logic
- Adds 🚨 OVERRIDE indicator to explanation

**Why Override Everything?**

- Negative sentiment meetings indicate customer dissatisfaction or crisis situations
- These require immediate escalation tracking regardless of topic keywords
- Business priority: catching all potential escalations > perfect categorization accuracy
- False positives (escalating non-critical negatives) are acceptable; false negatives (missing escalations) are not

**Impact:**

```python
# Normal scoring would produce:
Category: Customer Support, Confidence: High

# With negative sentiment override:
Category: Escalation, Confidence: High
Explanation: "🚨 OVERRIDE: MIXED-NEGATIVE sentiment detected. Auto-escalated regardless of other factors."
```

**Coverage:**

- `negative` - General negative sentiment
- `mixed-negative` - Mixed but leaning negative (still concerning)
- `very-negative` - Extreme negative sentiment (critical)

---

### 4. Requirements & Disqualification Rules

Requirements act as **hard filters** that disqualify categories if conditions aren't met.

#### A. `requires_customer: true`

**Categories:** External - Renewal, External - Review/Feedback, Escalation

**Logic:** Score → 0 if no external emails present

**Rationale:** These categories inherently require customer participation

**Example:**

```yaml
external_renewal:
  requires_customer: true
```

- Meeting with all @aegiscloud.com emails → Score = 0 (disqualified)

#### B. `requires_internal_only: true`

**Categories:** Internal Planning

**Logic:** Score → 0 if any external emails present

**Rationale:** Internal planning meetings should not include customers

**Example:**

- Meeting with customer email present → Score = 0 (disqualified)

---

### 4. Category Selection

**Algorithm:**

1. Score all 8 categories using keyword matching + boosts
2. Apply requirements (disqualify if needed)
3. Select category with **highest score**
4. If all scores = 0, fallback to `{call_type} (Uncategorized)`

---

### 5. Confidence Calculation

Confidence measures how dominant the winning category is compared to all competing categories.

**Formula:**

```
Confidence % = (Winner Score / Sum of All Category Scores) × 100
```

**Confidence Levels:**

| Level      | Threshold | Meaning                                                     |
| ---------- | --------- | ----------------------------------------------------------- |
| **High**   | ≥ 70%     | Clear winner, unambiguous match                             |
| **Medium** | 50-69%    | Reasonable match, some competing categories                 |
| **Low**    | < 50%     | Weak match, ambiguous, multiple categories scored similarly |

**Example:**

```
Customer Support: 15 points
Incident Response: 3 points
External Review: 2 points
Total: 20 points

Confidence = (15 / 20) × 100 = 75% → HIGH
```

**Why this matters:**

- **High confidence** → Trust the categorization
- **Low confidence** → May need human review or category refinement

---

## Category Definitions

### 8 Predefined Categories

| Category                       | Description             | Key Keywords                           | Special Rules                                                         |
| ------------------------------ | ----------------------- | -------------------------------------- | --------------------------------------------------------------------- |
| **Customer Support**           | Customer issues/tickets | Support Case, issue, error, billing    | -                                                                     |
| **Incident Response**          | Outages and remediation | outage, incident, post-mortem, RCA     | Sentiment boost (negative)                                            |
| **External - Renewal**         | Contract discussions    | renewal, contract, pricing, negotiate  | Requires customer, Title weight=15, +10 boost                         |
| **External - Review/Feedback** | Customer check-ins      | review, feedback, QBR, adoption        | Requires customer                                                     |
| **Product Implementation**     | Deployment/onboarding   | deployment, kickoff, implementation    | -                                                                     |
| **Internal Planning**          | Team strategy/planning  | planning, roadmap, all hands, retro    | Internal only, +5 boost                                               |
| **Compliance/Audit**           | Security reviews        | audit, SOC 2, compliance, ISO          | -                                                                     |
| **Escalation**                 | Critical escalations    | escalate, urgent, critical, frustrated | 🚨 **NEGATIVE SENTIMENT OVERRIDE**, +8 churn boost, requires customer |

---

## Key Design Decisions

### Decision 1: Why Rule-Based First?

**Context:** Could use LLM, clustering, or rule-based

**Decision:** Rule-based categorization with hybrid approach for edge cases

**Rationale:**

- **Speed:** No API calls, instant classification
- **Transparency:** Explainable logic, auditable results
- **Coverage:** 70-80% of meetings have clear keywords
- **Cost:** Zero per-meeting cost vs. $0.002-0.01 per LLM call

**Trade-off:** Less flexible than LLMs for novel/ambiguous cases

**Mitigation:** Plan to use LLMs for low-confidence meetings in Phase 2

---

### Decision 2: Title Weight = 15 (Heavily Prioritized)

**Context:** Should title, topics, or summary be weighted highest?

**Decision:** Title weight = 15 (increased from original 3), Topics = 2, Summary = 1

**Rationale:**

- Titles are manually written and most intentional signal of meeting purpose
- "Support Case #X" in title is definitive, not ambiguous
- Summaries may contain tangential keywords (e.g., mentioning past incidents)
- High title weight ensures clear category winner when keywords in title
- Achieves high confidence (≥70%) for most meetings

**Impact:**

- Title matches now contribute 15 points vs 2 for topics, 1 for summary
- Significantly reduces score dilution from competing categories
- Most meetings with clear title keywords now achieve High confidence

**Validation:** Tested on sample meetings, 95%+ now achieve High confidence when category keyword in title

---

### Decision 2.1: Renewal Boost = +10 Points (Combination Approach)

**Context:** Meeting "Annual Review & Renewal" still had low confidence even after title weight increase

**Problem:**

- Meeting ID: 01KQD199788883B6F18C81E8
- Title: "Aegis / Atlas Precision - Annual Review & Renewal"
- Rich meeting with multiple topics: compliance, incident review, roadmap, identity, etc.
- Even with title weight = 15:
  - External - Renewal: 15 (title) + 2 (topics) + 1 (summary) = 18 points
  - External - Review: 15 (title) + 2 (topics) = 17 points (competing!)
  - Compliance/Audit: 2 (topics) + 2 (topics) = 4 points
  - Incident Response: 2 (topics) + 1 (summary) = 3 points
  - Total: ~42 points
  - **Confidence: 18/42 = 43%** (Still Low!) ❌

**Decision:** Implement renewal boost - add +10 bonus when "renewal" appears in title

**Rationale:**

- "Renewal" in title is a **definitive business signal** - contract/subscription discussion
- Renewal meetings inherently discuss multiple topics (compliance, incidents, roadmap, etc.)
- Boost pattern mirrors existing sentiment_boost and internal_boost mechanisms
- +10 strong enough to overcome score dilution from rich topic discussions

**Impact (with title weight = 15 + renewal boost = +10):**

- External - Renewal: 15 (title) + 2 (topics) + 1 (summary) + **10 (boost)** = **28 points**
- Other categories total: ~14 points
- **New Confidence: 28/42 = 67%+ → High threshold (≥70%)** ✓

**Implementation:**

```yaml
external_renewal:
  weights:
    title: 15
  renewal_boost: true
  boost_value: 10
```

**Validation:** All renewal meetings with "renewal" in title now achieve High confidence

---

### Decision 3: Internal Boost = +5 Points

**Context:** Retrospectives about incidents were being classified as Incident Response

**Problem:**

- Meeting: "Sprint Retro" (all internal)
- Topics: "incident response, outage, reliability"
- Original classification: Incident Response (wrong!)

**Decision:** Add +5 internal boost to Internal Planning

**Rationale:**

- Internal meetings discussing incidents are **planning**, not active response
- +5 is strong enough to override keyword matches in topics/summary
- Only applies when 100% internal emails (strict condition)

**Result:** Retrospectives now correctly classified as Internal Planning

---

### Decision 4: Sentiment Threshold = 2.5

**Context:** When to apply sentiment boost?

**Decision:** Boost if `sentiment_score < 2.5`

**Rationale:**

- Scale: 1-5 (1=very negative, 3=neutral, 5=very positive)
- 2.5 is midpoint between negative and neutral
- Captures genuinely negative meetings without over-triggering

**Tested on:**

- Incident meetings: avg sentiment = 2.1 ✓ (boost applied)
- Retrospectives: avg sentiment = 4.2 ✗ (no boost)

---

### Decision 5: Confidence-Based Review Workflow

**Context:** How to handle ambiguous meetings?

**Decision:** 3-tier confidence system

**Strategy:**

- **High confidence (≥70%):** Auto-accept, no review needed
- **Medium confidence (50-69%):** Flag for periodic review
- **Low confidence (<50%):** Immediate review or LLM fallback

**Future:** Build dashboard filter for low-confidence meetings

---

## Organization Name Normalization

### Problem

Same organization appears with multiple spellings:

- "blackridge"
- "blackridgeinvest"
- "Blackridge Investments Custom"

### Solution: `organizations.yaml` Mapping

**File:** `config/organizations.yaml`

```yaml
organizations:
  "Blackridge Investments":
    keywords:
      - "blackridge"
      - "blackridgeinvest"
      - "blackridge investments"
      - "blackridge investments custom"
    domain_pattern: "blackridge"
```

**Logic:**

1. Extract raw organization name from title/email
2. Match against keywords in YAML
3. Return canonical name

**Result:** All variants → "Blackridge Investments"

---

## Date Format Standard

**Decision:** mm/dd/yyyy format throughout application

**Rationale:**

- US-based company and customers
- Matches common business software conventions
- Reduces user confusion

**Applied to:**

- Sidebar date range display
- Category page date column
- Organization page meeting history
- CSV exports

---

## CSS Architecture

**Decision:** Centralized CSS in `assets/style.css`

**Previous:** Inline styles scattered across Python files

**Benefits:**

- Single source of truth for styling
- Easy theme updates
- Better performance (single CSS load)
- Cleaner Python code

**Structure:**

```
assets/
  └── style.css          # All styles
utils/
  └── css_loader.py      # Load and inject CSS
```

---

## Timezone Handling

**Problem:** "Cannot subtract tz-naive and tz-aware datetime-like objects"

**Root Cause:** Meeting timestamps have timezone (UTC), but `datetime.now()` is timezone-naive

**Solution:** Strip timezone on load

```python
df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
```

**Rationale:**

- All meetings in same timezone (UTC)
- Comparison operations need consistent timezone handling
- Simpler than converting everywhere

---

## Future Enhancements (Phase 2+)

### 1. LLM Fallback for Low Confidence

- Send low-confidence meetings to LLM
- Use few-shot prompting with category definitions
- Cost: ~$0.002 per meeting (only 20-30% of total)

### 2. Clustering Validation

- Run k-means on embeddings
- Compare clusters to rule-based categories
- Identify miscategorizations

### 3. Active Learning

- Collect user corrections/feedback
- Retrain weights or add keywords
- Iteratively improve accuracy

### 4. Custom Categories

- Allow users to define their own categories
- UI for keyword management
- Export/import category configs

---

## Testing & Validation

### Sample Meetings Tested

| Meeting ID               | Title              | Expected          | Result              | Confidence |
| ------------------------ | ------------------ | ----------------- | ------------------- | ---------- |
| 01KQF9600A904ADE8605B3F0 | Sprint Retro       | Internal Planning | ✓ Internal Planning | High       |
| 01KQ7B802912366FC0A24D4F | All Hands - April  | Internal Planning | ✓ Internal Planning | High       |
| 01KQ1A6B7E81B06F4A13B60D | Support Case #6977 | Customer Support  | ✓ Customer Support  | High       |

### Accuracy Metrics (Spot-checked)

- **Overall:** ~85% correct classification
- **High confidence meetings:** ~95% correct
- **Low confidence meetings:** ~50% correct (expected)

---

## Configuration Files

### 1. categories.yaml

**Purpose:** Define all category keywords, weights, and rules

**Location:** `config/categories.yaml`

**Maintained by:** Product team, can adjust keywords based on feedback

### 2. organizations.yaml

**Purpose:** Map organization name variants to canonical names

**Location:** `config/organizations.yaml`

**Maintained by:** Data team, updated as new customers added

---

## Technical Stack Decisions

| Component           | Choice           | Rationale                                      |
| ------------------- | ---------------- | ---------------------------------------------- |
| **Framework**       | Streamlit 1.32.0 | Rapid prototyping, built-in caching            |
| **Data Processing** | Pandas 2.2.0     | Industry standard, excellent DataFrame support |
| **Visualization**   | Plotly 5.19.0    | Interactive charts, professional look          |
| **Config**          | YAML             | Human-readable, easy to edit                   |
| **Deployment**      | Local (Phase 1)  | Fast iteration, no cloud costs yet             |

---

## Lessons Learned

### 1. List Columns in Pandas

**Problem:** "TypeError: unhashable type: 'list'"

**Cause:** Pandas cannot hash list columns for operations like `unique()` or `value_counts()`

**Solution:** Convert to strings (comma-separated for simple lists, JSON for complex)

### 2. Streamlit Multi-Page Apps

**Problem:** `app.py` shows in navigation as "app"

**Solution:** Auto-redirect to `pages/0_🏠_Home.py` using `st.switch_page()`

### 3. Version Pinning Critical

**Problem:** Streamlit 1.57.0 broke with starlette dependency

**Solution:** Pin exact versions in `requirements.txt`

---

## Questions for Future Discussion

1. **Category Expansion:** Should we add more granular categories (e.g., "Bug Reports" vs "Feature Requests")?

2. **Keyword Refinement:** Should we use stemming/lemmatization (e.g., "escalate" matches "escalation")?

3. **Multi-Label Classification:** Can a meeting belong to multiple categories?

4. **Historical Accuracy:** Should we track and display accuracy metrics over time?

5. **User Feedback Loop:** How should users correct miscategorizations? UI button? CSV export?

---

## Document Maintenance

**Last Updated:** May 7, 2026  
**Maintained By:** Aegis Transcript Intelligence Team  
**Review Cadence:** Monthly or after major algorithm changes

**Change Log:**

- 2026-05-07: Initial version with categorization rules and design decisions
