
========================
Streaming Output with S3
========================

The S3 ``GetObject`` operation retrieves the content of an object stored
in S3.  Because this content can be of any type and can be up to 5GB in size,
``botocore`` handles this output in a different way than normal request
data.

Here's a simple example that retrieves an object from S3::

    import botocore.session

    session = botocore.session.get_session()
    s3 = session.get_service('s3')
    operation = s3.get_operation('GetObject')
    endpoint = s3.get_endpoint('us-east-1')
    http_response, response_data = operation.call(endpoint,
                                                  bucket='test-1357854246',
                                                  key='testcli.txt')

If we look at the ``response_data`` that is returned, we see::

    {u'Body': <requests.packages.urllib3.response.HTTPResponse object at 0x1016f4550>,
    u'LastModified': 'Tue, 26 Feb 2013 17:41:57 GMT',
    u'ContentLength': '26',
    u'ContentType': 'text/plain'}

The ``LastModified``, ``ContentLength``, and ``ContentType`` entries in the
``response_data`` are examples of response data that is returned in HTTP
headers.  ``botocore`` takes care of retrieving those values from the
headers and placing them into the ``response_data``.  The ``Body`` key is
different, though.  The value of this key is a file-like object that you
can read, either in a single operation or incrementally.  This means that
large files do not have to be read entirely into memory and can be handled
efficiently.

To get the actual data::

    my_content = response_data['Body'].read()

Or, to write incrementally to a file::

    buffsize = 1024 * 8
    with open('my_file', 'wb') as f:
        b = response_data['Body'].read(buffsize)
	while b:
	    f.write(b)
	    b = response_data['Body'].read(buffsize)
