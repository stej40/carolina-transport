# Design: MVP1 domain discovery outputs

This design.md is the container for discovery deliverables; sections are
filled during M2 and the whole document becomes the schema proposal for
Jiří's sign-off. Constraints inherited from `openspec/config.yaml`: UUID PKs,
NUMERIC money, idempotency, immutable event log, billing-ready orders,
external-ID mapping, taxonomy as data.

Source materials: `docs/discovery/documents/` (CMR, vážní lístek, ERKLÄRUNG,
2x přepravní smlouva) and `docs/discovery/walkthrough-notes.md`.

**STATUS: SIGNED OFF by Jiří, 2026-10-27** - schema proposal (§3) approved
for MVP1; the domain schema gate is lifted for mvp1-organizational-groups,
mvp1-transports-and-orders and mvp1-document-collection.

## 1. Document taxonomy (from samples)

Taxonomy is data (`document_types`), not code enums. "Required attributes"
below are the fields observed on the real paperwork; in MVP1 the system
stores the file + a small structured header, full attribute extraction is
MVP3 (OCR). Every type supports two sources: photo of paper, or uploaded
digital file (e-CMR / PDF) - per Jiří's notes both must be possible.

| # | Document type (Czech term) | Key | Required attributes (observed) | When required |
|---|---|---|---|---|
| 1 | přepravní smlouva (objednávka o přepravě) | `transport_order` | number + date; ordering party & carrier (name, IČO/DIČ, address); vyřizuje/contact; loading place + date + time window; unloading place + date + time window (incl. GPS in one sample); goods name + CODE/IDTF; weight/quantity + packaging; vehicle type/equipment requirements; goods customs status (EU); sender; receiver; contractual price (fixed or per-tonne) + VAT; pre-printed SPZ + osádka; additional instructions; payment terms + required attachments | always - basis of the transport; MVP1 scope is inbound only (customer→Agrotech); outbound subcontracting (Agrotech→subcarrier, sample 1) is a recorded follow-up (Jiří, Q-a) |
| 2 | mezinárodní nakladní list (CMR) | `cmr` | CMR number (e.g. CZ D 9059477); sender (box 1); receiver (box 2); place + date of goods acceptance (box 3); delivery place (box 4); person for taking over (box 5); packages count + description (box 6); gross weight (box 7); customs/other instructions (box 8); vehicle SPZ (box 10); carrier signature + date at loading; consignee signature + stamp + date at unloading; reservations (výhrady) | international transports only - Jiří (Q-b): CMR not required for domestic runs; HARD RULE: consignee stamp+signature+date required or invoice cannot be paid; e-CMR upload must be accepted as an equivalent source |
| 3 | vážní lístek - nakládka | `weighbridge_ticket_loading` | ticket number; weighing operator (IČO, name, address); medium; weighing type; analysis type; partner (IČO); goods (JKV code, ČSN/quality class); moisture; measuring device + place; declared category/dodací list/hmotnost/vlhkost; smlouva; disp. číslo; Btto + timestamp; Tára + timestamp; Ntto net [t]; packaging; quality indicators (objemová hmotnost, N-látky, číslo poklesu, lepek, zelený test, příměsi); doprava vlastní/cizí; SPZ; řidič; stav vozidla (čistota); majitel; poznámka; vážil; převzal; GMP+ FSA note | bulk goods priced by weight; one of two tickets (loading); digital (system-printed) format already today |
| 4 | vážní lístek - vykládka | `weighbridge_ticket_unloading` | same attribute set as #3 | second ticket at destination; net difference loading↔unloading is the settlement quantity |
| 5 | ERKLÄRUNG-WARENBEGLEITSCHEIN (vyčištění korby) | `cleaning_declaration` | Section 1 (supplier/loading site): product/trade name; supplier/manufacturer; loading place; delivery date; EU feed-law compliance flag; contains prohibited/critical substances (Nein/Ja+which); place, date, stamp/signature. Section 2 (carrier): forwarder name; tractor SPZ + trailer/return SPZ (e.g. 1UM 2744 / 2SF 8619); driver name; consignee; products carried on the last 3 tours; cleaning before loading (Nein-keine Reste / Trockenreinigung / mit Wasser / Wasser+RM / Desinfektion+certificate); place, date, stamp/signature | feed/food bulk transport (GMP+ FSA regime), before loading; bilingual DE/CS form; driver signs at loading site |
| 6 | dodací list / Lieferschein | `delivery_note` | number; supplier; receiver; goods + quantity; loading reference; consignee stamp + signature + date at unloading | when the order instructs it (sample 1: driver receives only dodací list at loading; sample 2: white LIEFERSCHEIN stamped at unloading is a payment precondition); system must be ready for BOTH printed (photo/upload) and later system-generated versions - it is sent to the customer with the invoice to get paid (Jiří, Q-e revised at sign-off) |
| 7 | celní doklad DZV | `customs_document` | confirmed DZV copy reference | only customs transports outside EU - seeded as an INACTIVE type (Jiří, Q-c); activate when such transports appear |

Completeness rule learned from the real paperwork: the required set is
seeded per transport from order attributes - international ⇒ CMR
(consignee-signed/stamped), goods priced by weight ⇒ both weighbridge
tickets, feed/food ⇒ cleaning declaration, order instruction ⇒ delivery
note; the dispatcher can adjust the set. Missing/rejected document ⇒
transport cannot reach "ready for invoicing".

## 2. Transport state machine (validated against the workflow)

States (append-only `transport_events` records every transition:
from_state, to_state, actor, timestamp, payload):

```
draft ──assign(driver,truck)──▶ assigned ──arrive at loading──▶ at_loading
   │                                │ (unassign → draft)            │ loading done:
   │ cancel                         ▼                               ▼ CMR signed,
   ├──────────────▶ cancelled   (driver executes)               in_transit  weigh-in,
   │                                                            │           cleaning decl.
   │                                                            ▼ arrive at unloading
   │                                                          at_unloading
   │                                                            │ consignee signs CMR,
   │                                                            ▼ weigh-out
   │                                                          completed
   │                                                            │ driver hands in docs
   ▼                                                            ▼
 (terminal)                                                   in_review
                                                    ┌──────────┴──────────┐
                                            reject(document)      accept(all)
                                                    │                   ▼
                                                    ▼            ready_for_invoicing
                                                 returned ──resubmit──▶ in_review
```

- `draft`: transport created from the order, no driver/truck yet.
- `assigned` / `at_loading` / `in_transit` / `at_unloading`: driver marks
  arrival/departure in the PWA (offline-capable, synced later); document
  uploads hang off the state they occur in.
- `completed`: driver-side work done, all collected documents submitted.
- `in_review` → `ready_for_invoicing` | `returned`: office review is the
  correction loop (Karolina's "must add/fix" step); `returned` reopens for
  the driver, resubmission goes back to `in_review`.
- `cancelled`: reachable from `draft`/`assigned` (and recorded later with a
  storno note - the 10 % cancellation penalty is an accounting concern,
  not a state).
- No "arrived at pickup/delivery" sub-states beyond `at_loading` /
  `at_unloading` - the samples show no intermediate checkpoints.

## 3. Schema proposal (tables, keys, scoping)

Aligned with the `mvp1-organizational-groups` design (that change's schema
is adopted verbatim here). All domain rows carry `group_id` (scoping);
all PKs are UUID, client-generatable for offline creation; all write
endpoints require an idempotency key.

| Table | Key columns (beyond PK/audit) | Notes |
|---|---|---|
| `groups` | name | per organizational-groups design |
| `group_members` | group_id, user_id, UNIQUE(group_id,user_id) | dispatcher memberships |
| `users` (+alter) | group_id FK nullable | driver home group; roles already implemented |
| `trucks` | spz UNIQUE, group_id FK NOT NULL, label | per organizational-groups design |
| `trailers` | spz UNIQUE, group_id FK NOT NULL, label | trailer master data added at sign-off (Jiří) - target company has 6 trucks / 7 trailers |
| `orders` | group_id, number, order_date, counterparty_name, counterparty_ico, direction (`in`\|`out`), cargo_text, cargo_code, quantity NUMERIC(12,3), unit, unit_price NUMERIC(12,2), currency CHAR(3), vat_rate NUMERIC(4,1), price_total NUMERIC(14,2), loading_place TEXT, loading_from/loading_to TIMESTAMPTZ, unloading_place TEXT, unloading_from/unloading_to TIMESTAMPTZ, vehicle_requirements TEXT, goods_status TEXT, instructions TEXT, terms TEXT, source_document_id FK nullable | billing-ready (constraint 1); `direction` accepts `in` only in MVP1 (Jiří Q-a), `out` is the reserved subcontracting follow-up; counterparty kept as inline fields in MVP1 - no `partners` master table yet (flagged) |
| `transports` | group_id, order_id FK, driver_id FK users, truck_id FK nullable, trailer_id FK nullable, is_international BOOL, state, planned_loading_at, planned_unloading_at, completed_at | **truck question answered: YES** - SPZ appears on every sample doc; trailer references the `trailers` table (free text dropped at sign-off); `is_international` seeds the required-document set (CMR only when true) |
| `transport_events` | transport_id FK, event_type (`state_change`\|`document_submitted`\|`review`\|`note`), from_state, to_state, actor_id, payload JSONB, occurred_at | append-only, no UPDATE/DELETE grants (constraint 5) |
| `document_types` | key UNIQUE, label_cs, label_de, attribute_schema JSONB, variant (`none`\|`loading`\|`unloading`), default_required BOOL, is_active | taxonomy as data (constraint 7); seeded from §1 |
| `documents` | id client-generated, group_id, transport_id FK, document_type_id FK, variant, source (`photo`\|`digital_file`\|`e_cmr`\|`generated` - reserved for system-made Lieferschein), storage_key, mime, captured_at, attributes JSONB, status (`submitted`\|`accepted`\|`rejected`), created_by | presigned direct-to-Garage upload; attributes filled by OCR in MVP3 |
| `document_reviews` | document_id FK, reviewer_id FK, decision, reason | review audit (constraint 5) |
| `external_ids` | entity_type, entity_id, system, external_id, UNIQUE(system,entity_type,external_id) | POHODA prep (constraint 6) |
| `idempotency_keys` | user_id, key, request_hash, response JSONB, created_at, UNIQUE(user_id,key) | outbox replay safety (constraint 4) |

## 4. Answers to open questions

- **Truck on transport (SPZ)?** ANSWERED: yes. SPZ is printed/handwritten on
  CMR (box 10), both weighbridge tickets, ERKLÄRUNG (tractor + trailer) and
  the orders. `transports.truck_id` + `transports.trailer_id`; a `trailers`
  master-data table was added at sign-off (Jiří).
- **Groups:** ANSWERED (Jiří): keep the multi-group model from the
  organizational-groups design - no single-default-group shortcut even
  though today's target company has 1 dispatcher + 6 drivers; company-admin
  owns groups and dispatcher memberships, dispatchers assign drivers/trucks
  within their own groups.
- **POHODA edition + VS practice:** ANSWERED: current target company runs
  POHODA Windows standalone; faktury are created manually directly in
  POHODA today (no export/import automation). MVP2 replaces that with
  system-owned VS (constraint 2) and order/invoice write. Requirement from
  Jiří: the integration must be designed edition-agnostically (Windows
  standalone, POHODA SQL and Pohoda Online/Cloud all possible) - MVP1
  consequence: keep `external_ids` generic (system, entity, external_id)
  and do not bake edition assumptions into the domain schema.
- **Volumes (přepravy/month, docs/transport, drivers, dispatchers):**
  ANSWERED (partial): one dispatcher, 6 drivers, 6 trucks, 7 trailers -
  small single-site fleet, no capacity concerns for MVP1; more trailers
  than trucks confirms trailer master data - `trailers` table added at
  sign-off (Jiří). přepravy/month unknown - revisit before load testing.
- **Bank statement format + VS/SS pairing:** ANSWERED: there is no
  statement file today - the dispatcher manually reviews the bank account
  and pairs incoming transactions by eye. MVP4 must therefore introduce a
  machine-readable export (CSV/camt.053) with the bank; format TBD then.
- **Legal status of photographed documents:** the real paperwork itself
  demands paper originals for payment ("originál CMR", "bez razítka z
  vykládky na Lieferscheinu nelze proplátit fakturu"). MVP1 is therefore a
  workflow/evidence system: photos and digital files drive the process,
  the paper-original handover to the office remains a checklist item, and
  tax-document status is unchanged. e-CMR/digital uploads are accepted as
  first-class sources.

### Answers to questions surfaced by the samples (Jiří, M2 session)

- **Q-a Subcontracting direction:** MVP1 covers `in` orders/transports
  only. Follow-up recorded: add `out` orders (Agrotech issuing přepravní
  smlouvy to subcarriers, sample 1) after MVP1.
- **Q-b Domestic transports:** CMR is NOT required for purely domestic
  runs; the required-document set is seeded per transport from
  `transports.is_international`.
- **Q-c DZV/customs docs:** `customs_document` stays in the seeded
  taxonomy as an inactive type.
- **Q-d SMS weigh reporting:** MVP1 only tracks it - dispatcher checklist
  item recorded as a `note` transport event; no sending/reminder
  automation.
- **Q-e Dodací list origin (REVISED at sign-off):** the system must be
  ready for both printed Lieferscheins (photo/upload) and later
  system-generated ones; it is typically sent to the customer together
  with the invoice to get paid (MVP2 delivery bundle). Actual generation
  stays out of MVP1, but `documents.source=generated` and file storage are
  prepared for it.

### Recorded follow-ups (post-MVP1 backlog)

1. `out` orders/transports (subcontracting) - Q-a.
2. System-generated dodací list + sending it bundled with the invoice -
   Q-e (MVP2).
3. `partners` master data (IČO repeats across documents; MVP1 keeps
   inline fields on orders).
