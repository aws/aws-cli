**To get the status of a change to resource record sets**

The following ``get-change`` example gets the status and other information about the ``change-resource-record-sets`` request that has an ``Id`` of ``/change/CWPIK4URU2I5S``. ::

    aws route53 get-change \
        --id /change/CWPIK4URU2I5S

Output::

    {
        "ChangeInfo": {
            "Id": "/change/CWPIK4URU2I5S",
            "Status": "INSYNC",
            "SubmittedAt": "2014-04-01T18:47:10.123Z"
        }
    }

