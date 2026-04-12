# Cube Foundry — Maintenance Guide

> Reference this file whenever you need to update, fix, or inspect a live deployment.
> Each section explains what you're doing and why, then gives exact commands.
> Every command assumes you are authenticated (`gcloud auth login`) and your project
> is set (`gcloud config set project cube-foundry-prod`).

---

## Quick-Reference Cheatsheet

| Task                            | Jump to                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------- |
| Deploy new backend code         | [Rebuild & Redeploy Backend](#rebuild--redeploy-backend)                            |
| Deploy new frontend code        | [Redeploy Frontend](#redeploy-frontend)                                             |
| Add or change a DB column       | [Update the Database Schema](#update-the-database-schema)                           |
| Check what's broken             | [Checking Logs](#checking-logs)                                                     |
| Roll back to a previous version | [Rolling Back a Deployment](#rolling-back-a-deployment)                             |
| Update an API key or secret     | [Managing Secrets](#managing-secrets)                                               |
| Check DB directly               | [Connect to the Database via Cloud Shell](#connect-to-the-database-via-cloud-shell) |
| Something is down / on fire     | [Incident Checklist](#incident-checklist)                                           |

---

## Infrastructure Reference

```
Project:        cube-foundry-prod
Region:         northamerica-northeast1
Cloud Run:      cube-foundry-api
Cloud SQL:      cube-foundry-db  (PostgreSQL)
Artifact Reg:   northamerica-northeast1-docker.pkg.dev/cube-foundry-prod/cube-foundry-repo/cube-foundry-api
Firebase:       cube-foundry-prod.web.app
Service Acct:   cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com
```

---

## Rebuild & Redeploy Backend

**When to use this:** You changed any Python file, updated `requirements.txt`, edited the
`Dockerfile`, or changed a backend model, endpoint, or service.

**Concept:** Cloud Run runs a Docker image, not raw source code. When you change the code,
you have to (1) build a new Docker image from your updated source, (2) push it to Artifact
Registry, and (3) tell Cloud Run to use the new image. `gcloud builds submit` does steps 1
and 2 in Google's cloud (no Docker Desktop needed). `gcloud run deploy` does step 3.

### Step 1 — Build a new image

```powershell
cd back_end
gcloud builds submit --tag northamerica-northeast1-docker.pkg.dev/cube-foundry-prod/cube-foundry-repo/cube-foundry-api:latest .
```

This uploads your `back_end/` folder to Cloud Build, runs your `Dockerfile`, and stores the
finished image tagged `latest` in Artifact Registry. It takes 3–5 minutes. Watch the output
for any pip install errors or build failures before proceeding.

### Step 2 — Deploy the new image

```powershell
gcloud run deploy cube-foundry-api `
  --image northamerica-northeast1-docker.pkg.dev/cube-foundry-prod/cube-foundry-repo/cube-foundry-api:latest `
  --platform managed `
  --region northamerica-northeast1 `
  --service-account cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com `
  --add-cloudsql-instances cube-foundry-prod:northamerica-northeast1:cube-foundry-db `
  --set-secrets DATABASE_URL=DATABASE_URL:latest `
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest `
  --set-secrets ALLOWED_ORIGINS=ALLOWED_ORIGINS:latest `
  --allow-unauthenticated `
  --port 8080 `
  --min-instances 0 `
  --max-instances 10 `
  --memory 512Mi
```

**Why you must include all the `--set-secrets` flags every time:** Each `gcloud run deploy`
call replaces the service's entire configuration. If you omit a secret, that environment
variable disappears from the running container. Always include all three.

### Verify the deployment

```powershell
gcloud run services describe cube-foundry-api `
  --region northamerica-northeast1 `
  --format="value(status.latestReadyRevisionName)"
```

The output shows the current live revision name like `cube-foundry-api-00015-abc`. If this
changed from your last known revision, the deploy succeeded.

You can also hit your health endpoint in a browser:

```
https://cube-foundry-api-841885569866.northamerica-northeast1.run.app/health
```

---

## Redeploy Frontend

**When to use this:** You changed any `.tsx`, `.ts`, or `.css` file in `front_end/src/`,
added a new page, updated API URLs, or changed `vite.config.ts`.

**Concept:** The frontend is a static React app. Vite compiles your TypeScript into plain HTML,
CSS, and JavaScript files in `front_end/dist/`. Firebase Hosting serves those files from
Google's CDN. Users get your latest code the next time their browser loads the page.

### Step 1 — Build the React app

```powershell
cd front_end
npm run build
```

This produces a `dist/` folder. Check that the build succeeds with no TypeScript errors before
deploying. If there are errors, fix them first — deploying a broken build will break the site.

### Step 2 — Deploy to Firebase Hosting

```powershell
firebase deploy --only hosting
```

Firebase uploads `dist/` to the CDN. It takes about 30 seconds. After completion you'll see
a "Deploy complete!" message with the live URL.

### Verify

Visit https://cube-foundry-prod.web.app. Open the browser DevTools → Network tab and do a
hard refresh (Ctrl+Shift+R) to confirm you're loading the latest build, not a cached version.

---

## Update the Database Schema

**When to use this:** You added a new column to a SQLAlchemy model (e.g., `models/cube.py`),
added a new table, or need to change a column type. SQLAlchemy does **not** auto-migrate —
you must run the SQL yourself.

**Concept:** The live database on Cloud SQL is separate from your local code. Adding a Python
column to a model class doesn't touch the database. The DB schema only changes when you run
ALTER TABLE or CREATE TABLE SQL directly against it. Cloud Shell gives you a browser-based
terminal that can connect to Cloud SQL using the Auth Proxy (private, no open ports).

### Step 1 — Open Cloud Shell

Go to https://console.cloud.google.com and click the **terminal icon** (>\_) in the top right
of the page header. A terminal opens at the bottom of the page.

### Step 2 — Connect to your database

In Cloud Shell:

```bash
gcloud sql connect cube-foundry-db --user=postgres --database=cube_foundry
```

It will prompt for your PostgreSQL password (the one stored in Secret Manager under
`DATABASE_URL` — it's the password portion of the connection string).

You are now in a `psql` prompt connected to the live database.

### Step 3 — Run your migration SQL

Type your SQL directly. Always use `IF NOT EXISTS` / `IF EXISTS` so the command is safe to
re-run:

```sql
-- Add a single column:
ALTER TABLE cubes ADD COLUMN IF NOT EXISTS cubecobra_link VARCHAR;

-- Add multiple columns at once:
ALTER TABLE post_draft_feedback ADD COLUMN IF NOT EXISTS cards_to_add TEXT;
ALTER TABLE post_draft_feedback ADD COLUMN IF NOT EXISTS cards_to_cut TEXT;

-- Rename a column:
ALTER TABLE cubes RENAME COLUMN old_name TO new_name;

-- Add a new table (example pattern):
CREATE TABLE IF NOT EXISTS my_new_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 4 — Verify the change

```sql
-- See all columns on a table:
\d cubes

-- See all tables:
\dt

-- Check row count:
SELECT COUNT(*) FROM cubes;
```

Type `\q` to exit psql when done.

### Important: migration files

After running a migration, save the SQL in a numbered file in `back_end/` so you have a
record:

```
back_end/migrate_schema.sql        ← already exists, add new changes here
back_end/migrate_<feature>.sql     ← or make a new one per feature
```

---

## Checking Logs

**When to use this:** A request is failing with a 500 error, the app is crashing on startup,
something works locally but not in production, or you just want to see what's happening.

### Live log tail (Cloud Run)

```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cube-foundry-api" `
  --limit=50 `
  --format="value(timestamp,textPayload)" `
  --order=desc
```

This prints the 50 most recent log lines. `--order=desc` puts newest first. Change `--limit`
to see more.

### Filter by severity (errors only)

```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cube-foundry-api AND severity>=ERROR" `
  --limit=20 `
  --format="value(timestamp,textPayload)" `
  --order=desc
```

### Stream logs in real time

```powershell
gcloud alpha logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cube-foundry-api"
```

Press Ctrl+C to stop. Useful when you're actively testing something and want to watch requests
come in.

### In the GCP Console (easier to read)

1. Go to https://console.cloud.google.com
2. Search **"Cloud Run"** → click `cube-foundry-api`
3. Click the **"Logs"** tab
4. Use the severity filter dropdown and date picker to narrow results
5. Click any log entry to expand its full JSON payload

### Cloud Build logs (if a build failed)

```powershell
gcloud builds list --limit=5
```

This lists your 5 most recent builds with their status (SUCCESS / FAILED). Copy the build ID
from a failed build, then:

```powershell
gcloud builds log <BUILD_ID>
```

---

## Rolling Back a Deployment

**When to use this:** You deployed a bad build and the app is broken. Cloud Run keeps all
previous revisions so you can instantly serve an older working one.

### List recent revisions

```powershell
gcloud run revisions list --service cube-foundry-api --region northamerica-northeast1
```

This shows all revisions with their name, creation time, and traffic allocation. The one
currently serving 100% of traffic has `TRAFFIC` listed.

### Send traffic to a previous revision

```powershell
gcloud run services update-traffic cube-foundry-api `
  --region northamerica-northeast1 `
  --to-revisions cube-foundry-api-00014-abc=100
```

Replace `cube-foundry-api-00014-abc` with the revision name you want. This takes effect in
seconds — no rebuild required. The app is immediately restored.

### Return to latest after fixing the issue

Once you've rebuilt and deployed a fixed image, send traffic back:

```powershell
gcloud run services update-traffic cube-foundry-api `
  --region northamerica-northeast1 `
  --to-latest
```

---

## Managing Secrets

**When to use this:** You need to rotate an API key, the database password changed, or you
need to add a new secret (e.g., a new third-party service).

**Concept:** Secrets live in Secret Manager. Each secret has multiple "versions" — you can
add a new version without deleting the old one. Cloud Run always pulls `latest` (configured in
the deploy command), so adding a new version is enough to update what the app uses at next
startup.

### View existing secrets

```powershell
gcloud secrets list
```

### Add a new version of an existing secret (rotate a key)

```powershell
echo "new-value-here" | gcloud secrets versions add SECRET_NAME --data-file=-
```

For example, to rotate the Gemini API key:

```powershell
echo "AIzaSy..." | gcloud secrets versions add GEMINI_API_KEY --data-file=-
```

The new version is now `latest`. The running containers won't pick it up until they restart.
To force a restart, redeploy using the same deploy command from [the backend section](#rebuild--redeploy-backend)
(the image doesn't need to change — just re-running the deploy command restarts the containers).

### View a secret's current value (careful — this prints it to terminal)

```powershell
gcloud secrets versions access latest --secret=DATABASE_URL
```

### Add a brand new secret

```powershell
echo "my-secret-value" | gcloud secrets create NEW_SECRET_NAME --data-file=-
```

Then grant your service account access to it:

```powershell
gcloud secrets add-iam-policy-binding NEW_SECRET_NAME `
  --member="serviceAccount:cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

Then add it to the deploy command using `--set-secrets NEW_SECRET_NAME=NEW_SECRET_NAME:latest`.

---

## Connect to the Database via Cloud Shell

**When to use this:** You want to inspect real data, fix a corrupted row, run a one-time data
migration, or debug something that's only happening with production data.

### Open psql

In Cloud Shell (https://console.cloud.google.com, click the >\_ icon):

```bash
gcloud sql connect cube-foundry-db --user=postgres --database=cube_foundry
```

### Useful psql commands

```sql
-- List all tables
\dt

-- Describe a table's columns
\d table_name

-- Count rows
SELECT COUNT(*) FROM cubes;

-- Look at recent rows
SELECT * FROM cubes ORDER BY created_at DESC LIMIT 10;

-- Check for orphaned records
SELECT * FROM draft_events WHERE cube_id NOT IN (SELECT id FROM cubes);

-- Delete a bad row (be careful!)
DELETE FROM cubes WHERE id = 123;

-- Exit
\q
```

**Always double-check a WHERE clause before running DELETE or UPDATE on production data.**
There is no undo.

---

## Incident Checklist

**Use this when the app is down or something is badly broken.**

1. **Check if Cloud Run is up:**

   ```powershell
   gcloud run services describe cube-foundry-api --region northamerica-northeast1 --format="value(status.conditions)"
   ```

   Look for `Ready: True`. If it says `False`, the backend is down.

2. **Check the latest revision:**

   ```powershell
   gcloud run revisions list --service cube-foundry-api --region northamerica-northeast1 --limit=3
   ```

   Note which revision is serving. Is it the one you just deployed, or an unexpected one?

3. **Check error logs:**

   ```powershell
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=cube-foundry-api AND severity>=ERROR" --limit=20 --order=desc --format="value(timestamp,textPayload)"
   ```

   Common errors to look for:
   - `connection refused` → Cloud SQL not connecting (check the `--add-cloudsql-instances` flag was included in the deploy)
   - `password authentication failed` → `DATABASE_URL` secret is wrong or missing
   - `module not found` → a pip dependency is missing from `requirements.txt`
   - `column X does not exist` → you added a model column but forgot to run the migration SQL

4. **If a bad deploy broke things, roll back immediately:**

   ```powershell
   gcloud run revisions list --service cube-foundry-api --region northamerica-northeast1
   # pick the last known-good revision name, then:
   gcloud run services update-traffic cube-foundry-api --region northamerica-northeast1 --to-revisions REVISION_NAME=100
   ```

5. **Check that the frontend is pointing at the right backend URL:**
   In `front_end/src/api/client.ts`, verify `baseURL` matches your Cloud Run service URL.
   If you accidentally rebuilt without the correct URL, redeploy the frontend.

6. **Check Firebase Hosting is serving the latest build:**
   Go to https://console.firebase.google.com → Cube Foundry project → Hosting → check the
   latest release timestamp matches when you last deployed.

---

## Routine Maintenance Tasks

### See your monthly GCP cost estimate

Go to https://console.cloud.google.com → **"Billing"** → **"Reports"**. Filter to the current
month. Cloud Run and Cloud SQL are the main cost drivers. Cloud Run scales to zero when idle
so cost is near zero with light usage. Cloud SQL charges ~$7–10/month even when idle (minimum
instance size).

### Check Cloud SQL storage usage

```powershell
gcloud sql instances describe cube-foundry-db --format="value(settings.dataDiskSizeGb,settings.dataDiskType)"
```

If you're approaching the storage limit, you can expand it in the GCP Console under
**SQL → cube-foundry-db → Edit → Storage**.

### Check if you're on the latest Cloud Run image

```powershell
gcloud run services describe cube-foundry-api `
  --region northamerica-northeast1 `
  --format="value(spec.template.spec.containers[0].image)"
```

This prints the image URI currently running. The tag should be `latest`.

### Keep dependencies updated

Before any rebuild, check for outdated packages:

```powershell
cd back_end
pip list --outdated
```

And for the frontend:

```powershell
cd front_end
npm outdated
```

Update carefully — test locally before rebuilding and deploying.
