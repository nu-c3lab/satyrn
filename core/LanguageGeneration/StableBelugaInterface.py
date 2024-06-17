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

import requests

class StableBelugaInterface:
    def __init__(self):
        # Init access to OpenAI's API
        self.HOST = 'localhost:5000'
        # self.URI = f'http://{self.HOST}/api/v1/generate'
        self.URI = 'https://governments-ton-democratic-councils.trycloudflare.com/api/v1/generate'
        self.request = {
            'max_new_tokens': 2048,

            # Generation params. If 'preset' is set to different than 'None', the values
            # in presets/preset-name.yaml are used instead of the individual numbers.
            'preset': 'None',  
            'do_sample': True,
            'temperature': 0.2,
            'top_p': 0.1,
            'typical_p': 1,
            'epsilon_cutoff': 0,  # In units of 1e-4
            'eta_cutoff': 0,  # In units of 1e-4
            'tfs': 1,
            'top_a': 0,
            'repetition_penalty': 1.18,
            'repetition_penalty_range': 0,
            'top_k': 40,
            'min_length': 0,
            'no_repeat_ngram_size': 0,
            'num_beams': 1,
            'penalty_alpha': 0,
            'length_penalty': 1,
            'early_stopping': False,
            'mirostat_mode': 0,
            'mirostat_tau': 5,
            'mirostat_eta': 0.1,

            'seed': -1,
            'add_bos_token': True,
            'truncation_length': 2048,
            'ban_eos_token': False,
            'skip_special_tokens': True,
            'stopping_strings': []
        }

    def format_beluga_prompt(self, prompt):
        return f"""### System:\nThis is a system prompt, please behave and help the user.\n\n### User:\n{prompt}\n\n###Assistant:\n"""

    def generate(self,
                 prompt: str) -> str:
        
        formatted_prompt = self.format_beluga_prompt(prompt)
        self.request['prompt'] = formatted_prompt

        # Feed the prompt to the language model
        response = requests.post(self.URI, json=self.request)

        if response.status_code == 200:
            result = response.json()['results'][0]['text']
            return result
