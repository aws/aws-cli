
========================
Streaming Input with S3
========================

The S3 ``PutObject`` operation stores the content of an object
in S3.  Because this content can be of any type and can be up to 5GB in size,
``botocore`` handles this output in a different way than normal request
data.

Here's a simple example that stores an object in S3::

    import botocore.session

    session = botocore.session.get_session()
    s3 = session.get_service('s3')
    operation = s3.get_operation('GetObject')
    endpoint = s3.get_endpoint('us-east-1')
    fp = open('my_large_local_file', 'rb')
    http_response, response_data = operation.call(endpoint,
                                                  bucket='test-1357854246',
                                                  key='testcli.txt',
						  body=fp)

If we look at the ``response_data`` that is returned, we see::

    ''

Which makes sense because S3 doesn't return any response data for a
successful ``PutObject`` operation.

If the file-like object passed in as the ``body`` parameter has a ``tell``
and ``seek`` method, ``botocore`` will automatically calculate the
MD5 checksum of the contents and send it as the ``Content-MD5`` header
in the HTTP request.  This MD5 checksum will then be compared to one
computed by S3 on the content it has received.  If the checksums
don't match, it indicates the data has been corrupted in transmission
and S3 will return an error.
