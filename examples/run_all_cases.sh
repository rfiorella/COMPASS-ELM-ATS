#!/usr/bin/env bash
#
# Build and run all three configurations (ELM, ELM+ATS IC, ELM-ATS) for a
# given example in parallel Docker containers, then optionally generate
# comparison plots.
#
# Usage:
#   ./run_all_cases.sh --example oakharbor_column [options]
#   ./run_all_cases.sh --example oakharbor_transect --ntasks 2 [options]
#
# Options:
#   --example NAME    Example directory under examples/ (required)
#   --case-name NAME  Override case name for output paths (default: same as
#                     --example, or --example.np<NTASKS> for transects)
#   --ntasks N        Number of MPI tasks (default: 1)
#   --output-dir DIR  Host directory for output (default: <repo>/output)
#   --hist-file h0|h1 History stream for plots (default: h0)
#   --no-plots        Skip comparison plot generation
#   --build-only      Build Docker image and exit
#
# The host output directory is mounted into the container at
# /home/amanzi_user/work (the container's E3SM_WORK_DIR).
# CIME writes run output to:
#   <output-dir>/output/<case-name>.{elm,ic_only,elm-ats}/run/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME=compass-elm-ats:run
EXAMPLE=
CASE_NAME=
NTASKS=1
OUTPUT_DIR="${REPO_ROOT}/output"
HIST_FILE=h0
RUN_PLOTS=true
BUILD_ONLY=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case $1 in
        --example)    EXAMPLE="$2"; shift 2 ;;
        --case-name)  CASE_NAME="$2"; shift 2 ;;
        --ntasks)     NTASKS="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --hist-file)  HIST_FILE="$2"; shift 2 ;;
        --no-plots)   RUN_PLOTS=false; shift ;;
        --build-only) BUILD_ONLY=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ -z "${EXAMPLE}" ]; then
    echo "Error: --example is required"
    echo "Available examples:"
    ls -d "${SCRIPT_DIR}"/*/  | xargs -n1 basename
    exit 1
fi

if [ ! -d "${SCRIPT_DIR}/${EXAMPLE}" ]; then
    echo "Error: example directory '${EXAMPLE}' not found under ${SCRIPT_DIR}/"
    exit 1
fi

# Derive case name if not explicitly set.
# Transect cases append .np<NTASKS> to the case name.
if [ -z "${CASE_NAME}" ]; then
    # Check if the per-case build_example.sh uses NTASKS in CASE_NAME
    if grep -q 'np${NTASKS}' "${SCRIPT_DIR}/${EXAMPLE}/build_example.sh" 2>/dev/null; then
        CASE_NAME="${EXAMPLE}.np${NTASKS}"
    else
        CASE_NAME="${EXAMPLE}"
    fi
fi

echo "Example:   ${EXAMPLE}"
echo "Case name: ${CASE_NAME}"
echo "NTASKS:    ${NTASKS}"
echo ""

# ---------------------------------------------------------------------------
# Build the Docker image
# ---------------------------------------------------------------------------
echo "=== Building Docker image ==="
docker build \
    -f "${REPO_ROOT}/Docker/Dockerfile-run" \
    -t "${IMAGE_NAME}" \
    "${REPO_ROOT}"

if [ "${BUILD_ONLY}" = true ]; then
    echo "Image built. Exiting (--build-only)."
    exit 0
fi

# ---------------------------------------------------------------------------
# Run three cases in parallel
# ---------------------------------------------------------------------------
mkdir -p "${OUTPUT_DIR}"

# Container E3SM_WORK_DIR — must match the ENV in Dockerfile-run
CONTAINER_WORK=/home/amanzi_user/work

declare -A PIDS
declare -A SUFFIXES=( [elm]=FALSE [ic_only]=IC_ONLY [elm-ats]=TRUE )

for SUFFIX in elm ic_only elm-ats; do
    USE_ATS_VAL="${SUFFIXES[$SUFFIX]}"
    CONTAINER_NAME="${CASE_NAME}-${SUFFIX}"

    echo "=== Launching ${CONTAINER_NAME} (USE_ATS=${USE_ATS_VAL}) ==="

    docker run --rm \
        --name "${CONTAINER_NAME}" \
        -e USE_ATS="${USE_ATS_VAL}" \
        -e NTASKS="${NTASKS}" \
        -v "${OUTPUT_DIR}:${CONTAINER_WORK}" \
        "${IMAGE_NAME}" \
        bash -c "cd /home/amanzi_user/compass/examples/${EXAMPLE} && ./build_example.sh" \
        > "${OUTPUT_DIR}/${SUFFIX}.log" 2>&1 &

    PIDS[$SUFFIX]=$!
    echo "  PID ${PIDS[$SUFFIX]} -> ${SUFFIX}.log"
done

# ---------------------------------------------------------------------------
# Wait for all containers
# ---------------------------------------------------------------------------
echo ""
echo "=== Waiting for all cases to finish ==="
FAILED=0
for SUFFIX in elm ic_only elm-ats; do
    if wait "${PIDS[$SUFFIX]}"; then
        echo "  ${SUFFIX}: SUCCESS"
    else
        echo "  ${SUFFIX}: FAILED (see ${OUTPUT_DIR}/${SUFFIX}.log)"
        FAILED=1
    fi
done

if [ "${FAILED}" -ne 0 ]; then
    echo ""
    echo "One or more cases failed. Check logs in ${OUTPUT_DIR}/"
    exit 1
fi

# ---------------------------------------------------------------------------
# Generate comparison plots
# ---------------------------------------------------------------------------
if [ "${RUN_PLOTS}" = true ]; then
    echo ""
    echo "=== Generating comparison plots ==="
    python "${SCRIPT_DIR}/compare_simulations.py" \
        --base-dir "${OUTPUT_DIR}" \
        --case-name "${CASE_NAME}" \
        --hist-file "${HIST_FILE}" \
        --output-dir "${OUTPUT_DIR}/figures"
    echo "Figures saved to ${OUTPUT_DIR}/figures/"
fi

echo ""
echo "=== Done ==="
