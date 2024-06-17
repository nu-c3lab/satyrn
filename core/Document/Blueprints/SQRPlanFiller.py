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
from copy import deepcopy
from typing import Dict, List, Union
from core.RingObjects.Ring import Ring

from core.Analysis.AnalysisStep import AnalysisStep

class SQRPlanFiller:
    def __init__(self,
                 ring: Ring):
        self.ring = ring
        self.template_token_matcher = '({([^}]+)})'
        self.template_token_matcher_regex = re.compile(self.template_token_matcher)

    def fill_plan(self,
                  plan: Dict[str, AnalysisStep],
                  slot_fillers: Dict[str, str]) -> Dict[str, AnalysisStep]:
        """
        Fills in the given plan steps with the specified slot fillers. If no slot fillers are specified or there are no slots to fill, the original plan is returned.
        :param plan:
        :type plan:
        :param slot_fillers:
        :type slot_fillers:
        :return:
        :rtype:
        """

        # Make a copy of the plan which will be filled in using the specified slots and fillers
        plan_to_fill = deepcopy(plan)
        filled_any_slot = False

        # Get useful information for filling in the slots
        plan_slot_info = self.identify_slots_in_plan_template(plan)

        # Fill in any of the slots, if possible
        for slot, filler in slot_fillers.items():
            if slot in plan_slot_info:
                for slot_location_dict in plan_slot_info[slot]:
                    step_idx = slot_location_dict['step_idx']
                    arg_idx = slot_location_dict['arg_idx']
                    if arg_idx == -1:
                        # The filler is meant to replace the operation, not one of the step arguments
                        plan_to_fill[step_idx].operation = filler
                    else:
                        plan_to_fill[step_idx].args[arg_idx] = filler
                filled_any_slot = True

        # If any of the slots were filled in this plan, add it to the list of output plans
        if filled_any_slot:
            return plan_to_fill
        else:
            return plan

    def generate_plans_with_specified_slots(self,
                                            partial_plan: Dict[str, AnalysisStep],
                                            fillers_for_slots: List[Dict[str, str]]) -> List[Dict[str, AnalysisStep]]:
        """
        Fill in the slots of the given set of plan steps using the given set of slots to fill.
        :param partial_plan: A plan which has been partially filled in.
        :type partial_plan: Dictionary mapping step references to analysis steps.
        :param fillers_for_slots: Each item in this list contains the slot fillers for a separate plan.
        :type fillers_for_slots: List of dict
        :return: The set of partial plans with some of their slots filled.
        :rtype: List of dict
        """

        partial_plans = []
        plan_slot_info = self.identify_slots_in_plan_template(partial_plan)
        for slot_fillers in fillers_for_slots:
            # Make a copy of the plan which will be filled in using the specified slots and fillers
            plan_to_fill = deepcopy(partial_plan)
            filled_any_slot = False

            # Fill in any of the slots, if possible
            for slot, filler in slot_fillers.items():
                if slot in plan_slot_info:
                    for slot_location_dict in plan_slot_info[slot]:
                        step_idx = slot_location_dict['step_idx']
                        arg_idx = slot_location_dict['arg_idx']
                        if arg_idx == -1:
                            # The filler is meant to replace the operation, not one of the step arguments
                            plan_to_fill[step_idx].operation = filler
                        else:
                            plan_to_fill[step_idx].args[arg_idx] = filler
                    filled_any_slot = True

            # If any of the slots were filled in this plan, add it to the list of output plans
            if filled_any_slot:
                partial_plans.append(plan_to_fill)

        # Deduplicate the partial plans
        deduplicated_partial_plans = self.dedupe_list_of_dict(partial_plans)

        return deduplicated_partial_plans

    def dedupe_list_of_dict(self,
                            lst: List[Dict]) -> List[Dict]:
        """
        Returns a new copy the list without duplicate dictionary elements.
        :param lst: The list of dictionaries for which there should be no duplicated dictionaries.
        :type lst: List of dict
        :return: A new list with no duplicated dictionary elements.
        :rtype:
        """
        unique_list = []
        for item in lst:
            if item not in unique_list:
                unique_list.append(item)
        return unique_list

    def identify_slots_in_plan_template(self,
                                        plan_template: Dict[str, AnalysisStep]) -> Dict[str, List[Dict[str, Union[str, int]]]]:
        """
        Returns a dictionary mapping slots (e.g. "Entity:0") to a list of dictionaries of properties of the slot (e.g. {"step_idx": "|1|", "arg_idx": 0})
        :param plan_template:
        :type plan_template:
        :return: A dictionary mapping the slot names to a list of locations where this slot appears in the plan.
        :rtype: Dict
        """
        slot_info = {}
        for step_idx, step in plan_template.items():
            # Check if the operation is a slot
            match = re.search(self.template_token_matcher_regex, step.operation)
            if match:
                if match.string.strip("{}") in slot_info:
                    slot_info[match.string.strip("{}")].append({
                        "step_idx": step_idx,
                        "arg_idx": -1
                    })
                else:
                    slot_info[match.string.strip("{}")] = [{
                        "step_idx": step_idx,
                        "arg_idx": -1
                    }]

            # Check if any of the arguments for this step is a slot
            for arg_idx, step_arg in enumerate(step.args):
                match = re.search(self.template_token_matcher_regex, str(step.args[arg_idx]))
                if match:
                    if match.string.strip("{}") in slot_info:
                        slot_info[match.string.strip("{}")].append({
                            "step_idx": step_idx,
                            "arg_idx": arg_idx
                        })
                    else:
                        slot_info[match.string.strip("{}")] = [{
                            "step_idx": step_idx,
                            "arg_idx": arg_idx
                        }]

        return slot_info