import json
from typing import List

from smart_open import open




def is_valid_api_request_json(json_data: dict, expected_keys: List[str]) -> bool:
    if not expected_keys:
        return True
    else:
        for key in expected_keys:
            if key not in json_data:
                return False

        return True