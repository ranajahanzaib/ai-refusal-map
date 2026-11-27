# Annotation guide

## Unit and independence

Annotate one assistant response paired with the preceding request and the context available before that response. Keep request and response separate. Do not use future turns to judge earlier behavior. Empty responses and malformed sequences should be retained with an indeterminate or non-answer outcome when supported by the rubric.

## Labeling

First assign a compliance outcome. Then record explicit stated reasons, alternatives offered, and quality scores independently. Assign refusal justification only when the reviewer can assess the request using the documented rubric and sufficient context. Use skip with a reason when sensitive content or missing context prevents review. Never label a machine-generated suggestion as a human annotation.

## Sampling and agreement

For population estimates, use a probability sample and preserve inclusion probabilities. Enriched samples for rare categories are classifier-development data and should not be mixed into unweighted prevalence estimates. Double-annotate a pilot and adjudicate disagreements. Report raw agreement plus an appropriate chance-corrected statistic, its task assumptions, denominators and uncertainty. No pilot annotations have been generated in this repository.

The browser annotation practice panel writes only to that browser's local storage. It is deliberately labeled as practice and is not a multi-rater research workflow. The API annotation service supports local persistent labels and revision counters; deployment still needs identity management, reviewer/adjudicator roles, audit policy, and a true revision-event history before multi-annotator use.
