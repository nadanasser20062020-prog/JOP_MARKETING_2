# User Journeys and Low-Fidelity Wireframes

These wireframes describe intended information hierarchy, not a built application. They preserve uncertainty and evidence alongside the result. A future interface should be mobile-accessible, keyboard operable, localized, and usable as tables without charts.

## Journey A: Explore skills

1. User opens a dashboard with the dataset scope and date limitations immediately visible.
2. User filters by a source/cohort whose coverage is documented.
3. User scans canonical skills sorted by distinct record count.
4. Selecting a skill reveals its count, denominator, share, match policy, source breakdown and exact interpretation.
5. User opens the source records only when a URL is available; otherwise the interface states that the archive has no source link for that row.

```text
┌──────────────────────────────────────────────────────────────────┐
│ JOB-SKILL EXPLORER                  Data: local archive snapshot   │
│ Not a live job feed · listing activity is not verified             │
├──────────────────────────────────────────────────────────────────┤
│ Source [All represented sources ▼]   Country [All labels ▼]       │
│ Search skill [____________________]   [Clear filters]               │
│                                                                  │
│ Skill                 Job records  Eligible jobs  Share   Policy  │
│ Python                   419,133       664,989    63.03%  approved│
│ SQL                      409,656       664,989    61.60%  approved│
│ AWS                      166,458       664,989    25.03%  approved│
│                                                                  │
│ Selected: Python                                                   │
│ 419,133 records / 664,989 with reviewed eligible skill evidence     │
│ This is archive frequency, not hiring probability or a census.     │
│ [View source breakdown] [Open record details, if available]        │
└──────────────────────────────────────────────────────────────────┘
```

## Journey B: Search a role title

1. User enters a title string.
2. Search normalizes outer whitespace and case only; the UI explains punctuation and seniority variants remain separate.
3. User selects a title and sees the count by source, label availability, and related observed skills.
4. If a role family is not curated, do not synthesize one from similar strings.

```text
┌──────────────────────────────────────────────────────────────────┐
│ ROLE TITLE SEARCH                                                  │
│ Exact normalized strings; seniority/abbreviations are not merged. │
├──────────────────────────────────────────────────────────────────┤
│ Title [data engineer____________]   Source [All ▼]  [Search]       │
│                                                                  │
│ DATA ENGINEER                 56,513 records  [View evidence]      │
│ SENIOR DATA ENGINEER          20,759 records  [View evidence]      │
│ AZURE DATA ENGINEER            3,599 records  [View evidence]      │
│                                                                  │
│ No reviewed occupation-family label is available for these rows.   │
└──────────────────────────────────────────────────────────────────┘
```

## Journey C: Compare represented market groups

1. User sees that only one source contains both groups and selects the comparison.
2. The page displays within-group percentages with explicit denominators and counts.
3. The page lists which configured country labels are absent instead of charting zeros.
4. Every visual has a sorted table equivalent and text explaining unknown snapshot dates/activity.

```text
┌──────────────────────────────────────────────────────────────────┐
│ SKILL COMPARISON: ARAB / OTHER REPRESENTED LABELS                  │
│ Source: merged_tech_jobs only · snapshot date/activity unverified  │
│ Describes this source snapshot; not current or representative.      │
├──────────────────────────────────────────────────────────────────┤
│ Arab-labelled: 22,442 records       Other labels: 17,279 records   │
│ Eligible-skill denominator: 22,398  Eligible-skill denominator:    │
│                                      17,279                         │
│                                                                  │
│ Skill                 Arab share         Other share                │
│ Python                  88.32%              97.60%                  │
│ SQL                     81.61%              82.86%                  │
│                                                                  │
│ Absent in merged source: Comoros, Djibouti, Mauritania, Somalia,  │
│                       Syria; not zero-opportunity claims            │
│ [Chart]                       [Accessible comparison table]          │
└──────────────────────────────────────────────────────────────────┘
```

## Journey D: Compare selected skills to a job profile

1. User selects reviewed canonical skills from the skill dictionary.
2. A future backend validates IDs and filters pending-review mappings before comparing.
3. The result presents overlap formula, matched IDs, user-only skills, job-only skills and directional coverage.
4. The user may use missing skills as a learning prompt, not as a requirement or suitability verdict.

```text
┌──────────────────────────────────────────────────────────────────┐
│ SKILL PROFILE EXPLORER                                             │
│ Your selected skills: Python · SQL · Tableau                       │
│ Job profile: Example title (source record link, if available)       │
├──────────────────────────────────────────────────────────────────┤
│ Skill overlap (Jaccard): 2 / 4 = 50%                               │
│ Matched: Python, SQL                                                │
│ In your profile only: Tableau                                       │
│ In job profile only: Airflow                                        │
│                                                                  │
│ Overlap is not a hiring probability, qualification, or full fit.   │
│ [Edit selected skills] [See eligible learning resources]            │
└──────────────────────────────────────────────────────────────────┘
```

## Journey E: Inspect historical month counts

1. User selects the named historical International 2023 cohort.
2. Month counts are shown as source records and labeled historical.
3. The UI avoids current demand/forecast language and does not combine other `updated` dates.
4. A month absent from the source is not filled with zero unless the source confirms complete coverage.

## Accessibility and localization checklist

- Every chart includes a screen-reader title/description, data table, direct labels and source/denominator text.
- Color is never the sole means of distinguishing market cohorts; use text labels and distinguishable patterns/markers.
- Keyboard focus order is logical; inputs and filters have explicit labels; comparison tables support horizontal scroll on small screens without hiding critical caveats.
- Arabic right-to-left and English left-to-right layouts retain source spellings and do not alter canonical skill IDs.
- Number formats and country labels may localize, but raw values, cohort definitions and match policy remain traceable.
