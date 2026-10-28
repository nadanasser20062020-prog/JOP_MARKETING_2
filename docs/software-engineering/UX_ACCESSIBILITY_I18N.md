# UX, Accessibility, and Localization Specification

## Information Architecture

Primary navigation should provide access to:

- Home and market overview.
- Job explorer and job details.
- Market analysis and comparison.
- Skill explorer.
- Skill matching and learning resources.
- Methodology and limitations.

The initial release has no account, saved items, saved searches, or notifications.

## Core Interaction Principles

- Explain what the dataset covers before presenting broad market claims.
- Keep search and filters visible and provide a clear reset action.
- Show active filters and the number of results where practical.
- Distinguish advertised values from derived metrics and model outputs.
- Make missing, unavailable, and unknown information explicit.
- Provide loading, no-results, validation-error, and service-error states for every data-driven flow.
- Do not require sign-in to browse the public dataset or submit temporary skill input.

## Page-Level UX Requirements

### Market Overview

Show coverage, sample size, and supported summary metrics. Provide routes to more detailed exploration. Each visualization should have a title, context, unit, and accessible text summary.

### Job Explorer and Details

Allow users to search and filter by supported fields. Display result summaries consistently. Detail pages should preserve original job wording, show standardized values where useful, and link to the source when available.

### Market Comparison

Use the same metric definition and compatible units for each market. Present sample sizes and coverage differences next to the comparison. Do not use visual scales that exaggerate small differences.

### Skill Matching

Provide an editable input experience, explain how recognized skills are normalized, and show the matching method, matched skills, missing skills, and evidence. Make clear that the score does not predict hiring success.

### Charts

Do not rely on color alone. Provide labels, legends, keyboard-accessible alternatives where supported, and a textual summary or table for key values. Clearly identify estimated values and sample sizes.

## Accessibility Target

Target WCAG 2.2 Level AA for the primary user flows, subject to verification. Required practices include:

- Complete keyboard navigation and visible focus indicators.
- Semantic headings, landmarks, labels, and descriptive link text.
- Sufficient text and non-text contrast.
- Accessible validation, status, and error messages.
- Text alternatives or equivalent data tables for important charts.
- No critical information conveyed by color alone.
- Respect reduced-motion preferences where animation is used.

## Localization and RTL

- Provide complete English and Arabic strings for navigation, forms, validation, empty states, and methodology summaries.
- Set language and direction at the page or component level; Arabic pages use RTL and English pages use LTR.
- Preserve original job titles and source text when translation would alter meaning.
- Keep URLs, email-like strings, technical identifiers, and numbers readable in mixed-direction content.
- Format dates, numbers, and currencies according to the selected locale without changing the underlying stored value.
- Normalize role and skill aliases for search while displaying user-appropriate labels.
- Review translations with a fluent speaker; machine translation alone is not an acceptance criterion.

## Responsive and Browser Support

Design for mobile and desktop. Define the supported browser versions before release and run smoke tests at the selected viewport sizes. Wide tables and charts must remain usable without horizontal overflow where practical.

## Usability Validation

Before release, ask representative users to complete at least these tasks: find a job in a market, inspect its source, compare two markets, enter skills, interpret a match, and open a learning resource. Record points of confusion and update the interface before final demonstration.
