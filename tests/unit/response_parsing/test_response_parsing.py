import os
import glob
import json
import pprint
import botocore.session
from botocore.response import XmlResponse


def check_dicts(d1, d2):
    if d1 != d2:
        pprint.pprint(d1)
        print '-' * 40
        pprint.pprint(d2)
    assert d1 == d2


def test_response_parsing():
    session = botocore.session.get_session()
    xml_files = glob.glob('data/*.xml')
    service_names = {os.path.split(fn)[1].split('-')[0] for fn in xml_files}
    for service_name in service_names:
        service = session.get_service(service_name)
        service_xml_files = glob.glob('data/%s-*.xml' % service_name)
        for xmlfile in service_xml_files:
            dirname, filename = os.path.split(xmlfile)
            basename = os.path.splitext(filename)[0]
            jsonfile = os.path.join(dirname, basename + '.json')
            sn, opname = basename.split('-', 1)
            operation = service.get_operation(opname)
            r = XmlResponse(operation)
            fp = open(xmlfile)
            xml = fp.read()
            fp.close()
            r.parse(xml)
            fp = open(jsonfile)
            data = json.load(fp)
            fp.close()
            check_dicts.description = basename
            yield check_dicts, r.get_value(), data


if __name__ == '__main__':
    test_all()
