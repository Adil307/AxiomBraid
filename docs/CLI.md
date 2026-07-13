# Command-line interface

```powershell
axiombraid --version
axiombraid inspect data.csv
axiombraid batch datasets --output reports --workers 4 --format json --format html
axiombraid stream large.csv --chunksize 100000 --sample-rows 50000
axiombraid cache-inspect data.csv
axiombraid validate data.csv contract.json
axiombraid fingerprint data.csv
axiombraid themes
```

The former `dataguide` command was part of the 0.9 migration window and is not
included in the 1.0 distribution.
