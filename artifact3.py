# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

# load ampl
# load apptainer
# load llvm

kernels = ["atax_MEDIUM", "bicg_MEDIUM", "gemm_MEDIUM", "gemver_MEDIUM", "mvt_MEDIUM"]

RUN_VITIS = False
SOURCE_VITIS = "/opt/xilinx/tools/Vitis_HLS/2021.1/settings64.sh"
FOLDER = "vs_harp"

os.system(f"mkdir -p {FOLDER}")


cmd_src = f"module load apptainer; module load ampl; module load llvm; source {SOURCE_VITIS};"
cmd_ulimit = "ulimit -s unlimited;"
option = "--csim"
if RUN_VITIS:
    option += " --vitis"


for kernel in kernels:
    option += " --double"
    cmd_python = f"python3 main.py --file cfile_harp/{kernel}.c --folder {FOLDER}/{kernel} {option}"
    os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")
