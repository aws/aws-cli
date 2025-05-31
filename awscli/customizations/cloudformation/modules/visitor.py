# Copyright 2012-2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""
Visitor pattern for recursively modifying all elements in a dictionary.
"""

from collections import OrderedDict


class Visitor:
    """
    This class implements a visitor pattern, to run a function on
    all elements of a template or subset.

    Example of a visitor that replaces all strings:

        v = Visitor(template_dict)
        def vf(v):
            if isinstance(v.d, string) and v.p is not None:
                v.p[v.k] = "replacement"
        v.vist(vf)
    """

    def __init__(self, d, p=None, k=""):
        """
        Initialize the visitor with a dictionary. This can be the entire
        template or a subset.

        :param d A dict or OrderedDict
        :param p The parent dictionary (default is None for the template)
        :param k the key for d (p[k] = d) (default is "" for the template)
        """
        self.d = d
        self.p = p
        self.k = k

    def __str__(self):
        return f"d: {self.d}, p: {self.p}, k: {self.k}"

    def visit(self, visit_func):
        """
        Run the specified function on all nodes.

        :param visit_func A function that accepts a Visitor
        """

        def walk(visitor):
            visit_func(visitor)
            if isinstance(visitor.d, (dict, OrderedDict)):
                for k, v in visitor.d.copy().items():
                    walk(Visitor(v, visitor.d, k))
            if isinstance(visitor.d, list):
                for i, v in enumerate(visitor.d):
                    walk(Visitor(v, visitor.d, i))

        walk(self)
