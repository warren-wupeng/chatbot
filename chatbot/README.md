
```mermaid
stateDiagram-v2
    [*] --> Opening
    Opening --> LifeExplorer: LifeExplorerIntent
    LifeExplorer --> Opening: PositiveIntent
    LifeExplorer --> Opening: NegativeIntent
    Opening --> Opening: TalenCounsultIntent
    Opening --> CognitionPractice: CognitionPracticeIntent
    CognitionPractice --> Opening: PositiveIntent
    CognitionPractice --> Opening: NegativeIntent
    Opening --> Opening: AstraNorlandStoryIntent
    Opening --> Opening: MovieIntent

```