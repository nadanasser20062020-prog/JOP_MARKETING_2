# Domain Class Diagram

This diagram gives an object-oriented view of the implemented SQLite domain model and the planned application services. Database classes map to the local relational schema in [`04_LOGICAL_ERD.md`](04_LOGICAL_ERD.md); service methods remain conceptual until the API is implemented.

```mermaid
classDiagram
    class DataSource {
        +String sourceDataset
        +String displayName
        +String notes
    }
    class SourceFile {
        +String sourceDataset
        +String sourceFile
        +String snapshotGroup
        +String snapshotType
        +String notes
    }
    class ImportRun {
        +Integer importRunId
        +String runStatus
        +String startedAt
        +String finishedAt
        +String pipelineVersion
        +String sourceFingerprint
        +String qualityReport
    }
    class ImportRunFile {
        +Integer importRunId
        +String sourceDataset
        +String sourceFile
        +Integer rowsRead
        +Integer rowsLoaded
        +Integer rowsRejected
        +String importStatus
    }
    class Job {
        +String recordId
        +String sourceDataset
        +String sourceFile
        +Integer sourceRowNumber
        +String title
        +String company
        +String country
        +String city
        +String region
        +String postedAt
        +String sourceUpdatedAt
        +String salaryRaw
        +String listingStatus
    }
    class Skill {
        +String skillId
        +String canonicalName
        +String category
        +String matchPolicy
        +String reviewStatus
    }
    class SkillAlias {
        +String aliasNormalized
        +String aliasLabel
        +String aliasType
        +String matchPolicy
        +String reviewStatus
    }
    class JobSkill {
        +String recordId
        +String skillId
        +String skillRaw
        +String skillNormalized
        +String skillProvenance
        +String skillStatus
    }
    class SkillObservation {
        +String sourceDataset
        +String skillRaw
        +String skillNormalized
        +Integer occurrenceCount
    }
    class LearningResource {
        +String resourceId
        +String title
        +String provider
        +String resourceType
        +String accessStatus
        +String costStatus
        +String verificationStatus
        +String verifiedOn
        +String resourceUrl
    }
    class LearningResourceSkill {
        +String resourceId
        +String skillId
    }
    class LearningResourceLanguage {
        +String resourceId
        +String languageLabel
    }
    class JobSearchService {
        +search(criteria, pagination) JobPage
        +getDetails(recordId) Job
    }
    class MarketAnalyticsService {
        +getOverview(filters) MarketOverview
        +compareMarkets(markets, metric) ComparisonResult
        +getSkillDemand(filters) SkillDemand
    }
    class SkillMatchingService {
        +normalizeInputSkills(input) NormalizedSkills
        +rankJobs(skills, preferences) MatchResult
        +identifySkillGaps(skills, role) SkillGap
    }
    class LearningResourceService {
        +findBySkill(skillId, language) LearningResource
    }

    DataSource "1" --> "0..*" SourceFile : identifies
    SourceFile "1" --> "0..*" Job : provides
    ImportRun "1" --> "0..*" ImportRunFile : records
    SourceFile "1" --> "0..*" ImportRunFile : accounts for
    Skill "1" --> "0..*" SkillAlias : has
    Job "1" --> "0..*" JobSkill : links
    Skill "1" --> "0..*" JobSkill : appears in
    DataSource "1" --> "0..*" SkillObservation : records
    LearningResource "1" --> "0..*" LearningResourceSkill : links
    Skill "1" --> "0..*" LearningResourceSkill : recommends
    LearningResource "1" --> "0..*" LearningResourceLanguage : labels
    JobSearchService ..> Job : searches and retrieves
    MarketAnalyticsService ..> Job : aggregates
    MarketAnalyticsService ..> JobSkill : analyzes demand
    SkillMatchingService ..> Skill : normalizes input
    SkillMatchingService ..> JobSkill : ranks matches and gaps
    LearningResourceService ..> LearningResource : finds reviewed resources
```

## Modeling Notes

- `Job` retains source company and location values as fields; they are not separate normalized database entities.
- Date and salary values retain their source text and semantics. The model does not infer posting dates, collection timestamps, or numeric salary amounts.
- A skill mention is not automatically a mandatory qualification.
- Resource cost, language, access, and verification data are specific to the curated record and are not guarantees of current access.
- A persistent user or candidate-profile class is not included in the current scope.
