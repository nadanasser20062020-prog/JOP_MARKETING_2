# Skill-Matching Request State Diagram

This conceptual state machine describes a single matching interaction. It does not imply that a request or skill profile is stored permanently. The proposed non-persistence behavior remains subject to team approval under D-015.

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Validating: submit skills
    Validating --> Invalid: input is empty or invalid
    Invalid --> Draft: edit input
    Validating --> Normalizing: input is valid
    Normalizing --> Ready: recognized and reviewed inputs prepared
    Ready --> Processing: request matching results
    Processing --> ResultsFound: relevant results available
    Processing --> NoResults: no supported matches
    Processing --> DataLimited: insufficient data coverage
    Processing --> ServiceFailure: required service unavailable
    ResultsFound --> Completed: display matches and explanations
    NoResults --> Completed: display empty state
    DataLimited --> Completed: display limitation
    ServiceFailure --> Recoverable: show retry or recovery guidance
    Recoverable --> Ready: retry request
    Recoverable --> [*]: leave matching flow
    Completed --> Draft: change submitted skills
    Completed --> [*]: leave matching flow
```

## State Rules

- Invalid input returns the visitor to an editable draft state.
- Only a valid request proceeds to normalization and matching.
- No-results and insufficient-data outcomes are distinct states.
- Service failure must not be displayed as a valid empty result.
- Under D-015, request content is not retained after the current interaction.
