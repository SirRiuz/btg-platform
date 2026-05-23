# BTG Pactual — Fondos de Inversión (Technical Test)

FastAPI + MongoDB platform that lets a user subscribe to investment funds,
cancel subscriptions, and receive transactional notifications by email
and SMS.

## Quick start (local)

```bash
cp .env.template .env
# Fill in the values — leave NOTIFICATIONS_PROVIDER=log for local dev.

docker compose up -d --build
make seed-funds          # seeds the 5 mandatory BTG funds
```

The API is available at `http://localhost:8000`.
OpenAPI / Swagger UI: `http://localhost:8000/docs`.

## Testing

Backend tests run with `pytest` inside the running `api` container. Make
sure the stack is up first (`docker compose up -d`).

```bash
# Run all tests with coverage report in the terminal
# (includes missing-line numbers + writes htmlcov/ inside the container).
make test

# Skip coverage for a faster feedback loop while iterating.
make test-fast

# Stricter run used in CI: fails if total coverage drops below 70%
# and emits coverage.xml (Cobertura format) for CI consumption.
make test-coverage
```

The HTML report lives at `api/htmlcov/index.html` (the `api/` directory
is bind-mounted into the container at `/app`, so the report shows up on
the host too). Open it from the host with:

```bash
open api/htmlcov/index.html     # macOS
xdg-open api/htmlcov/index.html # Linux
```

If you added or upgraded test deps in `api/requirements.txt`, rebuild
the image first: `make build`.

## Configuration

Every runtime knob lives in `api/core/settings.py` as a Pydantic
`BaseSettings`. The single `Settings()` instance is built at import time
and validates the environment up-front — a misspelled region or a
missing required credential causes the process to fail at boot, NOT at
the first incoming request.

See `.env.template` for the full list with placeholders and inline docs.

### Server port

The listen port has a single source of truth: `SERVER_PORT` in `.env`.
It propagates automatically to:

- **uvicorn** inside the `api` container — `docker compose` substitutes
  it into the service `command` at parse time.
- **nginx** — `nginx.conf.template` is rendered by the official image's
  envsubst entrypoint into `/etc/nginx/conf.d/default.conf`, replacing
  `${SERVER_PORT}` with the runtime value.
- **Host port mapping** — the `ports:` declaration of the nginx service
  uses the same variable, so the published port matches.
- **API healthcheck** — substituted into the `wget` URL at parse time.

To change the port:

```bash
# Edit the .env (single source of truth)
sed -i '' 's/^SERVER_PORT=.*/SERVER_PORT=80/' .env   # macOS
# sed -i  's/^SERVER_PORT=.*/SERVER_PORT=80/' .env   # Linux

# Recreate so compose re-reads .env (restart alone is not enough)
docker compose down
docker compose up -d

# Verify (no :80 because that is HTTP's default port)
curl http://localhost/docs
```

No edits to `Dockerfile`, `nginx.conf.template` or `docker-compose.yml`
are required — the whole stack reconfigures itself.

---

## Sending notifications to any recipient in any country

The notifications module supports **global delivery from day one**: the
code contains no per-country / per-domain / per-region restrictions. Any
RFC-valid email and any E.164-valid phone number is accepted.

**What the code does NOT do** (deliberately):

- Filter recipients by country code, dialing plan, or carrier.
- Filter emails by domain.
- Apply allow-lists or block-lists of any kind in the adapters.

**What AWS does** (operationally, NOT our code's concern):

| AWS state | Effect |
|---|---|
| **SES sandbox** (default for new accounts) | Delivers only to verified email addresses. Unverified → `MessageRejected`. |
| **SNS SMS sandbox** (default for new accounts) | Delivers only to verified phone numbers. Unverified → `InvalidParameter`. |
| **SES production access** (request via AWS Console → SES → Account dashboard) | Delivers to any valid address. Approval typically 24–48h. |
| **SNS production access** (request via AWS Console → SNS → Mobile → Text messaging → Exit SMS sandbox) | Delivers to any valid number, any country supported by AWS. Approval typically 24–48h. |

### Cost awareness

- **Email (SES)**: ~$0.10 per 1 000 messages, same in every region.
- **SMS (SNS)**, per message (transactional, us-east-1):

  | Destination | Approx price |
  |---|---|
  | Colombia | $0.04 |
  | México | $0.027 |
  | USA | $0.0075 |
  | India | $0.002 |
  | UK | $0.05 |

  The code does NOT optimize routing by cost; it logs the masked
  destination so an auditor can reconcile spend after the fact.

### Special-case countries

| Country | Note |
|---|---|
| USA | Alphanumeric `SNS_SENDER_ID` ignored; AWS swaps in a long number automatically. For "from name" branding you need 10DLC registration (weeks + per-message fee). |
| Canada | Same as USA. |
| India | DLT registration required for sender id; otherwise messages may be blocked. |
| China | Not supported by SNS at all. |

For multi-country production traffic at scale, consider **Amazon
Pinpoint** instead of SNS — better campaign management, opt-out lists,
and delivery analytics.

### Recommended: spending limit

Before exiting the sandbox, set an SNS monthly spending limit so a bug
cannot drain the budget:

> AWS Console → SNS → Mobile → Text messaging → Account-level settings → Spending limit

---

## Security — AWS credentials

**`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are SECRETS.** They
are never committed and never logged. The settings module wraps the
secret in `SecretStr`, so it cannot appear in `repr()` / serialization
output. The startup-summary log line explicitly excludes it.

### Local development

Set both values in your local `.env`. `.env` is in `.gitignore`
(verified) — do not check it in.

```env
NOTIFICATIONS_PROVIDER=aws
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
SES_FROM_EMAIL=noreply@yourdomain.com
```

The Settings cross-field validator enforces this: starting the app with
`NOTIFICATIONS_PROVIDER=aws` outside Lambda but without credentials
raises a `ValueError` at boot.

### Lambda production

In Lambda, attach an **IAM role** to the function with the minimum
permissions:

- `ses:SendEmail` scoped to the verified identity ARN.
- `sns:Publish` scoped to phone numbers (no `Resource: *` if avoidable).

**Do NOT** set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the
function's environment. boto3 picks up the role's temporary credentials
automatically via the instance metadata service. The Settings validator
detects Lambda via `AWS_LAMBDA_FUNCTION_NAME` (set by the runtime) and
relaxes the credential requirement accordingly.

### Production-grade secret handling (future)

For real production traffic, do not even keep the credentials in env
vars:

- Store them in **AWS Secrets Manager** (or SSM Parameter Store with
  `SecureString`).
- Rotate periodically with **AWS IAM Access Analyzer** suggesting unused
  permissions for removal.
- Enable **AWS GuardDuty** for anomaly detection on credential usage.
- For very-high-throughput sends, run boto3 against the EC2/Lambda
  metadata service through a short-lived assumed role.

---

## AWS Setup commands (sandbox)

```bash
# 1) Verify the FROM address in SES.
aws ses verify-email-identity \
  --email-address noreply@yourdomain.com \
  --region us-east-1

# 2) Verify a destination email — sandbox only.
aws ses verify-email-identity \
  --email-address yourtest@gmail.com \
  --region us-east-1

# 3) Verify an SMS destination — sandbox only.
aws sns create-sms-sandbox-phone-number \
  --phone-number +573001234567 \
  --region us-east-1

# Then submit the OTP that AWS sends to that number:
aws sns verify-sms-sandbox-phone-number \
  --phone-number +573001234567 \
  --one-time-password 123456 \
  --region us-east-1

# 4) Apply for production access via the AWS Console when you're ready.
```

---

## Running locally vs in Lambda

### Local (docker compose)

```env
NOTIFICATIONS_PROVIDER=log         # dev default: logs instead of calling AWS
# OR
NOTIFICATIONS_PROVIDER=aws
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
SES_FROM_EMAIL=noreply@yourdomain.com
```

```bash
docker compose up -d --force-recreate api
```

The startup log shows the effective config (without secrets):

```
settings.loaded debug=True mongo_db=soptest notifications_enabled=True
notifications_provider=log aws_region=us-east-1 ses_from_email=...
sns_sender_id=BTGPactual phone_default_region=CO is_running_in_lambda=False
```

### Lambda (production)

Function environment variables:

```env
NOTIFICATIONS_PROVIDER=aws
AWS_REGION=us-east-1
SES_FROM_EMAIL=noreply@yourdomain.com
SNS_SENDER_ID=BTGPactual
# No AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY — the IAM role provides them.
```

The startup log shows `is_running_in_lambda=True`, confirming the
credential validator allowed the access-key env vars to be absent.

---

## Future improvements

| Improvement | Why not now |
|---|---|
| AWS Secrets Manager for credentials with periodic rotation | Tech test scope. Document for production. |
| AWS GuardDuty integration for credential-misuse alerts | Account-level setting; not a code change. |
| Circuit breaker (pybreaker) on the AWS adapters | Useful at scale; the brief's volume is too low for the added complexity. |
| Migrate from SNS to Amazon Pinpoint for multi-country campaigns | Larger refactor; advisable when the use case becomes campaign-driven. |
| Idempotency-key header to dedupe retries | Requires Redis. Out of scope for the tech test. |
| Outbox pattern with SQS + worker Lambda for guaranteed delivery | Current `BackgroundTasks` fire-and-forget is sufficient for the brief's load profile. |
