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
from openai import OpenAI

from typing import Dict

class GPT3Interface:
    def __init__(self):
        # Init access to OpenAI's API
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key)

    def generate(self,
                 prompt: str) -> str:
        # Feed the prompt to the language model
        response = self.get_response(prompt)

        # Extract the generation from the response
        qdmr = self.extract_generation_from_response(response)

        return qdmr

    def get_response(self,
                     prompt: str) -> Dict:
        # Make the API call off to GPT
        print(f"Prompt:\n{prompt}")
        response = self.client.completions.create(engine="text-davinci-003",
        prompt=prompt,
        max_tokens=256,
        temperature=0.0)

        # Save the raw output
        print("RAW OPENAI RESPONSE")
        print(response)

        return response

    def extract_generation_from_response(self,
                                   response: Dict) -> str:
        # Pull out the generated text from the response
        qdmr = response.choices[0].text

        # Clean up the string
        qdmr = qdmr.strip()

        return qdmr