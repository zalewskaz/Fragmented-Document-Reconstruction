#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

shopt -s nullglob
FILES=(md/*.md)

if [ ${#FILES[@]} -eq 0 ]; then
    exit 1
fi

pandoc "${FILES[@]}" -o engineering_project_report.docx

pandoc "${FILES[@]}" -o engineering_project_report.pdf --pdf-engine=pdflatex 2>/dev/null || \
pandoc "${FILES[@]}" -o engineering_project_report.pdf --pdf-engine=weasyprint

pandoc "${FILES[@]}" -s -o engineering_project_report.tex