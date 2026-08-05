#!/usr/bin/env bash
# add_application.sh — Add a historical job application to tracker + documents
set -euo pipefail

TRACKER="/home/swolf/Projects/ai-job-search/job_search_tracker.csv"
APP_DIR="/home/swolf/Projects/ai-job-search/documents/applications"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check tracker exists
if [[ ! -f "$TRACKER" ]]; then
    echo "Error: job_search_tracker.csv not found at $TRACKER" >&2
    exit 1
fi

echo "=== Add Historical Job Application ==="
echo ""

# Date first
read -rp "Date applied (YYYY-MM-DD): " date

# Job ad file
echo ""
echo "Provide a job ad text file to auto-extract sector, role type, and fit score."
read -rp "Path to job ad file (or press Enter to skip): " job_ad_path

job_ad_file=""
sector=""
role_type=""
fit_rating=""
analysis_gaps=""

if [[ -n "$job_ad_path" ]]; then
    # Expand ~ and resolve relative paths
    job_ad_path=$(eval echo "$job_ad_path")
    if [[ -f "$job_ad_path" ]]; then
        job_ad_file="job_posting.md"
        echo "  Analyzing job ad..."
        
        # Run Python analysis script
        analysis_output=$(python3 "${SCRIPT_DIR}/analyze_job.py" "$job_ad_path" 2>/dev/null || echo "")
        
        if [[ -n "$analysis_output" ]]; then
            # Parse output
            sector=$(echo "$analysis_output" | grep "^SECTOR=" | cut -d= -f2-)
            role_type=$(echo "$analysis_output" | grep "^ROLE_TYPE=" | cut -d= -f2-)
            fit_rating=$(echo "$analysis_output" | grep "^FIT_SCORE=" | cut -d= -f2-)
            analysis_gaps=$(echo "$analysis_output" | grep "^GAPS=" | cut -d= -f2-)
            analysis_matches=$(echo "$analysis_output" | grep "^MATCHES=" | cut -d= -f2-)
            
            echo "  Extracted: sector=${sector}, role_type=${role_type}, fit=${fit_rating}/100"
            if [[ -n "$analysis_gaps" ]]; then
                echo "  Gaps: ${analysis_gaps}"
            fi
        else
            echo "  Warning: Analysis script failed. Will ask for fields manually."
        fi
    else
        echo "  File not found: ${job_ad_path} — skipping."
        job_ad_path=""
    fi
fi

# Gather remaining inputs (with defaults from analysis)
echo ""
read -rp "Company: " company
read -rp "Role/Job title: " role

# Use extracted values as defaults, allow override
if [[ -n "$sector" ]]; then
    read -rp "Sector [${sector}]: " sector_input
    sector="${sector_input:-$sector}"
else
    read -rp "Sector/Industry: " sector
fi

if [[ -n "$role_type" ]]; then
    read -rp "Role type [${role_type}]: " role_type_input
    role_type="${role_type_input:-$role_type}"
else
    read -rp "Role type (Full-time/Part-time/Contract): " role_type
fi

read -rp "Channel applied through (LinkedIn/Company site/Referral/etc): " channel
read -rp "Status (applied/rejected/no_response/interview_only/offer_declined/hired): " status
read -rp "Contact person (or leave blank): " contact

# Fit rating
if [[ -n "$fit_rating" ]]; then
    read -rp "Fit rating [${fit_rating}/100]: " fit_input
    fit_rating="${fit_input:-$fit_rating}"
else
    read -rp "Fit rating 0-100 (or leave blank): " fit_rating
fi

read -rp "Notes (or leave blank): " notes
read -rp "Source of job listing (LinkedIn/Glassdoor/etc): " source

# Build folder name: lowercase, underscores for spaces
folder_name=$(echo "${company}_${role}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | sed 's/_\+/_/g' | sed 's/^_//;s/_$//')
folder_path="${APP_DIR}/${folder_name}"

# Create folder
if [[ -d "$folder_path" ]]; then
    echo "Folder already exists: ${folder_path}"
    read -rp "Continue anyway? (y/N): " confirm
    [[ "$confirm" != "y" && "$confirm" != "Y" ]] && exit 0
else
    mkdir -p "$folder_path"
    echo "Created: ${folder_path}"
fi

# Copy job ad if provided
if [[ -n "$job_ad_path" ]]; then
    cp "$job_ad_path" "${folder_path}/${job_ad_file}"
    echo "Copied job ad to: ${folder_path}/${job_ad_file}"
fi

# Create outcome.md
cat > "${folder_path}/outcome.md" <<EOF
# Application Outcome

**Company:** ${company}
**Role:** ${role}
**Date Applied:** ${date}
**Status:** ${status}
**Channel:** ${channel}
**Sector:** ${sector}
**Role Type:** ${role_type}
**Contact:** ${contact:-N/A}
**Fit Rating:** ${fit_rating:-N/A}/100

## Notes
${notes:-No additional notes.}

## Fit Analysis
$(if [[ -n "$analysis_gaps" ]]; then echo "Gaps: ${analysis_gaps}"; fi)
$(if [[ -n "$analysis_matches" ]]; then echo "Matches: ${analysis_matches}"; fi)
EOF

echo "Created: ${folder_path}/outcome.md"

# Append to CSV (escape commas in notes field)
escaped_notes=$(echo "$notes" | sed 's/,/;/g')
escaped_contact=$(echo "$contact" | sed 's/,/;/g')

echo "${date},${company},${sector},${role},${role_type},${channel},${status},${escaped_contact},${fit_rating:-},${escaped_notes},,," >> "$TRACKER"
echo "Appended row to job_search_tracker.csv"
echo ""
echo "Done! Folder: documents/applications/${folder_name}"
echo ""
echo "Optional next steps:"
echo "  - Add cover_letter.tex (if you have the original)"
echo "  - Add cv_draft.tex (if you used a tailored CV)"
