#!/usr/bin/env python3

import argparse
import subprocess
import sys
import time

PORT = "$PORT"
JOB_NAME = "$JOB_NAME"
NUM_NODES = "$NUM_NODES"
NCPUS_PER_NODE = "$NCPUS_PER_NODE"
PARTITION_SUBMIT = "$PARTITION_SUBMIT"
COMMAND_PLACEHOLDER = "$COMMAND_PLACEHOLDER"


def parse_args() -> argparse.Namespace:  # noqa: D103
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name",
        type=str,
        help="The job name and path to logging file (exp_name.log).",
    )
    parser.add_argument(
        "--cpu-per-node",
        "-cpu",
        type=int,
        default=1,
        help="Number of cpu for each nodes to use.",
    )
    parser.add_argument(
        "--partition",
        "-p",
        type=str,
        default="ihicnormal",
        help="The partition to submit.",
    )
    parser.add_argument(
        "--command",
        "-cmd",
        type=str,
        required=True,
        help="The command you wish to execute. For example: "
        " --command 'python test.py'. "
        "Note that the command must be a string.",
    )

    parser.add_argument(
        "--submit",
        action="store_true",
        help="If true, submit this job.",
    )

    return parser.parse_args()


text = """#!/bin/bash
# shellcheck disable=SC2206

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=$JOB_NAME
#SBATCH --output=$JOB_NAME.log
#SBATCH --partition=$PARTITION_SUBMIT
#SBATCH --cpus-per-task=$NCPUS_PER_NODE

eval "$(micromamba shell hook --shell bash)"
micromamba activate base
$COMMAND_PLACEHOLDER
"""


if __name__ == "__main__":
    args = parse_args()
    name = str(args.name)
    ncpus = int(args.cpu_per_node)
    assert ncpus >= 1, f"Invalid num_cpus: {ncpus}."
    partition = str(args.partition)
    command = str(args.command)

    # Modify Job Name:
    time_tag = time.strftime("%m%d-%H%M", time.localtime())
    job_name = f"{name}_1n{ncpus}c_{time_tag}"
    text = text.replace(JOB_NAME, job_name)
    text = text.replace(PARTITION_SUBMIT, str(partition))
    text = text.replace(COMMAND_PLACEHOLDER, str(command))
    text = text.replace(NCPUS_PER_NODE, str(ncpus))

    # ===== Save the script =====
    script_file = "{}.sh".format(job_name)
    with open(script_file, "w") as f:
        f.write(text)

    # ===== Submit the job =====
    if args.submit:
        print("Starting to submit job!")
        subprocess.Popen(["sbatch", script_file])
        print("Job submitted! ")
        sys.exit(0)
