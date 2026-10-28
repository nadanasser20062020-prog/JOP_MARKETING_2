# Project Glossary

| Term | Definition |
|---|---|
| Advertisement | A single collected job posting from a source. It may be duplicated, expired, incomplete, or reposted. |
| Job post | The normalized record representing a collected advertisement in the application database. |
| Job role | A normalized occupation or role category that may be associated with multiple advertisements. |
| Original value | The text or value captured from the source before normalization. |
| Normalized value | A standardized representation used for filtering, grouping, or comparison while preserving the original value where useful. |
| Skill | A technology, tool, language, method, or capability mentioned in an advertisement. A mention is not automatically proof that it is mandatory. |
| Canonical skill | The preferred standardized name used to group known spelling variants and aliases. |
| Job-skill association | A record connecting a job post to a skill; it may include evidence or a required/preferred/unspecified classification when supportable. |
| Market sample | The subset of job advertisements collected by the project for a country, period, source, role, or filter. It is not necessarily representative of the whole labor market. |
| Posting date | The date an advertisement was published by its source, when available. |
| Collection date | The date the project collected the advertisement. It is distinct from the posting date. |
| Work arrangement | A standardized category such as remote, hybrid, onsite, or unknown, derived from available source information. |
| Advertised salary | Salary information explicitly stated in the source advertisement. |
| Salary estimate | A model-generated approximation based on available data. It is not equivalent to an advertised salary or a guarantee. |
| Match coverage | A transparent comparison between user-entered skills and skills associated with a job or role. It is not a probability of being hired. |
| Skill gap | A skill observed in relevant advertisements that is absent from the user's submitted skill set. It is evidence-based guidance, not necessarily a mandatory qualification. |
| Clustering | An unsupervised method that groups records by similarity without predefined target labels. |
| Classification | A supervised method that assigns a record to one of a predefined set of labels. |
| Regression | A supervised method that estimates a numeric target, such as a salary measure, from input attributes. |
| Data dictionary | A maintained description of fields, meaning, type, unit, source, and missing-value behavior. |
| ERD | An Entity-Relationship Diagram describing database entities and their relationships. |
| Provenance | Information describing where a record or result came from and how it was produced. |
| Conditional feature | A feature that may be implemented only if the data audit confirms sufficient reliable fields and records. |
