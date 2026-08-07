#!/bin/bash
# RF_ABM.sh
#
#SBATCH --account=def-nicoleli
#SBATCH --time=0-05:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=2000M
#SBATCH --output=RF_ABM_driver_%j.out
#SBATCH --error=RF_ABM_driver_%j.err
#SBATCH --mail-user=[email here]
#SBATCH --mail-type=END,FAIL
#
# Driver script for submitting a full Random Forest sensitivity sweep as
# individual cluster jobs, one job per sampled parameter set.
#
# Usage: sbatch RF_ABM.sh

set -euo pipefail
module load cuda

# -- Settings to edit --
N_SAMPLES=10              # Total number of RF sample runs (matches Part 1A/1B)
MAX_CONCURRENT_JOBS=900        # conservative job cap based on cluster's limit of 1000
POLL_INTERVAL_SECONDS=180       # How often to re-check the job queue while waiting
ABM_DIR="/path/to/ABM_DIR"      # Path to the ABM repo (contains bin/, configFiles/, etc.)
OUTPUT_DIR="./output"           # where each job writes its own job_[jobID]/ subfolder
OUTPUT_HOME_DIR="./output/output_home"  # where final per-sample CSVs are collected
EMAIL="your.email@mail.mcgill.ca" # required by submit_testrun.sh, but --quiet-mail
                                  # below suppresses notifications for the batch

# Associative array (bash "map") tracking which sample number each
# submitted job ID corresponds to. this gets populated as jobs
# are submitted below, and entries are removed once that job's output has
# been copied into output_home/ and its job_[jobID]/ folder deleted
declare -A PENDING_JOBS

# -d checks that the path exists AND is a directory (not a file)
if [ ! -d "$ABM_DIR" ]; then
    echo "Error: ABM directory '$ABM_DIR' does not exist."
    exit 1
fi

# copies the ABM executables folder from the ABM directory
echo "Copying bin/ from $ABM_DIR ..."
cp -r "$ABM_DIR/build/bin" ./build/bin

# copies the ABM config files folder from the ABM directory
echo "Copying configFiles/ from $ABM_DIR ..."
cp -r "$ABM_DIR/configFiles" ./configFiles

# copies the submit_testrun script(s) from /ABM-drectory/scripts/
echo "Copying scripts/ from $ABM_DIR ..."
cp -r "$ABM_DIR/scripts" ./scripts
chmod +x ./scripts/submit_testrun.sh # make sure it has run permission

# makes output directories
echo "Creating output directories ..."
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_HOME_DIR"

# helper to count how many of these jobs are currently queued and/or running
count_active_jobs() {
    # squeue: Slurm command that lists jobs.
    #   -u "$USER"  -> only show jobs belonging to the current user
    #   -h          -> "no header" (omit the column-header line so every
    #                  line of output is an actual job)
    #   -r          -> expand job arrays into one line per array element,
    #                  so array jobs are counted individually
    # wc -l counts the number of lines in squeue's output, i.e. the number
    # of currently active (queued or running) jobs for this user.
    squeue -u "$USER" -h -r | wc -l
}

# helper to see if a specific job ID is still queued/running
job_is_active() {
    local jobid="$1"
    # -j "$jobid" restricts squeue to just this one job ID.
    # 2>/dev/null suppresses the error squeue prints if the job ID is
    # already gone from the scheduler entirely (fully purged, not just
    # "completed but still listed") -- either way, no output means "not active".
    squeue -j "$jobid" -h 2>/dev/null | grep -q "$jobid"
}

# helper to process jobs that have finished since we last checked
# for every sample - job ID pair still in PENDING_JOBS, check whether
# that job is done. if so, copt its output CSV into output_home/ labelled
# by sample number, delete the job's job_[jobID] subfolder, and stop tracking
process_finished_jobs() {
    # "!PENDING_JOBS[@]" gives the array's keys (sample numbers); looping
    # over a copy of the keys is safe even though we remove entries below.
    for sample_num in "${!PENDING_JOBS[@]}"; do
        jobid="${PENDING_JOBS[$sample_num]}"

        # Skip (leave tracked) any job that's still queued or running.
        if job_is_active "$jobid"; then
            continue
        fi

        job_output_dir="${OUTPUT_DIR}/job_${jobid}"
        job_csv="${job_output_dir}/Output_Biomarkers.csv"

        if [ -f "$job_csv" ]; then
            # Copy (and rename) this sample's output CSV into output_home/,
            # labeled by sample number -- same intent as the old script's
            # "cp ./output/Output_Biomarkers.csv ./output/output_home/output_${c}.csv" line.
            cp -f "$job_csv" "${OUTPUT_HOME_DIR}/output_${sample_num}.csv"
            echo "  Collected output for sample $sample_num (job $jobid)."

            # Remove the now-redundant per-job folder so we don't end up
            # with one job_[jobID]/ subfolder left behind per sample.
            rm -rf "$job_output_dir"
        else
            # Job finished but no output CSV was found -- likely the run
            # failed/crashed. Flag it instead of silently losing the job ID,
            # so a failed sample doesn't just vanish unnoticed.
            echo "  Warning: job $jobid (sample $sample_num) finished but no output CSV found at $job_csv."
        fi

        # Stop tracking this sample/job now that it's been handled either way.
        unset "PENDING_JOBS[$sample_num]"
    done
}

# helper, wait until active job count drops below MAX_CONCURRENT_JOBS
wait_for_job_slot() {
    # Loop for as long as the current active job count is at or above the cap.
    # $(...) runs count_active_jobs and substitutes its printed output as a value.
    while [ "$(count_active_jobs)" -ge "$MAX_CONCURRENT_JOBS" ]; do
        # Print a timestamped status message so progress/waiting is visible
        # in the log if this script's output is redirected to a file.
        echo "  [$(date '+%Y-%m-%d %H:%M:%S')] Active jobs at or above cap ($MAX_CONCURRENT_JOBS). Waiting ${POLL_INTERVAL_SECONDS}s..."
        process_finished_jobs
        sleep "$POLL_INTERVAL_SECONDS" # pause before re-checking
    done
    # loop exits once count_active_jobs drops below the cap
}

for ((c=1; c<=N_SAMPLES; c++))
do
    # get this iteration's sampled config file
    SAMPLE_JSON="./samples/sample${c}.json"

    # -f checks that the path exists AND is a regular file. If a particular
    # sample is missing (e.g. Part 1B failed partway through), skip it with
    # a warning instead of letting the whole sweep crash on one bad file.
    if [ ! -f "$SAMPLE_JSON" ]; then
        echo "Warning: $SAMPLE_JSON not found, skipping sample $c."
        continue   # jump straight to the next loop iteration
    fi

    # Copy this sample's config into configFiles/, renaming it to
    # simulation_config.json in the process. The -f flag forces overwrite
    # of any existing file at that destination path without prompting --
    # this matters because every iteration writes to the same filename, so
    # each new sample must cleanly replace the previous one.
    cp -f "$SAMPLE_JSON" "./configFiles/simulation_config.json"

    # Before submitting the next job, check whether we're at/above the
    # concurrent job cap. If so, this call blocks (internally looping and
    # sleeping) until enough previously-submitted jobs have finished to
    # free up a slot -- this is what enforces the "batch of ~900, pause,
    # then continue" behavior requested.
    wait_for_job_slot

    # Status message so you can track progress in the terminal/log as the
    # sweep runs (5400 iterations would otherwise print nothing until done).
    echo "Submitting sample $c / $N_SAMPLES ..."

    # Submit this run as its own job, capturing its printed output (assumed
    # to include Slurm's standard "Submitted batch job <ID>" line) into a
    # variable instead of letting it print straight to the terminal.
    SUBMIT_OUTPUT="$(./submit_testrun.sh "$EMAIL" --quiet-mail --numticks 200 --time 0-00:45:00)"

    # Isolate just the "Submitted batch job <ID>" line (sbatch's standard
    # confirmation message, echoed verbatim by submit_testrun.sh), then pull
    # out only the trailing digits from that specific line.
    JOBID="$(echo "$SUBMIT_OUTPUT" | grep 'Submitted batch job' | grep -oE '[0-9]+$')"

    if [ -z "$JOBID" ]; then
        # If we couldn't parse a job ID, we have no way to later find and
        # collect this sample's output -- fail loudly rather than silently
        # losing track of a run.
        echo "Error: could not parse job ID from submit_testrun.sh output for sample $c:"
        echo "$SUBMIT_OUTPUT"
        exit 1
    fi

    echo "  -> submitted as job $JOBID"

    # Record this sample-number/job-ID pair so process_finished_jobs (called
    # while waiting for future slots, and in the final drain below) knows
    # to look for and collect this job's output once it completes.
    PENDING_JOBS[$c]="$JOBID"

done

# --- Step 4: final drain -- wait for all remaining submitted jobs ---------
# The main loop above only processes finished jobs opportunistically, while
# waiting for a submission slot to free up. Once the loop exits, there may
# still be tracked jobs (the last batch) that haven't finished yet -- so we
# keep checking and collecting until PENDING_JOBS is completely empty.
echo "All $NUM_SAMPLES sample jobs submitted. Waiting for remaining jobs to finish ..."
while [ "${#PENDING_JOBS[@]}" -gt 0 ]; do
    echo "  [$(date '+%Y-%m-%d %H:%M:%S')] ${#PENDING_JOBS[@]} job(s) still outstanding. Waiting ${POLL_INTERVAL_SECONDS}s..."
    process_finished_jobs
    # Only sleep if there's still something left to wait for -- avoids an
    # unnecessary final sleep after the very last job is collected.
    if [ "${#PENDING_JOBS[@]}" -gt 0 ]; then
        sleep "$POLL_INTERVAL_SECONDS"
    fi
done

echo "All sample outputs collected in ${OUTPUT_HOME_DIR}."
exit 0
