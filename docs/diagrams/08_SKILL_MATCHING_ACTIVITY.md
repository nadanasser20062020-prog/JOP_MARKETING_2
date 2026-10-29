# Skill-Matching Activity Diagram

```mermaid
flowchart TD
    Start([Start]) --> Input[Enter or select current skills]
    Input --> Valid{Is the input valid and within limits?}
    Valid -->|No| InputHelp[Explain required input and limits]
    InputHelp --> Input
    Valid -->|Yes| Normalize[Normalize recognized aliases]
    Normalize --> Unknown{Are any skills unrecognized?}
    Unknown -->|Yes| Confirm[Allow review or removal of unrecognized entries]
    Unknown -->|No| Submit[Submit temporary matching request]
    Confirm --> Submit
    Submit --> Service{Is matching data available?}
    Service -->|No| Limited[Show data-coverage limitation]
    Service -->|Yes| Candidates[Retrieve candidate roles and advertisements]
    Candidates --> Score[Calculate documented skill-coverage scores]
    Score --> Ranked{Are relevant results available?}
    Ranked -->|No| NoMatches[Explain no supported matches and offer input changes]
    Ranked -->|Yes| Explain[Show ranked results and matched skills]
    Explain --> Gaps[Show evidence-based missing skills]
    Gaps --> Resources{Are reviewed resources available?}
    Resources -->|Yes| Learning[Show resource links and access status]
    Resources -->|No| NoLearning[State that no reviewed resource is currently listed]
    Learning --> Job{Does the user want to inspect a job?}
    NoLearning --> Job
    Job -->|Yes| Details[Open job details and source link when available]
    Job -->|No| End([End])
    Details --> End
    NoMatches --> End
    Limited --> End
```

## Privacy Note

The proposed default is to process skills for the current request only and not persist them. Confirm this decision under D-015 before implementation. The matching score must not be described as the probability of being hired.
