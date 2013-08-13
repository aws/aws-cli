import json
import os
import subprocess

RST_GENERATION_SCRIPT = 'htmlgen'
script_path = os.path.join(os.path.dirname(__file__),
                           RST_GENERATION_SCRIPT)
os.environ['PATH'] += ':.'
#status = os.spawnlpe(os.P_WAIT, script_path, os.environ)
subprocess.call("python "+script_path, shell=True, env=os.environ)
