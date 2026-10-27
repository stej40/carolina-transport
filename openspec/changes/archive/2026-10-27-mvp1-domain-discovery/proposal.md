# Proposal: MVP1 domain discovery (M2)

## Why
Domain code must not be written before the real paperwork, workflow and
accounting practice are known (AGENTS.md hard gate: no domain schema
migration until the schema proposal is signed off by Jiří). This change is
that discovery step for the whole MVP1 program.

## What Changes
Planning only - no code, no spec deltas (`skip_specs: true`). Produces:
1. Document taxonomy + required attributes per type.
2. Transport state machine validated against the real workflow.
3. Domain schema proposal (groups, trucks, orders, transports, documents,
   events) signed off by Jiří - the gate that unblocks changes
   mvp1-organizational-groups, mvp1-transports-and-orders and
   mvp1-document-collection.
4. Answers to open questions: are transports tied to a truck (SPZ)? how many
   groups exist, who owns memberships? POHODA edition + VS practice (MVP2
   input); volumes; bank statement format (MVP4 input).

## Out of scope
Any implementation, any UI, POHODA/OCR/bank integration design (later MVPs).

## Capabilities
(none - pure planning change, see skip_specs)

## Impact
- Deliverables land in this change's design.md and `docs/` pointers.
- Waiting time depends on Jiří gathering anonymized paperwork samples and
  arranging the walkthrough; this is the program's critical path.
