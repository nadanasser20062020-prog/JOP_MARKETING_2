# Proposed Site Map

```mermaid
flowchart TD
    Home[Home / Market Overview]
    Explorer[Job Explorer]
    Details[Job Details]
    Market[Market Analysis]
    Compare[Market Comparison]
    Trends[Time Trends, when supported]
    Skills[Skill Explorer]
    SkillDetail[Skill Detail and Related Skills]
    Matching[Skill Matcher]
    MatchResults[Ranked Matches]
    Gaps[Skill Gaps]
    Resources[Learning Resources]
    Methodology[Methodology and Limitations]
    Locale[English / Arabic language switch]

    Home --> Explorer
    Home --> Market
    Home --> Matching
    Explorer --> Details
    Market --> Compare
    Market --> Trends
    Market --> Skills
    Skills --> SkillDetail
    SkillDetail --> Explorer
    SkillDetail --> Resources
    Matching --> MatchResults
    MatchResults --> Details
    MatchResults --> Gaps
    Gaps --> Resources
    Home --> Methodology
    Explorer --> Methodology
    Market --> Methodology
    Matching --> Methodology
    Locale -. available throughout .-> Home
```

## Navigation Notes

- Time trends are visible only when date coverage passes the data-quality gate.
- The original advertisement and learning provider are external destinations, not internal pages.
- The language switch applies across all primary product pages and relevant states.
