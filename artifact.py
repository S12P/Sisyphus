# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

# load ampl
# load apptainer
# load llvm

kernels = ["2mm_MEDIUM", "3mm_MEDIUM", "atax_MEDIUM", "bicg_MEDIUM", "bert_100_64", "bert_100_768", "bert_100_3072", "bert_3072_100", "cnn", "doitgen_MEDIUM", "gemm_MEDIUM", "gemver_MEDIUM", "gesummv_MEDIUM", "heat-3d_MEDIUM", "jacobi-2d_MEDIUM", "mvt_MEDIUM", "symm_MEDIUM", "syrk_MEDIUM", "syr2k_MEDIUM", "trmm_MEDIUM"]

RUN_VITIS = False
SOURCE_VITIS = "/opt/xilinx/tools/Vitis_HLS/2023.2/settings64.sh"
FOLDER_TREE = "with_tree"
FOLDER_WITHOUT_TREE = "without_tree"

os.system(f"mkdir -p {FOLDER_TREE}")
os.system(f"mkdir -p {FOLDER_WITHOUT_TREE}")


cmd_src = f"module load apptainer; module load ampl; module load llvm; source {SOURCE_VITIS};"
cmd_ulimit = "ulimit -s unlimited;"
option = "--csim"
if RUN_VITIS:
    option += " --vitis"


for kernel in kernels:
    cmd_python = f"python3 main.py --file cfile/{kernel}.c --folder {FOLDER_TREE}/{kernel} {option}"
    os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")

for kernel in kernels:
    option += " --no_tree_reduction"
    cmd_python = f"python3 main.py --file cfile/{kernel}.c --folder {FOLDER_WITHOUT_TREE}/{kernel} {option}"
    os.system(f"{cmd_src} {cmd_ulimit} {cmd_python}")