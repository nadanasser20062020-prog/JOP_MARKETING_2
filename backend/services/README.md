# Backend Query and Domain Services

The current Node.js service/query layer is [`../node/queries.js`](../node/queries.js). It owns the consistent skill-eligibility predicate, source/role/scope filters, aggregate denominators, role analysis, historical-only trends, resource lookup, and Jaccard match explanation. HTTP routing and validation stay in [`../node/api.js`](../node/api.js); the SQLite connection is read-only.

Use parameterized SQL and explicit allowlists. Do not loosen the skill policy to include `needs_review` or `needs_owner_review`. Missing values remain unavailable, salary/activity gates remain disabled, and raw job text is untrusted. See the [API contract](../../docs/software-engineering/API_SPECIFICATION.md) and [metrics/model method](../../docs/software-engineering/METRICS_AND_MODEL_METHOD.md).
