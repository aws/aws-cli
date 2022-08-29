**To list the available widgets**

The following ``command-name`` example lists the available widgets in your AWS account. ::

    aws awesomeservice command-name \
        --parameter1 file://myfile.json \
        --parameter2 value2 \
        --lastparam lastvalue

Contents of ``myfile.json``::

    {
        "somekey": "some value"
    }

Output::

    {
        "All of the output": "goes here",
        "More Output": [
            { "arrayitem1": 1 },
            { "arrayitem2": 2 }
        ]
        "Each indent": "Must be 4 spaces"
    }

For more information, see `This is the topic title <https://example.com>`__ in the *Name of your guide*.
