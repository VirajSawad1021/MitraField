# MitraField architecture

A question goes in; a narrated explainer video comes out. This document covers how the system is
built to run on Google Cloud, why each piece was chosen, and where its limits are.

## Shape

```
                      Firebase Hosting (CDN, static UI, security headers)
                                   │  /api/**  /files/**  rewrite
                                   ▼
┌───────────────────────── Cloud Run: mitrafield-api (public, stateless) ──────────────────────────┐
│  FastAPI. Reads and writes project state, validates, enforces the passcode and spend caps,        │
│  enqueues jobs. Never renders. Scales to zero.   SA: api (Firestore, Tasks enqueue, bucket)       │
└──────────────┬─────────────────────────────────────────────────────────────┬──────────────────────┘
               │ create task                                                 │ read/write
               ▼                                                             ▼
        Cloud Tasks queue ──── OIDC-signed HTTP POST ───►  Firestore  (projects, spend counters)
        (retries, backoff,                                       ▲
         6 parallel jobs)                                        │ transactions
               │                                                 │
               ▼                                                 │
┌───────────────────────── Cloud Run: mitrafield-worker (private) ─────────────────────────────────┐
│  Same image, STUDIO_ROLE=worker. One job per instance (concurrency 1), up to 6 instances.         │
│  Directs, narrates, renders one beat, assembles. Calls Vertex AI as its own service account.      │
│  Runs model-written code in a sandbox (see Security).      SA: worker (Vertex AI, Firestore)      │
└───────────────┬──────────────────────────────────────────────────────────────────────────────────┘
                │ media (clips, audio, stills, final mp4)
                ▼
        Cloud Storage bucket, mounted at /data in both services (no public access)
```

One container image, two services. `STUDIO_ROLE` decides which routes a process serves, so the API
process cannot execute a render even if asked, and the worker is not reachable from the internet.

## Why these choices

| Decision | Alternative considered | Reason |
|---|---|---|
| Cloud Run for compute | GKE, Compute Engine | Scale to zero, per-request billing, no cluster to run. Renders are bursty and short (minutes). |
| Cloud Tasks between API and worker | In-process threads; Pub/Sub; Workflows | Jobs survive restarts and deploys. Per-queue rate limit protects model quota and spend. Retries with backoff. HTTP delivery means the worker is a plain Cloud Run service. Workflows would add a second place to describe the pipeline. |
| Fan-out per beat, fan-in by transaction | One long job per video | Beats render in parallel across instances. No job waits on another. The last beat to finish claims assembly with a Firestore transaction, so assembly runs exactly once even when Cloud Tasks redelivers. |
| Firestore for project state | JSON files on a Cloud Storage mount | A FUSE mount has no cross-instance locking. Firestore transactions make concurrent workers safe and list queries fast. |
| Project stored as one JSON string per document | Native map with sub-collections | Engine parameters contain nested arrays (coordinates, series), which Firestore rejects. A project is tens of KB, far below the 1 MiB limit. |
| Vertex AI with the service account | Gemini API key in Secret Manager | No credential in the container. IAM-scoped, audited, regional. The key remains a local-development option only. |
| Cloud Storage mount for media | Signed URLs and the client library | Engines write files with ffmpeg, Manim and Chromium; a path is the interface they need. |
| Firebase Hosting in front | API serving the UI | CDN caching for the static app, security headers, a stable `web.app` domain. The API can still serve the UI on its own. |

## Request flow: render a video

1. `POST /api/projects/{id}/render` (API). Checks the passcode and the spend cap (429 if over), sets the
   status, enqueues `render_all`.
2. `render_all` (worker). Marks every beat queued, makes sure the cast reference images exist, then enqueues
   one `render_scene` per beat with `then_assemble=true`.
3. `render_scene` (worker, up to 6 at once). Narrates the beat first (so the picture is rendered to the exact
   audio length), plans, renders with the beat's engine, fits the clip. Every step is cached by content hash.
4. After each beat, `maybe_assemble` flips `rendering scenes → assembling` in one transaction. Exactly one
   caller wins and enqueues `assemble`.
5. `assemble` (worker). Concatenates clips, mixes voice and music to −14 LUFS, writes the mp4.

## Consistency and failure model

* **Delivery is at-least-once, so every job is idempotent.** Results are keyed by a content hash of the inputs;
  re-running a finished job finds its file and returns. Tested: redelivering the last beat's job three times
  assembles once.
* **State changes are transactions.** `store.mutate` is a read-modify-write transaction with jittered backoff on
  contention. Tested against the Firestore emulator with concurrent writers.
* **A job that fails deterministically is not retried.** The worker records the failure on the project and returns
  200, so Cloud Tasks does not re-run (and re-bill) it. Infrastructure failures (instance killed, deadline) return
  no response and *are* retried.
* **A job that dies silently cannot leave a spinner forever.** Anything busy and untouched for longer than a job can
  run (dispatch deadline plus margin) is failed with a clear message the next time someone reads the project.
* **Engine failures degrade, they do not abort.** A beat whose engine fails shows a title card and records why.
  A refused spend cap is the exception: it stops the work instead of being hidden by a fallback.

| Failure | Behaviour |
|---|---|
| Worker instance killed mid-render | Task is redelivered, cached steps are skipped, the beat finishes. |
| Gemini 429 or 5xx | Retried with backoff inside the call; then the beat fails with a readable message. |
| Cloud Tasks delivers the same job twice | Idempotent; assembly claim is a transaction. |
| Firestore contention (many beats finishing together) | Transaction retried with jittered backoff, up to 12 attempts. |
| Spend cap reached | API answers 429 up front; a running job stops at its next model call. |
| Bad deploy | Canary revision gets no traffic until its gate passes; the previous revision keeps serving. |

## Security model

* **Public surface:** only the API service. Browsing is open (it is a demo); every write needs the passcode,
  compared in constant time. Project ids are 10 hex characters and validated on every route, so a path cannot
  leave the data directory. Uploaded sources and state files are never served.
* **Worker is private.** Only the Cloud Tasks service account (and the deploy gate) hold `run.invoker`. The OIDC
  token is verified again in the app, so the endpoint stays safe if the service is ever exposed by mistake.
* **Least privilege, one service account per role.** API: Firestore, enqueue, bucket. Worker: Vertex AI, Firestore,
  bucket. Tasks: may only invoke the worker. Deploy: build and release, no access to data or models.
* **No keys anywhere.** Vertex AI and Firestore use the runtime identity. GitHub Actions deploys through Workload
  Identity Federation, bound to this repository; nothing is stored in GitHub. The passcode is in Secret Manager.
* **Model-written code is untrusted.** The Manim engine runs Python that Gemini wrote, steered by uploaded files.
  It gets: a static allow-list (imports, builtins, attributes, file-reading mobjects); a clean environment with no
  secrets; its own process group (a timeout kills LaTeX and ffmpeg too); and, where the kernel allows it, an empty
  network namespace, which also removes the metadata server. The residual risk where namespaces are unavailable is
  stated in `backend/sandbox.py` and logged at startup (`net_isolated`). The HTML/SVG engine blocks all network in
  headless Chromium.
* **Spend is bounded twice.** A per-project and a per-day cap are checked before every billable call (counters in
  Firestore, cached a few seconds), and a Cloud Billing budget alerts at 50, 90 and 100 percent.
* **Container:** non-root user, no API key in the image, pinned dependencies, Dependabot for actions, pip, npm and
  Docker.

## Observability

* One JSON log line per event with Cloud Logging fields (`severity`, `message`) plus `task`, `pid`, `sid`, `seconds`.
  Filter a whole render with `jsonPayload.pid="…"`.
* `/healthz` (liveness), `/readyz` (the store answers), and the worker's `/internal/selftest` (a real Firestore round
  trip and a real model call as the worker identity) which the deploy gate calls before shifting traffic.
* Every billable call is priced from Google's published rates and recorded per project; the studio shows the total.

## Delivery

* **CI** (every PR and branch push): ruff, the test suite (including Firestore tests on the emulator), web lint,
  type-check and build, shellcheck on the deploy scripts, workflow lint, and a container build with a contract check
  (non-root, ffmpeg, Manim, Chromium present, app imports).
* **CD** (every push to main, after CI): Cloud Build builds the image with layer caching; the worker is deployed as
  a no-traffic canary, gated by its selftest, then promoted; the API likewise gated by `/readyz` and `/api/meta`;
  then the static UI is released to Firebase Hosting and checked through the Hosting domain. Deploys never overlap.
* **Infrastructure** is created by `deploy/bootstrap.sh`, idempotent and reviewable. (Terraform would be the next step
  if more environments appear.)

## Limits, stated honestly

* A beat is one task and one Firestore transaction stream per project document. Hundreds of beats finishing in the
  same second on a single project would contend; the queue caps parallelism at six, which is well within range.
* A single Firestore document holds a project. Projects are small; a long video of a hundred beats is still under
  100 KB.
* Cloud Tasks caps an HTTP job at 30 minutes. A beat takes minutes; Veo is the longest at a few.
* The network-namespace layer of the sandbox depends on the runtime. See Security.
* Voice cloning (OmniVoice) is a local option only; deployed narration is Gemini TTS. See `docs/SPEC.md` for the
  GPU service design if the cloned voices are needed in production.
* The demo is public-read by design; add Firebase Authentication to make projects private per user.
