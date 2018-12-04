Contributing
============

We work hard to provide a high-quality and useful command line interface, and
we greatly value feedback and contributions from our community. Whether it's a
new feature, correction, or additional documentation, we welcome your pull
requests. Please submit any `issues <https://github.com/aws/aws-cli/issues>`__
or `pull requests <https://github.com/aws/aws-cli/pulls>`__ through GitHub.

This document contains guidelines for contributing code and filing issues.


Contributing Code
-----------------

The list below are guidelines to use when submitting pull requests.
These are the same set of guidelines that the core contributors use
when submitting changes, and we ask the same of all community
contributions as well:

* The SDK is released under the
  `Apache license <http://aws.amazon.com/apache2.0/>`__.
  Any code you submit will be released under that license.
* We maintain a high percentage of code coverage in our unit tests.  As
  a general rule of thumb, code changes should not lower the overall
  code coverage percentage for the project.  In practice, this means that
  **every bug fix and feature addition should include unit tests.**
* Code should follow `pep 8 <https://www.python.org/dev/peps/pep-0008/>`__,
  although if you are modifying an existing module, it is more important
  for the code to be consistent if there are any discrepancies.
* Code must work on ``python2.6``, ``python2.7``, and ``python3.3``,
  ``python3.4`` and higher.
* The AWS CLI is cross platform and code must work on at least Linux, Windows,
  and Mac OS X.  Avoid platform specific behavior.
* If you would like to implement support for a significant feature that is not
  yet available in the AWS CLI, please talk to us beforehand to avoid any duplication
  of effort.  You can file an
  `issue <https://github.com/aws/aws-cli/issues>`__
  to discuss the feature request further.

Reporting Issues
----------------

*  Check to see if there's an existing issue/pull request for the
   bug/feature. All issues are at
   https://github.com/aws/aws-cli/issues and pull reqs are at
   https://github.com/aws/aws-cli/pulls.
*  If there isn't an existing issue there, please file an issue. The
   ideal report includes:

   * A description of the problem/suggestion.
   * The specific AWS CLI commands you are running.  Please include
     debug logs for these commands by appending the ``--debug`` option
     to each command.  Be sure to remove any sensitive information
     from the debug logs.
   * The AWS CLI version you are using ``aws --version``.

The first thing an AWS CLI developer will do is try to reproduce the
issue you are seeing, so try to reduce your issue to the smallest
possible set of steps that demonstrate the issue.  This will lead
to quicker resolution of your issue.
