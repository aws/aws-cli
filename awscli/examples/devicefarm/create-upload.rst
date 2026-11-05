**To create an upload**

The following ``create-upload`` example creates an upload for an Android app. ::

    aws devicefarm create-upload \
        --project-arn "arn:aws:devicefarm:us-west-2:123456789012:project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name app.apk \
        --type ANDROID_APP

You can get the project ARN from the output of `create-project` or `list-projects`.

Output::

    {
        "upload": {
            "status": "INITIALIZED",
            "name": "app.apk",
            "created": 1503614408.769,
            "url": "https://prod-us-west-2-uploads.s3-us-west-2.amazonaws.com/arn%3Aaws%3Adevicefarm%3Aus-west-2%3A123456789012%3Aproject%3A070fc3ca-c7e1-4471-91cf-d3e4efc50604/uploads/arn%3Aaws%3Adevicefarm%3Aus-west-2%3A123456789012%3Aupload%3A070fc3ca-7ec1-4741-9c1f-d3e044efc506/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222/app.apk?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20170824T224008Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=AKIAEXAMPLEPBUMBC3GA%2F20170824%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Signature=05050370c38894ef5bd09f5d009f36fc8f96fa4bb04e1bba9aca71b8dbe49a0f",
            "type": "ANDROID_APP",
            "arn": "arn:aws:devicefarm:us-west-2:123456789012:upload:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }

Use the signed URL in the output to upload a file to Device Farm::

    curl -T app.apk "https://prod-us-west-2-uploads.s3-us-west-2.amazonaws.com/arn%3Aaws%3Adevicefarm%3Aus-west-2%3A123456789012%3Aproject%3A070fc3ca-c7e1-4471-91cf-d3e4efc50604/uploads/arn%3Aaws%3Adevicefarm%3Aus-west-2%3A123456789012%3Aupload%3A070fc3ca-7ec1-4741-9c1f-d3e044efc506/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222/app.apk?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20170824T224008Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86400&X-Amz-Credential=AKIAEXAMPLEPBUMBC3GA%2F20170824%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Signature=05050370c38894ef5bd09f5d009f36fc8f96fa4bb04e1bba9aca71b8dbe49a0f"

For more information, see `Creating a test run in Device Farm <https://docs.aws.amazon.com/devicefarm/latest/developerguide/how-to-create-test-run.html>`__ in the *AWS Device Farm Developer Guide*.
