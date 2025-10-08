"""Generate realistic patient data for medical prescription authorization.

This module provides functionality to generate synthetic patient data including
demographics, prescriptions, and realistic doctor visit notes using AI. The generated
data is suitable for testing and demonstration of medical authorization systems.

Example:
    Generate patient data from command line::

        $ python scripts/generate_patient_data.py
        $ python scripts/generate_patient_data.py -n 10
        $ python scripts/generate_patient_data.py --number 5 --output custom_patients.json

    Or use programmatically::

        from scripts.generate_patient_data import generate_patient_data
        patients = generate_patient_data(n=10)

"""

import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import logfire
from faker import Faker
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.env import get_openai_api_key, setup_env
from app.models import Patient, Prescription

# Initialize environment and logging
setup_env()
logger = logfire

# Constants
MIN_PATIENT_AGE = 18
MAX_PATIENT_AGE = 75
MIN_VISITS = 2
MAX_VISITS = 4
DAYS_BETWEEN_VISITS = 30
MAX_MONTHS_ON_MEDICATION = 24
VISIT_NOTE_PREVIEW_LENGTH = 500


class MedicationInfo(BaseModel):
    """Pydantic model for medication information."""

    dosages: list[str] = Field(description="Available dosage strengths")
    frequency: str = Field(description="Dosing frequency")
    duration: str = Field(description="Treatment duration")


MEDICATIONS: dict[str, MedicationInfo] = {
    "Zepbound": MedicationInfo(
        dosages=["2.5 mg", "5 mg", "7.5 mg", "10 mg", "12.5 mg", "15 mg"],
        frequency="once weekly",
        duration="ongoing",
    ),
    "Wegovy": MedicationInfo(
        dosages=["0.25 mg", "0.5 mg", "1 mg", "1.7 mg", "2.4 mg"],
        frequency="once weekly",
        duration="ongoing",
    ),
    "Skyrizi": MedicationInfo(
        dosages=["150 mg", "600 mg"],
        frequency="every 12 weeks after initial loading doses",
        duration="ongoing",
    ),
}


class VisitNoteRequest(BaseModel):
    """Request model for generating visit notes."""

    patient_first_name: str = Field(description="Patient's first name")
    patient_last_name: str = Field(description="Patient's last name")
    patient_age: int = Field(ge=0, le=120, description="Patient age in years")
    patient_gender: str = Field(pattern="^(Male|Female)$", description="Patient gender")
    patient_date_of_birth: str = Field(
        description="Patient's date of birth in YYYY-MM-DD format"
    )
    medication: str = Field(description="Prescribed medication name")
    dosage: str = Field(description="Medication dosage")
    frequency: str = Field(description="Medication frequency")
    duration: str = Field(description="Treatment duration")
    is_continuation: bool = Field(description="Whether continuing existing therapy")
    months_on_medication: int | None = Field(
        default=None, ge=1, description="Months on medication if continuation"
    )


class PatientDataGenerator:
    """Handles generation of synthetic patient data with AI-powered visit notes.

    This class encapsulates the logic for creating realistic patient records
    including demographics, prescriptions, and medical visit notes.

    Attributes:
        faker: Faker instance for generating demographic data
        visit_note_agent: AI agent for generating medical notes
    """

    def __init__(self) -> None:
        """Initialize the patient data generator."""
        self.faker = Faker()
        self._setup_ai_agent()

    def _setup_ai_agent(self) -> None:
        """Configure the AI agent for generating visit notes."""
        try:
            api_key = get_openai_api_key()
            model = OpenAIModel("gpt-4.1", provider=OpenAIProvider(api_key=api_key))

            self.visit_note_agent = Agent(
                model,
                system_prompt=self._get_system_prompt(),
                instrument=True,
            )
        except Exception as e:
            logger.exception("Failed to initialize AI agent")
            raise RuntimeError("Could not initialize AI agent") from e

    @staticmethod
    def _get_system_prompt() -> str:
        """Get the system prompt for the visit note agent.

        Returns:
            Detailed system prompt for generating medical visit notes
        """
        return """You are a medical professional writing detailed visit notes for patients being prescribed weight management or autoimmune medications.

        Generate realistic doctor's visit notes that include:
        1. Patient vital signs (weight, height, BMI)
        2. Chief complaint and reason for visit
        3. Medical history relevant to the prescription
        4. Physical examination findings
        5. Assessment covering the key criteria for the medication (e.g., BMI requirements, comorbidities, previous weight management attempts)
        6. Plan including medication dosing and follow-up

        Make the notes sound natural and medical, including:
        - Specific measurements and dates
        - Medical terminology where appropriate
        - References to prior visits if it's a continuation
        - Mention of lifestyle interventions (diet, exercise)
        - Any relevant comorbidities (hypertension, diabetes, dyslipidemia)
        - Side effect discussions
        - Patient adherence and response to treatment

        The notes should naturally incorporate answers to medication authorization questions without being a direct Q&A format.
        """

    async def generate_visit_notes(self, patient_info: VisitNoteRequest) -> list[str]:
        """Generate realistic medical visit notes for a patient.

        Creates 2-4 chronologically ordered visit notes that document the patient's
        treatment journey with appropriate medical detail.

        Args:
            patient_info: Patient information and prescription details

        Returns:
            List of generated visit notes in chronological order

        Raises:
            RuntimeError: If AI agent fails to generate notes
        """
        num_notes = random.randint(MIN_VISITS, MAX_VISITS)
        notes = []

        for visit_number in range(num_notes):
            try:
                visit_date = self._calculate_visit_date(visit_number)
                prompt = self._create_visit_prompt(
                    patient_info, visit_date, visit_number + 1, num_notes
                )

                result = await self.visit_note_agent.run(prompt)
                notes.append(result.output)

            except Exception as e:
                logger.error(f"Failed to generate visit note {visit_number + 1}: {e}")
                raise RuntimeError(
                    f"Could not generate visit note {visit_number + 1}"
                ) from e

        return notes

    @staticmethod
    def _calculate_visit_date(visit_index: int) -> datetime:
        """Calculate the date for a specific visit.

        Args:
            visit_index: Zero-based index of the visit

        Returns:
            Calculated visit date
        """
        days_ago = random.randint(
            DAYS_BETWEEN_VISITS * visit_index, DAYS_BETWEEN_VISITS * (visit_index + 1)
        )
        return datetime.now() - timedelta(days=days_ago)

    @staticmethod
    def _create_visit_prompt(
        patient_info: VisitNoteRequest,
        visit_date: datetime,
        visit_number: int,
        total_visits: int,
    ) -> str:
        """Create a prompt for generating a specific visit note.

        Args:
            patient_info: Patient demographic and prescription information
            visit_date: Date of the visit
            visit_number: Current visit number (1-based)
            total_visits: Total number of visits to generate

        Returns:
            Formatted prompt for the AI agent
        """
        visit_type = (
            "This is the initial consultation for starting the medication."
            if visit_number == 1 and not patient_info.is_continuation
            else "This is a follow-up visit."
        )

        return f"""Generate a realistic doctor's visit note for this patient. Ensure the patient's details are included in the notes. Do not redact anything:
        - Patient Name: {patient_info.patient_first_name} {patient_info.patient_last_name}
        - Date of Birth: {patient_info.patient_date_of_birth}
        - Age: {patient_info.patient_age} years old
        - Gender: {patient_info.patient_gender}
        - Medication: {patient_info.medication} {patient_info.dosage}
        - Frequency: {patient_info.frequency}
        - Duration: {patient_info.duration}
        - Visit Date: {visit_date.strftime("%Y-%m-%d")}
        - Visit Number: {visit_number} of {total_visits}
        - Is Continuation: {patient_info.is_continuation}
        - Months on Medication: {patient_info.months_on_medication if patient_info.is_continuation else "N/A"}

        This is visit {visit_number}. {visit_type}
        """

    def generate_patient(self) -> Patient:
        """Generate a single patient with complete medical records.

        Creates a patient with random demographics, appropriate prescription,
        and AI-generated visit notes.

        Returns:
            Complete Patient object with all fields populated

        Raises:
            RuntimeError: If patient generation fails
        """
        try:
            # Generate demographics
            gender = random.choice(["Male", "Female"])
            first_name = self._get_gender_appropriate_name(gender)
            last_name = self.faker.last_name()
            age = random.randint(MIN_PATIENT_AGE, MAX_PATIENT_AGE)
            date_of_birth = self._calculate_date_of_birth(age)

            # Generate prescription
            medication, dosage, prescription = self._generate_prescription()

            # Determine treatment status
            is_continuation = self._should_be_continuation(medication)
            months_on_medication = (
                random.randint(1, MAX_MONTHS_ON_MEDICATION) if is_continuation else None
            )

            # Create visit note request
            visit_note_request = VisitNoteRequest(
                patient_first_name=first_name,
                patient_last_name=last_name,
                patient_age=age,
                patient_gender=gender,
                patient_date_of_birth=date_of_birth,
                medication=medication,
                dosage=dosage,
                frequency=prescription.frequency,
                duration=prescription.duration,
                is_continuation=is_continuation,
                months_on_medication=months_on_medication,
            )

            # Generate visit notes synchronously (wrapper for async function)
            visit_notes = asyncio.run(self.generate_visit_notes(visit_note_request))

            return Patient(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                prescription=prescription,
                visit_notes=visit_notes,
            )

        except Exception as e:
            logger.error(f"Failed to generate patient: {e}")
            raise RuntimeError("Could not generate patient") from e

    def _get_gender_appropriate_name(self, gender: str) -> str:
        """Get a gender-appropriate first name.

        Args:
            gender: Patient gender (Male/Female)

        Returns:
            Appropriate first name
        """
        return (
            self.faker.first_name_male()
            if gender == "Male"
            else self.faker.first_name_female()
        )

    @staticmethod
    def _calculate_date_of_birth(age: int) -> str:
        """Calculate date of birth from age.

        Args:
            age: Patient age in years

        Returns:
            Date of birth in YYYY-MM-DD format
        """
        days_old = age * 365 + random.randint(0, 364)
        birth_date = datetime.now() - timedelta(days=days_old)
        return birth_date.strftime("%Y-%m-%d")

    @staticmethod
    def _generate_prescription() -> tuple[str, str, Prescription]:
        """Generate a random prescription.

        Returns:
            Tuple of (medication_name, dosage, Prescription object)
        """
        medication = random.choice(list(MEDICATIONS.keys()))
        med_info = MEDICATIONS[medication]
        dosage = random.choice(med_info.dosages)

        prescription = Prescription(
            medication=medication,
            dosage=dosage,
            frequency=med_info.frequency,
            duration=med_info.duration,
        )

        return medication, dosage, prescription

    @staticmethod
    def _should_be_continuation(medication: str) -> bool:
        """Determine if treatment should be marked as continuation.

        Args:
            medication: Name of the medication

        Returns:
            Whether this should be continuation therapy
        """
        # Skyrizi is typically not a continuation therapy
        return random.choice([True, False]) if medication != "Skyrizi" else False


async def generate_patients_async(n: int = 10) -> list[Patient]:
    """Generate multiple patients asynchronously for better performance.

    Args:
        n: Number of patients to generate

    Returns:
        List of generated Patient objects

    Raises:
        RuntimeError: If patient generation fails
    """
    generator = PatientDataGenerator()
    tasks = []

    async def generate_single_patient(index: int) -> Patient:
        """Generate a single patient with progress logging."""
        try:
            # Create patient info
            gender = random.choice(["Male", "Female"])
            first_name = generator._get_gender_appropriate_name(gender)
            last_name = generator.faker.last_name()
            age = random.randint(MIN_PATIENT_AGE, MAX_PATIENT_AGE)
            date_of_birth = generator._calculate_date_of_birth(age)

            medication, dosage, prescription = generator._generate_prescription()
            is_continuation = generator._should_be_continuation(medication)
            months_on_medication = (
                random.randint(1, MAX_MONTHS_ON_MEDICATION) if is_continuation else None
            )

            visit_note_request = VisitNoteRequest(
                patient_first_name=first_name,
                patient_last_name=last_name,
                patient_age=age,
                patient_gender=gender,
                patient_date_of_birth=date_of_birth,
                medication=medication,
                dosage=dosage,
                frequency=prescription.frequency,
                duration=prescription.duration,
                is_continuation=is_continuation,
                months_on_medication=months_on_medication,
            )

            # Generate visit notes asynchronously
            visit_notes = await generator.generate_visit_notes(visit_note_request)

            patient = Patient(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                prescription=prescription,
                visit_notes=visit_notes,
            )

            logger.info(f"Generated patient {index + 1}/{n}: {first_name} {last_name}")
            return patient

        except Exception as e:
            logger.error(f"Failed to generate patient {index + 1}: {e}")
            raise

    # Create tasks for all patients
    for i in range(n):
        tasks.append(generate_single_patient(i))

    # Execute all tasks concurrently
    patients = await asyncio.gather(*tasks)
    return patients


def generate_patient_data(n: int = 10, output_file: str | None = None) -> list[Patient]:
    """Generate mock patients with realistic data and visit notes.

    This is the main entry point for generating patient data. It creates
    synthetic patients with demographics, prescriptions, and AI-generated
    visit notes, then saves them to a JSON file.

    Args:
        n: Number of patients to generate (default: 10)
        output_file: Path to save JSON file. If None, saves to
                    sample_data/patient_data.json

    Returns:
        List of generated Patient objects

    Raises:
        RuntimeError: If generation or file writing fails

    Example:
        >>> patients = generate_patient_data(5, "output/patients.json")
        >>> print(f"Generated {len(patients)} patients")
        Generated 5 patients
    """
    logger.info(f"Starting generation of {n} patients")

    try:
        # Generate patients asynchronously for better performance
        patients = asyncio.run(generate_patients_async(n))

        # Determine output path
        if output_file is None:
            output_file = _get_default_output_path()

        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        patients_data = [patient.model_dump() for patient in patients]

        # Write to file with proper error handling
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(patients_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to write output file: {e}")
            raise RuntimeError(f"Could not write to {output_file}") from e

        logger.info(f"Successfully saved {len(patients)} patients to {output_file}")
        return patients

    except Exception as e:
        logger.error(f"Patient generation failed: {e}")
        raise RuntimeError("Failed to generate patient data") from e


def _get_default_output_path() -> str:
    """Get the default output path for patient data.

    Returns:
        Path to default output file
    """
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    return str(project_root / "sample_data" / "patient_data.json")


def log_patient_summary(patient: Patient) -> None:
    """Log a summary of a patient's information.

    Args:
        patient: Patient object to summarize
    """
    logger.info("Patient Summary:")
    logger.info(f"  Name: {patient.first_name} {patient.last_name}")
    logger.info(f"  DOB: {patient.date_of_birth}")
    logger.info(f"  Gender: {patient.gender}")
    logger.info(
        f"  Prescription: {patient.prescription.medication} {patient.prescription.dosage}"
    )
    logger.info(f"  Frequency: {patient.prescription.frequency}")
    logger.info(f"  Number of visit notes: {len(patient.visit_notes)}")

    if patient.visit_notes:
        preview = patient.visit_notes[0][:VISIT_NOTE_PREVIEW_LENGTH]
        if len(patient.visit_notes[0]) > VISIT_NOTE_PREVIEW_LENGTH:
            preview += "..."
        logger.info(f"First visit note preview:\n{preview}")


def main() -> None:
    """Entry point for the script when run via console.

    Parses command-line arguments to determine the number of patients to generate
    and displays information about the first one as an example of the generated data.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Generate realistic patient data for medical prescription authorization"
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=2,
        help="Number of patients to generate (default: 2)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file path (default: sample_data/patient_data.json)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate number of patients
    if args.number < 1:
        parser.error("Number of patients must be at least 1")

    try:
        # Generate sample patients
        logger.info(f"Generating {args.number} patients...")
        patients = generate_patient_data(args.number, args.output)

        # Display example
        if patients:
            log_patient_summary(patients[0])

    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise


if __name__ == "__main__":
    main()
