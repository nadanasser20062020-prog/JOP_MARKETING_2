# Web Application Plan and Data Flow

## Purpose

Turn database records and analytical findings into a simple experience for engineers: explore job markets, understand roles and required skills, and identify relevant learning opportunities.

## Proposed System Flow

1. Clean job-advertisement data and load it into PostgreSQL/Neon.
2. Run documented analyses and models to produce metrics and recommendations.
3. Use a secure backend layer to read data and handle search, filtering, and application requests.
4. Present results, charts, and details through the user interface.

The browser must not connect directly to Neon or contain database credentials. The team should select frontend and backend frameworks before implementation based on team experience and deployment requirements; this plan does not mandate an unapproved technology stack.

## Pages and User Flow

### 1. Home Page

- Summarize the sample size, covered markets, and available time period.
- Highlight available role, skill, and market indicators.
- Link directly to the job explorer, market comparison, and skill matcher.

### 2. Job Explorer

- Search and filter using fields supported by the dataset.
- Show concise results with title, employer, location, work arrangement, skills, and salary where available.
- Provide clear loading, no-results, and missing-value states.

### 3. Job Details

- Present collected advertisement details, skills, dates, and source information.
- Distinguish salary stated in the advertisement from any model estimate.
- Link to the original advertisement when the URL is available and valid.

### 4. Market Analysis and Country Comparison

- Visualize available role, skill, work-arrangement, and salary indicators.
- Allow comparison of two or more markets.
- Show time trends only when dates are sufficiently reliable.
- Display sample size and metric definitions.

### 5. Skill Explorer

- Show in-demand skills by role or market.
- Explore skills that commonly appear together.
- Navigate from a skill to relevant jobs and learning resources.

### 6. Skill Matching and Learning Resources

- Accept user-entered skills and optional market or work-arrangement preferences.
- Show closest roles or jobs and explain matching and missing skills.
- Link missing skills to resources; label items free only when `cost_status=free_verified`, and disclose mixed, conditional, or unverified access terms.

### 7. Methodology

- Explain data sources and dates, cleaning, metric definitions, analytical methods, models, and limitations.

## English and Arabic Support

- Provide English and Arabic interface text, including navigation and empty/error states.
- Support correct RTL layout in Arabic and LTR layout in English without reversing links or numbers.
- Preserve the original job title while using normalized titles for comparisons where appropriate.

## Suggested Implementation Sequence

1. Confirm user flows and required fields after the data audit.
2. Prepare and review page wireframes before implementation.
3. Prepare backend queries for search, filtering, and aggregation.
4. Build the job explorer and job-detail experience.
5. Build the market dashboard, comparison, and skill explorer.
6. Integrate matching and learning resources.
7. Add localization, missing-data states, and mobile layouts.
8. Test data accuracy, links, credential handling, and usability.

## General Acceptance Criteria

- Every displayed metric can be traced to a documented query or analysis result.
- Filters use supported dataset values and handle missing fields safely.
- Each displayed job links to its source when the source is available.
- Missing information is shown clearly and is not replaced with fabricated values.
- Matching results are explainable and do not claim to guarantee employment.
- The application contains no database credentials and does not expose unintended database access.
- Saving jobs, saving searches, and new-job alerts remain out of scope.
