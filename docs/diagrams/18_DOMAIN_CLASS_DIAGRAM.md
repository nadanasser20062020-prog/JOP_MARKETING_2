# Conceptual Domain Class Diagram

This UML-style class diagram complements the relational ERD by showing the conceptual objects and associations. It is not an implemented object model; attributes must be confirmed against the dataset.

```mermaid
classDiagram
    class JobPost {
        +JobPostId id
        +String originalTitle
        +String normalizedTitle
        +String description
        +Date postedAt
        +DateTime collectedAt
        +WorkMode workMode
        +SalaryRange advertisedSalary
        +URL sourceUrl
    }
    class Company {
        +CompanyId id
        +String originalName
        +String normalizedName
    }
    class Location {
        +LocationId id
        +String country
        +String city
        +String region
    }
    class Source {
        +SourceId id
        +String sourceName
        +String sourceDomain
    }
    class Skill {
        +SkillId id
        +String canonicalName
        +String category
    }
    class JobSkill {
        +JobPostId jobPostId
        +SkillId skillId
        +MentionType mentionType
        +String evidence
    }
    class LearningResource {
        +ResourceId id
        +String title
        +String provider
        +String language
        +String accessStatus
        +Date verifiedAt
        +URL url
    }
    class JobSearchService {
        +search(criteria, pagination) JobPage
        +getDetails(jobPostId) JobPost
    }
    class MarketAnalyticsService {
        +getOverview(filters) MarketOverview
        +compareMarkets(markets, metric) ComparisonResult
        +getSkillDemand(filters) SkillDemand
    }
    class SkillMatchingService {
        +normalizeInputSkills(input) NormalizedSkills
        +rankJobPosts(skills, preferences) MatchResult
        +identifySkillGaps(skills, roleId) SkillGap
    }
    class LearningResourceService {
        +findBySkill(skillId, language) LearningResource
    }

    JobPost "0..*" --> "0..1" Company : published by
    JobPost "0..*" --> "0..1" Location : located in
    JobPost "0..*" --> "0..1" Source : collected from
    JobPost "1" --> "0..*" JobSkill : has skill associations
    Skill "1" --> "0..*" JobSkill : appears in
    Skill "1" --> "0..*" LearningResource : has learning resources
    JobSearchService ..> JobPost : searches and retrieves
    MarketAnalyticsService ..> JobPost : aggregates
    MarketAnalyticsService ..> JobSkill : analyzes demand
    SkillMatchingService ..> Skill : normalizes input
    SkillMatchingService ..> JobSkill : ranks matches and gaps
    LearningResourceService ..> LearningResource : finds reviewed resources
```

## Modeling Notes

- The diagram includes candidate domain objects and proposed service operations. Method names describe responsibilities, not committed implementation signatures.
- A skill mention is not automatically a mandatory qualification.
- Salary and work-mode attributes may be unavailable for many advertisements.
- A persistent user or candidate-profile class is not included in the current scope.
