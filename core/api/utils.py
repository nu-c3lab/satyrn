'''
This file is part of Satyrn.
Satyrn is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.
Satyrn is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with Satyrn.
If not, see <https://www.gnu.org/licenses/>.
'''

import re
import json

from typing import List, Tuple, Optional, Any, Match

from langchain.docstore.document import Document

def parse_ref_string(ref_str: str) -> Tuple[list, list]:
    """

    :param ref_str:
    :type ref_str:
    :return:
    :rtype: Tuple of two lists
    """
    val_lst = []
    type_lst = []

    idx = 0
    is_attr = False
    val_start_idx = 0

    while idx < len(ref_str):
        if ref_str[idx] == "$":
            if idx > val_start_idx:
                val_lst.append(ref_str[val_start_idx:idx])
                type_lst.append(is_attr)

            is_attr = True
            val_start_idx = idx
        elif ref_str[idx] == "}":

            val_lst.append(ref_str[val_start_idx:idx+1])
            type_lst.append(is_attr)
            is_attr = False
            val_start_idx = idx + 1

        else:
            pass
        idx += 1

    if val_start_idx < len(ref_str):
        val_lst.append(ref_str[val_start_idx:len(ref_str)])
        type_lst.append(is_attr)

    return val_lst, type_lst

def mirror_rel(rel_type: str):
    dct = {
        "o2o": "o2o",
        "m2m": "m2m",
        "o2m": "m2o",
        "m2o": "o2m"
    }
    return dct[rel_type]

def rel_math(init_type: str,
             new_type: str):
    if init_type == "o2o":
        return new_type
    if new_type == "o2o":
        return init_type
    if init_type == "m2m" or new_type == "m2m":
        return "m2m"
    if init_type == "o2m":
        if new_type == "m2o":
            return "m2m"
        elif new_type == "o2m":
            return "o2m"
    elif init_type == "m2o":
        if new_type == "m2o":
            return "m2o"
        elif new_type == "o2m":
            return "NA"

def walk_rel_path(fro,
                  to,
                  rels):
    init_rel = "o2o"
    curr_ent = fro
    for rel in rels:
        if rel.fro == curr_ent:
            curr_rel = rel.type
            curr_ent = rel.to
        elif rel.to == curr_ent and rel.bidirectional:
            curr_rel = mirror_rel(rel.type)
            curr_ent = rel.fro
        else:
            print("Error, not properly formed relationship path")
            return "NA"

        init_rel = rel_math(init_rel, curr_rel)

    if curr_ent != to:
        print("error, not properly formed relationship path")
        return "NA"
    return init_rel


def entity_from_subquery_name(col_name: str,
                              subquery_names: List[str]) -> dict:
    """
    Extracts the entity and associated field from the column name.
    :param col_name:
    :type col_name: str
    :param subquery_names:
    :type subquery_names: List[str]
    :return:
    :rtype: dict
    """

    # We don't want to handle operations at this time
    if col_name.endswith(')'):
        return {}

    attrs = col_name.split("//")
    entity_dict = {}
    for attr in attrs.copy():
        if attr in subquery_names:
            attrs.remove(attr)
        else:
            break
    entity_dict['entity'], entity_dict['field'] = attrs[0:2]
    if len(attrs) > 2:
        for attr in attrs[2:]:
            val, key = attr.split("__")
            entity_dict[key] = val

    return entity_dict

def is_arg_reference(arg: Any) -> bool:
    """
    Checks if the given arg contains a reference of the form "|<num>|".
    :param arg: The argument string to be checked.
    :type arg: str
    :return: True if the arg contains a reference.
    :rtype: bool
    """
    return True if type(arg) == str and re.search(r'\|[\w]+\|', arg) else False

def concatenate_sentences_from_json(input_json_paths: List[str],
                                    output_txt_path: Optional[str] = None) -> str:
    sentences = []
    for json_input_path in input_json_paths:
        with open(json_input_path) as file:
            data = json.load(file)

        for _, sentence_list in data.items():
            for sentence in sentence_list:
                sentences.append(sentence)

    if output_txt_path:
        with open(output_txt_path, 'w+') as file:
            file.write('\n'.join(sentences))
    
    return '\n'.join(sentences)

def create_texts_from_json(input_json_path: str,
                           metadata_name: str) -> List[Document]:
    with open(input_json_path) as file:
        data = json.load(file)

    texts = []
    for metadata_value, factual_statements in data.items():
        for factual_statement in factual_statements:
            texts.append(Document(page_content=factual_statement, metadata={metadata_name: metadata_value}))
    return texts

def contains_date_denomination(column: str) -> Match:
    return re.fullmatch(r'(\w+)(:day|:dayofweek|:month|:onlyday|:onlymonth|:year)', column)
