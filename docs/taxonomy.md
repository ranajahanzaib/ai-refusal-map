# Taxonomy

Taxonomy definitions are versioned in `apps/api/arm_api/taxonomy.py`; API clients can retrieve `/api/v1/taxonomy`. Outcome, stated reason, justification, alternative assistance, and response quality are independent dimensions. A response may have multiple stated reasons and alternative types.

Annotators describe a reason only when the response states it. That statement is not evidence about hidden internal causes. Justification labels (`justified`, `unnecessary`, `excessive`, `ambiguous`, `unassessable`, `not_applicable`) require the documented context and rubric; they must not be inferred from moderation metadata or a classifier score.

Quality dimensions use anchored 1–5 ordinal scales where applicable, plus `not_applicable` and `cannot_assess`. Before production annotation, publish examples and edge-case guidance for each scale and validate inter-rater agreement on a pilot.
