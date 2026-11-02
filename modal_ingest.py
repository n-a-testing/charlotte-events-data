"""Deploy only after charlotte-events-ingest secret exists. Separate from public serving app."""
import subprocess
import modal
from modal_app import image
app=modal.App('charlotte-events-ingestion',image=image)
archive=modal.Volume.from_name('charlotte-event-archive',create_if_missing=True)
@app.function(secrets=[modal.Secret.from_name('charlotte-events-ingest')],volumes={'/root/data':archive},schedule=modal.Cron('0 11 * * *'),timeout=1800,max_containers=1)
def refresh():
    try:
        subprocess.run(['python','/root/pipeline.py'],check=True)
    finally:
        archive.commit()  # archive originals and errors even if parsing/publication fails
