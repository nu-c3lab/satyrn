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

import copy
import os
import json
import re
from enum import Enum
from typing import Dict, List

from core.api import utils
from core.RingObjects.Ring import Ring
from core.Planning.utils import capitalize_first_only, oxfordcomma
from core.Analysis.AnalysisPlan import AnalysisPlan
from core.Planning.StepExpressor import StepExpressor
from core.Analysis.OperationOntology import OperationOntology
from core.Planning.AnalysisPlanParser import AnalysisPlanParser
from core.Planning.QuestionGenerator import QuestionGenerator
from core.Planning.SQRComposer import SQRComposer
from core.Operations.ArgType import ArgType

class GenerationMode(Enum):
    OneStatementPerRow = 1
    OneStatementPerPlan = 2

class StatementGeneratorTemplateBased:
    def __init__(self,
                 ring: Ring,
                 operation_ontology: OperationOntology,
                 mode: GenerationMode = GenerationMode.OneStatementPerPlan):
        self.ring = ring
        self.operation_ontology = operation_ontology
        self.plan_parser = AnalysisPlanParser(self.operation_ontology)
        self.sqr_composer = SQRComposer(ring, operation_ontology)
        self.mode = mode
        self.step_expressor = StepExpressor(self.ring, self.operation_ontology)
        self.question_generator = QuestionGenerator(self.ring, self.operation_ontology)
        self.plan_parser = AnalysisPlanParser(self.operation_ontology)
        current_directory = os.path.dirname(__file__)
        relative_path = os.path.join('..','Document','Blueprints','base_plan_templates.json')
        p = os.path.normpath(os.path.join(current_directory, relative_path))
        with open(p, 'r') as f:
            self.base_plan_templates = json.load(f)

    def generate_statement(self,
                           base_plan_template_name: str,
                           result: Dict,
                           slot_fillers: Dict,
                           slots_to_ref: Dict,
                           metric_name_filler: str,
                           analysis_plan: AnalysisPlan,
                           filter_steps_for_postfix: Dict[str, AnalysisPlan]) -> str:
        # Get the template for the plan
        base_plan_template = self.base_plan_templates[base_plan_template_name]['statement_template']
        factual_statement = copy.deepcopy(base_plan_template)

        slots_to_fill = re.findall(r'{(?<={)[a-zA-Z]+:\d+}', base_plan_template)
        for slot in slots_to_fill:

            if "{Reference" in slot:
                reference_number = re.findall(r'\d+', slot)
                expressed_step = self.step_expressor.express_step("|" + str(reference_number[0]) + "|", analysis_plan)
                factual_statement = factual_statement.replace(slot, str(expressed_step))

            elif "{Metric" in slot:
                # metric_ref = slots_to_ref[slot]
                # express_ref = self.step_expressor.express_step(metric_ref[0], analysis_plan)
                # factual_statement = factual_statement.replace(slot, str(express_ref))
                factual_statement = factual_statement.replace(slot, metric_name_filler)

            elif 'Result' not in slot and 'Unit' not in slot:
                slot_key = re.findall(r'(?<={)[a-zA-Z]+:\d+', slot)[0]
                factual_statement = factual_statement.replace(slot, str(slot_fillers[slot_key]))

        # Fill in result and unit slots
        result_slots_to_fill = [slot for slot in slots_to_fill if 'Result' in slot or 'Unit' in slot]

        # More than one result (fill in the slots in the <repeat> tags, comma separate the values)
        if result['length'] > 1:

            # Get the string between the <repeat> tags
            statement_segment_to_repeat = re.findall(r'<repeat>(.+?)</repeat>', factual_statement)[0]

            # For each row of results
            all_statement_segments = []
            for result_value_list in result['results']:

                # Make a copy of the string between the <repeat> tags
                statement_segment = copy.deepcopy(statement_segment_to_repeat)

                # Fill in the slots for the current copy
                for slot in result_slots_to_fill:
                    slot_number = int(slot.strip("{}").partition(':')[2])
                    if "Result" in slot:
                        filler = self.get_result_filler(slot_number, result_value_list, result['fieldNames'], analysis_plan)
                        statement_segment = statement_segment.replace(slot, filler)

                    elif "Unit" in slot:
                        filler = self.get_unit_filler(slot_number, result_value_list, result['fieldNames'], analysis_plan, result['units']['results'])
                        statement_segment = statement_segment.replace(slot, filler)

                # Save this segment
                all_statement_segments.append(statement_segment)

            # Replace the original string (including <repeat> tags) in the factual statement with the collection of statements
            factual_statement = factual_statement.replace("<repeat>" + statement_segment_to_repeat + "</repeat>", oxfordcomma(all_statement_segments))

        else:
            # Only one result
            result_value_list = result['results'][0]
            for slot in result_slots_to_fill:
                slot_number = int(slot.strip("{}").partition(':')[2])
                if "Result" in slot:
                    filler = self.get_result_filler(slot_number, result_value_list, result['fieldNames'], analysis_plan)
                    factual_statement = factual_statement.replace(slot, filler)

                elif "Unit" in slot:
                    filler = self.get_unit_filler(slot_number, result_value_list, result['fieldNames'], analysis_plan, result['units']['results'])
                    factual_statement = factual_statement.replace(slot, filler)

        ## Add filters to the factual statements
        # return_step = list(analysis_plan.plan_steps.keys())[-1]
        # step = analysis_plan.plan_steps[return_step]
        # filter_steps_to_add = [ret_arg for ret_arg in step.args if self.operation_ontology.is_boolean_operation(analysis_plan.plan_steps[ret_arg].operation)]
        if filter_steps_for_postfix:
            filter_plan = self.plan_parser.parse_plan_snippet(filter_steps_for_postfix)

            # Get the reference of the final filter step
            final_step_ref = filter_plan.get_leaves()[0]

            # Call the step_expressor to express the filter step in natural language
            filter_statement = "for " + self.step_expressor.express_filter_step(final_step_ref, filter_plan)

            # Add the filter to the factual statement
            if filter_statement:
                if factual_statement.endswith((".", "?", "!")):
                    factual_statement  = factual_statement[0:-1] + " " + filter_statement + factual_statement[-1:]
                else:
                    factual_statement = factual_statement + " " + filter_statement + "."

        # Make sure the first letter of each statement is capitalized
        factual_statement = capitalize_first_only(factual_statement)

        return factual_statement

    def get_result_filler(self,
                          slot_number: int,
                          result: List,
                          field_names: List,
                          analysis_plan: AnalysisPlan) -> str:
        # Pull out the raw value of the desired result from the result dictionary
        answer = str(result[slot_number])
        if len(result) == 1 and answer in ['True', 'False']:
            return 'is' if answer else 'is not'

        # Convert any results that are for an Identifier attribute into the EntityReference for the corresponding ID
        field_dict = utils.entity_from_subquery_name(field_names[slot_number], list(analysis_plan.subplans.keys()))
        if field_dict:
            entity = self.ring.get_entity_by_name(field_dict['entity'])
        if field_dict and entity.reference and ArgType.Identifier in entity.attributes[field_dict['field']].type:
            # If the result to populate is an identifier attribute and the entity has a reference to stick in there
            answer = self.step_expressor.get_reference_values(field_dict['entity'], field_dict['field'], answer, entity.reference)

        return answer

    def get_unit_filler(self,
                        slot_number: int,
                        result: List,
                        field_names: List,
                        analysis_plan: AnalysisPlan,
                        units: List) -> str:
        # Convert any results that are for an Identifier attribute into the EntityReference for the corresponding ID
        field_dict = utils.entity_from_subquery_name(field_names[slot_number], list(analysis_plan.subplans.keys()))
        if field_dict:
            entity = self.ring.get_entity_by_name(field_dict['entity'])
        if field_dict and entity.reference and ArgType.Identifier in entity.attributes[field_dict['field']].type:
            # If the result to populate is an identifier attribute and the entity has a reference to stick in there
            return ""
        elif len(units[slot_number][1]) > 0:
            # Otherwise, if there are units, add the units
            return units[slot_number][1]
        return ""
