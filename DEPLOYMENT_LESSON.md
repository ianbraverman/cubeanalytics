# Cube Foundry — Google Cloud Deployment Lesson

> Work through this file top to bottom. Every section explains the concept first,
> then gives you the exact command or UI steps to complete it. Do NOT skip ahead.
> Each phase depends on the one before it.

---

## Architecture: What We're Building

Before writing a single command, understand what the finished system looks like:

```
[User's Browser]
       |
       |--- loads React app from ---> Firebase Hosting (Google CDN, free)
       |
       |--- makes API calls to -----> Cloud Run (your FastAPI backend, containerized)
                                            |
                                            |--- reads secrets from ---> Secret Manager
                                            |
                                            |--- connects to DB via --> Cloud SQL (PostgreSQL)
                                                 (using Cloud SQL Auth Proxy — no open ports)

Docker images live in: Artifact Registry
Images are built by:   Cloud Build
```

**Why each service:**
| Service | What it does | Why not the alternative |
|---|---|---|
| **Cloud Run** | Runs your backend container | Scales to zero = free when idle. App Engine is always-on ($$$) |
| **Cloud SQL** | Managed PostgreSQL | You don't manage backups, patches, or hardware |
| **Artifact Registry** | Stores Docker images | Modern replacement for deprecated gcr.io |
| **Cloud Build** | Builds the Docker image in GCP | No Docker Desktop required; reproducible builds |
| **Secret Manager** | Stores API keys & DB password | Never in code, never plain text in config |
| **Firebase Hosting** | Serves your React build files | Google's global CDN; free tier; automatic HTTPS |

---

## Prerequisites — Install the Tools

### 1. Google Cloud CLI (`gcloud`)

**Concept:** `gcloud` is the command-line remote control for your entire GCP account. Almost
every GCP operation can be done via `gcloud`. It authenticates using your Google account, so
there are no API key files to manage.

**Install:**

1. Go to: https://cloud.google.com/sdk/docs/install-sdk
2. Under Windows, download and run the **Google Cloud CLI installer**
3. Leave all defaults checked during install
4. At the end, it will open a new terminal and run `gcloud init` — let it finish
5. Open a **new** PowerShell window and verify:

```powershell
gcloud version
```

You should see output like `Google Cloud SDK 515.x.x`. If not, restart your machine.

---

### 2. Docker Desktop

**Concept:** Docker is what creates and runs containers. A container is a self-contained
package of your app + all its dependencies that runs identically everywhere. Your `Dockerfile`
(already created at `back_end/Dockerfile`) defines exactly what goes into your container.

We'll use Cloud Build to build the image in the cloud, but Docker Desktop needs to be installed
locally for later development and testing.

**Install:**

1. Go to: https://www.docker.com/products/docker-desktop/
2. Download **Docker Desktop for Windows**
3. Install and **restart your computer**
4. After restart, open PowerShell and verify:

```powershell
docker --version
```

---

### 3. Firebase CLI

**Concept:** Firebase is Google's mobile/web platform (fully owned by Google, integrated with
GCP). Firebase Hosting is their static file CDN. The Firebase CLI deploys your built React
files to that CDN.

```powershell
npm install -g firebase-tools
firebase --version
```

---

## Phase 1 — Create Your GCP Project

**Concept:** A GCP "Project" is the top-level container for all your cloud resources. It groups
your database, backend, secrets, and images together. It has its own billing account and its
own set of enabled APIs. Think of it as your cloud workspace.

### In GCP Console:

1. Go to https://console.cloud.google.com
2. At the top of the page, click the **project dropdown** (it says "Select a project" or your
   current project name) — it's right next to the Google Cloud logo
3. In the popup, click **"New Project"** (top right of the popup)
4. Fill in:
   - **Project name:** `Cube Foundry`
   - **Project ID:** `cube-foundry-prod` ← this must be globally unique across all of Google.
     If it's taken, try `cube-foundry-prod-2` or add your initials
   - **Organization:** Leave as "No organization"
5. Click **"Create"** and wait ~30 seconds
6. Click the project dropdown again and select **"Cube Foundry"**

**Verify:** The project name should appear in the blue top bar. Every console page you open
from now on is scoped to this project.

### Enable Billing

**Concept:** GCP requires a billing account linked to use most services. The free tier covers
everything we're building for light usage — you won't be charged unless you have significant
traffic. You need billing enabled to unlock the APIs.

1. In the GCP Console search bar at the top, type **"Billing"** and click it
2. Click **"Link a billing account"**
3. Follow the prompts to add a credit card
4. Once done, come back to the project and continue

---

## Phase 2 — Authenticate the CLI and Enable APIs

### Authenticate gcloud with your Google account:

```powershell
gcloud auth login
```

A browser window opens. Log in with the same Google account you used for the GCP Console.
When done, return to the terminal — you'll see `You are now logged in as [your@email.com]`.

### Set your project as the default:

```powershell
gcloud config set project cube-foundry-prod
```

Replace `cube-foundry-prod` with your actual Project ID if you used a different one.
From now on, every `gcloud` command targets this project automatically.

### Enable the required APIs:

**Concept:** Every GCP service has an API. By default, all APIs are disabled for new projects —
this is a security and billing control. You explicitly opt in to each service you want to use.

```powershell
gcloud services enable `
  run.googleapis.com `
  sqladmin.googleapis.com `
  artifactregistry.googleapis.com `
  cloudbuild.googleapis.com `
  secretmanager.googleapis.com `
  firebase.googleapis.com
```

**What each one is:**

- `run.googleapis.com` — Cloud Run (your backend)
- `sqladmin.googleapis.com` — Cloud SQL (your database)
- `artifactregistry.googleapis.com` — stores Docker images
- `cloudbuild.googleapis.com` — builds your Docker image
- `secretmanager.googleapis.com` — stores passwords and API keys
- `firebase.googleapis.com` — Firebase Hosting (frontend)

This takes about 1-2 minutes. You'll see each API confirmed as enabled.

### Verify in GCP Console:

1. Search **"APIs & Services"** → click **"Enabled APIs & services"**
2. You should see all 6 APIs listed

---

## Phase 3 — Create an Artifact Registry Repository

**Concept:** When Cloud Build compiles your Dockerfile into an image, that image needs a place
to live before Cloud Run can pull it. **Artifact Registry** is Google's private container
registry — like a private Docker Hub that only your GCP project can access. Every build
creates a new versioned image here. You can roll back to any previous image if needed.

### In GCP Console:

1. Search **"Artifact Registry"** in the top search bar → click it
2. Click **"Create Repository"**
3. Fill in:
   - **Name:** `cube-foundry-repo`
   - **Format:** Docker
   - **Mode:** Standard
   - **Location type:** Region
   - **Region:** `northamerica-northeast1` (use this same region for everything — it's cheapest) (I did Montreal)
   - **Encryption:** Google-managed encryption key (default)
4. Click **"Create"**

### Authorize your local Docker to push to this registry:

```powershell
gcloud auth configure-docker northamerica-northeast1-docker.pkg.dev
```

**What this does:** Updates your local Docker config to use your Google credentials whenever
it communicates with `northamerica-northeast1-docker.pkg.dev`. You only ever run this once per machine.

---

## Phase 4 — Create a Dedicated Service Account

**Concept:** A **Service Account** is an identity for a non-human process (your running app)
rather than a human user. Cloud Run uses a service account to authenticate when it needs to
access other GCP services (like reading a database password from Secret Manager).

**Best practice — Principle of Least Privilege:** Only give your app the exact permissions it
needs, and nothing more. We create a dedicated service account for this app instead of using
the default one, which has broader permissions. If your app were ever compromised, the attacker
would only have the limited permissions you defined here.

Your backend needs:

- Access to Cloud SQL (to connect to the database)
- Access to Secret Manager (to read the DB password and API keys)
- Access to Artifact Registry (to pull the Docker image when starting)

### Create the service account:

```powershell
gcloud iam service-accounts create cube-foundry-sa `
  --display-name="Cube Foundry Backend Service Account"
```

### Grant it the Cloud SQL Client role:

**Concept:** IAM (Identity and Access Management) roles are bundles of permissions. The
`cloudsql.client` role allows connecting to Cloud SQL via the Auth Proxy — nothing more.

```powershell
gcloud projects add-iam-policy-binding cube-foundry-prod `
  --member="serviceAccount:cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com" `
  --role="roles/cloudsql.client"
```

### Grant it the Secret Manager Secret Accessor role:

```powershell
gcloud projects add-iam-policy-binding cube-foundry-prod `
  --member="serviceAccount:cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com" `
  --role="roles/secretmanager.secretAccessor"
```

### Grant it the Artifact Registry Reader role:

```powershell
gcloud projects add-iam-policy-binding cube-foundry-prod `
  --member="serviceAccount:cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com" `
  --role="roles/artifactregistry.reader"
```

### Verify in GCP Console:

1. Search **"IAM & Admin"** → click **"Service Accounts"**
2. You should see `cube-foundry-sa@cube-foundry-prod.iam.gserviceaccount.com` listed

---

## Phase 5 — Create the Cloud SQL Database

**Concept:** **Cloud SQL** is Google's fully managed relational database service. "Managed"
means Google handles OS patches, database version upgrades, automated backups, and hardware
failures. You just connect to it like a normal PostgreSQL server.

The key security feature: your Cloud Run backend connects via the **Cloud SQL Auth Proxy**,
which is a secure tunnel that GCP automatically provides when you attach an instance to Cloud Run.
This means NO public IP exposure, NO firewall rules, NO SSL certificate management — the proxy
handles all of that.

### In GCP Console:

1. Search **"SQL"** → click **Cloud SQL**
2. Click **"Create Instance"**
3. Choose **PostgreSQL** → click **"Choose PostgreSQL"**
4. Fill in the form:
   - **Instance ID:** `cube-foundry-db`
   - **Password:** Create a strong password for the `postgres` user.
     Example: `CubeF0undry$2024!` — write it down somewhere safe right now.
   - **Database version:** PostgreSQL 15
   - **Cloud SQL edition:** Enterprise (only option shown)
   - **Preset:** Click "Development" ← IMPORTANT. The default "Production" preset
     costs $200+/month. Development is ~$8/month. (I did sandbox cause even cheaper)
   - **Machine configuration:** `db-f1-micro` (1 shared vCPU, 614 MB RAM)
   - **Region:** `northamerica-northeast1` ← must match your Cloud Run region
   - **Zonal availability:** Single zone (Multi-zone is for redundancy, costs double)
   - **Storage:** 10 GB SSD. Uncheck **"Enable automatic storage increases"** to prevent
     surprise bills.
5. Click **"Create Instance"** — this takes 3-5 minutes to provision.

### After the instance is ready — create the database:

1. Click on your instance `cube-foundry-db` to open it
2. In the left sidebar, click **"Databases"**
3. Click **"Create Database"**
4. Name: `cube_foundry`
5. Click **"Create"**

### Copy your Connection Name:

On the instance **Overview** page, find **"Connection name"** on the right side panel.
It looks exactly like this:

```
cube-foundry-prod:northamerica-northeast1:cube-foundry-db (this is the name)
```

**Write this down.** You will use it in the Cloud Run deploy command and in your DATABASE_URL.

---

## Phase 6 — Store Secrets in Secret Manager

**Concept:** Never put passwords or API keys in plain text anywhere — not in your code, not in
a config file checked into git, not as raw environment variables visible in the Cloud Run console.

**Secret Manager** is GCP's encrypted vault. Secrets are versioned (you can add new versions and
roll back). Cloud Run can reference a secret by name and automatically injects it as an environment
variable at runtime — the value never appears in your container image or deployment config.

The pattern `DATABASE_URL=DATABASE_URL:latest` in the deploy command means:
"Inject the latest version of the secret named DATABASE_URL as the env var DATABASE_URL."

### Build your DATABASE_URL connection string:

The format for Cloud SQL via the Auth Proxy uses Unix sockets:

```
postgresql://postgres:YOUR_PASSWORD@/cube_foundry?host=/cloudsql/cube-foundry-prod:northamerica-northeast1:cube-foundry-db
```

Replace:

- `YOUR_PASSWORD` → the password you set in Phase 5
- `cube-foundry-prod:northamerica-northeast1:cube-foundry-db` → your actual connection name from Phase 5

### Create the DATABASE_URL secret:

Paste your full connection string into this command (replace the entire `postgresql://...` part):

```powershell
$dbUrl = "postgresql://postgres:YOUR_PASSWORD@/cube_foundry?host=/cloudsql/cube-foundry-prod:northamerica-northeast1:cube-foundry-db"
echo $dbUrl | gcloud secrets create DATABASE_URL --data-file=-
```

### Create the GEMINI_API_KEY secret:

Get your key from https://aistudio.google.com/apikey if you don't have it.

```powershell
$geminiKey = "YOUR_GEMINI_API_KEY_HERE"
echo $geminiKey | gcloud secrets create GEMINI_API_KEY --data-file=-
```

### Create the ALLOWED_ORIGINS secret (placeholder for now — updated after deploy):

```powershell
echo "https://placeholder.web.app" | gcloud secrets create ALLOWED_ORIGINS --data-file=-
```

### Verify in GCP Console:

1. Search **"Secret Manager"**
2. You should see three secrets listed: `DATABASE_URL`, `GEMINI_API_KEY`, `ALLOWED_ORIGINS`
3. Click any one → click **"Versions"** → you'll see "Version 1" in ENABLED state

---

## Phase 7 — Build the Docker Image with Cloud Build

**Concept:** **Cloud Build** is GCP's managed build service. Instead of running `docker build`
on your local machine and uploading a large image over your home internet, you upload just your
source code (much smaller) to Google's servers, and Cloud Build runs the Dockerfile steps on
fast GCP infrastructure, then automatically pushes the resulting image to Artifact Registry.

This is also the foundation of CI/CD — later you can trigger Cloud Build automatically on every
git push.

### Navigate to the back_end directory:

```powershell
cd C:\Users\Ianbr\OneDrive\Desktop\CodingProjects\cubeanalyticssoftware\back_end
```

###

gcloud projects add-iam-policy-binding cube-foundry-prod `  --member="serviceAccount:841885569866-compute@developer.gserviceaccount.com"`
--role="roles/storage.objectViewer"

had to run this also because GCP project initialization quirk — Cloud Build internally uses the Compute Engine default service account for certain operations, and it doesn't have storage access by default on new projects. The two fixes we just applied are correct.

### also had to give a couple other permissions

gcloud projects add-iam-policy-binding cube-foundry-prod `  --member="serviceAccount:841885569866-compute@developer.gserviceaccount.com"`
--role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding cube-foundry-prod `  --member="serviceAccount:841885569866-compute@developer.gserviceaccount.com"`
--role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding cube-foundry-prod `  --member="serviceAccount:841885569866-compute@developer.gserviceaccount.com"`
--role="roles/logging.logWriter"

### Submit the build:

```powershell
gcloud builds submit `
  --tag northamerica-northeast1-docker.pkg.dev/cube-foundry-prod/cube-foundry-repo/cube-foundry-api:latest `
  .
```

**Breaking down this command:**

- `gcloud builds submit` — uploads the current directory to Cloud Build
- `--tag` — the full path where the finished image will be stored in Artifact Registry:
  - `northamerica-northeast1-docker.pkg.dev` — Artifact Registry endpoint for northamerica-northeast1
  - `cube-foundry-prod` — your project ID
  - `cube-foundry-repo` — your repository name from Phase 3
  - `cube-foundry-api` — the image name
  - `latest` — the tag (like a version label)
- `.` — use the `Dockerfile` in the current directory

You'll see build logs scroll by in your terminal. It takes 2-4 minutes.
The last line should say: `SUCCESS`

### Verify in GCP Console:

1. Search **"Artifact Registry"** → click your project's registry
2. Click `cube-foundry-repo`
3. You should see `cube-foundry-api` with a `latest` tag and a recent timestamp

---

## Phase 8 — Deploy to Cloud Run

**Concept:** **Cloud Run** is a fully managed serverless container platform. You give it a
Docker image and it handles everything else: HTTPS certificates, load balancing, health checks,
zero-downtime rolling deploys, and auto-scaling.

The killer feature for a small app: **scale to zero**. When nobody is using your app, Cloud Run
runs zero instances and you pay nothing. When a request arrives, it cold-starts in ~1-2 seconds
and handles it. For small apps with light traffic, your monthly compute cost is literally $0.

### Deploy command:

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

**What every flag means:**
| Flag | What it does |
|---|---|
| `--service-account` | Use your dedicated SA (not the default with broad permissions) |
| `--add-cloudsql-instances` | Attaches the Cloud SQL Auth Proxy for secure DB connections |
| `--set-secrets X=Y:latest` | Injects Secret Manager secret Y as env var X at runtime |
| `--allow-unauthenticated` | Allows public HTTP requests (your frontend needs this) |
| `--port 8080` | The port your app listens on (matches your Dockerfile's CMD) |
| `--min-instances 0` | Scale to zero when idle (saves money) |
| `--max-instances 10` | Cap to prevent runaway cost if you get unexpected traffic |
| `--memory 512Mi` | RAM allocated per instance (FastAPI is light) |

When it completes successfully:

```
Service [cube-foundry-api] revision [cube-foundry-api-00001-xxx] has been deployed
Service URL: https://cube-foundry-api-XXXXXXXXXX-uc.a.run.app
https://cube-foundry-api-841885569866.northamerica-northeast1.run.app
```

**Copy that Service URL. You need it in the next two phases.**

### Test the backend is alive:

Open this URL in your browser (replace with your actual URL):

```
https://cube-foundry-api-XXXXXXXXXX-uc.a.run.app/
```

You should see: `{"message": "Welcome to Cube Foundry API", "version": "0.1.0"}`

### Verify in GCP Console:

1. Search **"Cloud Run"**
2. Click `cube-foundry-api`
3. The **"Logs"** tab shows real-time application logs — bookmark this for debugging

---

## Phase 9 — Initialize the Database Schema

**Concept:** Your Cloud SQL database exists and is running, but it has no tables. Your
`setup_db.sql` file creates all the tables. You need to run it once against the production
database. We'll use **Cloud Shell** — a free Linux terminal that runs directly in your browser
inside Google's network, giving it direct access to your Cloud SQL instance.

### Open Cloud Shell:

1. In the GCP Console top bar, click the **Cloud Shell icon** — it looks like `>_` and is
   in the top-right corner next to the notifications bell
2. A Linux terminal opens at the bottom of your browser window
3. Wait for it to initialize (takes ~10 seconds the first time)

### Upload your SQL file from Cloud Shell:

1. In the Cloud Shell toolbar (above the terminal), click the **three-dot menu (⋮)**
2. Click **"Upload"**
3. Navigate to `back_end/setup_db.sql` on your computer and upload it
4. The file will land in your Cloud Shell home directory

### Connect to the database:

In the Cloud Shell terminal, run:

```bash
gcloud sql connect cube-foundry-db --user=postgres --database=cube_foundry
```

It will ask: `Allowlisting your IP for incoming connection for 5 minutes...`
Then prompt: `Enter password:` — type the password you set in Phase 5.

You'll see the PostgreSQL prompt:

```
cube_foundry=#
```

### Run the schema:

```sql
\i setup_db.sql
```

You should see a list of `CREATE TABLE`, `CREATE INDEX` statements running.

### Verify the tables exist:

```sql
\dt
```

You should see your tables (users, cubes, cards, drafts, etc.) listed.

### Exit PostgreSQL:

```sql
\q
```

---

## Phase 10 — Deploy the Frontend to Firebase Hosting

**Concept:** Your React app (`front_end/src`) is not directly runnable by a browser — it needs
to be compiled. `npm run build` runs the Vite compiler which:

1. Bundles all your TypeScript/TSX files into plain JavaScript
2. Optimizes and minifies the code for production
3. Outputs static files into `front_end/dist/`

**Firebase Hosting** then serves those static files from Google's global CDN. Every user in
the world gets files served from a Google datacenter near them — fast load times everywhere,
automatic HTTPS, and it's free up to 10 GB/month transfer.

### Step 1 — Update the API URL

Open `front_end/.env.production` and replace the placeholder with your Cloud Run URL from
Phase 8:

```
VITE_API_URL=https://cube-foundry-api-XXXXXXXXXX-uc.a.run.app
```

### Step 2 — Build the frontend

```powershell
cd C:\Users\Ianbr\OneDrive\Desktop\CodingProjects\cubeanalyticssoftware\front_end
npm run build
```

This creates a `dist/` folder. Those are the files Firebase will serve.

### Step 3 — Log in to Firebase CLI

```powershell
firebase login
```

A browser window opens. Sign in with the same Google account. Return to the terminal when done.

### Step 4 — Link Firebase to your GCP project

**Concept:** Your GCP project already exists. This command adds Firebase services to that
same project — it does NOT create a new separate project. Everything stays in one place.

```powershell
firebase projects:addfirebase cube-foundry-prod
```

If asked to confirm, type `Y`.

Did this instead on the actual website and did these instructions:
Go to https://console.firebase.google.com
Click "Add project"
At the bottom, click "Add Firebase to a Google Cloud Platform project"
Select cube-foundry-prod from the dropdown
Click through the prompts (accept defaults, no need for Google Analytics)
Wait for it to finish (~30 seconds)

Click "Get started" (or the "Add project" button)
On the "Create a project" screen, look for the dropdown — type cube-foundry-prod or select it from the list (it should appear since it's an existing GCP project)
Click Continue
On the "Google Analytics" screen → click the toggle to disable it (you don't need it), then click Add Firebase
Wait ~30 seconds for it to finish → click Continue

### Step 5 — Initialize Firebase Hosting in the front_end folder

```powershell
cd C:\Users\Ianbr\OneDrive\Desktop\CodingProjects\cubeanalyticssoftware\front_end
firebase init hosting
```

Answer the prompts exactly like this:

- **"Which Firebase project?"** → select `cube-foundry-prod`
- **"What do you want to use as your public directory?"** → type `dist`
- **"Configure as a single-page app (rewrite all URLs to /index.html)?"** → `y`
  (This is critical for React Router — without it, refreshing any URL breaks the app)
- **"Set up automatic builds and deploys with GitHub?"** → `N` (we'll do this manually for now)
- **"File dist/index.html already exists. Overwrite?"** → `N`

### Step 6 — Deploy to Firebase

```powershell
firebase deploy --only hosting
```

When it finishes:

```
Hosting URL: https://cube-foundry-prod.web.app
```

Open that URL. Your full app should load. Try logging in!

---

## Phase 11 — Update CORS with Your Firebase URL

**Concept:** CORS (Cross-Origin Resource Sharing) is a browser security feature. When your
React app (at `cube-foundry-prod.web.app`) makes a request to your backend (at
`cloud-foundry-api-xxx.a.run.app`), those are two different origins. The browser checks that
the backend explicitly allows requests from the frontend's origin. Right now your backend's
`ALLOWED_ORIGINS` secret still says `placeholder` — fix that now.

### Add a new version to the ALLOWED_ORIGINS secret:

```powershell
echo "https://cube-foundry-prod.web.app" | `
  gcloud secrets versions add ALLOWED_ORIGINS --data-file=-
```

**Concept:** Secret Manager uses versions. You never delete the old version — you add a new
one and set it as latest. This means you can always roll back if something goes wrong.

### Redeploy Cloud Run to pick up the updated secret:

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

do full deploy always

Cloud Run does a zero-downtime rolling restart — existing requests finish before the old
instance shuts down.

---

## Phase 12 — Smoke Test Everything

Go through each of these manually in your browser:

- [ ] Open `https://cube-foundry-prod.web.app` — landing page loads
- [ ] Register a new account
- [ ] Log in with that account
- [ ] Create a cube
- [ ] Create a draft event
- [ ] Open your profile page
- [ ] Check that card images load (Scryfall calls go through your backend)

### If something breaks — how to read logs:

In the terminal:

```powershell
gcloud run logs read --service cube-foundry-api --region northamerica-northeast1 --limit 50
```

Or in GCP Console: **Cloud Run** → `cube-foundry-api` → **"Logs"** tab.

Common issues and fixes:
| Symptom | Likely cause | Fix |
|---|---|---|
| Backend 500 errors | DATABASE_URL wrong | Check Phase 6, re-create secret |
| Frontend can't reach backend | CORS blocked | Check Phase 11 |
| "Cold start" slow first load | Cloud Run scaling up | Normal — takes 1-2 seconds |
| Images not loading | Scryfall API being called | Check backend logs |

---

## Phase 13 — Seed Demo Data (Optional)

If you want demo data in production, run the seed script locally but pointed at Cloud SQL.

**To allow your local machine to connect:**

1. GCP Console → **Cloud SQL** → `cube-foundry-db` → **"Connections"** tab
2. Under **"Authorized networks"**, click **"Add a network"**
3. Name: `My IP`; value: your public IP (find it at https://whatismyip.com)
4. Click **"Done"** → **"Save"**

Then in your local terminal with venv active:

```powershell
cd C:\Users\Ianbr\OneDrive\Desktop\CodingProjects\cubeanalyticssoftware\back_end
$env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@YOUR_CLOUD_SQL_PUBLIC_IP/cube_foundry"
python seed_demo.py
```

Your Cloud SQL Public IP is on the instance Overview page under "Connect to this instance".

**When done — go back and remove your IP from Authorized networks** (security best practice).

---

## Phase 14 — Monthly Costs

With everything deployed and light usage:

| Service               | Cost                                                             |
| --------------------- | ---------------------------------------------------------------- |
| Cloud Run             | ~$0 (scales to zero, free tier covers 2M requests/month)         |
| Cloud SQL db-f1-micro | ~$8/month                                                        |
| Artifact Registry     | ~$0.10/month (a few hundred MB storage)                          |
| Firebase Hosting      | Free (10 GB storage, 10 GB transfer/month)                       |
| Secret Manager        | Free (first 6 secrets free, 10,000 access operations free/month) |
| Cloud Build           | Free (120 build-minutes/day free)                                |
| **Total**             | **~$8-10/month**                                                 |

---

## What You Now Know

You just deployed a production web application using:

1. **Containerization** — Docker packages your app so it runs identically everywhere
2. **Container Registry** — Artifact Registry stores versioned images
3. **Managed builds** — Cloud Build compiles images without needing your local machine
4. **Serverless compute** — Cloud Run auto-scales to demand, including zero
5. **Managed database** — Cloud SQL removes ops burden from you
6. **Secrets management** — Secret Manager keeps credentials out of code and configs
7. **IAM & least privilege** — Service accounts with only the permissions they need
8. **CDN hosting** — Firebase Hosting serves static files from a global edge network
9. **Zero-downtime deploys** — Cloud Run rolling restarts

---

## Redeployment Cheat Sheet

Every time you update the backend code:

```powershell
cd back_end
gcloud builds submit --tag northamerica-northeast1-docker.pkg.dev/cube-foundry-prod/cube-foundry-repo/cube-foundry-api:latest .
gcloud run deploy cube-foundry-api --image northamerica-northeast1-docker.pkg.dev/cube-foundry-prod/cube-foundry-repo/cube-foundry-api:latest --region northamerica-northeast1
```

Every time you update the frontend code:

```powershell
cd front_end
npm run build
firebase deploy --only hosting
```
