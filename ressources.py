# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

class Ressources:
    """
    Define the ressources of the FPGA
    LUT:              Number of LUT
    FF:               Number of FF
    DSP:              Number of DSP
    BRAM:             Number of BRAM
    partitioning_max: Partitioning max (usually 1024)
    """
    def __init__(self, data_type="float", DSP=6840):

        self.DSP = 6840
        if data_type == "float":
            self.sizeof = 32
        elif data_type == "double":
            self.sizeof = 64
        else:
            print("Data type not supported")
            exit(1)
        self.partitioning_max = 1024    
        self.ON_CHIP_MEM_SIZE = 1800000
        self.MAX_BUFFER_SIZE = 0  # i.e. no constraint if = 0

        self.DSP_per_operation = {}
        if self.sizeof == 32:
            self.DSP_per_operation = {"+": 2, "-":2, "*": 3, "=": 0,"/":0}
        elif self.sizeof == 64:
            self.DSP_per_operation = {"+": 3, "-":3, "*": 8, "=": 0,"/":0}

        self.IL = {}
        if self.sizeof == 32:
            self.IL = {"+": 7, "*": 6, "=": 1, "-":7, "/": 12}
        elif self.sizeof == 64:
            self.IL = {"+": 5, "*": 6, "=": 1, "-":5, "/": 12}
        