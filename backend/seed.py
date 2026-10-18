"""Copy finished projects from a local data dir into the deployed app.

    GOOGLE_CLOUD_PROJECT=<id> python -m backend.seed <project-id> [...]

Project documents go to Firestore (paths made portable), cost ledgers become spend counters, and the
media is uploaded to the bucket with `gcloud storage rsync`. Needs `gcloud auth application-default login`.
"""
import json
import subprocess
import sys

from . import config, store


def main(ids):
    if not config.GCP_PROJECT:
        sys.exit("set GOOGLE_CLOUD_PROJECT")
    bucket = config.env("BUCKET", f"{config.GCP_PROJECT}-mitrafield-data")
    fs = store.FirestoreBackend()
    local = store.FileBackend()
    spend = local._rebuild_spend()
    for pid in ids:
        doc = local.get(pid)
        fs.put(pid, store.encode(doc))
        s = spend.get(f"p:{pid}")
        if s:
            fs.db.collection("spend").document(f"p:{pid}").set(s)
        src = config.DATA / pid
        subprocess.run(["gcloud", "storage", "rsync", "--recursive", "--exclude", r".*/sources/.*|.*costs\.jsonl|.*project\.json",
                        str(src), f"gs://{bucket}/projects/{pid}"], check=True)
        print(f"seeded {pid}: {doc.get('title')!r}, {len(doc.get('scenes', []))} beats, ${(s or {}).get('total', 0):.2f} recorded", flush=True)
    print(json.dumps({"seeded": list(ids)}))


if __name__ == "__main__":
    main(sys.argv[1:])
