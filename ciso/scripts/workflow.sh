#!/usr/bin/env bash
set -Eeuo pipefail

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
REPORT_DIR="./vuln-reports/${TIMESTAMP}"
mkdir -p "$REPORT_DIR"

echo "════════════════════════════════════════════════════════════"
echo "  VULNERABILITY REMEDIATION WORKFLOW"
echo "  Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"
echo

# ─── Step 1: Pre-remediation report ──────────────────────────────────────────

echo "[1/5] Generating PRE-remediation report..."
PRE_REPORT="$REPORT_DIR/pre_vulnerability_report.txt"
sudo bash ./vulnerability_report.sh --pre 2>&1 | tee "$PRE_REPORT"
echo "✓ Pre-report saved: $PRE_REPORT"
echo

# ─── Step 2: Dry-run the fix script ──────────────────────────────────────────

echo "[2/5] Running DRY-RUN of fix script..."
DRY_RUN_REPORT="$REPORT_DIR/dryrun_fix_vulnerable_apps.txt"
sudo bash ./fix_vulnerable_apps.sh --dry-run 2>&1 | tee "$DRY_RUN_REPORT"
echo "✓ Dry-run report saved: $DRY_RUN_REPORT"
echo

# ─── Step 3: Apply fixes ─────────────────────────────────────────────────────

echo "[3/5] Applying fixes to vulnerable apps..."
APPLY_REPORT="$REPORT_DIR/apply_fix_vulnerable_apps.txt"
sudo bash ./fix_vulnerable_apps.sh --apply 2>&1 | tee "$APPLY_REPORT"
echo "✓ Apply report saved: $APPLY_REPORT"
echo

# ─── Step 4: Post-remediation report ─────────────────────────────────────────

echo "[4/5] Generating POST-remediation report..."
POST_REPORT="$REPORT_DIR/post_vulnerability_report.txt"
sudo bash ./vulnerability_report.sh --post 2>&1 | tee "$POST_REPORT"
echo "✓ Post-report saved: $POST_REPORT"
echo

# ─── Step 5: Diff report ─────────────────────────────────────────────────────

echo "[5/5] Generating DIFF report (pre vs post)..."
DIFF_REPORT="$REPORT_DIR/diff_vulnerability_report.txt"
sudo bash ./vulnerability_report.sh --diff 2>&1 | tee "$DIFF_REPORT"
echo "✓ Diff-report saved: $DIFF_REPORT"
echo

# ─── Summary ──────────────────────────────────────────────────────────────────

echo "════════════════════════════════════════════════════════════"
echo "  WORKFLOW COMPLETE"
echo "════════════════════════════════════════════════════════════"
echo
echo "📋 Generated Reports:"
echo "  • Pre-remediation  : $PRE_REPORT"
echo "  • Dry-run analysis : $DRY_RUN_REPORT"
echo "  • Apply fixes log  : $APPLY_REPORT"
echo "  • Post-remediation : $POST_REPORT"
echo "  • Diff comparison  : $DIFF_REPORT"
echo
echo "📁 All reports stored in: $REPORT_DIR"
echo
echo "🔍 View reports:"
echo "  cat $PRE_REPORT"
echo "  cat $POST_REPORT"
echo "  cat $DIFF_REPORT"
echo
echo "✉️  Send to cybersec team:"
echo "  tar -czf remediation-reports-${TIMESTAMP}.tar.gz $REPORT_DIR/"
echo