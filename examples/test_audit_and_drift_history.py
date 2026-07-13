from pathlib import Path

import pandas as pd

from axiombraid import DataGuide

guide = DataGuide(pd.DataFrame({"Department": ["CS", "cs"], "Marks": [1, 2]}))
guide.apply_cleaning(inplace=True, confirm=True)
guide.undo_last_cleaning()
print(guide.export_cleaning_audit_log(Path(__file__).parent / "reports" / "cleaning_audit.json"))

guide.detect_drift(pd.DataFrame({"Department": ["Math", "Math"], "Marks": [10, 20]}), label="new_batch")
print(guide.export_drift_history(Path(__file__).parent / "reports" / "drift_history.json"))
