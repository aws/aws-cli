**To delete an AWS Cost and Usage Report**

The following ``delete-report-definition`` example deletes an AWS Cost and Usage Report. ::

    aws cur delete-report-definition \
        --region us-east-1 \
        --report-name "ExampleReport"

Output::

    {
        "ResponseMessage": "Report ExampleReport deleted successfully."
    }

For more information, see `What are AWS Cost and Usage Reports? <https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html>`__ in the *AWS Data Exports User Guide*.
