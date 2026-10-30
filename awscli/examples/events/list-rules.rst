**Example 1: To display a list of all CloudWatch Events rules**

The following ``list-rules`` example displays all CloudWatch Events rules in the region. ::

    aws events list-rules

**Example 2: To display a list of CloudWatch Events rules beginning with a certain string**

The following ``list-rules`` example displays all CloudWatch Events rules in the region that have a name starting with ``Daily``. ::

    aws events list-rules \
        --name-prefix "Daily"
