import axiombraid as AB


# Replace this path with your own dataset.
df = AB.read_csv("examples/students.csv")

# 1. Human-readable terminal report with full confidence details.
AB.report(
    df,
    include_confidence=True,
)

# 2. Export a professional HTML report with confidence cards.
AB.export_html(
    df,
    "reports/v2_phase3_confidence.html",
    include_confidence=True,
    theme="dark",
)

# 3. Export machine-readable JSON with confidence metadata.
guide = AB.Guide(df)
guide.export_json(
    "reports/v2_phase3_confidence.json",
    include_confidence=True,
)
