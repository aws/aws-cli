**Example 1: To get the Android SDK for a REST API stage**

The following ``get-sdk`` example gets the Android SDK for the ``dev`` stage of a REST API and saves it to a file. ::

    aws apigateway get-sdk /path/to/android_sdk.zip \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --sdk-type android \
        --parameters groupId='com.mycompany',invokerPackage='com.mycompany.clientsdk',artifactId='Mycompany-client',artifactVersion='1.0.0'

Output::

    {
        "contentType": "application/octet-stream",
        "contentDisposition": "attachment; filename=\"android_2016-02-22_23-52Z.zip\""
    }

**Example 2: To get the IOS SDK for a REST API stage**

The following ``get-sdk`` example gets the iOS SDK for the ``dev`` stage of a REST API and saves it to a file. ::

    aws apigateway get-sdk /path/to/iOS_sdk.zip \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --sdk-type objectivec \
        --parameters classPrefix='myprefix'

Output::

    {
        "contentType": "application/octet-stream",
        "contentDisposition": "attachment; filename=\"objectivec_2016-02-22_23-52Z.zip\""
    }

**Example 3: To get the Javascript SDK for a REST API stage**

The following ``get-sdk`` example gets the JavaScript SDK for the ``dev`` stage of a REST API and saves it to a file. ::

    aws apigateway get-sdk /path/to/javascript_sdk.zip \
        --rest-api-id 1234123412 \
        --stage-name dev \
        --sdk-type javascript

Output::

    {
        "contentType": "application/octet-stream",
        "contentDisposition": "attachment; filename=\"javascript_2016-02-22_23-52Z.zip\""
    }

