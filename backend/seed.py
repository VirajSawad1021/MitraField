"""Copy finished projects from a local data dir into the deployed app.

    GOOGLE_CLOUD_PROJECT=<id> python -m backend.seed <project-id> [...]
    STUDIO_STORE=firestore STUDIO_DATA=<scratch dir> GOOGLE_CLOUD_PROJECT=<id> \\
        python -m backend.seed --voices <dir of voice_clone_prompt_*.pt>        # the channel narrators

Project documents go to Firestore (paths made portable), cost ledgers become spend counters, and the
media is uploaded to the bucket with `gcloud storage rsync`. Needs `gcloud auth application-default login`.
"""
import json
import subprocess
import sys

from . import config, store


# The channel's own narrators. Their voice-clone prompts were built by OmniVoice from the channel's reference
# recordings; the prompt files (not the recordings) are what the voice service needs.
CHANNEL_VOICES = [
    ("Johnny", "c319e078-00eb-4b99-8e3f-6352933204d0",
     "Here is something most people get wrong on the first try. Back in 2015, nobody expected this result. And honestly, neither did I.",
     "acompressor=threshold=-19dB:ratio=3:attack=5:release=130,equalizer=f=3300:t=q:w=1.1:g=3.3,highshelf=f=8000:g=2,atempo=1.08"),
    ("Viraj_v8", "f08990de-b71b-48fb-8da4-466ff71a93de",
     "Learning is an important part of life, every day we learn something new, it can be a new idea, a new skill or a simple fact, step by step.",
     None),
]


def seed_voices(prompts_dir):
    """Register the channel voices from a folder holding voice_clone_prompt_<id>.pt files. Works against the
    configured store, so it seeds a local data dir or, with STUDIO_STORE=firestore and a mounted/synced
    volume, the deployed app. Prompts are written to <DATA>/voices/<name>/prompt.pt."""
    import shutil
    from pathlib import Path

    from .models import VoiceProfile
    for name, omni_id, text, post in CHANNEL_VOICES:
        src = Path(prompts_dir) / f"voice_clone_prompt_{omni_id}.pt"
        if not src.exists():
            print(f"skip {name}: {src} not found")
            continue
        shutil.copy(src, store.vdir(name) / "prompt.pt")
        store.voice_save(VoiceProfile(id=name, name=name.replace("_v", " v").replace("_", " "), reference_text=text, status="ready",
                                      builtin=True, post_filter=post))
        print(f"voice {name}: ready")


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
    if sys.argv[1:2] == ["--voices"]:
        seed_voices(sys.argv[2])
        if config.STORE == "firestore":   # the prompts are media: upload them next to the projects
            subprocess.run(["gcloud", "storage", "rsync", "--recursive", str(config.DATA / "voices"),
                            f"gs://{config.env('BUCKET', f'{config.GCP_PROJECT}-mitrafield-data')}/projects/voices"], check=True)
    else:
        main(sys.argv[1:])
