from pathlib import Path

from axiombraid import DataGuide

base = Path(__file__).with_name("students.csv")
guide = DataGuide(base)
contract = guide.create_validation_contract({
    "Age": {"nullable": False, "minimum": 0, "maximum": 120},
    "Status": {"allowed_values": ["Pass", "Fail"]},
})
print(guide.validate_contract(contract))
print(guide.export_validation_contract(Path(__file__).parent / "reports" / "contract.json", contract=contract))
