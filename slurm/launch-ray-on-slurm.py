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
        "--num-nodes",
        "-n",
        type=int,
        default=1,
        help="Number of nodes to use.",
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
        "--port",
        "-P",
        type=str,
        default="6379",
        help="The port used by Ray.",
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

#SBATCH --ntasks-per-node=1
#SBATCH --nodes=$NUM_NODES
#SBATCH --job-name=$JOB_NAME
#SBATCH --output=$JOB_NAME.log
#SBATCH --partition=$PARTITION_SUBMIT
#SBATCH --cpus-per-task=$NCPUS_PER_NODE
#SBATCH --exclusive

# Load modules or your own conda environment here
eval "$(micromamba shell hook --shell bash)"
micromamba activate base



# ===== DO NOT CHANGE THINGS HERE UNLESS YOU KNOW WHAT YOU ARE DOING =====
# This script is a modification to the implementation suggest by gregSchwartz18 here:
# https://github.com/ray-project/ray/issues/826#issuecomment-522116599
redis_password=$(uuidgen)
export redis_password
nodes=$(scontrol show hostnames "$SLURM_JOB_NODELIST") # Getting the node names
nodes_array=($nodes)
node_1=${nodes_array[0]}
ip=$(srun --nodes=1 --ntasks=1 -w "$node_1" hostname --ip-address) # making redis-address



# if we detect a space character in the head node IP, we'll
# convert it to an ipv4 address. This step is optional.
if [[ "$ip" == *" "* ]]; then
  IFS=' ' read -ra ADDR <<< "$ip"
  if [[ ${#ADDR[0]} -gt 16 ]]; then
    ip=${ADDR[1]}
  else
    ip=${ADDR[0]}
  fi
  echo "IPV6 address detected. We split the IPV4 address as $ip"
fi
port=$PORT
ip_head=$ip:$port
export ip_head
echo "IP Head: $ip_head"



echo "STARTING HEAD at $node_1"
srun --nodes=1 --ntasks=1 -w "$node_1" \
  ray start --head --node-ip-address="$ip" --port=$port --redis-password="$redis_password" --block &
sleep 30



worker_num=$((SLURM_JOB_NUM_NODES - 1)) #number of nodes other than the head node
for ((i = 1; i <= worker_num; i++)); do
  node_i=${nodes_array[$i]}
  echo "STARTING WORKER $i at $node_i"
  srun --nodes=1 --ntasks=1 -w "$node_i" ray start --address "$ip_head" --redis-password="$redis_password" --block &
  sleep 5
done

# ===== Call your code below =====
$COMMAND_PLACEHOLDER
"""


if __name__ == "__main__":
    args = parse_args()
    name = str(args.name)
    port = int(args.port)
    nnodes = int(args.num_nodes)
    ncpus = int(args.cpu_per_node)
    assert 5000 < port and port < 65536, f"Invalid port: {port}."
    assert nnodes >= 1, f"Invalid num_nodes: {nnodes}."
    assert ncpus >= 1, f"Invalid num_cpus: {ncpus}."
    partition = str(args.partition)
    command = str(args.command)

    # Modify Job Name:
    time_tag = time.strftime("%m%d-%H%M", time.localtime())
    job_name = f"{name}_{nnodes}n{ncpus}c_{time_tag}"
    text = text.replace(JOB_NAME, job_name)
    text = text.replace(NUM_NODES, str(nnodes))
    text = text.replace(PARTITION_SUBMIT, str(partition))
    text = text.replace(COMMAND_PLACEHOLDER, str(command))
    text = text.replace(NCPUS_PER_NODE, str(ncpus))
    text = text.replace(PORT, str(port))
    if int(args.cpu_per_node) < 28:
        text = text.replace("#SBATCH --exclusive", "")

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
