# UI/UX Guidelines and Low-Fidelity Wireframes

**Status:** Proposed design baseline for team review. The wireframes describe layout and information hierarchy, not final visual mockups. Review them after the data audit and before frontend implementation.

## 1. Design Principles

- **Evidence first:** Show sample size, data coverage, source date, and limitations near the relevant result.
- **Explainability:** Explain why a job or skill appears in a recommendation.
- **Honest missing data:** Use clear unavailable states; do not fill gaps with invented values.
- **Progressive disclosure:** Summarize results first and provide details on demand.
- **Low friction:** Allow public browsing and temporary skill matching without requiring an account.
- **Consistent patterns:** Reuse page headers, filters, cards, chart controls, and status messages.
- **Accessible by default:** Design for keyboard access, readable contrast, text alternatives, and both language directions.

## 2. Proposed Visual Tokens

These values are starting recommendations, not approved brand guidelines. Confirm them with the team and verify contrast before implementation.

| Token | Proposed value | Use |
|---|---|---|
| Primary navy | `#123B5D` | Main navigation, primary headings, primary actions |
| Accent teal | `#0F766E` | Secondary actions, selected states, data highlights |
| Page background | `#F8FAFC` | Main application background |
| Surface | `#FFFFFF` | Cards, filters, panels |
| Main text | `#0F172A` | Body text and labels |
| Muted text | `#475569` | Supporting text and metadata |
| Border | `#CBD5E1` | Dividers and input borders |
| Success | `#166534` | Positive status, always paired with text/icon |
| Warning | `#92400E` | Coverage warnings, always paired with text/icon |
| Error | `#B91C1C` | Errors, always paired with text/icon |

Do not use color as the only way to communicate categories, salary status, model status, or chart values. Use labels, icons, patterns, or direct annotations as well.

## 3. Typography and Layout

- Use a clear sans-serif type system. Proposed families: Inter or a system sans-serif for English, and Noto Sans Arabic or a suitable system Arabic sans-serif for Arabic.
- Keep headings, body, metadata, and chart labels visually distinct and consistently scaled.
- Use an 8-pixel spacing rhythm as a starting point, with consistent page gutters and card spacing.
- Target a readable content width of approximately 1,200 pixels on large screens; avoid stretching long text across the full viewport.
- Use touch targets of at least 44 by 44 CSS pixels for primary mobile controls where practical.
- Keep salary units, currencies, dates, counts, and sample sizes close to their values.

## 4. Navigation and Page Structure

Primary navigation:

- Home / Market Overview
- Explore Jobs
- Compare Markets
- Explore Skills
- Skill Matcher
- Methodology
- Language switch: English / Arabic

Do not add saved jobs, saved searches, notifications, or user accounts to the initial interface.

## 5. Low-Fidelity Wireframes

The sketches below show content hierarchy only. They are not pixel-perfect mockups and must be revised to match the verified dataset fields.

### 5.1 Market Overview — Desktop

```text
+--------------------------------------------------------------------------------+
| JOP Marketing Intelligence | Explore Jobs | Compare | Skills | Method | EN / AR |
+--------------------------------------------------------------------------------+
| Understand the job market from collected advertisements                       |
| [ Search role, skill, or company                         ] [ Explore Jobs ]      |
| Coverage: N advertisements | Countries: N | Collected: date range              |
+--------------------------------------------------------------------------------+
| [ KPI: top role ] [ KPI: top skill ] [ KPI: remote share ] [ KPI: salary data ]|
+-------------------------------------+------------------------------------------+
| Most requested skills               | Job advertisements by market / role     |
| [accessible chart + summary]        | [accessible chart + filters]             |
+-------------------------------------+------------------------------------------+
| Data coverage and interpretation note                                           |
| These results describe the collected sample; salary/date coverage varies.       |
+--------------------------------------------------------------------------------+
```

### 5.2 Job Explorer — Desktop

```text
+--------------------------------------------------------------------------------+
| Header and primary navigation                                                  |
+--------------------------------------------------------------------------------+
| Search: [ role, skill, company, or keyword                       ] [ Search ]   |
+--------------------------+-----------------------------------------------------+
| Filters                  | N results | Sort: [ Relevance / Newest ]                  |
| Country                  | [Job card: title, employer, country, work mode]      |
| Role family              | [Skills] [Salary if disclosed] [View details]        |
| Skill                    |-----------------------------------------------------|
| Work arrangement         | [Job card: title, employer, country, work mode]      |
| Experience               | [Skills] [Salary if disclosed] [View details]        |
| Salary, if comparable    |-----------------------------------------------------|
| [Clear filters]          | Page controls and sample-coverage note               |
+--------------------------+-----------------------------------------------------+
```

### 5.3 Job Detail — Desktop

```text
+--------------------------------------------------------------------------------+
| Header and primary navigation                                                  |
+--------------------------------------------------------------------------------+
| Job title                         Employer | Location | Work arrangement        |
| Salary: disclosed / not provided  Posting date | Collected date              |
| [Open original advertisement]                                               |
+-------------------------------------------+------------------------------------+
| Description and qualifications            | Skills mentioned in this posting   |
| Original wording where available          | [skill] [skill] [skill]            |
|                                           | Required/preferred only if known   |
+-------------------------------------------+------------------------------------+
| Source, collection date, and data limitations                                 |
| Related role/market insights, when supported by the sample                    |
+--------------------------------------------------------------------------------+
```

### 5.4 Skill Matcher — Desktop

```text
+--------------------------------------------------------------------------------+
| Header and primary navigation                                                  |
+--------------------------------------------------------------------------------+
| Find roles related to your current skills                                      |
| Skills: [ Search and add a skill ] [skill chip x] [skill chip x]               |
| Market: [ optional ]   Work arrangement: [ optional ]   [ Find matches ]       |
| Privacy note: submitted skills are not saved under the proposed D-015 policy.  |
+--------------------------------------------------------------------------------+
| Ranked matches                    | Why this matches                            |
| 1. Role / job title               | Skill coverage: N of M observed skills     |
|    [View details]                 | Matched: [skill] [skill]                   |
|                                   | Missing: [skill] [View free resources]      |
| 2. Role / job title               | Sample and method explanation              |
+--------------------------------------------------------------------------------+
| Match coverage is not a probability of being hired.                            |
+--------------------------------------------------------------------------------+
```

### 5.5 Mobile Behavior

On narrow screens, the navigation collapses into an accessible menu, filters open in a clearly labelled panel, result cards stack vertically, charts may switch to a summary/table view, and primary actions remain reachable without horizontal scrolling. RTL behavior must be tested independently from LTR behavior.

## 6. Interaction and Content Rules

- Keep filters visible or one action away, and provide a clear reset action.
- Show active filters and result counts.
- Use explicit labels such as “Advertised salary” and “Model estimate”; never combine them.
- Show “Not provided” or “Unavailable in this sample” rather than zero for missing values.
- Link each result to its source when available and identify external destinations.
- Explain a matching score in plain language and list matched and missing skills.
- Provide informative loading, empty, no-resource, validation, and service-error states.

## 7. Accessibility Requirements

Target WCAG 2.2 Level AA for primary flows, as stated in the SRS and accessibility specification.

- Support keyboard-only navigation and visible focus indicators.
- Use semantic headings, labelled controls, accessible validation, and descriptive link names.
- Meet text and non-text contrast requirements after the palette is finalized.
- Never communicate meaning through color alone.
- Provide an accessible text summary or data-table alternative for each important chart.
- Ensure screen-reader announcements for loading, result counts, errors, and language changes.
- Respect reduced-motion preferences if animation is introduced.

## 8. Localization and RTL Rules

- Translate navigation, controls, validation, empty states, and methodology summaries into English and Arabic.
- Set correct language and direction per locale; do not reverse URLs, technical identifiers, or source titles.
- Format dates, numbers, and currencies for the selected locale while preserving stored values and units.
- Review Arabic text and wireframes with a fluent speaker before acceptance.

## 9. Review and Approval

Before frontend implementation, review the wireframes against the final data dictionary, API contract, and feature scope. Record approved color and typography decisions in an ADR or design record. These wireframes do not replace usability testing with representative users.
