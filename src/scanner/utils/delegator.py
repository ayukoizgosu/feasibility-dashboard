import json
import os
import subprocess
from typing import Any, Dict


def delegate_extraction(raw_text: str) -> Dict[str, Any]:
    """
    Delegate complex property feature extraction to Gemini CLI.
    """
    prompt = f"""
    You are an expert real estate data analyst. 
    Extract the following fields from the real estate listing text provided below.
    
    Fields:
    - property_type: One of [House, Townhouse, Unit, Apartment, Land]
    - internal_area_m2: Internal building size (GFA/Floor area) in m2. If given in 'squares', multiply by 9.29.
    - finish_quality: Rating of the interior finish.
        - Basic: Original condition, needs work, dated.
        - Standard: Neat, tidy, typical project home or older renovation.
        - Premium: High quality, stone benchtops, modern appliances, hardwood floors.
        - Luxury: Architect designed, high-end bespoke finishes, butler's pantry, pool.
    - renovated: Boolean (True/False). True if described as "recently renovated", "as new", or similar.
    - land_size_m2: Total land area in square meters.
    - features: List of 3-5 key features.
    - year_built_estimate: Estimate of the decade built (e.g. 1970s, 2020s).

    Return ONLY a valid JSON object. Do not include any other text or markdown blocks.
    
    Listing Text:
    {raw_text[:2000]}
    """

    try:
        # Construct command: gemini -p "prompt"
        # We need to escape double quotes in prompt if necessary, or pass via stdin if gemini supports it.
        # Most CLIs support reading from stdin. Let's try passing the prompt as an argument carefully.

        # Using temp file for prompt to avoid shell length limits and quoting issues
        temp_file = "temp_prompt.txt"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Run gemini command
        # gemini command usually takes prompt as positional arg or via -p

        # User requested Fast/Flash model. Using gemini-2.0-flash-exp or similar.
        env = os.environ.copy()
        # env["GEMINI_MODEL"] = "gemini-2.0-flash-exp"

        if os.name == "nt":
            command = f'type "{temp_file}" | gemini'
        else:
            command = f'cat "{temp_file}" | gemini'

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            shell=True,
        )
        stdout, stderr = process.communicate()

        if os.path.exists(temp_file):
            os.remove(temp_file)

        if process.returncode != 0:
            print(f"Gemini CLI Failed. RC: {process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return {}

        # Clean JSON from output
        output = stdout.strip()

        # Try markdown blocks first
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()

        # Fallback: Find first { and last }
        if not output.startswith("{"):
            start = output.find("{")
            end = output.rfind("}")
            if start != -1 and end != -1:
                output = output[start : end + 1]

        return json.loads(output)
    except Exception as e:
        print(f"Delegator Error: {e}")
        return {}
