# UI/UX Guidelines and Low-Fidelity Wireframes

**Status:** Proposed design baseline for team review. The wireframes describe layout and information hierarchy, not final visual mockups or an implemented frontend; no frontend entry point is present in this checkout. Review them after the data audit and before frontend implementation.

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

Primary navigation, in priority order:

- Overview
- Analyze Roles
- Compare Markets
- Skill Matcher
- Related Job Advertisements (secondary)
- Methodology
- Language switch: English / Arabic

Role analysis is the primary job-discovery flow; individual advertisements are an optional supporting view. Do not add saved jobs, saved searches, notifications, or user accounts to the initial interface.

## 5. Low-Fidelity Wireframes

The sketches below show content hierarchy only. They are not pixel-perfect mockups and must be revised to match the verified dataset fields.

### 5.1 Overview — Default Landing Page

```text
+--------------------------------------------------------------------------------+
| JOP | Overview | Analyze Roles | Compare | Match Skills | Related Ads | EN / AR |
+--------------------------------------------------------------------------------+
| [ Search a job title to analyze it                         ] [ Analyze role ]   |
+--------------------------------------------------------------------------------+
| [ Total Jobs ]          [ Total Skills ]          [ Total Countries ]           |
+--------------------------------------+-----------------------------------------+
| Country distribution: label and count | Top 10 reviewed skills                 |
| Accessible table; map only after       | Horizontal bars: count, denominator     |
| reviewed name-to-geometry mapping      | and share, with sample caveat           |
| Select a country to filter if supported| Select a skill to filter if supported   |
+--------------------------------------+-----------------------------------------+
| Arab vs other represented markets: `merged_tech_jobs` only                     |
| Within-group counts/shares; not a global-market comparison                    |
+--------------------------------------------------------------------------------+
```

Keep the four overview elements visually distinct and spacious. KPI definitions, denominators, and supporting sample counts are available on hover/tap or in an accessible details view rather than as dense page text.

### 5.2 Role Analysis — Desktop

```text
+--------------------------------------------------------------------------------+
| Analyze a role: [ Search/select normalized job title                 ]         |
| Selected role: Data Analyst                         [Market: All / Select]     |
+--------------------------------------------------------------------------------+
| [ Countries ]          [ Skills by country ]          [ Salary coverage ]      |
+--------------------------------------------------------------------------------+
| One focused accessible table/chart for the selected tab                       |
| Countries: job counts and share with denominator                              |
| Skills: most common reviewed skills for this role and selected market         |
| Salaries: coverage/provenance counts; no mean/median currently                 |
| Show an average only after a currency, period, provenance, and sample gate     |
+--------------------------------------------------------------------------------+
| [ Related advertisements for this role ]  (secondary action)                   |
+--------------------------------------------------------------------------------+
```

Selecting a role opens this analysis view first, not an advertisement list. Tabs and on-demand chart details keep the page useful without crowding it.

### 5.3 Related Job Advertisements — Desktop

```text
+--------------------------------------------------------------------------------+
| Related advertisements for: Data Analyst                       [Back to role]  |
+--------------------------------------------------------------------------------+
| Search: [ role, skill, company, or keyword                       ] [ Search ]   |
+--------------------------+-----------------------------------------------------+
| Filters                  | N results | Sort: [ Title / Company / Country / Source ] |
| Country                  | [Job card: title, employer, country, work mode]      |
| Exact role / skill       | [Open details for reviewed skills + salary fields]  |
| Work mode (raw)          |-----------------------------------------------------|
| Experience (raw)         | [Job card: title, employer, country, work mode]      |
| Salary filter: disabled  | [Open details for reviewed skills + salary fields]  |
| (not comparable)         |-----------------------------------------------------|
| [Clear filters]          | Page controls                                        |
+--------------------------+-----------------------------------------------------+
```

### 5.4 Job Detail — Desktop

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

### 5.5 Skill Matcher — Desktop

```text
+--------------------------------------------------------------------------------+
| Header and primary navigation                                                  |
+--------------------------------------------------------------------------------+
| Find roles related to your current skills                                      |
| Skills: [ Search and add a skill ] [skill chip x] [skill chip x]               |
| Market: [ optional ]   Work arrangement: [ optional ]   [ Find matches ]       |
| Privacy note: submitted skills are not saved under the proposed D-015 policy.  |
+--------------------------------------------------------------------------------+
| Ranked role profiles (Jaccard)    | Why this matches                            |
| 1. Exact observed title           | Overlap: matched / union; not hiring odds  |
|    [View role analysis]           | Matched: [skill] [skill]                   |
|                                   | Missing: [skill] [View resources]           |
| 2. Exact observed title           | Sample count + scope + limitation           |
+--------------------------------------------------------------------------------+
| Match coverage is not a probability of being hired.                            |
+--------------------------------------------------------------------------------+
```

### 5.6 Mobile Behavior

On narrow screens, the navigation collapses into an accessible menu, filters open in a clearly labelled panel, result cards stack vertically, and charts stack without horizontal scrolling. Tap replaces hover for chart details; keyboard and screen-reader alternatives remain available. The map may switch to a searchable country list or table while preserving the same counts and filters. RTL behavior must be tested independently from LTR behavior.

## 6. Interaction and Content Rules

- Keep filters visible or one action away, and provide a clear reset action.
- Show active filters and result counts.
- Make charts interactive: hover or tap reveals values and definitions; clicking a country, bar, or comparison item filters related views. Keyboard focus must expose the same detail so essential information is never hover-only.
- Open role analysis as the primary response to role search; keep related advertisements as an optional secondary action.
- Show salary averages only with compatible currency and pay period, and include the supporting record count and median. Keep advertised values distinct from any separately evaluated model estimate.
- Show “Not provided” or “Unavailable in this sample” rather than zero for missing values.
- Link each displayed advertisement or resource to its source when available and identify external destinations.
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
