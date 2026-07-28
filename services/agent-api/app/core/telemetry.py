import os
import braintrust

# Initialize the Braintrust logger
# This will pick up the BRAINTRUST_API_KEY from the environment automatically
def init_telemetry(project_name: str = "PourMind-AI"):
    """
    Initializes Braintrust logging for the project.
    Call this function at application startup (e.g., in main.py).
    """
    if os.environ.get("BRAINTRUST_API_KEY"):
        braintrust.init_logger(project=project_name)
    else:
        print("Warning: BRAINTRUST_API_KEY not found. Telemetry will not be sent to Braintrust.")

# A convenient alias for @traced decorator to use across the application
# Use @traced on any function you want to log (e.g., LLM calls, tool executions, API endpoints)
traced = braintrust.traced
