# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


def literal(value):
    return {"type": "literal", "children": [], "value": value}


def identifier(name):
    return {"type": "identifier", "children": [], "value": name}


def path_identifier(left, right):
    return {"type": "path_identifier", "children": [left, right]}


def index_identifier(name, index):
    return {"type": "index_identifier", "children": [name], "value": index}


def sequence(elements):
    return {"type": "sequence", "children": elements}


def or_expression(left, right):
    return {"type": "or_expression", "children": [left, right]}


def and_expression(left, right):
    return {"type": "and_expression", "children": [left, right]}


def not_expression(expression):
    return {"type": "not_expression", "children": [expression]}


def subexpression(expression):
    return {"type": "subexpression", "children": [expression]}


def function_expression(name, arguments):
    return {"type": "function", "children": arguments, "value": name}


def in_expression(left, right):
    return {"type": "in_expression", "children": [left, right]}


def between_expression(left, center, right):
    return {"type": "between_expression", "children": [left, center, right]}


def comparison_expression(name, left, right):
    return {"type": "comparator", "children": [left, right], "value": name}

