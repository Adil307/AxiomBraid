from pathlib import Path

from axiombraid import DataGuide

path = Path(__file__).with_name("students.csv")
guide = DataGuide(path)
result = guide.report()

print("\nAxiomBraid 0.9 features:")
print("Fingerprint:", result["dataset_fingerprint"]["combined_hash"][:16] + "...")
contract = guide.create_validation_contract()
print("Contract valid:", guide.validate_contract(contract)["valid"])

plan = guide.cleaning_plan()
print("Cleaning actions:", plan["action_count"])
cleaning_result = guide.apply_cleaning()
print("Applied actions:", cleaning_result["applied_actions"])
print("Audit events:", len(guide.cleaning_audit_log()))
