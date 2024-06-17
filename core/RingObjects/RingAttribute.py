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

import os
import json
from typing import Dict, Tuple, Union

from .RingObject import RingObject
from core.Operations.ArgType import ArgType

class RingAttribute(RingObject):

    def __init__(self,
                 parent_entity=None):

        # Set default values
        self.result_format = [False, False]

        # Initialize other properties
        self.name = None
        self.nicename = None
        self.isa = None
        self.base_isa = None
        self.type = None
        self.units = None
        self.source_table = None
        self.source_columns = None
        self.source_joins = []

        # a flag to track whether it requires a join
        self.join_required = False
        self.parent_entity = parent_entity

        # Properties for attributes which are metrics
        self.target_value = None

        self.null_handling = None
        self.null_value = None
        self.date_min_granularity = None
        self.date_max_granularity = None
        ## addition of rounding
        '''
            exp of syntax: "rounding":["True", 0]  means 0 decimal rounding--> round to the nearest int
        '''
        self.rounding = None
        self.sig_figs = None

        # Property to specify a plan for retrieving this attribute from the database
        self.access_plan = None

        self.error_set = set()

    def parse(self,
              name: str,
              info: Dict) -> None:
        self.name = name
        self.nicename = info.get('nicename')
        self.isa = info.get('isa')

        # this next one is to separate conceptual type from data type (currency vs float)
        # doesn't matter know but will be useful later when we leverage upper ontology
        self.base_isa = info.get('isa')

        self.units = info.get('units')

        self.type = [ArgType.from_str(t) for t in info.get('type')]
        self._update_types_with_parents()

        self.target_value = info.get('target_value')

        # a flag for the analysis engine to avoid aggregating this value if it's a number
        # more often this is False (or not present/pertinent) and defaults accordingly
        self.preaggregated = info.get("preaggregated", False)

        if 'source' in info:
            source = info['source']
            self.source_table = source.get('table')
            self.source_columns = source.get('columns')
            self.join_required = self.source_table != self.parent_entity["table"]
            self.source_joins = source.get('joins',[])

        if 'metadata' in info:
            md = info['metadata']
            self.description = md.get('description')

        default_path = os.environ.get("SATYRN_ROOT_DIR") + "/" +"core" + "/" + "defaults.json"
        with open(default_path, 'r') as file:
            defaults = json.load(file)
            ##check if the value is set in the ring
            if info.get("nullHandling"):
                self.null_handling = info.get("nullHandling")
            else:
                self.null_handling = defaults.get("null_defaults")[self.base_isa][0]
            if info.get("nullValue"):
                self.null_value = info.get("nullValue")
            else:
                self.null_value = defaults.get("null_defaults")[self.base_isa][1]

            ## rounding
            if self.base_isa in ["float"]: # , "integer"]:
                ##chek if the value is set in the ring
                if info.get("rounding"):
                    self.rounding = info.get("rounding")[0]
                    self.sig_figs = info.get("rounding")[1]
                else:
                    self.rounding = defaults.get("result_formatting")["rounding"][0]
                    self.sig_figs = defaults.get("result_formatting")["rounding"][1]

            if self.base_isa and self.base_isa in ["date", "datetime", "date:year"]:
                if info.get("dateGranularity"):
                    granularity = info.get("dateGranularity")
                else:
                    granularity = defaults.get("date_defaults")[self.base_isa]
                self.date_max_granularity = granularity[1]
                self.date_min_granularity = granularity[0]

        return None

    def construct(self):

        attribute = {}
        self.safe_insert('name', self.name, attribute)
        self.safe_insert('nicename', self.nicename, attribute)
        self.safe_insert('isa', self.isa, attribute)
        self.safe_insert('type', self.type, attribute)

        source = {}
        self.safe_insert('table', self.source_table, source)
        self.safe_insert('columns', self.source_columns, source)

        md = {}
        self.safe_insert('description', self.description, md)

        self.safe_insert('source', source, attribute)
        self.safe_insert('metadata', md, attribute)

        self.safe_insert('nullHandling', self.null_handling, attribute)
        self.safe_insert('nullValue', self.null_value, attribute)
        self.safe_insert('dateMinGranularity', self.date_min_granularity, attribute)
        self.safe_insert('dateMaxGranularity', self.date_max_granularity, attribute)

        return attribute

    def is_valid(self) -> Tuple[bool, Union[str, dict]]:
        if self.name == None:
            self.error_set.add("Ring Attribute 'name' is missing.")
        if self.nicename == None:
            self.error_set.add("Attribute 'nicename' is missing.")
        if self.isa == None:
            self.error_set.add("Ring Attribute 'isa' value missing.")
        if self.type == None:
            self.type.add("Ring Attribute 'type' value missing.")
        if self.source_table == None:
            self.error_set.add("Ring Attribute 'table' is missing.")
        if self.source_columns == None:
            self.error_set.add("Ring Attribute 'column' is missing.")
        ## now we do some imp stuff
        if len(self.error_set) == 0:
            ## No errors!
                ## It will return (True, [])
            return (bool(self.name and self.nicename and self.isa and self.source_table and self.source_columns), {})
        else:
            ## will return a string of errors
            errorString = ' '.join(self.error_set)
            return (False, errorString)

    def _update_types_with_parents(self) -> None:

        # This is an attribute, and therefore should always have this as one of its types.
        self.type.append(ArgType.Attribute)

        # Get the parents for each of the remaining types that were specified in the ring
        new_types = []
        for arg_type in self.type:
            if arg_type == ArgType.StartDate or arg_type == ArgType.EndDate:
                new_types.append(ArgType.Datetime)
            # if arg_type == ArgType.ComparativeMetric or arg_type == ArgType.DiagnosticMetric:
            #     new_types.append(ArgType.Metric)

        self.type.extend(new_types)
        return None
