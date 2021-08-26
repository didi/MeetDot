import json
from dataclasses import dataclass


@dataclass
class EvaluationScore:
    def save(self, filename):
        """
        Save evaluation scores to a file
        """
        with open(filename, "w") as f:
            json.dump(self.__dict__, f, indent=2)
        print(f"Saved evaluation scores to {filename}")
