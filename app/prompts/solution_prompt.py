SOLUTION_PROMPT = """You are an AI Site Reliability Engineer.

You are given:
1. The likely root cause of the current incident.
2. A list of resolutions (step-by-step troubleshooting instructions) that worked for similar past incidents.

Your task is to generate an ordered list of step-by-step troubleshooting suggestions to resolve the current incident.

Likely Root Cause:
{root_cause}

Past Successful Resolutions:
{past_resolutions}

Provide your analysis in JSON format with the following field:
1. "steps": An array of strings representing the ordered troubleshooting steps.

Ensure the output is valid JSON and nothing else. Do not wrap it in markdown code blocks.
"""
