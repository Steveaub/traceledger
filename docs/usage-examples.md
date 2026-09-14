# Usage examples

Start the application using the README setup instructions and open the local workspace. The bundled project records and conversations are fictional.

## Find the cause of a delay

Ask **What caused Project Alpha to fall behind its commissioning schedule?** Review the cited incident and status records. The example describes transformer winding insulation failing factory testing and a six-week delay.

## Investigate a decision

Select **Investigate**, enable the relevant sources, and ask **Investigate Project Alpha: why was commissioning delayed, who approved the change, and was the schedule updated?** Expand the activity trail to inspect searches and thread reads. Select a citation and **Read full record** to review its source.

Disable Email and repeat the investigation to see the missing-approval warning. Source toggles select indexed records; they do not connect live accounts. See [conversation sources](conversation-feeds.md) for supported imports.

## Trace a change

Ask **Trace the requirement and incident linked to CR-001.** Expand documented relationships to inspect source-backed graph edges.

## Explore cross-project knowledge

Ask **Which active projects use the equipment affected by INC-001, and what lesson follows that incident?** The fictional corpus links TX-880 to active Elm and Iris. Retrieval may miss some related records; inspect the sources and known limitations rather than assuming the result is exhaustive.

## Reuse a lesson

Ask **What should we learn from Project Alpha before releasing a purchase order?** Inspect the cited procurement lesson and its incident context.

## Check missing evidence

Ask **What affected INC-999?** The missing identifier should produce an insufficient-evidence response. Other unsupported questions can behave differently; this example does not establish universal abstention accuracy.

## Inspect evaluation results

Open **Evaluation lab**, choose a cohort, compare runs and inspect question-level results. Investigation citation-order metrics and original document-retrieval metrics use separate protocols. See [evaluation history](evaluation-history.md) and [investigation evaluation](agentic-investigation.md).
