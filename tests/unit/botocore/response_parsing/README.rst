======================
Response Parsing Tests
======================

The purpose of this collection of tests it to determine whether the XML
responses from the services are being correctly parsed and transformed
into Python data structures.

Within the ``data`` directory you will find pairs of files, an XML file
and a JSON file using a naming convention of::

    <service_name>-<operation_name>.[xml|json]

Each pair of files represents one test.  The XML file contains the
response sent from the server for that particular request and the JSON
file contains the expected Python data structure created from the XML
response.

The main test is contained in ``test_response_parser.py`` and is
implemented as a nose generator.  Each time through the loop an XML
file is read and passed to a ``botocore.response.XmlResponse``
object.  The corresponding JSON file is then parsed and compared to
the value created by the parser.  If the are equal, the test passes.  If
they are not equal, both the expected result and the actual result are
pretty-printed to stdout and the tests continue.

-----------------
Adding More Tests
-----------------

You can add more tests by simply placing appropriately named XML and JSON
files into the data directory.  Make sure you follow the naming convention
shown above as that is how the generator determines which service and
operation to call.
