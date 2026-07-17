# Doxygen Source Documentation

AxiomBraid 2.0.0 includes a final Doxygen configuration for API and source-code documentation.

## Included files

```text
Doxyfile
 generate_doxygen.cmd
 generate_doxygen.ps1
 .github/workflows/doxygen.yml
```

The **recommended Windows command** is:

```powershell
.\generate_doxygen.cmd
```

The CMD script avoids PowerShell execution-policy and digital-signature restrictions.

## Install Doxygen and Graphviz on Windows

```powershell
winget install --id DimitriVanHeesch.Doxygen -e
winget install --id Graphviz.Graphviz -e
```

Close and reopen the terminal, then verify:

```powershell
doxygen --version
dot -V
```

When the tools are installed but not yet visible in the current PowerShell session:

```powershell
$env:Path += ";C:\Program Files\doxygen\bin"
$env:Path += ";C:\Program Files\Graphviz\bin"
```

## Generate the documentation

From the project root:

```powershell
.\generate_doxygen.cmd
```

Direct Doxygen command:

```powershell
doxygen .\Doxyfile
```

PowerShell script alternative:

```powershell
Unblock-File .\generate_doxygen.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\generate_doxygen.ps1
```

## Generated files

Main page:

```text
docs/doxygen/html/index.html
```

Warnings log:

```text
docs/doxygen/doxygen-warnings.log
```

Doxygen tag file:

```text
docs/doxygen/axiombraid-2.0.0.tag
```

Open the documentation manually:

```powershell
Start-Process .\docs\doxygen\html\index.html
```

## What is documented

- Python packages and modules
- Public classes, functions, and methods
- Python docstrings and signatures
- Source-code browser and cross-references
- README and Markdown documentation
- Example scripts
- Class, dependency, and directory diagrams through Graphviz

## GitHub Actions

The `Doxygen Documentation` workflow generates the HTML documentation and uploads it as a downloadable workflow artifact. It does not replace the existing MkDocs website workflow.

## Sharing with a reviewer

Send:

```text
Doxyfile
```

and optionally ZIP the generated HTML folder:

```powershell
Compress-Archive -Path .\docs\doxygen\html\* -DestinationPath .\AxiomBraid-2.0.0-Doxygen-HTML.zip -Force
```
