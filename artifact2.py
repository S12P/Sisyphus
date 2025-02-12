# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

# load ampl
# load apptainer
# load llvm

kernels = ["2mm_MEDIUM", "3mm_MEDIUM", "atax_MEDIUM", "bicg_MEDIUM"]

RUN_VITIS = False
SOURCE_VITIS = "/opt/xilinx/tools/Vitis_HLS/2023.2/settings64.sh"
FOLDER = "bitstream"

os.system(f"mkdir -p {FOLDER}")


cmd_src = f"module load apptainer; module load ampl; module load llvm; source {SOURCE_VITIS};"
cmd_ulimit = "ulimit -s unlimited;"
option = "--csim"
if RUN_VITIS:
    option += " --vitis"

# kernel = "atax_MEDIUM"
# curr_option = option + " --DSP 1804 --ON_CHIP_MEM_SIZE 453600 --MAX_BUFFER_SIZE 256"
# cmd_python = f"python3 main.py --file cfile/{kernel}.c --folder {FOLDER}/{kernel} {curr_option}"
# os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")

# kernel = "bicg_MEDIUM"
# curr_option = option + " --DSP 1804 --ON_CHIP_MEM_SIZE 453600 --MAX_BUFFER_SIZE 256"
# cmd_python = f"python3 main.py --file cfile/{kernel}.c --folder {FOLDER}/{kernel} {curr_option}"
# os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")

kernel = "2mm_MEDIUM"
curr_option = option + " --DSP 1300 --ON_CHIP_MEM_SIZE 360000 --partitioning_max 128"
curr_option += " --vitis_2021 --optimize_shape --no_optimistic_reuse"
cmd_python = f"python3 main.py --file cfile/{kernel}.c --folder {FOLDER}/{kernel} {curr_option}"
os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")

# kernel = "3mm_MEDIUM"
# curr_option = option + " --DSP 1300 --ON_CHIP_MEM_SIZE 360000 --MAX_BUFFER_SIZE 128"
# curr_option += " --vitis_2021 --no_optimistic_reuse --reuse_nlp"
# curr_option += " --optimize_shape"
# cmd_python = f"python3 main.py --file cfile/{kernel}.c --folder {FOLDER}/{kernel} {curr_option}"
# os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")


