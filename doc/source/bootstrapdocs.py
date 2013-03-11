import json
import os

JSON_DATA_FILE = 'aws_man_pages.json'
RST_GENERATION_SCRIPT = 'rstgen'

data_path = os.path.join(os.path.dirname(__file__),
                         JSON_DATA_FILE)
if not os.path.exists(data_path):
    script_path = os.path.join(os.path.dirname(__file__),
                               RST_GENERATION_SCRIPT)
    os.environ['PATH'] += ':.'
    status = os.spawnlpe(os.P_WAIT, script_path, os.environ)
fp = open(JSON_DATA_FILE)
man_pages = json.load(fp)
fp.close()
