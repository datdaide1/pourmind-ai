import os
import braintrust
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def parse_scenario_bank(filepath):
    scenarios = []
    current_scenario = {}
    capturing_field = None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith('*   **ID**:'):
                if current_scenario:
                    scenarios.append(current_scenario)
                current_scenario = {'ID': stripped.split('`')[1]}
                capturing_field = None
            elif stripped.startswith('*   **Query Type**:'):
                current_scenario['Query Type'] = stripped.split(':', 1)[1].strip()
                capturing_field = None
            elif stripped.startswith('*   **Input**:'):
                val = stripped.split(':', 1)[1].strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                current_scenario['Input'] = val
                capturing_field = None
            elif stripped.startswith('*   **Expected Behavior**:'):
                current_scenario['Expected Behavior'] = stripped.split(':', 1)[1].strip()
                capturing_field = 'Expected Behavior'
            elif stripped.startswith('*   **Reason**:'):
                current_scenario['Reason'] = stripped.split(':', 1)[1].strip()
                capturing_field = 'Reason'
            else:
                if capturing_field and line.strip() and not line.startswith('####') and not line.startswith('---') and not line.startswith('###'):
                    # Append multi-line content
                    current_scenario[capturing_field] += '\n' + line.strip()
    if current_scenario:
        scenarios.append(current_scenario)
    
    return scenarios

def main():
    api_key = os.environ.get("BRAINTRUST_API_KEY")
    if not api_key:
        print("Error: BRAINTRUST_API_KEY is not set. Please set it in .env to upload.")
        return
        
    print("Authenticating with Braintrust...")
    
    # Resolve input relative to this pipeline workspace.
    pipeline_root = Path(__file__).resolve().parents[1]
    filepath = pipeline_root / "data" / "evals" / "scenario_bank.md"
    
    scenarios = parse_scenario_bank(filepath)
    print(f"Parsed {len(scenarios)} scenarios from scenario_bank.md")
    
    if len(scenarios) != 20:
        print(f"Warning: Expected 20 scenarios, found {len(scenarios)}")
    
    dataset = braintrust.init_dataset(
        project="PourMind-AI",
        name="PourMind-Scenarios-Golden"
    )
    
    for s in scenarios:
        dataset.insert(
            input=s.get("Input", ""),
            expected=s.get("Expected Behavior", ""),
            metadata={
                "id": s.get("ID", ""),
                "query_type": s.get("Query Type", ""),
                "reason": s.get("Reason", "")
            }
        )
    
    print("Successfully uploaded scenarios to Braintrust Golden Dataset.")

if __name__ == "__main__":
    main()
