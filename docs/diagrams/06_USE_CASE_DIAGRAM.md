# Use Case Diagram

This diagram summarizes the in-scope capabilities for the visitor and project team. It does not include account management, saved items, or alerts.

```mermaid
flowchart LR
    Visitor[Visitor / job seeker]
    Team[Project team]
    JobProvider[External job source]
    LearningProvider[External learning provider]

    subgraph Product[JOP Marketing Intelligence]
        Overview([View market overview])
        Search([Search and filter jobs])
        Details([View job details])
        Compare([Compare markets])
        Trends([Explore supported time trends])
        Skills([Explore skill demand and relationships])
        Match([Submit skills and review matches])
        Gaps([Review skill gaps])
        Resources([Open learning resources])
        Methodology([Review methodology and limitations])
        Localize([Switch English / Arabic])
        Audit([Audit and prepare data])
        Curate([Maintain skills and learning resources])
        Release([Review and release the application])
    end

    Visitor --> Overview
    Visitor --> Search
    Visitor --> Details
    Visitor --> Compare
    Visitor --> Trends
    Visitor --> Skills
    Visitor --> Match
    Visitor --> Gaps
    Visitor --> Resources
    Visitor --> Methodology
    Visitor --> Localize
    Details --> JobProvider
    Resources --> LearningProvider
    Team --> Audit
    Team --> Curate
    Team --> Release
```

## Scope Notes

- Time trends and some market comparisons are conditional on data coverage.
- Matching is explainable skill coverage, not a hiring probability.
- The visitor can navigate to external sources; the product does not control those sites.
