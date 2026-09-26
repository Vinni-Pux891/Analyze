# ShadowAI project audit

Audit date: 26 September 2026. Scope: the current working tree, installed `.venv`, application routes, persistence, analytical logic, templates, JavaScript, exports, configuration and tests.

## Overall assessment

**This is a functioning demonstration prototype, but it does not yet establish that the proposed economic-risk analysis is reliable.** It demonstrates ingestion, basic statistics, a rules-based score, optional AI interpretation, persistence, charts and report downloads. That is a useful engineering starting point.

The largest blockers are correctness and data modeling: the same company receives different scores depending on how it is entered; a multi-company upload becomes one anonymous company; graph links can reflect identical descriptive text rather than a shared identity. These issues undermine the main product claim even when the UI works.

A credible POC should prove a narrower hypothesis: **an analyst can import company-period records, see reproducible signals with source evidence, review them, and retrieve the same result later.** It should not claim to estimate the size of the shadow economy or identify illegal behavior. Neither capability is implemented or validated here.

## 1. Technology stack

Versions below are observed in the current environment, not reproducible installation guarantees.

| Layer | Current implementation | Assessment |
|---|---|---|
| Runtime | Python 3.11.16 | No declared supported runtime version; README uses generic `python`. |
| Backend | Flask 3.1.3; Jinja templates; Werkzeug development server | Suitable for a small POC. Most application behavior sits in one 735-line `app.py`, including a very long AI prompt. |
| Analytics | Pandas 3.0.6 | Descriptive statistics, missing values, duplicates, ±3 sample-standard-deviation outliers, custom rules. No trained model or evaluation dataset. |
| AI | `google-genai` 2.25.0; hardcoded `gemini-2.5-flash` | Interprets computed results and provides an inspection recommendation. Runs synchronously inside requests. |
| Database | Python `sqlite3`, local `data.db` | One `companies` table; parameterized SQL; limited startup schema alterations. |
| Encryption | `cryptography` 50.0.1, Fernet | Six company fields encrypted using one environment-provided key. |
| Configuration | `python-dotenv` 1.2.3, `.env` | Only Gemini and encryption keys are documented environment settings. |
| Frontend | HTML, CSS, vanilla JavaScript | No Node build or frontend framework required. Charts and graph rendered in browser. |
| Charts / graph | Chart.js from unversioned jsDelivr URL; custom SVG force layout | No graph database or relationship discovery service. |
| Spreadsheet / PDF | `openpyxl` 3.1.5; `reportlab` 5.0.1 | CSV, XLSX and PDF exports; bundled Montserrat PDF font. |
| Styling assets | Local CSS; Google-hosted PT Sans / PT Serif | Online font dependency; Chart.js also needs external availability. |
| Testing | Python `unittest` and mocks | 18 tests in one file; no checked-in CI or browser test suite. |
| Dependencies | `requirements.txt` with minimum bounds or no bounds | No lockfile, hashes or repeatable resolved dependency set. Both `venv/` and `.venv/` exist locally. |

The current stack is sufficient for the next stage. A frontend rewrite, graph database, microservices, or a trained ML model is not a prerequisite for a credible POC.

## 2. What actually works

- Manual JSON entry has meaningful server-side checks for required fields, finite nonnegative numbers, tax percentage and integer employee counts.
- CSV/XLSX parsing, descriptive statistics, missingness and duplicate counts are implemented.
- Manual signals and uploaded-table signals produce actual calculated results; dashboard figures are not simply static mock values.
- Company persistence and field encryption work; missing or invalid encryption keys fail explicitly.
- AI output is schema-constrained and parsed. For accepted structured responses, company facts and score are copied back from trusted application input rather than trusting model-generated values.
- Gemini failures allow local analysis to continue. Some fallback paths produce a local structured recommendation.
- CSV and XLSX exports defend against spreadsheet formula interpretation; PDF text is escaped and a Cyrillic-capable font is bundled.
- Main UI paths use safe text rendering or explicit HTML escaping. Navigation includes keyboard handling, focus management and reduced-motion accommodations.
- Regional summaries and relationship edges are computed from stored rows.
- `.env`, virtual environments, database files and uploads are ignored by Git; the current tracked-file list does not include them. This was not a historical secret scan.

## 3. Verified findings and priorities

Priority meanings: **P0** blocks confidence in the analytical POC; **P1** is needed for a dependable controlled pilot, with access/security items required before sharing sensitive data; **P2** improves usability and maintainability.

| Priority | Finding and evidence | Consequence | Recommended change |
|---|---|---|---|
| P0 | Different scoring engines: `app.py:33` versus `app.py:566`. A synthetic company with revenue 1000, tax 0.5%, zero employees and activity “высокая” scored **50 manually, 0 from CSV**. | Input method changes the supposed risk of the same company. Regional averages mix incomparable scores. | Normalize both inputs into one company-period schema and run the same versioned rules. Keep dataset quality metrics separate. |
| P0 | Multi-row uploads set `company=None`, then insert one company (`app.py:649`). A two-row upload returned one record with null name, revenue and region. | Company records, regional company counts, exports and graph coverage are wrong for batch input. | Create an import batch and one validated observation per company row. If keeping generic table analysis, give it a separate dataset entity and report. |
| P0 | `social_media` is both descriptive text and a graph key (`database.py:115`). Separate companies with “высокая” became connected. | The graph suggests associations unsupported by identity evidence. | Split activity text from canonical social profile URL/account ID. Only identity fields should create identity edges. |
| P0 | No evaluation corpus or documented score calibration. Upload scoring includes missingness and duplicate frequency (`app.py:72`). | The score conflates data quality with economic signals; a clean table can look reassuring despite unknown analytical validity. | Define the intended outcome, record expected signals in expert-reviewed fixtures, evaluate false positives and misses, and present quality separately. |
| P1 | Upload validation is much weaker than manual validation. Header-only CSV, unrelated `hello/world` CSV and tax percentage 200 were all accepted with HTTP 200. | Invalid business records enter persistence without useful correction instructions. | Require a schema, preview mapped columns, reject invalid rows with field/row errors and agree partial-import behavior. |
| P1 | `inf` in an uploaded numeric column emitted nonstandard `Infinity`/`NaN` JSON from statistics. | Browser `response.json()` cannot parse that response even though the route returns 200. | Validate finite inputs and outputs; represent unavailable statistics as null; serialize strict JSON. |
| P1 | `normalize_report_input` omits `phone` (`app.py:133`); that normalized object is also used for upload persistence. A valid CSV phone became null. | Uploaded records cannot participate in phone matching. | Separate report serialization from persistence models; preserve validated phone data. |
| P1 | All routes are unauthenticated. An anonymous test-client request downloaded record 1 with HTTP 200 (`app.py:673`). | Anyone able to reach a shared server could enumerate and export records; writes and AI calls also have no access control. | For a shared pilot, require authentication and record/workspace authorization across every route; add quotas/rate limits. Cookie-based authentication also needs CSRF protection. |
| P1 | `MAX_CONTENT_LENGTH` is unset; files are read fully, twice per upload; text, row and column counts are uncapped (`app.py:27`, `app.py:642`). | Large files, expansive spreadsheets or long text can exhaust memory, disk, request time or AI budget. | Bound request size, spreadsheet expansion, rows, columns and text; parse once and reject unsupported formats early. |
| P1 | Analysis evidence is returned but not stored: no rule version, full statistics, anomaly evidence, import row reference or model/prompt version (`database.py:33`). | Results cannot be reconstructed or meaningfully audited after rules change. | Persist immutable analysis runs, signal evidence and provenance alongside normalized observations. |
| P1 | Insert and score update are separate transactions, with Gemini between them for manual entry (`app.py:616`). No idempotency key or company identity constraint exists. | Failures leave incomplete rows; retries create duplicates and distort summaries. | Persist explicit run states, use idempotent submissions and transactional local updates; store AI results separately from the completed local analysis. |
| P1 | Gemini controls `needs_inspection` except for a forced commerce signal; the narrative is not checked against actual evidence (`app.py:455`). | Stable scores do not imply stable recommendations. Prompt-like input can influence free text, and unsupported prose is not corrected by restoring fact fields. | Make review status rule-based or analyst-controlled. Restrict AI to evidence-linked explanation with a consistent structured unavailable state. |
| P1 | Debug server is hardcoded (`app.py:735`); no deployment configuration, health endpoint or application error instrumentation is present. | The current run method is a local development setup, not a managed shared service. | Configure debug off for shared use; add a production WSGI launch, health checks, structured error logs and backups. |
| P2 | `.xls` is advertised, but `xlrd` is neither declared nor installed. | Legacy Excel support is incomplete in the audited environment. | Explicitly support and test an appropriate engine, or remove `.xls` from accepted formats and documentation. |
| P2 | No company list/detail/history/review UI; current download ID lives in JavaScript memory (`static/app.js:2`). | Refresh loses the active result; users cannot conveniently retrieve or manage previous analyses. | Add a paginated analysis list, detail permalink and review workflow. |
| P2 | PDF forces all text onto one page by scaling (`report_export.py:68`). | Long recommendations can technically fit but become unreadable. | Use multi-page layout, readable minimum font size and visual export checks. |

## 4. Hardcoded and demonstration behavior

Hardcoding is not inherently wrong for a POC. Analytical assumptions need explicit ownership, versioning and evidence; ordinary display defaults can remain in code.

| Area | Exact current behavior | What should change |
|---|---|---|
| Upload score | 12 points per numeric column containing any ±3σ outlier, capped at 60; duplicate fraction ×20, capped at 20; missing-cell fraction ×100, capped at 20; total capped at 100. | Describe it as dataset diagnostics until replaced by per-company evidence rules. One versus many outliers in a column currently contributes the same points. |
| Manual tax signal | Positive revenue and tax <1% adds 30; tax from 1% to <3% adds 15. | Define the meaning of tax percentage, period, jurisdiction and regime; no tax-regime validation is currently implemented. |
| Manual workforce signals | Positive revenue and zero employees adds 20; zero revenue and positive employees adds 20. | Evaluate legitimate counterexamples and distinguish zero from missing. |
| Manual social signal | Exactly `высокая` with zero revenue adds 12. | Normalize or replace the category; spelling, case and free-text alternatives behave differently. |
| Commerce keywords | `цена`, `заказ`, `доставка`, `скидка`, `опт`, `продажа`, `акция`, `в наличии`; case-insensitive substring matching. | Use token-aware matching and relevant languages; validate negatives and contextual usage. `реакция` incorrectly matches `акция`. |
| Commerce revenue threshold | Revenue ≤1000, including non-finite/missing/unparseable revenue, plus a keyword adds 15 points. | Store currency and reporting period; missing revenue must be an uncertainty state, not evidence of low revenue. |
| Commerce recommendation | Commerce signal forces `needs_inspection=true`, including AI failure paths. | Expose the rule and let the analyst determine follow-up; do not imply validated inspection criteria. |
| Risk bands | Below 30, 30–70, ≥71; high-risk cutoff 71 is duplicated in backend, JavaScript and template text. | Put versioned band metadata alongside the scoring rules and return it through the API. |
| AI settings | Model `gemini-2.5-flash`, embedded Russian prompt, fixed output schema. | Configure model; version prompt/schema; set explicit request budgets and record provider outcome. |
| AI prompt examples | Fictional TechNova LLC, UZS values, score 57 and sector benchmarks. Markdown report instructions conflict with JSON response configuration; the explicit JSON instructions at lines 399 onward are commented out. | Replace with concise schema-aligned instructions containing only available evidence. These examples are not computed benchmark features. |
| Storage/runtime | `data.db` beside source; relative `uploads/`; host `127.0.0.1`, port 5500, debug on. | Environment-specific configuration and an explicit application data directory. |
| UI/export | Russian strings/formatting, fixed eight report rows, single-page PDF, fixed SVG layout and simulation iterations. | Keep Russian if intentional; improve long-text layout and bound graph size before adding localization. |
| Product content | Contacts page is explicitly placeholders; bundled CSV is fixed demonstration data. | Supply real ownership/support details for a pilot and a documented representative demonstration dataset. |

There is no implemented social-media collection, registry integration, bank/payment feed, sector benchmark dataset or longitudinal monitoring. “Social activity” is submitted text. Region and sector are optional labels; sector is not used by the scoring engine. `tax_paid` and `transactions` in the sample CSV are generic numeric columns, not interpreted economic features.

## 5. Analytical and AI limitations

The uploaded-table detector uses mean and sample standard deviation on whatever numeric columns Pandas infers. It does not exclude identifiers, group comparable companies, normalize currency/periods or handle skewed distributions explicitly. Small samples and extreme values influencing their own baseline can make ±3σ ineffective. The bundled 11-row sample returned **zero anomalies and score 0**, including its visibly larger record. This is an observed property of the heuristic, not evidence that the larger record is actually risky.

The current score is not a probability, validated risk estimate or measure of undeclared economic activity. There are no labeled outcomes, precision/recall measurements, robustness checks or reviewer agreement measurements. The existing disclaimers are useful, but they do not resolve score inconsistency.

Gemini receives normalized company facts and aggregate analysis. For a one-company record that can include name, revenue, employees, social text, tax, region and sector. This is an external data transfer even though the database encrypts some fields. Phone is not part of that AI payload. Multi-row inputs instead have empty company facts and aggregate statistics, despite the prompt describing a single company.

The AI integration has no application-configured deadline, output budget, retry policy, caching, token/cost accounting or prompt-injection evaluation. The SDK may supply defaults; those defaults were not treated as deliberate application controls. A provider failure returns either a string or a structured object depending on commerce signals. Malformed AI output may be passed through as a raw string. Unify these cases into a typed result with status, evidence, explanation and provider metadata.

No live Gemini requests were made during the audit. Availability, latency, cost and live recommendation quality remain unverified.

## 6. Data, security and operation gaps

**Data model.** One table combines identity, observation, analytical result and recommendation. There is no stable registration ID, reporting period, currency, unique import identifier or separate analysis history. Re-entering a company creates another “company,” so summaries count submissions rather than reliably counting unique entities. Region normalization handles whitespace/case only; `Tashkent` and `Ташкент` remain separate.

**Evidence retention.** Uploaded files are normally deleted in `finally`, which reduces unnecessary raw-file retention, but no source hash, row provenance or full analytical snapshot remains. Preserve sufficient normalized evidence and provenance without automatically retaining sensitive raw files forever. Define retention and deletion rules explicitly.

**Encryption boundaries.** Name, revenue, tax percentage, employees, social text and phone are encrypted. Region, sector, score, recommendation and commerce keywords remain plaintext. AI prose can itself repeat sensitive facts, so field encryption is not complete protection of the database's contents. There is no key rotation/versioning or documented key recovery procedure. Losing the key makes existing ciphertext unusable; silently replacing it is not a migration plan.

**Access and errors.** Encryption at rest does not restrict API readers. Public deployment requires access control, transport security and ownership checks. Upload errors return raw exception text (`app.py:664`); other routes often hide exceptions without recording useful diagnostic context. Return safe structured errors and log redacted detail with request IDs.

**Performance.** Regional summaries decrypt every company and all sensitive fields. Graph generation also loads all records and expands every matching group into all pair combinations. Browser force simulation compares every node pair repeatedly. Large groups therefore create quadratic work and large responses. Set POC limits, paginate records, filter graph queries and consider identity-group nodes instead of complete pairwise cliques. SQLite itself is not the immediate blocker for a small bounded pilot.

**Deployment.** There are no checked-in CI workflows, deployment scripts/container definition, backup/restore instructions or monitoring configuration. Initialization alters the database at import time. A small application factory, explicit migration step and environment-specific config would make startup and testing more predictable.

**Dependencies and offline behavior.** Unbounded Python updates and unversioned Chart.js make installations change over time. If Chart.js fails to load, chart rendering can throw during dashboard rendering before the AI report is rendered. Pin tested dependencies and serve essential assets locally or handle their failure independently.

## 7. Verification performed

Commands: `.venv/bin/python -m unittest discover -s tests -v` and `.venv/bin/python -m pip check`.

- **18/18 existing tests passed.** Coverage includes structured AI parsing/fallback, fact restoration, persistence/encryption checks, commerce signals, exports/formula protection, graph matching and region aggregation.
- **Installed dependency consistency passed.** This is not a vulnerability assessment or proof that optional file-format dependencies exist.
- Additional synthetic probes confirmed input-path score divergence, anonymous batch persistence, dropped upload phones, false social-text links, invalid CSV acceptance, nonstandard JSON, anonymous report access and missing upload-size configuration.
- These probes used a temporary database, temporary upload directory, a newly generated ephemeral encryption key and Gemini disabled. They did not add synthetic records to the working `data.db` or send company data externally.
- Repository source, templates and scripts were inspected. No browser visual/accessibility audit, stress test, penetration test, historical secret scan, actual legacy `.xls` fixture test or live Gemini evaluation was performed.

Existing tests preserve several problematic behaviors rather than testing the intended business contract. Passing them demonstrates implementation stability within their scope, not analytical validity. The suite also uses shared test-class state for some cases; use per-test fixtures when expanding it.

Add targeted coverage for manual/upload equivalence, row-by-row batch persistence, identity-only graph edges, invalid/non-finite data, repeat-submission idempotency, transaction failures, access boundaries, provider timeouts and browser chart failures. Export validation should check legibility and evidence content, not only valid bytes and page count.

## 8. Recommended POC scope and architecture

Keep Flask, Pandas, SQLite, Jinja and vanilla JavaScript. First improve their contracts and separation of responsibilities.

Proposed flow:

`CSV/XLSX or manual entry → shared schema validation → normalized company-period observations → versioned deterministic signals → persisted analysis run → optional AI explanation → analyst review and export`

Suggested logical records, which can remain in SQLite initially:

| Record | Minimum purpose |
|---|---|
| Company | Stable ID, name, canonical region/sector, normalized identity fields. |
| Observation | Company ID, reporting period, currency, revenue, tax definition/value, workforce and source evidence. |
| Import batch | File hash/reference, submitter, status, row counts and row errors; supports idempotency. |
| Analysis run | Observation/batch reference, rule version, score/status, quality findings, signal evidence and timestamp. |
| AI explanation | Analysis ID, provider/model/prompt version, status, validated explanation and usage metadata. |
| Review | Analysis ID, reviewer, disposition, reason and timestamp. |

Extract ingestion, scoring, reporting and persistence services from routes. Use an application factory and typed validation objects. Avoid introducing a background queue until a bounded synchronous request cannot meet measured latency; if necessary, local analysis should complete independently and AI enrichment should have its own status and retries.

## 9. Prioritized delivery plan

Effort ranges are planning estimates for one experienced engineer familiar with this code, with reviewer/domain input available. They are not commitments and exclude obtaining external datasets or approvals.

| Stage | Deliverables | Indicative effort | Exit condition |
|---|---|---|---|
| 1: Correctness | Canonical schema; shared scorer; batch/observation separation; preserve phones; finite-value validation; separate profile identity from activity text. | 4–7 engineering days | Same facts yield identical signals/score through either input path; N valid rows persist as N observations; invalid rows have useful errors. |
| 2: Analytical proof | Versioned rules; quality vs signal separation; representative expert-reviewed fixtures; evidence display; unknown-data states. | 3–5 days plus domain review | Every displayed signal traces to a rule and source value; measured errors and limitations are documented. |
| 3: Usable workflow | Result history/detail pages; idempotency; review disposition; durable report evidence; consistent AI fallback and budgets. | 3–5 days | An analyst can submit, reload, review, retry and export without losing context or duplicating records. |
| 4: Shared-pilot operation | Authentication/authorization, input limits, debug-off deployment, logs, health checks, pinned dependencies, CI, backup/restore. | 3–5 days | Access tests pass; bounded load and provider-failure checks succeed; backup restoration is demonstrated. |

For a local demonstration using synthetic data, stages 1–3 are the core. For any shared pilot with sensitive records, stage 4 access and deployment protections are launch prerequisites and should be developed alongside the earlier stages. Overall, budget roughly **3–5 engineer-weeks**, then revise after the canonical schema and evaluation scope are agreed.

## 10. POC acceptance checklist

The following are proposed acceptance criteria, not capabilities already demonstrated:

- A documented company-period schema defines currency, tax meaning, missing values and identity fields.
- Equivalent manual and uploaded input gives exactly the same deterministic result and rule version.
- A batch with 100 valid observations produces 100 traceable observations; invalid rows are identified and retries do not duplicate accepted input.
- A representative reviewed fixture set covers ordinary companies, intended signals, missing data and legitimate counterexamples. Expected signal behavior and evaluation targets are agreed before tuning.
- Every signal exposes its input values, threshold, rule version and reason; uncertainty is distinguishable from low risk.
- The graph only links canonical identifiers, explains edge evidence and does not link generic descriptions such as “high activity.”
- Reloading a result and exporting it preserve analysis provenance, not merely the latest display state.
- Gemini unavailable, malformed or slow responses do not lose local results or block the workflow indefinitely.
- Request/data limits are enforced, JSON is strict, and a declared target dataset size/latency is benchmarked on the intended host.
- Shared deployments enforce record access, run without debug mode, record useful redacted errors and have a tested recovery procedure.

## Reference checks

Findings above are based primarily on this repository and isolated runtime checks. External documentation was used only to verify relevant platform behavior:

- Flask explicitly advises against using its development server for deployment: [Deploying to Production](https://flask.palletsprojects.com/en/stable/deploying/).
- Flask documents request/resource limits, including `MAX_CONTENT_LENGTH`: [Security Considerations](https://flask.palletsprojects.com/en/stable/web-security/).
- Pandas documents Excel engine selection and legacy `.xls` handling: [read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html).
