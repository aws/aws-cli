import json
import os
import subprocess
import sys

RST_GENERATION_SCRIPT = 'htmlgen'
script_path = os.path.join(os.path.dirname(__file__), RST_GENERATION_SCRIPT)
_ref_dir = os.path.join(os.path.dirname(__file__), 'reference')

# conf.py imports this module on every sphinx-build invocation. Without this
# guard, a single build that runs sphinx-build more than once (e.g. `make
# html man text`, or a sharded build that invokes sphinx-build once per
# batch of services) regenerates the entire RST tree for every service from
# scratch on every single invocation, regardless of what that invocation
# actually needs to read. `make clean` removes `reference/`, so a real
# fresh build still regenerates normally; set FORCE_RST_REGEN=1 to force a
# regeneration even if `reference/` already has content.
if os.environ.get('FORCE_RST_REGEN') or not os.path.isdir(_ref_dir) or not os.listdir(_ref_dir):
    os.environ['PATH'] += ':.'
    rc = subprocess.call("python " + script_path, shell=True, env=os.environ)
    if rc != 0:
        sys.stderr.write("Failed to generate documentation!\n")
        sys.exit(2)
