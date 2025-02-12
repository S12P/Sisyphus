# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import numpy as np
import generate_csim
import re

def replace_i_not_in_word(statement, var, replacement):
    # Regular expression pattern to match 'i' when it's not part of a word
    pattern = rf'(?<![a-zA-Z0-9_]){var}(?![a-zA-Z0-9_])'

    # Replace occurrences of 'i' using the pattern
    replaced_statement = re.sub(pattern, replacement, statement)

    return replaced_statement

class GenerateCodeComputation:
    def __init__(self, data_type, fold, cfile, nlp_file, log_file):
        self.data_type = data_type
        self.fold = fold
        self.cfile = cfile
        self.nlp_file = nlp_file
        self.log_file = log_file
        
        
        self.lines_cfile = self.readfile(self.cfile)
        self.lines_nlp_file = self.readfile(self.nlp_file)
        self.lines_log_file = self.readfile(self.log_file)
        self.schedule = []
        self.iterators = {}
        self.is_red = {}
        self.cte = []
        self.extract_cte()
        self.compute_schedule()
        self.log = {}
        self.size_on_chip = {}
        self.extract_log()
        self.statements = []
        self.which_loop_iterate_array_dim = {}
        self.compute_which_loop_iterate_array_dim()
        self.extract_statements()
        is_one_statement_per_loop_body = self.check_one_statement_per_loop_body()
        # if is_one_statement_per_loop_body:
        self.generate_code()

    def compute_which_loop_iterate_array_dim(self):
        for line in self.lines_nlp_file:
            if "#loop" in line and "iterates" in line:
                id_loop = int(line.split("loop_")[-1].split(" iterates")[0])
                id_array = line.split("Array ")[-1].split(" in")[0]
                id_dim = int(line.split("in dim ")[-1].replace("\n", ""))
                self.which_loop_iterate_array_dim[id_array] = {}
        for line in self.lines_nlp_file:
            if "#loop" in line and "iterates" in line:
                id_loop = int(line.split("loop_")[-1].split(" iterates")[0])
                id_array = line.split("Array ")[-1].split(" in")[0]
                id_dim = int(line.split("in dim ")[-1].replace("\n", ""))
                self.which_loop_iterate_array_dim[id_array][id_dim] = [] 
        for line in self.lines_nlp_file:
            if "#loop" in line and "iterates" in line:
                id_loop = int(line.split("loop_")[-1].split(" iterates")[0])
                id_array = line.split("Array ")[-1].split(" in")[0]
                id_dim = int(line.split("in dim ")[-1].replace("\n", ""))
                if id_loop not in self.which_loop_iterate_array_dim[id_array][id_dim]:
                    self.which_loop_iterate_array_dim[id_array][id_dim] += [id_loop]

    def extract_cte(self):
        for line in self.lines_cfile:
            if "void" in line:
                line = line.split("(")[-1].split(")")[0]
                l = line.split(",")
                for cte in l:
                    if "[" not in cte:
                        self.cte.append(cte.replace(f"{self.data_type}", "").replace(" ", ""))


    def extract_statements(self):
        for line in self.lines_cfile:
            if "=" in line and f"{self.data_type}" not in line and "int" not in line and "for" not in line and "//" not in line:
                l = line.replace("\n", "").replace(" ", "")
                self.statements.append(l)

    def readfile(self, file):
        f = open(file, "r")
        lines = f.readlines()
        f.close()
        return lines
    
    def extract_log(self):
        for line in self.lines_log_file:
            if "=" in line:
                l = line.split("=")
                l[0] = l[0].replace(" ", "")
                l[1] = l[1].replace(" ", "").replace("\n", "")
                self.log[l[0]] = l[1].replace("\n", "")
    
    def find_permutation(self, id_, sched):
        perm = ""
        for line in self.lines_log_file:
            if f"perm" in line and f"S{id_}" in line and "= 1" in line:
                perm = line.split("=")[0].replace(" ", "")
        for line in self.lines_nlp_file:
            if f"var {perm} binary" in line:
                l = line.split("#")[-1].replace("\n", "").replace(" ", "").replace("(", "").replace(")", "").split(",")
                while "" in l:
                    l.remove("")
                for k in range(len(l)):
                    sched[2*k+1] = l[k]

        return sched



    def compute_schedule(self):
        id_iterator = 0
        current_sched = []
        for line in self.lines_nlp_file:
            if "#schedule" in line:
                line = line.replace("#schedule ", "").replace("\n", "")
                l = line.split(" ")
                current_sched = l
                self.schedule.append(l)
            if "#iterators" in line:
                line = line.replace("#iterators ", "").replace("\n", "")
                l = line.split(" ")
                for k in range(1, len(current_sched), 2):
                    self.iterators[current_sched[k]] = l[(k-1)//2]
            if "#loop" in line and "Array" not in line:
                l, b = line.split(":=")
                b = b.replace("\n", "").replace(" ", "")
                b = eval(b)
                l = l.replace("#loop_", "").replace("\n", "").replace(" ", "")
                self.is_red[l] = b

        for k in range(len(self.schedule)):
            self.schedule[k] = self.find_permutation(k, self.schedule[k])

    def check_one_statement_per_loop_body(self):
        loops = []
        for k in range(len(self.schedule)):
            loops += self.schedule[k][1::2]
        for loop in loops:
            if loops.count(loop) > 1:
                return False
        return True

    def compute_tab(self, n):
        str_ = ""
        for k in range(n):
            str_ += "    "
        return str_

    def write_load(self, arr, original_name, size, size_burst, burst_size, it_dim):
        lines = []
        tab = ""
        arg = []
        size_str = list(map(str, size))
        arg += [f"{self.data_type} {original_name}[{']['.join(size_str)}]"]

        arg += [f"{self.data_type}{burst_size} v{original_name}[{size_burst}]"]
        nb_loop = len(size)
        for dim in it_dim:
            arg += [f"int d{dim}"]
        lines += [f"void load_{arr} ({', '.join(arg)}) {{\n"]
        lines += [f"#pragma HLS inline off\n"]
        UB = {}
        for k in range(nb_loop):
            tab += "    "
            lb = 0
            ub = size[k]
            UB[k] = ub
            inc = 1

            if k == nb_loop - 1:
                inc = burst_size
            
            lines += [f"{tab}for (int i{k} = {lb}; i{k} < {ub}; i{k}+={inc}){{\n"]
        lines += [f"#pragma HLS pipeline II=1\n"]
        tab += "    "
        curr_size = 1
        if nb_loop - 1 in it_dim:
            id_vector = [f"(i{nb_loop-1} + d{nb_loop-1} * {UB[k]})/{burst_size}"]
        else:
            id_vector = [f"i{nb_loop-1}/{burst_size}"]
        if burst_size == "":
            burst_size = 1
        arr_name = arr.split("_S")[0]
        curr_size = self.size_array_per_dim[arr_name][nb_loop-1]//burst_size


        for k in range(nb_loop-2, -1, -1):
            if k in it_dim:
                id_vector = [f"(i{k} + d{k} * {UB[k]}) * {curr_size}"] + id_vector
            else:
                id_vector = [f"i{k} * {curr_size}"] + id_vector
            curr_size *= size[k]

        id_vector = " + ".join(id_vector)
        lines += [f"{tab}{self.data_type}{burst_size} tmp_{original_name} = v{original_name}[{id_vector}];\n"]
        for bb in range(burst_size):
            str_ = ""
            for k in range(nb_loop):
                if k == nb_loop - 1:
                    str_ += f"[i{k} + {bb}]"
                else:
                    str_ += f"[i{k}]"
            lines += [f"{tab}{original_name}{str_} = tmp_{original_name}[{bb}];\n"]
        for k in range(nb_loop):
            tab = tab[:-4]
            lines += [f"{tab}}}\n"]
        lines += [f"}}\n"]
        
        return lines

    def write_store(self, arr, original_name, size, size_burst, burst_size, it_dim):
        lines = []
        tab = ""
        arg = []
        size_str = list(map(str, size))
        arg += [f"{self.data_type} {original_name}[{']['.join(size_str)}]"]

        arg += [f"{self.data_type}{burst_size} v{original_name}[{size_burst}]"]
        nb_loop = len(size)
        for dim in it_dim:
            arg += [f"int d{self.schedule[0][dim]}"]
        lines += [f"void store_{arr} ({', '.join(arg)}) {{\n"]
        lines += [f"#pragma HLS inline off\n"]
        UB = {}
        for k in range(nb_loop):
            tab += "    "
            lb = 0
            ub = size[k]
            UB[k] = ub
            inc = 1

            if k == nb_loop - 1:
                inc = burst_size
            
            lines += [f"{tab}for (int i{k} = {lb}; i{k} < {ub}; i{k}+={inc}){{\n"]
        lines += [f"#pragma HLS pipeline II=1\n"]
        tab += "    "
        curr_size = 1
        if nb_loop - 1 in it_dim:
            id_vector = [f"(i{nb_loop-1} + d{nb_loop-1} * {UB[k]})/{burst_size}"]
        else:
            id_vector = [f"i{nb_loop-1}/{burst_size}"]
        arr_name = arr.split("_S")[0]
        curr_size = self.size_array_per_dim[arr_name][nb_loop-1]//burst_size

        for k in range(nb_loop-2, -1, -1):
            if k in it_dim:
                id_vector = [f"(i{k} + d{k} * {UB[k]}) * {curr_size}"] + id_vector
            else:
                id_vector = [f"i{k} * {curr_size}"] + id_vector
            curr_size *= size[k]

        id_vector = " + ".join(id_vector)
        lines += [f"{tab}{self.data_type}{burst_size} tmp_{original_name};\n"]
        for bb in range(burst_size):
            str_ = ""
            for k in range(nb_loop):
                if k == nb_loop - 1:
                    str_ += f"[i{k} + {bb}]"
                else:
                    str_ += f"[i{k}]"
            lines += [f"{tab}tmp_{original_name}[{bb}] = {original_name}{str_};\n"]
        lines += [f"{tab}v{original_name}[{id_vector}] = tmp_{original_name};\n"]
        for k in range(nb_loop):
            tab = tab[:-4]
            lines += [f"{tab}}}\n"]
        lines += [f"}}\n"]
        
        return lines

    def extract_tasks(self, id_task, lines):
        nb_bracket = 0
        inside = False
        begin = 0
        end = 0
        for id_, line in enumerate(lines):
            if f"void task{id_task}" in line:
                inside = True
                begin = id_
            if inside:
                if "{" in line:
                    nb_bracket += 1
                if "}" in line:
                    nb_bracket -= 1
                if nb_bracket == 0:
                    inside = False
                    end = id_
                    break
        return begin, end+1, lines[begin:end+1]

    def generate_code(self):
        self.size_array = {}
        self.size_array_per_dim = {}

        lines = []
        tasks = []
        arrays_on_chip = []

        lines += ["#include <ap_int.h>\n"]
        lines += ["#include <hls_stream.h>\n"]
        lines += ["#include <hls_vector.h>\n"]
        lines += ["#include <cstring>\n"]
        lines += ["\n"]
        lines += [f"typedef hls::vector<{self.data_type},16> {self.data_type}16;\n"]
        lines += [f"typedef hls::vector<{self.data_type},8> {self.data_type}8;\n"]
        lines += [f"typedef hls::vector<{self.data_type},4> {self.data_type}4;\n"]
        lines += [f"typedef hls::vector<{self.data_type},2> {self.data_type}2;\n"]
        lines += [f"typedef hls::vector<{self.data_type},1> {self.data_type}1;\n"]
        lines += ["\n"]
        for k in range(len(self.schedule)):
            arg = []
            nb_loop = 0
            lines += [f"void task{k}({' ,'.join(arg)}) {{\n"]
            for j in range(1, len(self.schedule[k]), 2):
                it = self.iterators[self.schedule[k][j]]
                lines += [f"    int {it};\n"]
            for tile_level in range(3):
                for j in range(1, len(self.schedule[k]), 2):
                    it = f"{self.iterators[self.schedule[k][j]]}{tile_level}"
                    loop = self.schedule[k][j]
                    ub = self.log[f"TC{loop}_{tile_level}"]
                    if tile_level == 1 and self.log[f"is_loop{loop}_pip"] == "0":
                        pass
                    else:
                        lines += [f"{self.compute_tab(nb_loop+1)}for (int {it} = 0; {it} < {ub}; {it}++) {{\n"]
                        if tile_level == 2:
                            lines += ["#pragma HLS unroll\n"]
                        elif tile_level == 1:
                            lines += ["#pragma HLS pipeline\n"]
                    
                        nb_loop += 1
            for j in range(1, len(self.schedule[k]), 2):
                it = f"{self.iterators[self.schedule[k][j]]}"
                loop = self.schedule[k][j]
                if self.log[f"is_loop{loop}_pip"] == "0":
                    str_ = f"{it} = {it}0 * {self.log[f'TC{loop}_2']} + {it}2;"
                else:
                    val = int(self.log[f'TC{loop}_2']) * int(self.log[f'TC{loop}_1'])
                    str_ = f"{it} = {it}0 * {val} + {it}1 * {self.log[f'TC{loop}_2']} + {it}2;"
                lines += [f"{self.compute_tab(nb_loop+1)}{str_}\n"]
            lines += [f"{self.compute_tab(nb_loop+1)}{self.statements[k]}\n"]
            for j in range(nb_loop):
                lines += [f"{self.compute_tab(nb_loop-j)}}}\n"]
            lines += [f"}}\n\n"]
        
        lines += ["void kernel_nlp() {\n"]
        lines += ["\n"]
        arrays = []
        for key in list(self.log.keys()):
            if "AP" in key:
                dd = key.split("_")
                dim = dd[-1]
                var = "_".join(dd[1:-1])
                if var not in arrays:
                    arrays.append(var)
        for cte in self.cte:
            lines += [f"#pragma HLS INTERFACE m_axi port={cte} offset=slave bundle=kernel_{cte}\n"]
        for arr in arrays:
            lines += [f"#pragma HLS INTERFACE m_axi port=v{arr} offset=slave bundle=kernel_{arr}\n"]
        for cte in self.cte:
            lines += [f"#pragma HLS INTERFACE s_axilite port={cte} bundle=control\n"]
        for arr in arrays:
            lines += [f"#pragma HLS INTERFACE s_axilite port=v{arr} bundle=control\n"]
        lines += [f"#pragma HLS INTERFACE s_axilite port=return bundle=control\n"]
        lines += ["\n"]
        input_for_statement = {}
        output_for_statement = {}
        for k in range(len(self.schedule)):
            input_for_statement[k] = []
            output_for_statement[k] = []
        
        for arr in arrays:
            tot_trans = False
            under_loop = ""
            stat = 0
            possi = []
            for line in self.lines_log_file:
                if f"transfer_{arr}_total" in line and "1" in line:
                    tot_trans = True
                elif not tot_trans and f"transfer_{arr}" in line and "under" in line and "= 1" in line:
                    under_loop = line.split("loop")[-1].split("=")[0].replace(" ", "")
                    stat = int(line.split("S")[-1].split("_")[0])
                    possi += [(under_loop, stat)]
            size = []
            partial_size = []
            
            for line in self.lines_nlp_file:
                if "#Size" in line and "array" in line and f"{arr}:" in line:
                    size = line.replace("\n", "").split(":")[-1].replace(" ", "").replace("[", "").replace("]", "")
                    size = size.split(",")
                    self.size_array[arr] = np.prod(list(map(int, size)))
                    self.size_array_per_dim[arr] = list(map(int, size))

                    
                    if not tot_trans:
                        
                        for y, pos in enumerate(possi):
                            under_loop = int(pos[0])
                            stat = pos[1]
                            size_ = size.copy()
                            for l in range(1, len(self.schedule[stat]), 2):
                                curr_loop = int(self.schedule[stat][l])
                                
                                for dim in list(self.which_loop_iterate_array_dim[arr].keys()):
                                    if curr_loop in self.which_loop_iterate_array_dim[arr][dim]:
                                        size_[dim] = int(size_[dim])
                                        size_[dim] = size_[dim] // int(self.log[f"TC{curr_loop}_0"])

                                        
                                if curr_loop == under_loop:
                                    break
                            possi[y] = (under_loop, stat, size_)
                            deja_vu = False
                            gg = 0
                            for g in range(stat):
                                size_ = list(map(str, size_))
                                if f"{self.data_type} {arr}_S{g}[{']['.join(size_)}];\n" in lines:
                                    gg = g
                                    deja_vu = True
                            size_ = list(map(str, size_))
                            is_write = False
                            if arr in self.statements[stat].split("=")[0]:
                                is_write = True
                            if deja_vu:
                                input_for_statement[stat] += [f"{self.data_type} {arr}_S{gg}[{']['.join(size_)}];\n"]

                                if is_write:
                                    output_for_statement[stat] += [f"{self.data_type} {arr}_S{gg}[{']['.join(size_)}];\n"]
                            else:
                                lines += [f"    {self.data_type} {arr}_S{stat}[{']['.join(size_)}];\n"]
                                arrays_on_chip += [f"{arr}_S{stat}"]
                                input_for_statement[stat] += [f"{self.data_type} {arr}_S{stat}[{']['.join(size_)}];\n"]
                                if f"{arr}_S{stat}" not in list(self.size_on_chip.keys()):
                                    self.size_on_chip[f"{arr}_S{stat}"] = {}
                                for kkk2, ddd2 in enumerate(size_):
                                    if kkk2 in list(self.size_on_chip[f"{arr}_S{stat}"].keys()):
                                        self.size_on_chip[f"{arr}_S{stat}"][kkk2] = min(ddd2, self.size_on_chip[f"{arr}_S{stat}"][kkk2])
                                    else:
                                        self.size_on_chip[f"{arr}_S{stat}"][kkk2] = ddd2
                                if is_write:
                                    output_for_statement[stat] += [f"{self.data_type} {arr}_S{stat}[{']['.join(size_)}];\n"]
            
            if tot_trans:
                lines += [f"    {self.data_type} {arr}[{']['.join(size)}];\n"]
                arrays_on_chip += [f"{arr}"]
                for k in range(len(self.schedule)):
                    for j in range(1, len(self.schedule[k]), 2):
                        for ll in self.lines_nlp_file:

                            if f"#loop_{self.schedule[k][j]} iterates Array {arr}" in ll:
                                if f"{self.data_type} {arr}[{']['.join(size)}];\n" not in input_for_statement[k]:
                                    input_for_statement[k] += [f"{self.data_type} {arr}[{']['.join(size)}];\n"]
                                    is_write = False
                                    if arr in self.statements[k].split("=")[0]:
                                        is_write = True
                                    if is_write:
                                        output_for_statement[k] += [f"{self.data_type} {arr}[{']['.join(size)}];\n"]
        lines += ["\n"]

        
        for k in range(len(self.schedule)):
            for c in self.cte:
                input_for_statement[k] += [f"{self.data_type} {c}"]
        
        last_dim = {}
        burst_size = {}
        for arr in arrays:
            last_dim[arr] = []
        
        for key in list(input_for_statement.keys()):
            for dec in range(len(input_for_statement[key])):
                if "[" not in input_for_statement[key][dec]:
                    continue
                arr = input_for_statement[key][dec].split(" ")[1].split("[")[0]
                last_dim_ = 0
                if "][" in input_for_statement[key][dec]:
                    last_dim_ = input_for_statement[key][dec].split("][")[-1].split("]")[0]
                else:
                    last_dim_ = input_for_statement[key][dec].split("[")[-1].split("]")[0]

                curr_arr = arr
                for k in range(30):
                    curr_arr = curr_arr.replace(f"_S{k}", "")

                last_dim[curr_arr] += [int(last_dim_)]
        for key in list(last_dim.keys()):
            pos = last_dim[key]
            for burst in [16, 8, 4, 2, 1]:
                all_divide = True
                for p in pos:
                    if  int(p) % burst != 0:
                        all_divide = False
                if all_divide:
                    burst_size[key] = burst
                    break

        arg = []


        original_arg = []
        last_void = ""
        for ll in self.lines_cfile:
            if "void" in ll:
                last_void = ll.replace("\n", "").split("(")[-1].split(")")[0].split(",")
        
        for elemt in last_void:
            for cte in self.cte:
                if cte in elemt:
                    arg += [f"{self.data_type} {cte}"]
            for arr in arrays:
                if arr == elemt.split("[")[0].replace(f"{self.data_type}", "").replace(" ", ""):
                    size = self.size_array[arr] // burst_size[arr]

                    arg += [f"{self.data_type}{str(burst_size[arr])} v{arr}[{str(size)}]"]
        
        for k, line in enumerate(lines):
            if "void kernel_nlp() {\n" in lines[k]:
                lines[k] = f"void kernel_nlp({', '.join(arg)}) {{\n"

        for key in list(self.log.keys()):
            if "AP" in key:
                tab = self.compute_tab(1)
                dd = key.split("_")
                dim = dd[-1]
                var = "_".join(dd[1:-1])
                factor = self.log[key]
                for arr2 in arrays_on_chip:
                    if var == arr2:
                        lines += [f"#pragma HLS ARRAY_PARTITION variable={var} cyclic factor={factor} dim={int(dim)+1}\n"]
                    elif var in arr2:

                        lines += [f"#pragma HLS ARRAY_PARTITION variable={arr2} cyclic factor={factor} dim={int(dim)+1}\n"]
        
        lines += ["\n"]
        for k in range(len(self.schedule)):
            tab = self.compute_tab(1)
            inputt = []
            for l in input_for_statement[k]:
                inputt += [l.replace(f'{self.data_type}', '').replace(' ', '').replace('\n', '').split('[')[0]]
            arg2 = []
            arg3 = []
            for a in arg:
                if "[" in a:
                    arg2 += [a.split(' ')[1].split("[")[0]]
                    arg3 += [a]
            inputt = ', '.join(inputt + arg2)
            tasks += [f"{tab}task{k}({inputt});\n"]
            for kk, ll in enumerate(lines):
                if f"void task{k}() {{\n" in lines[kk]:
                    tmpp = [0 for kkk in range(len(input_for_statement[k]))]
                    for kkk in range(len(input_for_statement[k])):
                        tmpp[kkk] = input_for_statement[k][kkk].replace(";", "").replace("\n", "")
                        for s in range(30):
                            tmpp[kkk] = tmpp[kkk].replace(f"_S{s}", "")
                    
                    lines[kk] = f"void task{k}({', '.join(tmpp + arg3)}) {{\n"
        

        
        
        load_lines = []
        write_lines = []
        load_already_seen = []
        deja_vu = []

        for key in list(input_for_statement.keys()):
            for elemt in input_for_statement[key]:
                if "[" not in elemt:
                    continue
                name = elemt.split(" ")[1].split("[")[0]
                original_name = name
                for t in range(30):
                    original_name = original_name.replace(f"_S{t}", "") 
                size = elemt[elemt.index("[")+1:].split("];")[0]
                size = size.split("][")
                size = list(map(int, size))
                it_dim = []
                for id_, ss in enumerate(size):
                    if ss != self.size_array_per_dim[original_name][id_]:
                        it_dim += [id_]
                burst_size_ = burst_size[original_name]
                if burst_size_ == "":
                    burst_size_ = 1
                buffer_size = int(self.size_array[original_name]) // int(burst_size_)
                ll = self.write_load(name, original_name, size, buffer_size, burst_size_, it_dim)
                if ll not in deja_vu:
                    load_lines += ll
                    deja_vu += [ll]
                if elemt in output_for_statement[key]:
                    ll = self.write_store(name, original_name, size, buffer_size, burst_size_, it_dim)
                    if ll not in deja_vu:
                        write_lines += ll
                        deja_vu += [ll]

        
        lines = lines[:10] + ["\n"] + load_lines + write_lines + lines[10:]

        deja_vu_load = []
        deja_vu_store = []
        for k in range(len(tasks)):
            for load in input_for_statement[k]:
                if "[" in load and "_S" not in load and load not in deja_vu_load:
                    name = load.split(" ")[1].split("[")[0]
                    lines += [f"    load_{name}({name}, v{name});\n"]
                    deja_vu_load += [load]
            lines += [tasks[k]]
            for write in output_for_statement[k]:
                in_an_other_statement = False
                for kk in range(len(tasks)):
                    if kk > k:
                        if write in output_for_statement[kk]:
                            in_an_other_statement = True
                if not in_an_other_statement:
                    if "[" in write and "_S" not in write and write not in deja_vu_store:
                        name = write.split(" ")[1].split("[")[0]
                        lines += [f"    store_{name}({name}, v{name});\n"]
                        deja_vu_store += [write]
        
        for k in range(len(tasks)):
            begin, end, lines_task = self.extract_tasks(k, lines)

            new_task = lines_task
            
            for arr in input_for_statement[k]:
                if "[" in arr:
                    name = arr.split(" ")[1].split("[")[0]
                    original_name = name.split("_S")[0]
                    if original_name != name:
                        nb_for = 0
                        arg_dim = [0 for y in range(len(self.which_loop_iterate_array_dim[original_name]))]
                        for j, line in enumerate(new_task):
                            if "for" in line:
                                nb_for += 1
                                it_loop = line.split("int ")[1].split(" =")[0]
                                for w in range(10):
                                    it_loop = it_loop.replace(f"{w}", "")
                                id_loop = 0
                                for u in range(1, len(self.schedule[k]), 2):
                                    if self.iterators[self.schedule[k][u]] == it_loop:
                                        id_loop = self.schedule[k][u]

                                for dim in list(self.which_loop_iterate_array_dim[original_name].keys()):

                                    if int(id_loop) in self.which_loop_iterate_array_dim[original_name][dim]:
                                        if int(self.log[f"TC{id_loop}_0"]) > 1:
                                            arg_dim[dim] = f"{self.iterators[id_loop]}0"

                                if f"transfer_{original_name}_S{k}_under_loop{id_loop}" in list(self.log.keys()):
                                    if self.log[f"transfer_{original_name}_S{k}_under_loop{id_loop}"] == "1":
                                        tab = "    "
                                        for h in range(nb_for):
                                            tab += "    "
                                        if len(arg_dim) == 0:
                                            new_task = new_task[:j+1] + [f"{tab}load_{name}({original_name}, v{original_name});\n"] + new_task[j+1:]
                                        else:
                                            while 0 in arg_dim:
                                                arg_dim.remove(0)
                                            new_task = new_task[:j+1] + [f"{tab}load_{name}({original_name}, v{original_name}, {', '.join(arg_dim)});\n"] + new_task[j+1:]
                                        
                                        
                                        for jj, line_ in enumerate(new_task):
                                            if jj > j:
                                                if "=" in line_ and "for" not in line_ and "if" not in line_:
                                                    stat = line_.replace(";", "").replace("\n", "")
                                        
                                        
                                        break
                                

            lines = lines[:begin] + new_task + lines[end:]
        


        for k in range(len(tasks)):
            begin, end, lines_task = self.extract_tasks(k, lines)

            new_task = lines_task
            
            for arr in output_for_statement[k]:
                arg_dim = []
                if "[" in arr:
                    name = arr.split(" ")[1].split("[")[0]
                    original_name = name.split("_S")[0]
                    
                    nb_bracket = 0
                    see_at_least_loop_or_statement = False
                    inside = False
                    tab = "    "
                    for j, line in enumerate(new_task):
                        if not inside and "for" in line:
                            tab += "    "
                        if inside and ("for" in line or "=" in line):
                            see_at_least_loop_or_statement = True
                        if f"load_{name}" in line:
                            inside = True
                            arg_dim = line.split("(")[-1].split(")")[0].split(", ")[2:]
                        if inside:
                            if "{" in line:
                                nb_bracket += 1
                            if "}" in line:
                                nb_bracket -= 1
                            if nb_bracket == 0 and see_at_least_loop_or_statement:
                                if len(arg_dim) == 0:
                                    new_task = new_task[:j+1] + [f"{tab}store_{name}({original_name}, v{original_name});\n"] + new_task[j+1:]
                                else:
                                    new_task = new_task[:j+1] + [f"{tab}store_{name}({original_name}, v{original_name}, {', '.join(arg_dim)});\n"] + new_task[j+1:]
                                break
            
            lines = lines[:begin] + new_task + lines[end:]
        
        for k in range(len(tasks)):
            
            it_of_schedule = []
            for j in range(1, len(self.schedule[k]), 2):
                it = self.iterators[self.schedule[k][j]]
                it_of_schedule += [it]
            begin, end, lines_task = self.extract_tasks(k, lines.copy())

            new_task = lines_task.copy()

            
            
            it_until_now = []
            array_iterated_by = {}
            declaration = {}
            nb_loop = 0
            for id_, line in enumerate(new_task):
                if "for" in line and "=" in line:
                    it = line.split("int ")[1].split(" =")[0]
                    it_until_now += [it.replace("0", "")]
                    nb_loop += 1
                if "load_" in line:
                    name = line.split("load_")[1].split("_S")[0]
                    array_iterated_by[name] = it_until_now.copy()
                if "=" in line and "for" not in line and "if" not in line:
                    out = line.split("=")[0].replace(" ", "")
                    if out in it_of_schedule:
                        declaration[out] = " + ".join(line.replace(";", "").replace("\n", "").replace(" ", "").split("=")[1].split("+")[1:])
                    else:
                        arr_out = []
                        arr_in = []
                        op = []
                        eq = "="
                        ll = line.replace(";", "").replace("\n", "").replace(" ", "")
                        if "+=" in ll:
                            eq = "+="
                        elif "-=" in ll:
                            eq = "-="
                        elif "*=" in ll:
                            eq = "*="
                        elif "/=" in ll:
                            eq = "/="
                        arr_out += [ll.split(eq)[0]]
                        curr_array = ""
                        inside_bracket = False
                        if "[" not in ll.split(eq)[1]:
                            arr_in += [ll.split(eq)[1]]
                        else:
                            seen_a_bracket = False
                            lll=ll.split(eq)[1]
                            for id2, elemt in enumerate(lll):
                                if elemt == "[":
                                    seen_a_bracket = True
                                    inside_bracket = True
                                if elemt == "]":
                                    inside_bracket = False
                                
                                if not inside_bracket and elemt in ["+", "-", "*", "/"]:
                                    op += [elemt]
                                    if curr_array != "":
                                        arr_in += [curr_array]
                                        curr_array = ""
                                        seen_a_bracket = False
                                else:
                                    curr_array += elemt
                                if seen_a_bracket and not inside_bracket and curr_array != "":
                                    if id2 < len(lll)-2:
                                        if lll[id2+1] != "[":
                                            arr_in += [curr_array]
                                            curr_array = ""
                                            seen_a_bracket = False
                                    else:
                                        arr_in += [curr_array]
                                        curr_array = ""
                                        seen_a_bracket = False
                            if curr_array != "":
                                arr_in[-1] += curr_array

                        for id3, o in enumerate(arr_out):
                            if o.split("[")[0] in list(array_iterated_by.keys()):

                                name = o.split("[")[0]
                                for itt in array_iterated_by[name]:
                                    arr_out[id3] = replace_i_not_in_word(o, itt, declaration[itt])
                        for id3, o in enumerate(arr_in):
                            if o.split("[")[0] in list(array_iterated_by.keys()):

                                name = o.split("[")[0]
                                for itt in array_iterated_by[name]:

                                    arr_in[id3] = replace_i_not_in_word(o, itt, declaration[itt])
                        op += [";\n"]
                        new_stat = ""
                        new_stat = f"{arr_out[0]} {eq}"

                        for id3, o in enumerate(arr_in):
                            new_stat += f"{o} "
                            if id3 < len(op):
                                new_stat += f"{op[id3]} "
                        if "\n" not in new_stat:
                            new_stat += "\n"
                        tab = "    "
                        for g in range(nb_loop):
                            tab += "    "
                        new_task[id_] = f"{tab}{new_stat}"

            
            lines = lines[:begin] + new_task + lines[end:]


        lines += ["}\n"]



        f = open(f"{self.fold}/code_generated.cpp", "w")
        f.writelines(lines)
        f.close()



