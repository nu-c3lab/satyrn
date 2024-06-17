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
from typing import List, Dict, Tuple
from copy import deepcopy
from collections import defaultdict

from core.RingObjects.Ring import Ring
from core.Analysis.OperationOntology import OperationOntology
from core.Operations.ArgType import ArgType
from core.Analysis.AnalysisStep import AnalysisStep
from core.api.utils import is_arg_reference
from core.Planning.StepExpressor import StepExpressor

class SQRComposer:
    def __init__(self,
                 ring: Ring,
                 operation_ontology: OperationOntology):
        self.ring = ring
        self.operation_ontology = operation_ontology
        self.step_expressor = StepExpressor(self.ring, self.operation_ontology)
        self.template_token_matcher = '({([^}]+)})'
        self.template_token_matcher_regex = re.compile(self.template_token_matcher)

        self.alphabet_idx = 0
        self.alphabet_multiplier = 1

    def get_next_ref_letter(self) -> str:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        letter = alphabet[self.alphabet_idx] * self.alphabet_multiplier

        # Update the alphabet index
        self.alphabet_idx += 1

        # Update the alphabet multiplier
        if self.alphabet_idx == len(alphabet):
            self.alphabet_multiplier += 1
            self.alphabet_idx = 0

        return letter

    def compose(self,
                    base_plan: Dict[str, AnalysisStep],
                    access_plans: Dict[str, Dict[str, AnalysisStep]]) -> Tuple[Dict[str, AnalysisStep], Dict]:
        """
        Compose a set of access plans with a single base plan.
        :param base_plan:
        :type base_plan:
        :param access_plans:
        :type access_plans:
        :return:
        :rtype:
        """
        all_slots_to_ref = defaultdict(list, {})

        final_plan = deepcopy(base_plan)
        for access_plan_input_ref, access_plan in access_plans.items():
            # Identify the slots in the base plan which depend on an access plan
            base_plan_slots = self.get_base_plan_slots(final_plan, access_plan_input_ref)

            # Get the letter reference for the access plan
            access_plan_ref_id = self.get_next_ref_letter()

            # Update the step references in the access plan
            access_plan = self.append_to_plan_refs(access_plan, access_plan_ref_id)

            # Get the mapping from slots in the base plan to step refs in the access plan that can satisfy this slot
            slots_to_refs = self.get_refs_for_slots(access_plan, base_plan_slots)

            # Add these slots_to_refs to the global all_slots_to_ref dict
            for k, v in slots_to_refs.items():
                all_slots_to_ref[k].extend(v)

            # Ensure that all slots in the base plan have at least one possible attribute to put in there
            for base_plan_slot, access_plan_refs in slots_to_refs.items():
                if len(access_plan_refs) < 1:
                    raise ValueError("Access plan and base plan incompatible due to lack of viable slot fillers.")

            # Merge in the current access plan
            final_plan = self.compose_access_plan_and_base_plan(access_plan, final_plan, base_plan_slots, slots_to_refs)

        return final_plan, all_slots_to_ref

    def compose_filter_and_access_plan(self,
                                       access_plan: Dict[str, AnalysisStep],
                                       access_plan_filter: Dict[str, AnalysisStep]) -> Dict[str, AnalysisStep]:
        """
        Adds the given access plan filter into the access plan.
        ASSUMPTION: The final step of the access_plan_filter is a filter step (and not a return step).
        :param access_plan:
        :type access_plan:
        :param access_plan_filter:
        :type access_plan_filter:
        :return:
        :rtype:
        """
        # Make sure there is a filter to compose with the access plan
        if not access_plan_filter:
            return deepcopy(access_plan)

        # Get the letter reference for the access plan
        access_plan_ref_id = self.get_next_ref_letter()

        # Update the step references in the access plan
        access_plan_filter = self.append_to_plan_refs(access_plan_filter, access_plan_ref_id)

        # Produce a new dictionary with the steps all added together
        combined_plan = deepcopy(access_plan)
        combined_plan.update(access_plan_filter)

        # Add the reference to the final filter step to the access plan's return step
        return_step_ref = [step_ref for step_ref, step in access_plan.items() if step.operation == 'return'][0]
        combined_plan[return_step_ref].args.append(list(access_plan_filter.keys())[-1])

        return combined_plan

    def compose_filter_plans(self,
                             filter_plans: List[Dict[str, AnalysisStep]],
                             joiner_op: str) -> Dict[str, AnalysisStep]:
        """
        Composes multiple filter plans into a single filter.
        If the joiner type passed in is None, then this will default to joining them with "or".
        :param filter_plans:
        :type filter_plans:
        :param joiner_op:
        :type joiner_op:
        :return:
        :rtype:
        """

        if len(filter_plans) == 0:
            return {}
        elif len(filter_plans) == 1:
            return filter_plans[0]
        else:
            # Add letters to the references for the filters
            updated_filter_plans = []
            for filter_plan in filter_plans:
                # Get the letter reference for the access plan
                access_plan_ref_id = self.get_next_ref_letter()

                # Update the step references in the access plan
                updated_filter_plans.append(self.append_to_plan_refs(filter_plan, access_plan_ref_id))

            # Ensure there is a valid filter joining condition
            if not joiner_op:
                joiner_op = 'or'

            # Combine the filters
            # Get the final step references for each of the filters
            final_step_references = [list(plan_steps.keys())[-1] for plan_steps in updated_filter_plans]

            # Combine all the plans
            combined_filter_plan = updated_filter_plans[0]
            for updated_filter_plan in updated_filter_plans[1:]:
                combined_filter_plan.update(updated_filter_plan)

            # Create a new joiner step (with next_ref_letter) that joins all of the final steps
            joiner_step_ref = "|1" + self.get_next_ref_letter() + "|"
            joiner_step = AnalysisStep(joiner_step_ref, joiner_op, final_step_references)
            combined_filter_plan[joiner_step_ref] = joiner_step

            return combined_filter_plan

    def compose_access_plan_and_base_plan(self,
                                          access_plan: Dict[str, AnalysisStep],
                                          base_plan: Dict[str, AnalysisStep],
                                          base_plan_slots_to_base_plan_refs: dict,
                                          base_plan_slots_to_access_plan_refs: dict) -> Dict[str, AnalysisStep]:
        """

        :param access_plan:
        :type access_plan: dict
        :param base_plan:
        :type base_plan: dict
        :param base_plan_slots_to_base_plan_refs:
        :type base_plan_slots_to_base_plan_refs: dict
        :param base_plan_slots_to_access_plan_refs:
        :type base_plan_slots_to_access_plan_refs: dict
        :return: The final SQR plan.
        :rtype: dict
        """

        # Get the final "return" step reference in the access plan (for now, assumes only one return step)
        for step_ref, step in access_plan.items():
            if step.operation == 'return':
                access_plan_return_step_ref = step_ref

        # Update the "retrieve_attribute" steps
        # base_plan_step_info = self.parse_raw_plan(base_plan)
        for base_plan_slot, base_plan_step_refs in base_plan_slots_to_base_plan_refs.items():
            for base_plan_ref in base_plan_step_refs:
                # NOTE: This assumes that these steps are ALWAYS "retrieve_attribute" steps
                if base_plan[base_plan_ref].args[1] == base_plan_slot:
                    # Replace the first arg with the reference to the final "return" step of the access plan
                    base_plan[base_plan_ref].args[0] = access_plan_return_step_ref

                    # Replace the second arg with the proper attribute reference from the access plan
                    base_plan[base_plan_ref].args[1] = base_plan_slots_to_access_plan_refs[base_plan_slot][0]  # Get the first possible value to fill this slot in with...

        # Combine the access and base plan info into a single structure
        combined_plan = deepcopy(base_plan)
        combined_plan.update(access_plan)

        # Compose the base_plan_step_info and access_plan_step_info lists into a single SQR plan
        # final_plan = self.convert_step_info_to_sqr_plan_format(combined_step_info)
        # return final_plan
        return combined_plan

    def get_refs_for_slots(self,
                           access_plan: Dict[str, AnalysisStep],
                           base_plan_slots: dict) -> dict:
        """
        Produce a mapping from slots in the base plan to step references in the access plan that fit that type.
        :param access_plan:
        :type access_plan:
        :param base_plan_slots:
        :type base_plan_slots:
        :return:
        :rtype:
        """
        # Get the "collect" step in the access plan
        collect_args = []
        for step_ref, step in access_plan.items():
            if step.operation == 'collect':
                collect_args = step.args

        # For each of the references in the "collect" step, get the arg type of the output for that step
        collect_slot_types = {}
        for arg_ref in collect_args:
            # Get the arg types for the current step
            step = access_plan[arg_ref]
            collect_slot_types[arg_ref] = self.get_arg_types_for_step(step, access_plan)

        # Produce a mapping from slots in the base plan to step references in the access plan that fit that type
        map_slot_to_access_plan_ref = defaultdict(list, {k:[] for k in base_plan_slots.keys()})
        for base_plan_slot, base_plan_step_refs in base_plan_slots.items():
            for access_plan_ref, types in collect_slot_types.items():
                if self.extract_slot_type(base_plan_slot) in types:
                    map_slot_to_access_plan_ref[base_plan_slot].append(access_plan_ref)

        return map_slot_to_access_plan_ref

    def extract_slot_type(self,
                          slot: str) -> ArgType:
        """

        :param slot: A slot in the form {SLOT_TYPE:0} where SLOT_TYPE is the type of slot.
        :type slot: str
        :return:
        :rtype:
        """
        return ArgType.from_str(slot.strip("{}").split(":")[0])

    def get_arg_types_for_step(self,
                               step: AnalysisStep,
                               plan: Dict[str, AnalysisStep]) -> List[ArgType]:
        if step.operation == 'retrieve_attribute':
            # For retrieve_attribute steps, look up the type from the ring
            collect_slot_types = self.get_retrieve_attribute_type(step, plan)
        elif self.operation_ontology.is_analysis_operation(step.operation):
            # For analysis steps, look up the type from the operation ontology
            collect_slot_types = self.operation_ontology.analysis_operations[step.operation].output_args[0].arg_types
        else:
            raise ValueError(f"Unhandled operation type in collect statement: {step.operation}")
        return collect_slot_types

    def get_retrieve_attribute_type(self,
                                    step: AnalysisStep,
                                    plan: Dict[str, AnalysisStep]) -> List[ArgType]:
        # Get the entity which the attribute is coming from
        entity_ref = step.args[0]
        attribute_name = step.args[1]
        ent_name = plan[entity_ref].args[0]

        # Look up the attribute for this entity in the ring and get its types
        ring_entity = [ent for ent in self.ring.entities if ent.name == ent_name][0]
        return ring_entity.attributes[attribute_name].type

    def get_base_plan_slots(self,
                            base_plan: Dict[str, AnalysisStep],
                            access_plan_input_ref: str) -> dict:
        """
        Produce a mapping of slots in retrieve_attribute steps of the base plan (where the source entity of the step is the same as the access_plan_input_ref) to the step reference they are in.
        :param base_plan: The SQR base plan
        :type base_plan: Dict[str, AnalysisStep]
        :param access_plan_input_ref: The input_slot key of the base plan (e.g. '|A|', '|B|')
        :type: access_plan_input_ref: str
        :return:
        :rtype: A dictionary mapping slots to a list of the step reference which they can be found in.
        {
            "{Metric:0}": ["|1|", "|2|"],
            "{Identifier:0}: ["|3|"]
        }
        """
        slots = defaultdict(list)

        for step_ref, step in base_plan.items():
            if step.operation == "retrieve_attribute":
                ent_ref = step.args[0]
                if ent_ref not in base_plan and ent_ref == access_plan_input_ref:
                    # Check if the second argument is a slot, and if so, add it to the slots dictionary
                    if self.is_slot(step.args[1]):
                        slots_to_add = step.args[1]
                        slots[slots_to_add].append(step_ref)
        return slots

    def is_slot(self,
                s: str) -> bool:
        if re.search(self.template_token_matcher_regex, s):
            return True
        else:
            return False

    def append_to_plan_refs(self,
                            plan: Dict[str, AnalysisStep],
                            ref_addition: str) -> Dict[str, AnalysisStep]:
        """
        Adds the ref_addition to each of the references in the given plan. Returns a copy (does not update in place).
        For example, given the ref_addition = "A" and the following plan:
        {
            "|1|": "(retrieve_entity State)",               ---> "|1A|": "(retrieve_entity State)",
            "|2|": "(retrieve_attribute |1| fire_size)",    ---> "|2A|": "(retrieve_attribute |1A| fire_size)",
            "|3|": "(retrieve_attribute |1| id)",           ---> "|3A|": "(retrieve_attribute |1A| id)",
            "|4|": "(collect |1| |2|)",                     ---> "|4A|": "(collect |1A| |2A|)",
            "|5|": "(return |4|)"                           ---> "|5A|": "(return |4A|)"
        }
        :param access_plan:
        :type access_plan:
        :param ref_addition:
        :type ref_addition:
        :return:
        :rtype: dict
        """

        # Get the mapping from the original step references to the updated step references
        ref_map = {original_ref: original_ref[0:-1] + ref_addition + original_ref[-1] for original_ref in plan.keys()}

        # Make a copy of the plan and update the step references
        updated_plan = {ref_map[step_ref]: deepcopy(step) for step_ref, step in plan.items()}
        for step_ref, step in updated_plan.items():
            step.ref = step_ref

        # Update the references made in the arguments of each step of the plan
        for step_ref, step in updated_plan.items():
            # Update any references in args for the original plan
            for idx, arg in enumerate(step.args):
                if is_arg_reference(arg):
                    step.args[idx] = ref_map[arg]

        return updated_plan
