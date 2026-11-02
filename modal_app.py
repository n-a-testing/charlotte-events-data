import subprocess
from pathlib import Path
import modal
ROOT=Path(__file__).parent
image=modal.Image.debian_slim(python_version='3.13').pip_install_from_requirements(str(ROOT/'requirements.txt'))
# Read-only publishable configuration. No privileged ingestion credential is bundled.
image=image.env({'SUPABASE_URL':'https://spmwoqrgyjilbivzodxw.supabase.co','SUPABASE_PUBLISHABLE_KEY':'sb_publishable_tRll82_bbG7_XbYCvFgMqQ_0iR6liu7','MPLCONFIGDIR':'/tmp/matplotlib'})
for name in ['dashboard.py','storage.py','pipeline.py','tagging.py','analysis.py','recommend.py','api.py']:
    image=image.add_local_file(ROOT/name,'/root/'+name)
app=modal.App('charlotte-events-data',image=image)
@app.function(cpu=1,memory=1024,max_containers=2,timeout=600)
@modal.concurrent(max_inputs=100)
@modal.web_server(8000)
def dashboard():
    subprocess.Popen(['streamlit','run','/root/dashboard.py','--server.port=8000','--server.address=0.0.0.0','--server.headless=true','--browser.gatherUsageStats=false'])
@app.function(cpu=1,memory=512,max_containers=2)
@modal.asgi_app()
def api():
    from api import app as application
    return application
