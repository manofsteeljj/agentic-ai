import os
import json
from enum import Enum
from typing import List
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Symptom(BaseModel):
    symptom_name: str
    severity: Severity
    duration_days: int = Field(..., ge=0)


class MedicalIntake(BaseModel):
    symptoms: List[Symptom]
    allergies: List[str]
    urgency_rating: int = Field(..., ge=1, le=10)
    clinical_reasoning: str


def _extract_json(text: str):
    """Attempt to extract the first JSON object from model output."""
    try:
        start = text.index("{")
        end = text.rindex("}")
        return json.loads(text[start : end + 1])
    except Exception:
        # fallback: try direct load
        try:
            return json.loads(text)
        except Exception:
            raise ValueError("Could not extract JSON from model output")


def process_intake(patient_input: str) -> MedicalIntake:
    max_retries = 3
    feedback = None

    system_instruction = (
        "You are a clinical intake assistant. "
        "Given a free-text patient complaint, output a single JSON object matching the MedicalIntake schema exactly. "
        "The JSON must include: symptoms (list of {symptom_name, severity, duration_days}), allergies (list of strings), "
        "urgency_rating (int 1-10), and clinical_reasoning (string with step-by-step triage reasoning). "
        "Respond with JSON only and no additional commentary."
    )

    for attempt in range(1, max_retries + 1):
        prompt_parts = [system_instruction]
        if feedback:
            prompt_parts.append(f"Previous attempt produced validation errors: {feedback}")
        prompt_parts.append(f"PATIENT: {patient_input}")
        prompt_parts.append(
            "Return a JSON object. Use severity values LOW, MEDIUM, or HIGH. "
            "Duration is in days (integer). Urgency must be 1-10. clinical_reasoning must explain choices."
        )

        prompt = "\n\n".join(prompt_parts)

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            config={"system_instruction": system_instruction},
            contents=prompt,
        )

        model_output = response.text.strip()
        try:
            data = _extract_json(model_output)
        except Exception as e:
            # If we cannot parse JSON at all, prepare feedback and retry
            feedback = f"JSON parsing error: {e}. Full output: {model_output}"
            print(f"Attempt {attempt}: JSON parsing failed. {e}")
            if attempt == max_retries:
                raise RuntimeError("Could not parse JSON from model after retries")
            continue

        try:
            record = MedicalIntake(**data)
            # success
            return record
        except ValidationError as ve:
            # Print local error, append to feedback, and retry
            feedback = ve.errors()
            print(f"Attempt {attempt}: ValidationError:\n{ve}")
            if attempt == max_retries:
                raise RuntimeError("Validation failed after max retries")
            # on next loop, feedback will be included in prompt

    raise RuntimeError("Unreachable: process_intake exited loop without returning or raising")


if __name__ == "__main__":
    test_input = (
        "My stomach is cramping incredibly badly since last night! The pain is unbearable, "
        "definitely an urgency of 15 out of 10! I don't think I have allergies."
    )

    try:
        record = process_intake(test_input)
        print("\n--- Validated Intake Record ---")
        print(record.model_dump_json(indent=2))
    except Exception as e:
        print(f"Failed: {e}")
import os
from enum import Enum
from typing import List

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# --------------------------------------------------
# Custom Exception
# --------------------------------------------------
class IntakeValidationError(Exception):
    """Raised when intake validation fails after retries."""
    pass


# --------------------------------------------------
# Schema Definitions
# --------------------------------------------------
class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Symptom(BaseModel):
    symptom_name: str
    severity: Severity
    duration_days: int = Field(ge=0)


class MedicalIntake(BaseModel):
    symptoms: List[Symptom]
    allergies: List[str]

    # Must be between 1 and 10 inclusive
    urgency_rating: int = Field(
        ge=1,
        le=10
    )

    clinical_reasoning: str


# --------------------------------------------------
# Core Processing Function
# --------------------------------------------------
def process_intake(patient_input: str) -> MedicalIntake:
    """
    Generate and validate a structured medical intake record.
    Retries up to 3 times using validation feedback.
    """

    max_retries = 3

    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": f"""
Convert the following patient description into a structured
MedicalIntake JSON object.

Patient description:
{patient_input}

Requirements:
- Use ONLY valid JSON.
- Follow the schema exactly.
- urgency_rating must be between 1 and 10 inclusive.
- duration_days must be >= 0.
- Provide detailed clinical_reasoning explaining symptom severity
  and urgency assessment.
"""
                }
            ]
        }
    ]

    for attempt in range(1, max_retries + 1):

        print(f"\nAttempt {attempt}/{max_retries}")

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": MedicalIntake,
                },
            )

            raw_json = response.text

            print("\nRaw Model Output:")
            print(raw_json)

            validated_record = MedicalIntake.model_validate_json(raw_json)

            print("\nValidation successful.")
            return validated_record

        except ValidationError as e:

            print("\nPydantic Validation Error:")
            print(e)

            feedback = f"""
The previous response failed validation.

Validation Error:
{e}

Please regenerate the JSON and correct ALL issues.

Important constraints:
- urgency_rating must be between 1 and 10.
- duration_days must be >= 0.
- severity must be LOW, MEDIUM, or HIGH.
- Return valid JSON only.
"""

            contents.append(
                {
                    "role": "model",
                    "parts": [{"text": raw_json if 'raw_json' in locals() else ""}],
                }
            )

            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": feedback}],
                }
            )

        except Exception as e:
            raise RuntimeError(f"Generation failed: {e}")

    raise IntakeValidationError(
        f"Failed validation after {max_retries} attempts."
    )


# --------------------------------------------------
# Test Harness
# --------------------------------------------------
if __name__ == "__main__":

    test_input = (
        "My stomach is cramping incredibly badly since last night! "
        "The pain is unbearable, definitely an urgency of 15 out of 10! "
        "I don't think I have allergies."
    )

    try:
        record = process_intake(test_input)

        print("\n--- Validated Intake Record ---")
        print(record.model_dump_json(indent=2))

    except Exception as e:
        print(f"Failed: {e}")