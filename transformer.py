#!/usr/bin/env python
'''
Transforms an Ansible Dynamic Inventory JSON object, using group/group vars
definitions defined in a Groupsfile.

Reads JSON object from STDIN
Takes a single argument
  - groupsfile_path | The path to the Groupsfile

'''

# Copyright (C) 2016 Manuel Zubieta
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from __future__ import print_function
import parsley
import fnmatch
import json
import argparse
import sys

inventory = json.loads(sys.stdin.read())
cleaned_inventory = {}
if '_meta' in inventory:
    cleaned_inventory['_meta'] = inventory['_meta']
for k, v in inventory.items():
    if type(v) == list:
        cleaned_inventory[k] = {'hosts': v, 'vars': {}}
    else:
        cleaned_inventory[k] = v

grammer = parsley.makeGrammar("""
punctuation = '!' | '@' | '#' | '$' | '%' | '^' | '&' | '"' | '\\'' |
                '*' | '(' | ')' | '-' | '_' | '=' | '`' |
                '~' | '[' | '{' | '}' | ']' | '\\\\' | '|' |
                ';' | ':' | '?' | ',' | '.' | '/' | '<' | '>'

positive_number = <digit+>:ds -> int(ds)
negative_number = '-' positive_number:n -> -n
number = positive_number | negative_number
single_index = '[' number:n ']' -> (n,n)
range_index = '[' number:start ':' number:end ']' -> (start,end)
toend_index = '[' number:start ':]' -> (start,-1)
index = single_index | range_index | toend_index

allowed_name_chars = letterOrDigit | '_' | '.' 
ansible_name_partial = <allowed_name_chars+>:ps -> ps
indexed_name = ansible_name_partial:name index:idx -> (name,idx)

wild_card = '*'
wildcard_front = wild_card ansible_name_partial:x -> '*' + x
wildcard_mid = ansible_name_partial:f wild_card ansible_name_partial:b -> f + '*' + b
wildcard_back = ansible_name_partial:x wild_card -> x + '*'

regex_name = '~' <( punctuation | letterOrDigit)+>:r -> '~' + r

ansible_name = (wildcard_front | wildcard_mid | wildcard_back | indexed_name | ansible_name_partial | regex_name)

op_union = ':' -> 'union'
op_intersection = ':&' -> 'intersection'
op_difference = ':!' -> 'difference'
operation = op_intersection | op_difference | op_union

group_name = '[' ansible_name_partial:g ']' (ws comment)? -> g
grouping_expression = ansible_name:left ( (operation:op grouping_expression:exp -> (op,exp))?:rest -> (left, rest)
                                                                              | -> (left,None))
group = ws group_name:name ws? comments? (grouping_expression:exp (ws comments)? -> exp)*:expressions -> ('group',(name,expressions))

allowed_groupvar_value_chars = letterOrDigit | punctuation | ' ' | '\t'

rest_of_line = <('\\\n' | (~'\n' anything))*>
comment = '#' rest_of_line -> None
comments = (comment ws)*

groupvar_value = <allowed_groupvar_value_chars*>:val -> val
groupvar_name = ansible_name_partial
groupvar_expression = groupvar_name:name '=' groupvar_value:val -> (name,val)
group_var_head = '[' ansible_name_partial:g ':vars]' (ws comment)? -> g
groupvars = group_var_head:gname ws ( comments? groupvar_expression:var (ws comments)? -> var)*:vars -> ('vars',{'name':gname,'vars':vars})

group_file = ws? comments (group|groupvars)+:items -> {'groups':[x[1] for x in items if x is not None and x[0] == 'group'], 'vars':[x[1] for x in items if x is not None and x[0] == 'vars']}
""", {})


def fetch_matching_groups(group_expr):
    sublists, vars = [], {}
    if group_expr.startswith('~'):
        def matches(pattern, test): return re.match(pattern[1:], test)
    else:
        def matches(pattern, test): return fnmatch.fnmatch(test, pattern)
    for k, v in cleaned_inventory.items():
        if matches(group_expr, k):
            sublists.append(v['hosts'])
            vars.update(v['vars'])
    flattened_list = [item for sublist in sublists for item in sublist]
    return {'hosts': set(flattened_list), 'vars': vars}


def process_grouping(grouping):
    lhs, rest = grouping
    if rest is None:
        return lhs
    (operation, (rhs, rest)) = rest

    rhs = fetch_matching_groups(rhs)
    new_lhs_hosts = getattr(lhs['hosts'], operation)(rhs['hosts'])
    new_lhs = {'hosts': new_lhs_hosts, 'vars': lhs['vars']}

    if operation in {'union', 'intersection'}:
        new_lhs['vars'].update(rhs['vars'])

    new_grouping = (new_lhs, rest)
    return process_grouping(new_grouping)


def main(groupingsfile_path):
    parsed_groupsfile = None

    with open(groupingsfile_path, 'r') as f:
        parsed_groupsfile = grammer(f.read()).group_file()
    for group in parsed_groupsfile['vars']:
        if group['name'] not in cleaned_inventory:
            cleaned_inventory[group['name']] = {'hosts': [], 'vars': {}}
        for k, v in group['vars']:
            cleaned_inventory[group['name']]['vars'][k] = v
    for new_group_name, groupings in parsed_groupsfile['groups']:
        result = cleaned_inventory.get(
            new_group_name, {'hosts': [], 'vars': {}})
        result['hosts'] = set(result['hosts'])
        if new_group_name == '_meta':
            raise Exception("group name _meta not allowed")
        for group, pattern in groupings:
            first_grouping = (fetch_matching_groups(group), pattern)
            processed = process_grouping(first_grouping)
            result['hosts'] = result['hosts'].union(processed['hosts'])
            result['vars'].update(processed['vars'])
        result['hosts'] = list(result['hosts'])
        cleaned_inventory[new_group_name] = result
    print(json.dumps(cleaned_inventory))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description="Dynamic Inventory transformer")
    arg_parser.add_argument('Groupingsfile_path',
                            help='the path to your Groupingsfile')
    args = arg_parser.parse_args()
    main(args.Groupingsfile_path)
