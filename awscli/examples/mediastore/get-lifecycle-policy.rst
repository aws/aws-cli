**To view an object lifecycle policy**

The following ``get-lifecycle-policy`` example displays the object lifecycle policy attached to the specified container. ::

    aws mediastore get-lifecycle-policy \
        --container-name LiveEvents

Output::

    {
        "LifecyclePolicy": "{\"rules\":[{\"definition\":{\"path\":[{\"prefix\":\"Football/\"},{\"prefix\":\"Baseball/\"}],\"days_since_create\":[{\"numeric\":[\">\",28]}]},\"action\":\"EXPIRE\"}]}"
    }
