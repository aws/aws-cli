==========================
Building The Documentation
==========================

Before building the documentation, make sure you have Python 3.7,
the awscli, and all the necessary dependencies installed.  You can
install dependencies by using the requirements-docs.txt file at the
root of this repo::

    pip install -r requirements-docs.txt

The process for building the documentation is:

* Run ``make html`` which will build all of the HTML documentation
  into the ``build/html`` directory.

* Run ``make man`` which will build all of the man pages into
  ``../doc/man/man1``.  These files are included in the source
  distribution and installed by ``python setup.py install``.

* Run ``make text`` which will build all of the text pages that
  are used for interactive help on the Windows platform.  These files
  are included in the source distribution and installed by
  ``python setup.py install``.

You can perform all of these tasks by running ``make all`` in this
directory.  If you have previously built the documentation and want
to regenerate it, run ``make clean`` first.





* This is my Answer for this documentation i tried this solution using some other Ai tools to leverage my work :

It seems like you're encountering an issue with the AWS SDK for Ruby when using the describe_security_groups method. The error message indicates an incompatibility between the group_names and filters options.

The issue appears to arise when you provide both group_names and filters options in the describe_security_groups call. The error message suggests that the provided security group name (group_name) does not exist in the default VPC.

It's important to note that the AWS API documentation indicates that group_ids is a required field if you are not in the default VPC. However, you've observed that this is not the case in your scenario.

This discrepancy between the documented behavior and the actual behavior you're experiencing could indeed indicate a bug in the AWS SDK for Ruby. It might be worth checking the AWS SDK for Ruby's issue tracker or forums to see if others have reported similar issues. Additionally, reaching out to AWS support could provide further insights or assistance in resolving this issue.

In the meantime, you might consider adjusting your code to either use group_ids instead of group_names or to remove the group_names option altogether if it's not necessary for your use case. This might help to work around the issue until a fix is available.
