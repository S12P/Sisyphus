# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import numpy as np
import islpy as isl
from sympy import simplify
from sympy.abc import i

def unique_list_in_order(l1):
    l2 = []
    for l in l1:
        if l not in l2:
            l2.append(l)
    return l2




CYCLIC_BUFFER = False

class Node:
    def __init__(self, value, string, l, kind, depth, it=None, lb=None, ub=None, is_innermost=None, is_reduction=None):
        self.value = value
        self.string = string
        self.l = l
        self.kind = kind
        self.depth = depth
        self.l += [self]
        self.children = []
        self.aready_seen = False
        self.it = it
        self.lb = lb
        self.ub = ub
        self.is_innermost = is_innermost
        self.is_reduction = is_reduction

    def add_child(self, child):
        self.children.append(child)

    def __str__(self):

        str_ = f"Node: {self.value}"
        str_ += "-> Child ["
        if self.children:

            for child in self.children:
                str_ += f"{child} "
        str_ += "]"
        return str_


class AST:
    def __init__(self, data_type, schedule, UB, LB, statements, iterators, output, headers, arguments, name_function, pragmas, pragmas_top, optimize_burst, burst_dataflow, analysis, normale_file, CB, array_need_more_than_one_copy, sched_need_different_copy_par_array, condition_copy_array_between_statement, array_need_complete_copy_inside_task,  array_need_partial_copy_inside_task,  array_dont_need_copy_per_schedule, code_gen):
        self.schedule = schedule
        self.iterator_cyclic = {}
        self.output_array = {}
        self.normale_file = normale_file
        self.should_reduce = {}
        self.UB = UB
        self.LB = LB
        self.code_gen = code_gen

        self.array_need_more_than_one_copy = array_need_more_than_one_copy
        self.sched_need_different_copy_par_array = sched_need_different_copy_par_array
        self.condition_copy_array_between_statement = condition_copy_array_between_statement
        self.array_need_complete_copy_inside_task = array_need_complete_copy_inside_task
        self.array_need_partial_copy_inside_task = array_need_partial_copy_inside_task
        self.array_dont_need_copy_per_schedule = array_dont_need_copy_per_schedule
        
        self.optimize_burst = optimize_burst
        self.burst_dataflow = burst_dataflow
        self.statements = statements
        self.iterators = iterators
        self.output = output
        self.headers = headers
        self.limit_IL = 4
        self.transfer_totally = {}
        self.condition_fifo = {}
        self.arguments = arguments
        self.analysis = analysis
        self.UB_ = self.analysis.UB_
        self.LB_ = self.analysis.LB_
        for k in range(len(self.schedule)):
            self.transfer_totally[k] = {}
            self.condition_fifo[k] = {}
            stat = self.statements[k]
            out, inp = self.extract_array_and_constant(stat)
            for in_ in inp + [out]:
                self.condition_fifo[k][in_] = ""
        try:
            self.compute_condition_fifo()
        except:
            pass
        

        
        for i, it in enumerate(self.schedule):
            self.iterator_cyclic[i] = {}
            self.output_array[i] = ""
            self.should_reduce[i] = False

        self.name_function = name_function
        self.pragmas = pragmas
        self.pragmas_top = pragmas_top
        self.tab = "    "
        self.data_type = data_type
        self.list_nodes = []
        self.array_need_reuse = {}
        self.level_read = {}

        self.array_information = {}
        self.compute_arrays_information()

        self.compute_not_copy()

        self.tree = Node("Root",  "", self.list_nodes, "Root", 0)
        self.compute()
        
        self.order = []
        self.write_order(self.tree)

        self.order_per_loop_body = []

        if CB:
            self.write_order_per_loop_body_cyclic_buffer(self.tree)
        else:

            self.write_order_per_loop_body(self.tree)

    def compute_condition_fifo(self):
        last_view = {}
        stat_for_array = {}
        corresponding_array = {}
        for id_stat in list(self.condition_fifo.keys()):
            last_view[id_stat] = {}
            corresponding_array[id_stat] = {}
            for arr in list(self.condition_fifo[id_stat].keys()):
                stat_for_array[arr] = []
                corresponding_array[id_stat][arr] = ""
                self.condition_fifo[id_stat][arr] = ""

        for id_stat in list(self.condition_fifo.keys()):
            for arr in list(self.condition_fifo[id_stat].keys()):
                stat_for_array[arr] += [id_stat]

        for id_stat in list(self.condition_fifo.keys()):
            for arr in list(self.condition_fifo[id_stat].keys()):
                index = stat_for_array[arr].index(id_stat)
                if index > 0:
                    last_view[id_stat][arr] = stat_for_array[arr][index-1]

        for id_stat in list(self.condition_fifo.keys()):
            sched = self.schedule[id_stat]
            read = self.analysis.dic[id_stat]["read"]
            write = self.analysis.dic[id_stat]["write"]
            arr_corespond = ""
            for arr in list(self.condition_fifo[id_stat].keys()):
                arr = arr.replace("(", "").replace(")", "").replace("sqrt", "")
                is_float = False
                try:
                    float(arr)
                    is_float = True
                except:
                    pass
                if is_float:
                    continue
                for arr2 in read + write:
                    if arr2.split('[')[0].replace(" ", "") == arr.replace(" ", ""):
                        arr_corespond = arr2
                        break
                corresponding_array[id_stat][arr] = arr_corespond
                iterators = self.extract_iterator(arr_corespond)
                dim_array = arr2.count("[")
                if len(list(set(iterators))) < dim_array:

                    lv = last_view[id_stat][arr]
                    previous_call = corresponding_array[lv][arr]
                    previous_iterators = self.extract_iterator(previous_call)
                    cond = []
                    for k1, it1 in enumerate(iterators):
                        for k2, it2 in enumerate(previous_iterators):
                            if it1 != it2:
                                if f"{it1} == {it2}" not in cond:
                                    cond.append(f"{it1} == {it2}")

                    self.condition_fifo[lv][arr] = " && ".join(cond)


    def extract_size_array(self, arg):
        if "[" in arg:
            index = arg.index("[")
            arg = arg[index:]
            arg = arg.replace("][", "*")
            arg = arg.replace("[", "")
            arg = arg.replace("]", "")
            return eval(arg)
        return 1
    
    def extract_size_array_dim(self, arg):
        if "[" in arg:
            index = arg.index("[")
            arg = arg[index:]
            arg = arg.replace("][", "*")
            arg = arg.replace("[", "")
            arg = arg.replace("]", "")
        return arg.split("*")

    def compute_arrays_information(self):
        all_arrays = []
        for stat in self.statements:
            if "=" in stat:
                out, inp = stat.split("=")
                out = out.strip().split("[")[0]
                inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
                all_arrays += [out] 
                all_arrays += inp
        all_arrays = unique_list_in_order(all_arrays)
        for arr in all_arrays:
            self.array_information[arr] = {"size": 0, "type": "", "W": [], "size_burst": 0, "size_vector": 0, "statements": [], "dim": 0, "loop_to_dim": {}, "part_per_dim": [], "size_per_dim": [], "iterators":{}, "polyhedron":{}, "intersection":{}, "polyhedron_size": {}, "access":{}}
            for i, stat in enumerate(self.statements):
                out, inp = stat.split("=")
                out = out.strip().split("[")[0]
                if f"{arr}[" in stat:
                    self.array_information[arr]["statements"].append(i)
                if f"{arr}" in out:
                    self.array_information[arr]["W"].append(i)
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                self.array_information[arr]["iterators"][id_stat] = []
                self.array_information[arr]["polyhedron"][id_stat] = []
                self.array_information[arr]["polyhedron_size"][id_stat] = []
                self.array_information[arr]["access"][id_stat] = []
                self.array_information[arr]["intersection"][id_stat] = []
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                stat = self.statements[id_stat]
                out, inp = self.extract_array_and_constant(stat, False)
                all_ = [out] + inp
                for id_, al_ in enumerate(all_):
                    if al_.split("[")[0] == arr:

                        for k in range(0, 10):
                            al_ = al_.replace(f"{k}", "")
                        if "[" in al_:
                            it = al_[al_.index("[") + 1:-1].split("][")
                            self.array_information[arr]["iterators"][id_stat].append(it)
                            if ("+=" in stat or "-=" in stat or "*=" in stat or "/=" in stat) and id_ == 0: # output
                                self.array_information[arr]["iterators"][id_stat].append(it)
        for arr in all_arrays:
            for arg in self.arguments:
                if arr in arg:
                    self.array_information[arr]["type"] = arg.split(" ")[0].strip()
                    self.array_information[arr]["size"] = self.extract_size_array(arg)
                    self.array_information[arr]["size_per_dim"] = self.extract_size_array_dim(arg)
                    self.array_information[arr]["dim"] = arg.count("[")
                    self.array_information[arr]["part_per_dim"] = [1 for k in range(self.array_information[arr]["dim"])]
                    break
        for arr in all_arrays:
            for stat in self.array_information[arr]["statements"]:
                it_per_dim = []
                ss = self.multi_split(self.statements[stat].replace(";", "").replace(" ", ""), ["+", "-", "*", "/", "="])
                ss = unique_list_in_order(ss)
                for s in ss:
                    tmp = ["" for k in range(self.array_information[arr]["dim"])]
                    if f"{arr}[" in s:
                        index = s.index(f"[")
                        s = s[index:]
                        s = s.replace("][", "*")
                        s = s.replace("[", "")
                        s = s.replace("]", "")
                        tmp = s.split("*")
                        it_per_dim.append(tmp)
                loop_to_it = {}
                for i in range(1, len(self.schedule[stat]), 2):
                    loop = int(self.schedule[stat][i])
                    it = self.iterators[loop]
                    loop_to_it[loop] = it
                it_to_loop = {v: k for k, v in loop_to_it.items()}
                for i, it in enumerate(it_per_dim):
                    for j, it_ in enumerate(it):
                        if it_ in loop_to_it:
                            it_per_dim[i][j] = it_to_loop[it_]
                        

                for pos in range(len(it_per_dim)):
                    for dim in range(len(it_per_dim[pos])):
                        self.array_information[arr]["loop_to_dim"][it_per_dim[pos][dim]] = dim
                for pos in range(len(it_per_dim)):
                    for dim in range(len(it_per_dim[pos])):
                        loop = it_per_dim[pos][dim]
                        if type(loop) == str:
                            continue
                        pragma_loop = self.pragmas[loop]
                        if pragma_loop != [""]:
                            if ";" in pragma_loop:
                                pragma_loop = pragma_loop.split(";")
                                for p in pragma_loop:
                                    if "unroll" in p.lower():
                                        factor = p.split("=")[-1].strip().replace(" ", "")
                                        self.array_information[arr]["part_per_dim"][dim] = max(self.array_information[arr]["part_per_dim"][dim], int(factor))
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                for i, it in enumerate(self.array_information[arr]["iterators"][id_stat]):
                    try:
                        var1 = []
                        var2 = []
                        cond_arr1 = []
                        cond_arr2 = []
                        for j, it_ in enumerate(it):
                            if it_ != "":
                                cond_arr1.append(f"0 <= {it_} < {self.array_information[arr]['size_per_dim'][j]}")
                                var1.append(f"{it_}")
                        cond_arr2 += self.analysis.dic[id_stat]["constraint"]
                        for conf in self.analysis.dic[id_stat]["constraint"]:
                            conf = conf.replace(" ", "").replace("+", "@").replace("-", "@").replace("0", "@").replace("1", "@").replace("2", "@").replace("3", "@").replace("4", "@").replace("5", "@").replace("6", "@").replace("7", "@").replace("8", "@").replace("9", "@").replace("=", "@").replace("<", "@").replace(">", "@")
                            conf = conf.split("@")
                            while "" in conf:
                                conf.remove("")
                            
                            var2 += conf
                        var1 = unique_list_in_order(var1)
                        var2 = unique_list_in_order(var2)
                        var = var1 + var2
                        while "" in var:
                            var.remove("")
                        var = unique_list_in_order(var)
                        cond1 = " and ".join(cond_arr1)
                        cond2 = " and ".join(cond_arr2)
                        # sort var
                        var1 = sorted(var1)
                        var2 = sorted(var2)
                        var = sorted(var)
                        str_1 = f"[{', '.join(var)}] -> {{ [{', '.join(var)}] :{cond1} }}"
                        str_2 = f"[{', '.join(var)}] -> {{ [{', '.join(var)}] :{cond2} }}"
                        poly1 = isl.Set(str_1)
                        poly2 = isl.Set(str_2) #domain

                        poly = {} #poly1.intersect(poly2) 
                        self.array_information[arr]["polyhedron"][id_stat].append(poly)
                        self.array_information[arr]["access"][id_stat].append(f"{arr}[{']['.join(it)}]")
                        self.array_information[arr]["polyhedron_size"][id_stat].append(0)
                    except:
                        pass
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                self.array_information[arr]["intersection"][id_stat] = {}
                for k1, elmt1 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                    self.array_information[arr]["intersection"][id_stat][k1] = {}
                    for k2, elmt2 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                        if k2!=k1:
                            self.array_information[arr]["intersection"][id_stat][k1][k2] = 0
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                for k1, elmt1 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                    for k2, elmt2 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                        if k2!=k1:
                            intersection = {} 
                            self.array_information[arr]["intersection"][id_stat][k1][k2] = intersection




    def compute(self):
        for i, stat in enumerate(self.schedule):
            str_statement = self.statements[i]
            for j in range(1, len(stat), 2):
                loop = int(self.schedule[i][j])
                it = self.iterators[loop]
                lb = self.LB_[loop]
                ub = self.UB_[loop]
                if loop not in [x.value for x in self.list_nodes]:
                    loop_str = self.create_tab((j-1)//2+1) + self.create_loop(it, f"{lb}", f"{ub}+1", self.schedule[i][j]) 
                if j == 1:
                    if loop not in [x.value for x in self.list_nodes]:
                        is_innermost = False
                        if j == len(stat)-2:
                            is_innermost = True
                        is_reduction = False
                        node = Node(loop, loop_str, self.list_nodes, "Loop", (j-1)//2+1, it, lb, ub, is_innermost, is_reduction)
                        self.tree.add_child(node)
                else:
                    if loop not in [x.value for x in self.list_nodes]:
                        is_innermost = False
                        if j == len(stat)-2:
                            is_innermost = True
                        is_reduction = False
                        node = Node(loop, loop_str, self.list_nodes, "Loop", (j-1)//2+1, it, lb, ub, is_innermost, is_reduction)
                        parent = int(self.schedule[i][j-2])
                        parent_node = [x for x in self.list_nodes if x.value == parent][0]

                        parent_node.add_child(node)
            if ";" not in str_statement:
                str_statement += ";"
            str_statement = self.create_tab((len(stat)-1)//2+1) + str_statement
            node_statement = Node(f"S{i}", str_statement, self.list_nodes, "Statement", (len(stat)-1)//2+1)
            if len(stat) > 1:
                parent_node = [x for x in self.list_nodes if x.value == int(self.schedule[i][-2])][0]
                parent_node.add_child(node_statement)
            else:
                self.tree.add_child(node_statement)
    def create_loop(self, it, lb, ub, id_=None, inc=None):
        str_ = ""
        try:
            ub = eval(ub)
        except:
            try:
                ub = simplify(ub)
            except:
                pass
        try:
            lb = eval(lb)
        except:
            try:
                lb = simplify(lb)
            except:
                pass
        try:
            ub = int(ub)
        except:
            pass
        try:
            lb = abs(int(lb))
        except:
            pass
        if id_ != None:
            if self.pragmas_top:
                for p in self.pragmas[id_].split(";"):
                    if p != "":
                        str_ += f"#pragma ACCEL {p}\n"
        if "i - 1" in str(lb):
            lb = str(lb).replace("-", "+")
        if self.normale_file:
            if inc is not None:
                str_ += f"for ( {it} = {lb}; {it} < {ub}; {it}+={inc}) {{\n"
            else:
                str_ += f"for ( {it} = {lb}; {it} < {ub}; {it}++) {{\n"
        else:
            if inc is not None:
                str_ += f"for (int {it} = {lb}; {it} < {ub}; {it}+={inc}) {{\n"
            else:
                str_ += f"for (int {it} = {lb}; {it} < {ub}; {it}++) {{\n"
        if id_ != None:
            if not self.pragmas_top:
                if ";" in self.pragmas[id_]:
                    for p in self.pragmas[id_].split(";"):
                        if p != "":
                            str_ += f"#pragma HLS {p}\n"
        str_ = str_[:-1]
        return str_

    def create_tab(self, nb):
        nb = max(0,nb)
        return self.tab * nb

    def print_ast(self):
        print(self.tree)

    def write_order(self, tree):
        tree.aready_seen = True
        if tree.kind == "Statement":
            if tree.string.split("=")[-1].replace(" ", "") == ";":
                tree.string = tree.string.replace(";", "")
                tree.string = tree.string + "0;"
            self.order.append(tree.string)
        elif tree.kind == "Loop":
            self.order.append(tree.string)
            for child in tree.children:
                if not child.aready_seen:
                    self.write_order(child)
            tab = self.create_tab(tree.depth)
            self.order.append(f"{tab}}}")
        else: # Root
            for child in tree.children:
                self.write_order(child)

    def reinit(self):
        for node in self.list_nodes:
            node.aready_seen = False

    def replace_increment(self, loop, burst_dataflow):
        loop = loop.replace("++", f"+={burst_dataflow}")
        return loop

    def write_order2(self, tree, out, id_stat, depth):
        self.reinit()
        tree.aready_seen = True
        if tree.kind == "Statement":
            if self.optimize_burst:
                # DATAFLOW
                str_ = self.transform_statement_dataflow_burst(tree.string, id_stat, depth)
            else:
                str_ = self.transform_statement(tree.string, id_stat, depth)
            out.append(str_)
        elif tree.kind == "Loop":
            if self.optimize_burst and depth == (len(self.schedule[id_stat])-1)//2-1:
                out.append(self.replace_increment(tree.string, self.burst_dataflow))
            else:
                out.append(tree.string)
            if depth == (len(self.schedule[id_stat])-1)//2-1:
                out.append("#pragma HLS pipeline II=1")
            for key in list(self.level_read[id_stat].keys()):
                if self.level_read[id_stat][key] == depth:
                    tab = self.create_tab(tree.depth+1)
                    if key in self.array_need_reuse[id_stat]: 
                        if (not self.from_off_chip[id_stat][key] or id_stat == 0):
                            pass
                    else:
                        if key in self.nameR[id_stat]:
                            out.append("// read 1\n")
                            if key in list(self.transfer_totally[id_stat].keys()):
                                continue
                            if self.optimize_burst:

                                if depth != (len(self.schedule[id_stat])-1)//2-1:
                                    it_last_dim_array = ""
                                    it_array = self.array_information[key]["iterators"][id_stat][0]
                                    for sche in self.schedule[id_stat]:
                                        if self.analysis.iterators[sche] in it_array:
                                            it_last_dim_array = self.analysis.iterators[sche]
                                    
                                    tabp1 = self.create_tab(tree.depth+2)
                                    out.append(f"{tab}{self.data_type}{self.burst_dataflow} v{key};")
                                    out.append(f"{tab}if ({it_last_dim_array} % {self.burst_dataflow} == 0) {{")
                                    out.append(f"{tabp1}v{key} = {self.nameR[id_stat][key]}.read();")
                                    out.append(f"{tab}}}")
                                    out.append(f"{tab}{self.data_type} {key} = v{key}[{it_last_dim_array} % {self.burst_dataflow}];")
                                else:
                                    out.append(f"{tab}{self.data_type}{self.burst_dataflow} {key} = {self.nameR[id_stat][key]}.read();")
                            else:
                                out.append(f"{tab}{self.data_type} {key} = {self.nameR[id_stat][key]}.read();")
                        else:
                            if self.optimize_burst:
                                out.append(f"{tab}{self.data_type}{self.burst_dataflow} {key};")
                            else:
                                out.append(f"{tab}{self.data_type} {key};")
            for child in tree.children:
                if not child.aready_seen:
                    self.write_order2(child, out, id_stat, depth+1)

            for key in list(self.level_read[id_stat].keys()):
                if self.level_read[id_stat][key] == depth:
                    tab = self.create_tab(tree.depth+1)
                    if key in self.array_need_reuse[id_stat]:
                        pass
                    else:
                        if key in self.nameW[id_stat]:
                            tab = self.create_tab(tree.depth+1)
                            if key not in self.transfer_totally[id_stat]:
                                out.append(f"// write 1 {id_stat} {key} ")
                                if key in list(self.array_dont_need_copy_per_schedule.keys()) and id_stat in self.array_dont_need_copy_per_schedule[key]:
                                    continue
                                if self.optimize_burst and depth != (len(self.schedule[id_stat])-1)//2-1:
                                    it = self.iterators[int(self.schedule[id_stat][2*(depth+1)-1])]
                                    out.append(f"{tab}v{key}[{it} % {self.burst_dataflow}] = {key};")
                                    tabp1 = self.create_tab(tree.depth+2)
                                    out.append(f"{tab}if ({it} % {self.burst_dataflow} == {self.burst_dataflow} - 1) {{")
                                    out.append(f"{tabp1}{self.nameW[id_stat][key]}.write(v{key});")
                                    if self.lastWrite[key] == id_stat and f"{tabp1}fifo_{key}_to_off_chip.write(v{key});" not in out:
                                        out.append(f"{tabp1}fifo_{key}_to_off_chip.write(v{key});")
                                    out.append(f"{tab}}}")
                                    
                                else:
                                    out.append(f"{tab}{self.nameW[id_stat][key]}.write({key});")
                                    if self.lastWrite[key] == id_stat and f"{tab}fifo_{key}_to_off_chip.write({key});" not in out:
                                        out.append(f"{tab}fifo_{key}_to_off_chip.write({key});")

            tab = self.create_tab(tree.depth)
            out.append(f"{tab}}}")
        else: # Root
            for child in tree.children:
                self.write_order2(child, out, id_stat, depth+1)

    def find_divisor(self, n, limit):
        for i in range(max(1, limit), n):
            if n % i == 0:
                return i
        return n

    def write_order2_cyclic_buffer(self, tree, out, id_stat, depth, IS_RED=False):
        self.reinit()
        tree.aready_seen = True
        
        if tree.kind == "Statement":
            if IS_RED:
                str_ = self.transform_statement_cyclic_buffer(tree.string, id_stat, depth+1, True)
                out.append(str_)
            else:
                str_ = self.transform_statement_cyclic_buffer(tree.string, id_stat, depth)
                out.append(str_)
        elif tree.kind == "Loop":

            if self.analysis.is_reduction_innermost[id_stat] and depth == (len(self.schedule[id_stat])-1)//2-1:
                div = self.find_divisor(int(tree.ub)-int(tree.lb)+1, self.limit_IL)
                tab = self.create_tab(tree.depth)
                new_loop = tab + self.create_loop(tree.it, int(tree.lb), (int(tree.ub)+1)//div)
                initi = ', '.join(["0" for k in range(div)])
                out.append(f"{tab}{self.data_type} cyclic_buffer[{div}] = {{{initi}}};")
                out.append("#pragma HLS array_partition variable=cyclic_buffer complete")
                tab = self.create_tab(tree.depth+1)
                loop_unroll = tab + self.create_loop("cyclic_it", 0, div)
                
                out.append(new_loop)
                out.append("#pragma HLS pipeline II=1")
                out.append(loop_unroll)

                IS_RED = True

                self.iterator_cyclic[id_stat][tree.it] = f"{tree.it} * {div} + cyclic_it"
            else:
                out.append(tree.string)
            if depth == (len(self.schedule[id_stat])-1)//2-1 and not self.analysis.is_reduction_innermost[id_stat]:
                out.append("#pragma HLS pipeline II=1")
            for key in list(self.level_read[id_stat].keys()):
                if self.level_read[id_stat][key] == depth:
                    tab = self.create_tab(tree.depth+1)
                    if IS_RED:
                        tab = self.create_tab(tree.depth+2)
                    if key in self.array_need_reuse[id_stat]: 
                        if (not self.from_off_chip[id_stat][key] or id_stat == 0):
                            pass
                    else:
                        if key not in self.transfer_totally[id_stat]:
                            if key in self.nameR[id_stat]:
                                out.append("// read 2\n")
                                out.append(f"{tab}{self.data_type} {key} = {self.nameR[id_stat][key]}.read();")
                            else:
                                out.append(f"{tab}{self.data_type} {key};")
            for child in tree.children:
                if not child.aready_seen:
                    self.write_order2_cyclic_buffer(child, out, id_stat, depth+1, IS_RED)
            for key in list(self.level_read[id_stat].keys()):
                if self.level_read[id_stat][key] == depth:
                    tab = self.create_tab(tree.depth+1)
                    if key in self.array_need_reuse[id_stat]:
                        pass
                    else:

                        if key in self.nameW[id_stat]:

                            if self.should_reduce[id_stat] and self.output_array[id_stat] == key:
                                out.append("// reduction\n")
                                tab = self.create_tab(tree.depth+1)
                                out.append(f"{tab}{self.create_loop('cyclic_it', 0, self.find_divisor(self.UB[0]-self.LB[0]+1, self.limit_IL))}")
                                out.append(f"#pragma HLS unroll")
                                tab = self.create_tab(tree.depth+2)
                                out.append(f"{tab}{key} += cyclic_buffer[cyclic_it];")
                                tab = self.create_tab(tree.depth+1)
                                out.append(f"{tab}}}")
                                tab = self.create_tab(tree.depth+1)
                                if key not in self.transfer_totally[id_stat]:
                                    out.append("// write 2")
                                    out.append(f"{tab}{self.nameW[id_stat][key]}.write({key});")
                                    if self.lastWrite[key] == id_stat and f"{tab}fifo_{key}_to_off_chip.write({key});" not in out:
                                        out.append(f"{tab}fifo_{key}_to_off_chip.write({key});")
                            else:
                                tab = self.create_tab(tree.depth+1)
                                if key not in self.transfer_totally[id_stat]:
                                    out.append("// write 3")
                                    if self.condition_fifo[id_stat][key] != "":
                                        out.append(f"{tab}if({self.condition_fifo[id_stat][key]}){{")
                                        out.append(f"{tab}    {self.nameW[id_stat][key]}.write({key});")
                                        out.append(f"{tab}}}")
                                    else:
                                        out.append("// write 44\n")
                                        out.append(f"{tab}{self.nameW[id_stat][key]}.write({key});")
                                    if self.lastWrite[key] == id_stat and f"{tab}fifo_{key}_to_off_chip.write({key});" not in out:
                                        out.append(f"{tab}fifo_{key}_to_off_chip.write({key});")
            if IS_RED:
                tab = self.create_tab(tree.depth+1)
                out.append(f"{tab}}}")
            tab = self.create_tab(tree.depth)
            out.append(f"{tab}}}")
        else: # Root
            for child in tree.children:
                self.write_order2_cyclic_buffer(child, out, id_stat, depth+1)

    def transform_statement_cyclic_buffer(self, statement, id_stat, depth, is_red=False):
        tab = self.create_tab(depth+1)
        tabp1 = self.create_tab(depth+2)
        str_ = ""

        need_reuse = False
        out, inp = self.extract_array_and_constant(statement)
        op = self.extract_operation(statement)
        self.output_array[id_stat] = out

        for k, inn in enumerate(inp + [out]):
            if inn in self.array_need_reuse[id_stat]:
                need_reuse = True
                break
        out, inp = self.extract_array_and_constant(statement, False)

        for k1, inn1 in enumerate([out] + inp):
            self.reuse_it_total[id_stat][inn1.split("[")[0].replace(' ', '')] = []
        for k1, inn1 in enumerate([out] + inp):
            for k2, inn2 in enumerate([out] + inp):
                if k2 > k1:
                    
                    if inn1.split("[")[0].split() == inn2.split("[")[0].split():

                        if inn1.replace(" ", "") != inn2.replace(" ", ""):
                            need_reuse = True
                            self.array_need_reuse[id_stat].append(inn1.split("[")[0].replace(' ', ''))
                            self.reuse_it_total[id_stat][inn1.split("[")[0].replace(' ', '')] += [inn1]
                            self.reuse_it_total[id_stat][inn1.split("[")[0].replace(' ', '')] += [inn2]

                            self.condition[id_stat][inn1.split("[")[0].replace(' ', '')] = []
                            cc_loops = self.schedule[id_stat][1::2]
                            cc_it = [self.iterators[int(x)] for x in cc_loops]

                            
                            break
        out, inp = self.extract_array_and_constant(statement)
        if is_red:
            self.should_reduce[id_stat] = True
        if not need_reuse:
            str_ = f"{tab}"
            if out in self.array_need_reuse[id_stat]:
                it = self.reuse_it[id_stat][out]
                if is_red:
                    self.should_reduce[id_stat] = True
                    it = it.replace(list(self.iterator_cyclic[id_stat].keys())[0], list(self.iterator_cyclic[id_stat].values())[0])
                str_ += f"{out}{it} = "
            else:
                
                if is_red:
                    str_ += f"cyclic_buffer[cyclic_it] = "
                else:
                    remove_one_op = False
                    if "+=" in statement:
                        str_ += f"{out} += "
                        remove_one_op = True
                    elif "-=" in statement:
                        str_ += f"{out} -= "
                        remove_one_op = True
                    elif "*=" in statement:
                        str_ += f"{out} *= "
                        remove_one_op = True
                    elif "/=" in statement:
                        str_ += f"{out} /= "
                        remove_one_op = True
                    else:
                        str_ += f"{out} = "
                    if remove_one_op:
                        op = op[1:]
            for k, inn in enumerate(inp):
                if inn == out and is_red:
                    inn = f"cyclic_buffer[cyclic_it]"
                if inn in self.array_need_reuse[id_stat]:
                    it = self.reuse_it[id_stat][inn]
                    if is_red:
                        it = it.replace(list(self.iterator_cyclic[id_stat].keys())[0], list(self.iterator_cyclic[id_stat].values())[0])
                    str_ += f"{inn}{it}"
                else:
                    str_ += inn
                if k < len(op):
                    str_ += " "
                    str_ += op[k]
                    str_ += " "
            str_ += ";"

        else:
            conditions = []
            initialization = []
            already_seen = []
            str_stat = ""
            nb_array = {}
            for key in list(self.level_read[id_stat].keys()):
                
                if type(self.reuse_it_total[id_stat][key]) == list:
                    nb_array[key] = 0
            
            if out in self.array_need_reuse[id_stat]:
                itts = ""
                
                # if list
                if type(self.reuse_it_total[id_stat][out]) == list and len(self.reuse_it_total[id_stat][out]) > 0:
                    itts = self.reuse_it_total[id_stat][out][0]
                    nb_array[out] += 1
                    need_remove_op = False
                    if "+=" in statement:
                        str_stat += f"{itts} += "
                        need_remove_op = True
                    elif "-=" in statement:
                        str_stat += f"{itts} -= "
                        need_remove_op = True
                    elif "*=" in statement:
                        str_stat += f"{itts} *= "
                        need_remove_op = True
                    elif "/=" in statement:
                        str_stat += f"{itts} /= "
                        need_remove_op = True
                    else:
                        str_stat += f"{itts} = "
                    if need_remove_op:
                        op = op[1:]
                else:
                    need_remove_op = False
                    if "+=" in statement:
                        itts = self.reuse_it[id_stat][out]
                        str_stat += f"{out}{itts} += "
                    elif "-=" in statement:
                        itts = self.reuse_it[id_stat][out]
                        str_stat += f"{out}{itts} -= "
                    elif "*=" in statement:
                        itts = self.reuse_it[id_stat][out]
                        str_stat += f"{out}{itts} *= "
                    elif "/=" in statement:
                        itts = self.reuse_it[id_stat][out]
                        str_stat += f"{out}{itts} /= "
                    else:
                        itts = self.reuse_it[id_stat][out]
                        str_stat += f"{out}{itts} = "
                    if need_remove_op:
                        op = op[1:]
                    
                cc = self.condition[id_stat][out]
                if cc not in conditions:
                    conditions.append(cc)
                if out not in already_seen:
                    it = self.reuse_it_total[id_stat][out]
                    if it != []:
                        if is_red:
                            it = it.replace(list(self.iterator_cyclic[id_stat].keys())[0], list(self.iterator_cyclic[id_stat].values())[0])
                        if out not in self.transfer_totally[id_stat]:
                            if is_red: # FIXME normally this case does not exist
                                out.append("// read 3\n")
                                initialization.append(f"{tabp1}{out}{it} = {self.nameR[id_stat][out]}.read();\n")
                            else:
                                out.append("// read 4\n")
                                initialization.append(f"{tabp1}{out}{it} = {self.nameR[id_stat][out]}.read();\n")
                            already_seen.append(out)
            else:
                need_remove_op = False
                if is_red:
                    str_stat += f"cyclic_buffer[cyclic_it] = "
                else:
                    
                    if "+=" in statement:
                        str_stat += f"{out} += "
                        need_remove_op = True
                    elif "-=" in statement:
                        str_stat += f"{out} -= "
                        need_remove_op = True
                    elif "*=" in statement:
                        str_stat += f"{out} *= "
                        need_remove_op = True
                    elif "/=" in statement:
                        str_stat += f"{out} /= "
                        need_remove_op = True
                    else:
                        str_stat += f"{out} = "
                if need_remove_op:
                    op = op[1:]

            for k, inn in enumerate(inp):
                if inn == out and is_red:
                    inn = f"cyclic_buffer[cyclic_it]"
                if inn in self.reuse_it_total[id_stat] and len(self.reuse_it_total[id_stat][inn]) > 0:
                    if type(self.reuse_it_total[id_stat][out]) == list and len(self.reuse_it_total[id_stat][out]) > 0:
                        itts = self.reuse_it_total[id_stat][out][nb_array[out]]
                        nb_array[out] += 1
                        str_stat += f"{itts}"
                elif inn in self.array_need_reuse[id_stat]:
                    itts = self.reuse_it[id_stat][inn]
                    str_stat += f"{inn}{self.reuse_it[id_stat][inn]}"
                    cc = self.condition[id_stat][inn]
                    if cc not in conditions:
                        conditions.append(cc)
                    if inn not in already_seen:
                        it = self.reuse_it[id_stat][inn]
                        if type(it) != list:
                            if is_red:
                                it = it.replace(list(self.iterator_cyclic[id_stat].keys())[0], list(self.iterator_cyclic[id_stat].values())[0])
                            if inn not in self.transfer_totally[id_stat]:
                                if inn in list(self.nameR[id_stat].keys()):
                                    initialization.append(f"{tabp1}{inn}{it} = {self.nameR[id_stat][inn]}.read();\n")
                                    already_seen.append(inn)
                else:
                    str_stat += inn
                if k < len(op):
                    str_stat += " "
                    str_stat += op[k]
                    str_stat += " "
            str_stat += ";"
            if conditions != [[]] and len(conditions) > 0:
                conds = " && ".join(conditions)
            else:
                conds = ""
            str_stat_init = "".join(initialization) + tabp1 + str_stat
            if conds != "":
                str_ += f"{tab}if({conds}){{\n{str_stat_init}\n{tab}}}\n"
                str_ += f"{tab}else{{\n{tab}    {str_stat}\n{tab}}}\n"
            else:
                tab = self.create_tab(depth-2)
                str_ += f"{tab}{str_stat}"
        return str_

        

    def transform_statement_dataflow_burst(self, statement, id_stat, depth):
        # FIXME
        tab = self.create_tab(depth+1)
        tabp1 = self.create_tab(depth+2)
        str_ = ""

        need_reuse = False
        out, inp = self.extract_array_and_constant(statement)
        op = self.extract_operation(statement)

        for k, inn in enumerate(inp + [out]):
            if inn in self.array_need_reuse[id_stat]:
                need_reuse = True
                break
        
        out, inp = self.extract_array_and_constant(statement, False)
        for k1, inn1 in enumerate([out] + inp):
            for k2, inn2 in enumerate([out] + inp):
                if k2 > k1:
                    if inn1.split("[")[0] == inn2.split("[")[0]:
                        if inn1 != inn2:
                            need_reuse = True
                            break
        out, inp = self.extract_array_and_constant(statement)

        if not need_reuse:
            if self.optimize_burst:
                str_ = [f"{tab}" for d in range(self.burst_dataflow)]
            else:
                str_ += f"{tab}"

            if out in self.array_need_reuse[id_stat]:
                str_ += f"{out}{self.reuse_it[id_stat][out]} = "
            else:
                remove_one_op = False
                if out in list(self.transfer_totally[id_stat].keys()):
                    str_op = ""
                    if "+=" in statement:
                        str_op += f" += "
                        remove_one_op = True
                    elif "-=" in statement:
                        str_op += f" -= "
                        remove_one_op = True
                    elif "*=" in statement:
                        str_op += f" *= "
                        remove_one_op = True
                    elif "/=" in statement:
                        str_op += f" /= "
                        remove_one_op = True
                    else:
                        str_op += f" = "
                    it = self.array_information[out]["iterators"][id_stat][0]
                    is_it_innermost = self.iterators[self.schedule[id_stat][-2]] in it
                    cond = ""
                    UB_ = self.UB_[self.schedule[id_stat][-2]]
                    LB_ = self.LB_[self.schedule[id_stat][-2]]
                    is_UB_cte = False
                    is_LB_cte = False
                    try:
                        UB_ = int(UB_)
                        is_UB_cte = True
                    except:
                        pass
                    try:
                        LB_ = int(LB_)
                        is_LB_cte = True
                    except:
                        pass
                    
                    it_loop = self.iterators[self.schedule[id_stat][-2]]
                    if self.optimize_burst:
                        for g in range(self.burst_dataflow):
                            cond = ""
                            if is_UB_cte and is_LB_cte:
                                pass
                            elif not is_UB_cte and not is_LB_cte:
                                cond = f"if({it_loop}+{g} < {UB_}+1 && {it} >= {LB_}) "
                            elif not is_UB_cte:
                                cond = f"if({it_loop}+{g} < {UB_}+1) "
                            elif not is_LB_cte:
                                cond = f"if({it_loop}+{g} >= {LB_}) "
                            if is_it_innermost:
                                tmp_it = it.copy()
                                index = tmp_it.index(self.iterators[self.schedule[id_stat][-2]])
                                tmp_it[index] += f" + {g}"
                                str_[g] += f"{cond}{out}[{']['.join(tmp_it)}] {str_op}"
                            else:
                                str_[g] += f"{cond}{out}[{']['.join(it)}] {str_op}"
                    else:
                        str_ += f"{out}[{']['.join(it)}] {str_op}"
                elif self.optimize_burst:
                    for g in range(self.burst_dataflow):
                        
                        if "+=" in statement:
                            str_[g] += f"{out}[{g}] += "
                            remove_one_op = True
                        elif "-=" in statement:
                            str_[g] += f"{out}[{g}] -= "
                            remove_one_op = True
                        elif "*=" in statement:
                            str_[g] += f"{out}[{g}] *= "
                            remove_one_op = True
                        elif "/=" in statement:
                            str_[g] += f"{out}[{g}] /= "
                            remove_one_op = True
                        else:
                            str_[g] += f"{out}[{g}] = "
                else:
                    if "+=" in statement:
                        str_ += f"{out} += "
                        remove_one_op = True
                    elif "-=" in statement:
                        str_ += f"{out} -= "
                        remove_one_op = True
                    elif "*=" in statement:
                        str_ += f"{out} *= "
                        remove_one_op = True
                    elif "/=" in statement:
                        str_ += f"{out} /= "
                        remove_one_op = True
                    else:
                        str_ += f"{out} = "
            if remove_one_op:
                op = op[1:]
            for k, inn in enumerate(inp):
                if inn in list(self.transfer_totally[k].keys()):
                    call = f"{inn}"
                    nb = str_[0].count(f"{inn}[")
                    if remove_one_op:
                        nb += 1
                    it = self.array_information[inn]["iterators"][id_stat][nb]
                    is_it_innermost = self.iterators[self.schedule[id_stat][-2]] in it
                    if is_it_innermost and self.optimize_burst:
                        for g in range(self.burst_dataflow):
                            tmp_it = it.copy()
                            index = tmp_it.index(self.iterators[self.schedule[id_stat][-2]])
                            tmp_it[index] += f" + {g}"
                            call = f"{inn}[{']['.join(tmp_it)}]"
                            str_[g] += f"{call}"
                    else:
                        call += f"[{']['.join(it)}]"
                        if self.optimize_burst:
                            for g in range(self.burst_dataflow):
                                str_[g] += f"{call}"
                        else:
                            str_ += f"{call}"
                else:
                    if self.optimize_burst:
                        for g in range(self.burst_dataflow):
                            if inn in self.array_need_reuse[id_stat]:
                                str_[g] += f"{inn}{self.reuse_it[id_stat][inn]}"
                            else:
                                if inn in self.array_information:
                                    it = self.array_information[inn]["iterators"][id_stat][0][-1]
                                    it_current_loop = self.iterators[int(self.schedule[id_stat][-2])]
                                    if it in it_current_loop:
                                        str_[g] += f"{inn}[{g}]"
                                    else:
                                        str_[g] += f"{inn}"
                                else:
                                    str_[g] += f"{inn}"
                    else:
                        if inn in self.array_need_reuse[id_stat]:
                            str_ += f"{inn}{self.reuse_it[id_stat][inn]}"
                        else:
                            str_ += f"{inn}"
                if self.optimize_burst:
                    for g in range(self.burst_dataflow):
                        if k < len(op):
                            str_[g] += " "
                            str_[g] += op[k]
                            str_[g] += " "
                else:
                    if k < len(op):
                        str_ += " "
                        str_ += op[k]
                        str_ += " "
            if self.optimize_burst:
                for g in range(self.burst_dataflow):
                    str_[g] += ";"
            else:
                str_ += ";"
            if self.optimize_burst:
                str_ = f"\n".join(str_)

        else:
            conditions = []
            initialization = []
            already_seen = []
            str_stat = ["" for d in range(self.burst_dataflow)]

            if out in self.array_need_reuse[id_stat]:
                for g in range(self.burst_dataflow):
                    it = self.reuse_it[id_stat][out][1:-1]
                    it = it.split("][")
                    it[-1] += f" + {g}"
                    it = "[" + "][".join(it) + "]"
                    str_stat[g] += f"{out}{it} = "
                cc = self.condition[id_stat][out]
                if cc not in conditions:
                    conditions.append(cc)
                if out not in already_seen:
                    if out in self.nameR[id_stat]:
                        if out not in self.transfer_totally[id_stat]:

                            initialization.append(f"{tabp1}{self.data_type}{self.burst_dataflow} v{inn} = {self.nameR[id_stat][inn]}.read();\n")
                            for g in range(self.burst_dataflow):
                                it = self.reuse_it[id_stat][inn][1:-1].split("][")
                                it_of_innermost_loop = self.iterators[int(self.schedule[id_stat][-2])]
                                for id_, ii in enumerate(it):
                                    if ii == it_of_innermost_loop:
                                        it[id_] = f"{ii} + {g}"
                                it = "[" + "][".join(it) + "]"
                                initialization.append(f"{tabp1}{inn}{it} = v{inn}[{g}];\n")

                            already_seen.append(out)
            else:
                for g in range(self.burst_dataflow):
                    str_stat[g] += f"{out} = "
            for k, inn in enumerate(inp):
                if inn in self.array_need_reuse[id_stat]:
                    for g in range(self.burst_dataflow):
                        it = self.reuse_it[id_stat][inn][1:-1]
                        it = it.split("][")
                        it[-1] += f" + {g}"
                        it = "[" + "][".join(it) + "]"

                        str_stat[g] += f"{inn}{it}"
                    cc = self.condition[id_stat][inn]
                    if cc not in conditions:
                        conditions.append(cc)
                    if inn not in already_seen:
                        if inn in self.nameR[id_stat]:
                            if inn not in self.transfer_totally[id_stat]:
                                initialization.append("// read 88\n")
                                initialization.append(f"{tabp1}{self.data_type}{self.burst_dataflow} v{inn} = {self.nameR[id_stat][inn]}.read();\n")
                                for g in range(self.burst_dataflow):
                                    it = self.reuse_it[id_stat][inn][1:-1].split("][")
                                    it_of_innermost_loop = self.iterators[int(self.schedule[id_stat][-2])]
                                    for id_, ii in enumerate(it):
                                        if ii == it_of_innermost_loop:
                                            it[id_] = f"{ii} + {g}"
                                    it = "[" + "][".join(it) + "]"
                                    initialization.append(f"{tabp1}{inn}{it} = v{inn}[{g}];\n")
                                already_seen.append(inn)
                else:
                    it_iterate_array = False
                    it_of_innermost_loop = self.iterators[int(self.schedule[id_stat][-2])]
                    it_arrays = []

                    statement_ = self.statements[id_stat]
                    out_, inn_ = self.extract_array_and_constant(statement_, False)
                    arr_ = inn_ + [out_]
                    for arr in arr_:
                        if arr.split("[")[0] == inn.split("[")[0]:
                            its_ = self.extract_iterator(arr)
                            it_arrays += its_

                
                    for it in it_arrays:
                        if it == it_of_innermost_loop:
                            it_iterate_array = True
                            break
                    if it_iterate_array:
                        for g in range(self.burst_dataflow):
                            str_stat[g] += f"{inn}[{g}]"
                    else:
                        for g in range(self.burst_dataflow):
                            str_stat[g] += f"{inn}" 
                if k < len(op):
                    for g in range(self.burst_dataflow):
                        str_stat[g] += " "
                        str_stat[g] += op[k]
                        str_stat[g] += " "
            for g in range(self.burst_dataflow):
                str_stat[g] += ";"
            conds = " && ".join(conditions)
            str_stat = f"\n{tabp1}".join(str_stat)
            str_stat_init = "".join(initialization) + tabp1 + str_stat
            str_ += f"{tab}if({conds}){{\n{str_stat_init}\n{tab}}}\n"
            str_ += f"{tab}else{{\n{tab}    {str_stat}\n{tab}}}\n"

        return str_
    
    def transform_statement(self, statement, id_stat, depth):
        tab = self.create_tab(depth+1)
        tabp1 = self.create_tab(depth+2)
        str_ = ""

        need_reuse = False
        out, inp = self.extract_array_and_constant(statement)
        op = self.extract_operation(statement)

        for k, inn in enumerate(inp + [out]):
            if inn in self.array_need_reuse[id_stat]:
                need_reuse = True
                break
        
        out, inp = self.extract_array_and_constant(statement, False)
        for k1, inn1 in enumerate([out] + inp):
            for k2, inn2 in enumerate([out] + inp):
                if k2 > k1:
                    if inn1.split("[")[0] == inn2.split("[")[0]:
                        if inn1 != inn2:
                            need_reuse = True
                            break
        out, inp = self.extract_array_and_constant(statement)

        if not need_reuse:
            str_ = f"{tab}"

            if out in self.array_need_reuse[id_stat]:

                str_ += f"{out}{self.reuse_it[id_stat][out]} = "
            else:
                remove_one_op = False

                if out in list(self.transfer_totally[id_stat].keys()) and self.transfer_totally[id_stat][out]:
                    it_arr = self.array_information[out]["iterators"][id_stat][0]
                    out = f"{out}[{']['.join(it_arr)}]"
                if "+=" in statement:
                    str_ += f"{out} += "
                    remove_one_op = True
                elif "-=" in statement:
                    str_ += f"{out} -= "
                    remove_one_op = True
                elif "*=" in statement:
                    str_ += f"{out} *= "
                    remove_one_op = True
                elif "/=" in statement:
                    str_ += f"{out} /= "
                    remove_one_op = True
                else:
                    str_ += f"{out} = "
            if remove_one_op:
                op = op[1:]
            for k, inn in enumerate(inp):
                if inn in list(self.transfer_totally[id_stat].keys()) and self.transfer_totally[id_stat][inn]:
                    id_ = k
                    if remove_one_op:
                        id_ += 1
                    it_arr = self.array_information[inn]["iterators"][id_stat][id_]
                    inn = f"{inn}[{']['.join(it_arr)}]"
                if inn in self.array_need_reuse[id_stat]:
                    str_ += f"{inn}{self.reuse_it[id_stat][inn]}"
                else:
                    str_ += f"{inn}"
                if k < len(op):
                    str_ += " "
                    str_ += op[k]
                    str_ += " "
            str_ += ";"

        else:
            conditions = []
            initialization = []
            already_seen = []
            str_stat = ""

            if out in self.array_need_reuse[id_stat]:
                str_stat += f"{out}{self.reuse_it[id_stat][out]} = "
                cc = self.condition[id_stat][out]
                if cc not in conditions:
                    conditions.append(cc)
                if out not in already_seen:
                    if out in self.nameR[id_stat]:
                        if out not in self.transfer_totally[id_stat]:
                            initialization.append("// read 7\n")
                            initialization.append(f"{tabp1}{out}{self.reuse_it[id_stat][out]} = {self.nameR[id_stat][out]}.read();\n")
                            already_seen.append(out)
            else:
                str_stat += f"{out} = "
            for k, inn in enumerate(inp):
                if inn in self.array_need_reuse[id_stat]:
                    str_stat += f"{inn}{self.reuse_it[id_stat][inn]}"
                    cc = self.condition[id_stat][inn]
                    if cc not in conditions:
                        conditions.append(cc)
                    if inn not in already_seen:
                        if inn in self.nameR[id_stat]:
                            if inn not in self.transfer_totally[id_stat]:
                                initialization.append("// read 8\n")
                                initialization.append(f"{tabp1}{inn}{self.reuse_it[id_stat][inn]} = {self.nameR[id_stat][inn]}.read();\n")
                                already_seen.append(inn)
                else:
                    str_stat += inn
                if k < len(op):
                    str_stat += " "
                    str_stat += op[k]
                    str_stat += " "
            str_stat += ";"
            conds = " && ".join(conditions)
            str_stat_init = "".join(initialization) + tabp1 + str_stat
            str_ += f"{tab}if({conds}){{\n{str_stat_init}\n{tab}}}\n"
            str_ += f"{tab}else{{\n{tab}    {str_stat}\n{tab}}}\n"

        return str_

        
    def write_order_per_loop_body(self, tree):
        self.analyze_reuse()
        for k,subtree in enumerate(tree.children):
            out = []
            out.append(f"    // Schedule: {self.schedule[k]}")
            for reuse in self.array_need_reuse[k]:
                for arg in self.arguments:
                    if f"{reuse}[" in arg:
                        out.append(f"    {arg};")
                if self.from_off_chip[k][reuse] and k >= 1:
                    loops = list(self.array_information[reuse]["loop_to_dim"].keys())
                    for j in range(1, len(self.schedule[k]), 2):
                        loop = int(self.schedule[k][j])
                        if loop in loops:
                            it = self.iterators[loop]
                            lb = self.LB_[loop]
                            ub = self.UB_[loop]
                            tab = self.create_tab((j-1)//2)
                            out.append(tab + self.create_loop(it, f"{lb}", f"{ub}+1", self.schedule[k][j]))
                    tab = self.create_tab(len(self.schedule[k])//2 )
                    if reuse not in self.transfer_totally[k]:
                        out.append("// read 9\n")
                        out.append(f"{tab}{reuse}{self.reuse_it[k][reuse]} = {self.nameR[k][reuse]}.read();")
                    for j in range(1, len(self.schedule[k]), 2):
                        loop = int(self.schedule[k][j])
                        if loop in loops:
                            tab = self.create_tab((j-1)//2)
                            out.append(f"{tab}}}")

            self.transfer_totally[k] = self.compute_transfer_totally(k)
            for arr in list(self.transfer_totally[k].keys()):
                out.append(f"// beginnn {arr}")
                dim = []
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if arr in tmp:
                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):

                            it = it.replace("+", "").replace("1", "").replace("-", "")
                            dim += [self.analysis.dic[k]["TC"][it]]
                        break
                dim = list(map(str, dim))
                out.append(f"    {self.data_type} {arr}[{']['.join(dim)}];")
                nb = 0
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if arr in tmp:
                        lit = []
                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):

                            it = it.replace("+", "").replace("1", "").replace("-", "")
                            lb = self.analysis.dic[k]["LB_"][it]
                            ub = self.analysis.dic[k]["UB_"][it]
                            tab = self.create_tab(kk+1)
                            if self.optimize_burst and kk == len(its)-1:
                                out.append(f"{tab}{self.create_loop(it, f'{lb}', f'({ub}+1)/{self.burst_dataflow}')}")
                            else:
                                out.append(f"{tab}{self.create_loop(it, f'{lb}', f'{ub}+1')}")
                            lit += [it]
                            nb += 1
                        tab = self.create_tab(len(its)+1)
                        out.append("// read 11\n")
                        if self.optimize_burst:
                            out.append(f"{tab}{self.data_type}{self.burst_dataflow} tmp_{arr} = {self.nameR[k][arr]}.read();")
                            for g in range(self.burst_dataflow):
                                tab = self.create_tab(2)
                                its = lit.copy()
                                its[-1] += " + " + str(g)
                                out.append(f"{tab}{arr}[{']['.join(its)}] = tmp_{arr}[{g}];")
                        else:
                            out.append(f"{tab}{tmp} = {self.nameR[k][arr]}.read();")
                        for l in range(nb):
                            tab = self.create_tab(len(its)-l)
                            out.append(f"{tab}}}")
                        break

            self.write_order2(subtree, out, k, 0)

            for arr in list(self.transfer_totally[k].keys()):

                nb = 0
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if arr in tmp:

                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):

                            it = it.replace("+", "").replace("1", "").replace("-", "")
                            try:
                                lb = math.abs(int(self.analysis.dic[k]["LB_"][it]))
                            except:
                                lb = self.analysis.dic[k]["LB_"][it]
                            ub = self.analysis.dic[k]["UB_"][it]
                            tab = self.create_tab(kk+1)
                            if self.optimize_burst and kk == len(its)-1:
                                out.append(f"{tab}{self.create_loop(it, f'{lb}', f'({ub}+1)/{self.burst_dataflow}')}")
                            else:
                                out.append(f"{tab}{self.create_loop(it, f'{lb}', f'{ub}+1')}")
                            nb += 1
                        tab = self.create_tab(len(its)+1)
                        out.append("// write 6")
                        if self.optimize_burst:
                            out.append(f"{tab}{self.data_type}{self.burst_dataflow} tmp_{arr};")
                            for g in range(self.burst_dataflow):
                                tab = self.create_tab(2)
                                its2 = its.copy()
                                its2[-1] += " + " + str(g)
                                out.append(f"{tab}tmp_{arr}[{g}] = {arr}[{']['.join(its2)}];")
                            out.append(f"{tab}{self.nameW[k][arr]}.write(tmp_{arr});")
                        else:
                            if arr in list(self.nameW[k].keys()):
                                out.append(f"{tab}{self.nameW[k][arr]}.write({tmp});")
                        for l in range(nb):
                            tab = self.create_tab(len(its)-l)
                            out.append(f"{tab}}}")
                        break
            for reuse in self.array_need_reuse[k]:
                if reuse not in self.nameW[k]:
                    continue

                loops = list(self.array_information[reuse]["loop_to_dim"].keys())
                iterator_array = []
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if reuse in tmp:
                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):
                            iterator_array.append(it)
                        break
                nb = 0
                last_it_loop = ""
                all_loops = []
                for j in range(1, len(self.schedule[k]), 2):
                    loop = int(self.schedule[k][j])
                    if self.iterators[loop] in iterator_array:
                        all_loops.append(loop)
                for g, loop in enumerate(all_loops):
                    it = self.iterators[loop]
                    last_it_loop = it
                    try:
                        lb = math.abs(int(self.LB_[loop]))
                    except:
                        lb = self.LB_[loop]
                    ub = self.UB_[loop]
                    tab = self.create_tab((g-1)//2)
                    if self.optimize_burst:
                        if g == len(all_loops)-1:
                            inc = self.burst_dataflow
                            out.append(tab + self.create_loop(it, f"{lb}", f"{ub}+1", inc=inc))
                        else:
                            out.append(tab + self.create_loop(it, f"{lb}", f"{ub}+1"))
                    else:
                        out.append(tab + self.create_loop(it, f"{lb}", f"{ub}+1"))
                    nb += 1
                tab = self.create_tab(len(self.schedule[k])//2 )
                out.append("// write 4\n")
                if self.optimize_burst:
                    out.append(f"{tab}{self.data_type}{self.burst_dataflow} v{reuse};")
                    for g in range(self.burst_dataflow):
                        tab = self.create_tab(2)
                        reuse_it = self.reuse_it[k][reuse][1:-1].split("][")
                        for id_, ii in enumerate(reuse_it):
                            if ii == last_it_loop:
                                reuse_it[id_] = f"{ii} + {g}"
                        current_it = f"[{']['.join(reuse_it)}]"
                        out.append(f"{tab}v{reuse}[{g}] = {reuse}{current_it};")
                    out.append(f"{tab}{self.nameW[k][reuse]}.write(v{reuse});")
                    if self.lastWrite[reuse] == k and f"{tab}fifo_{reuse}_to_off_chip.write(v{reuse});" not in out:
                        out.append(f"{tab}fifo_{reuse}_to_off_chip.write(v{reuse});")
                else:
                    out.append(f"{tab}{self.nameW[k][reuse]}.write({reuse}{self.reuse_it[k][reuse]});")
                    if self.lastWrite[reuse] == k and f"{tab}fifo_{reuse}_to_off_chip.write({reuse}{self.reuse_it[k][reuse]});" not in out:
                        out.append(f"{tab}fifo_{reuse}_to_off_chip.write({reuse}{self.reuse_it[k][reuse]});")
                for j in range(nb):
                        tab = self.create_tab(1-j)
                        out.append(f"{tab}}}")
            self.order_per_loop_body.append(out)


    def compute_transfer_totally(self, id_stat):
        transfer = {}
        out, inp = self.extract_array_and_constant(self.statements[id_stat], False)
        for k1, inn1 in enumerate([out] + inp):
            for k2, inn2 in enumerate([out] + inp):
                if k2 > k1:
                    if inn1.split("[")[0] == inn2.split("[")[0]:
                        if inn1 != inn2:
                            transfer[inn1.split("[")[0].replace(' ', '')] = True
        return transfer

    def write_order_per_loop_body_cyclic_buffer(self, tree):
        self.analyze_reuse()
        
        for k,subtree in enumerate(tree.children):

            out = []
            out.append(f"    // Schedule: {self.schedule[k]}")

            for reuse in self.array_need_reuse[k]:
                for arg in self.arguments:
                    if f"{reuse}[" in arg:
                        out.append(f"    {arg};")

                if self.from_off_chip[k][reuse] and k >= 1:

                    loops = list(self.array_information[reuse]["loop_to_dim"].keys())
                    iterator_array = []
                    for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                        if reuse in tmp:
                            its = self.extract_iterator(tmp)
                            for kk, it in enumerate(its):
                                iterator_array.append(it)
                            break
                    nb = 0
                    for j in range(1, len(self.schedule[k]), 2):
                        loop = int(self.schedule[k][j])
                        if self.iterators[loop] in iterator_array:
                            it = self.iterators[loop]
                            try:
                                lb = math.abs(int(self.LB_[loop]))
                            except:
                                lb = self.LB_[loop]
                            ub = self.UB_[loop]
                            tab = self.create_tab((j-1)//2)
                            out.append(tab + self.create_loop(it, f"{lb}", f"{ub}+1", self.schedule[k][j]))
                            nb += 1
                    tab = self.create_tab(len(self.schedule[k])//2 )
                    if reuse not in self.transfer_totally[k]:
                        out.append("// read 10\n")
                        out.append(f"{tab}{reuse}{self.reuse_it[k][reuse]} = {self.nameR[k][reuse]}.read();")
                    for j in range(nb):
                        tab = self.create_tab(1-j)
                        out.append(f"{tab}}}")
        
            self.transfer_totally[k] = self.compute_transfer_totally(k)

            for arr in list(self.transfer_totally[k].keys()):
                out.append(f"// beginnn {arr}")
                dim = []
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if arr in tmp:

                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):

                            dim += [self.analysis.dic[k]["TC"][it]]
                        break
                dim = list(map(str, dim))
                out.append(f"    {self.data_type} {arr}[{']['.join(dim)}];")

                nb = 0
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if arr in tmp:

                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):

                            try:
                                lb = math.abs(int(self.analysis.dic[k]["LB_"][it]))
                            except:
                                lb = self.analysis.dic[k]["LB_"][it]
                            ub = self.analysis.dic[k]["UB_"][it]
                            tab = self.create_tab(kk+1)
                            out.append(f"{tab}{self.create_loop(it, f'{lb}', f'{ub}+1')}")
                            nb += 1
                        tab = self.create_tab(len(its)+1)
                        out.append("// read 11\n")
                        out.append(f"{tab}{tmp} = {self.nameR[k][arr]}.read();")
                        for l in range(nb):
                            tab = self.create_tab(len(its)-l)
                            out.append(f"{tab}}}")
                        break
                
            self.write_order2_cyclic_buffer(subtree, out, k, 0)
            for arr in list(self.transfer_totally[k].keys()):

                nb = 0
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if arr in tmp:

                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):

                            try:
                                lb = math.abs(int(self.analysis.dic[k]["LB_"][it]))
                            except:
                                lb = self.analysis.dic[k]["LB_"][it]
                            ub = self.analysis.dic[k]["UB_"][it]
                            tab = self.create_tab(kk+1)
                            out.append(f"{tab}{self.create_loop(it, f'{lb}', f'{ub}+1')}")
                            nb += 1
                        tab = self.create_tab(len(its)+1)
                        out.append("// write 6")
                        out.append(f"{tab}{self.nameW[k][arr]}.write({tmp});")
                        for l in range(nb):
                            tab = self.create_tab(len(its)-l)
                            out.append(f"{tab}}}")
                        break
            
            for reuse in self.array_need_reuse[k]:
                if reuse not in self.nameW[k] or reuse in list(self.transfer_totally[k].keys()):
                    continue

                iterator_array = []
                for tmp in self.analysis.dic[k]["read"] + self.analysis.dic[k]["write"]:
                    if reuse in tmp:
                        its = self.extract_iterator(tmp)
                        for kk, it in enumerate(its):
                            iterator_array.append(it)
                        break
                nb = 0
                for j in range(1, len(self.schedule[k]), 2):
                    loop = int(self.schedule[k][j])

                    if self.iterators[loop] in iterator_array:
                        it = self.iterators[loop]
                        try:
                            lb = math.abs(int(self.LB_[loop]))
                        except:
                            lb = self.LB_[loop]
                        ub = self.UB_[loop]
                        tab = self.create_tab((j-1)//2)
                        out.append(tab + self.create_loop(it, f"{lb}", f"{ub}+1", self.schedule[k][j]))
                        nb += 1
                tab = self.create_tab(len(self.schedule[k])//2 )
                if reuse not in self.transfer_totally[k]:
                    out.append("// write 8")
                    out.append(f"{tab}{self.nameW[k][reuse]}.write({reuse}{self.reuse_it[k][reuse]});")
                for j in range(nb):
                    tab = self.create_tab(2-nb)
                    out.append(f"{tab}}}")
            self.order_per_loop_body.append(out)


    def extract_iterator(self, string):
        index = string.find("[")
        string = string[index:]
        string = string.replace("][", "!")
        string = string.replace("[", "")
        string = string.replace("]", "")
        string = string.split("!")
        return string

    def multi_split(self, str_, delimiters, delete_array=False):
        for delim in delimiters:
            str_ = str_.replace(delim, "@")
        res = str_.split("@")

        new_res = []
        for r in res:
            if "[" in r:
                new_res.append(r)
        res = new_res
        new_res = []
        if delete_array:
            for r in res:
                if "[" in r:
                    r = r.split("[")[0]
                new_res.append(r)
                while "" in res:
                    res.remove("")
            return new_res
        while "" in res:
            res.remove("")

        return res
    
    def remove_init_on_chip(self, all_arrays):
        self.dont_need_load = []
        for stat in self.statements:
            out, inp = stat.split("=")
            out = out.strip().split("[")[0]
            inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
            if len(inp) == 0:
                if out in all_arrays:
                    all_arrays.remove(out)
                self.dont_need_load.append(out)
        return all_arrays
    
    def multi_split2(self, str_, delimiters, delete_array=False):
        for delim in delimiters:
            str_ = str_.replace(delim, "@")
        res = str_.split("@")

        new_res = []
        if delete_array:
            for r in res:
                if "[" in r:
                    r = r.split("[")[0]
                new_res.append(r)
                while "" in res:
                    res.remove("")
            return new_res
        while "" in res:
            res.remove("")

        return res

    def extract_array(self, statement):
        out = statement.split("=")[0]
        out = out.strip().split("[")[0]
        inp = statement.split("=")[1]
        inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
        return out, inp
    
    def extract_array_and_constant(self, statement, remove_bracket=True):
        out = statement.split("=")[0]
        if remove_bracket:
            out = out.strip().split("[")[0]
        else:
            if len(out) > 0 and "]" in out:

                while out[-1] != "]":
                    out = out[:-1]
        inp = statement.split("=")[1]
        inp = self.multi_split2(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], remove_bracket)
        return out, inp
    
    def extract_operation(self, statement):
        op = []
        inside_bracket = False
        for s in statement:
            if s == "[":
                inside_bracket = True
            if s == "]":
                inside_bracket = False
            if not inside_bracket:
                if s in ["+", "-", "*", "/"]:
                    op.append(s)
        return op

    def analyze_reuse(self):
        self.array_use_in_statement = {}
        self.Read = {}
        self.Write = {}
        self.posR = {}
        self.posW = {}
        self.nameR = {}
        self.nameW = {}
        self.lastWrite = {}
        self.from_off_chip = {}
        for id_stat, stat in enumerate(self.statements):
            self.Read[id_stat] = {}
            self.Write[id_stat] = {}
            self.posR[id_stat] = {}
            self.posW[id_stat] = {}
            self.nameR[id_stat] = {}
            self.nameW[id_stat] = {}
            self.from_off_chip[id_stat] = {}
            out, inp = self.extract_array(stat)
            self.array_use_in_statement[out] = []
            self.Write[id_stat][out] = False
            self.Read[id_stat][out] = False
            self.posW[id_stat][out] = -1
            
            for i in inp:
                self.array_use_in_statement[i] = []
                self.Read[id_stat][i] = False
                self.Write[id_stat][i] = False
                self.posR[id_stat][i] = -1
                self.posW[id_stat][i] = -1 # for next task if any
                self.nameR[id_stat][i] = f"fifo_{i}_S{id_stat}"
        for k, stat in enumerate(self.statements):
            out, inp = self.extract_array(stat)
            self.Write[k][out] = True
            if k not in self.array_use_in_statement[out]:
                self.array_use_in_statement[out].append(k)
            for i in inp:
                self.Read[k][i] = True
                if k not in self.array_use_in_statement[i]:
                    self.array_use_in_statement[i].append(k)
        

        for arr in list(self.array_use_in_statement.keys()):
            self.lastWrite[arr] = -1
            for stat in self.Write:
                if arr in self.Write[stat]:
                    if self.Write[stat][arr]:
                        self.lastWrite[arr] = stat


        for arr in list(self.array_use_in_statement.keys()):
            for l in range(len(self.array_use_in_statement[arr])):
                if l==0:
                    self.from_off_chip[self.array_use_in_statement[arr][l]][arr] = False # FIXME
                else:
                    self.from_off_chip[self.array_use_in_statement[arr][l]][arr] = False
        

        for id_stat, stat in enumerate(self.statements):
            for array in list(self.array_use_in_statement.keys()):

                if id_stat in self.array_use_in_statement[array]:
                    if self.array_use_in_statement[array].index(id_stat) != len(self.array_use_in_statement[array])-1:
                        next_stat = self.array_use_in_statement[array][self.array_use_in_statement[array].index(id_stat)+1]
                        self.nameW[id_stat][array] = f"fifo_{array}_S{next_stat}"
                    else:
                        if self.Write[id_stat][array]:
                            self.nameW[id_stat][array] = f"fifo_{array}_to_off_chip"

        statement_after_fifo = {}

        self.condition = {}
        self.reuse_it = {}
        self.reuse_it_total = {}

        for id_stat, stat in enumerate(self.statements):
            self.array_need_reuse[id_stat] = []
            self.level_read[id_stat] = {}
            self.condition[id_stat] = {}
            self.reuse_it[id_stat] = {}
            self.reuse_it_total[id_stat] = {}
            out, inp = self.extract_array(stat)
            statement_after_fifo[id_stat] = ""
            for i in unique_list_in_order(inp+[out]):
                level, need_reuse, cond, reuse_it = self.find_level(id_stat, i)
                if need_reuse:
                    self.array_need_reuse[id_stat].append(i)
                    self.condition[id_stat][i] = cond
                    self.reuse_it[id_stat][i] = reuse_it

                self.level_read[id_stat][i] = level


    def extract_iteration_per_dim(self, stat, array):
        it_per_dim = []
        ss = self.multi_split(stat.replace(";", "").replace(" ", ""), ["+", "-", "*", "/", "="])
        ss = unique_list_in_order(ss)
        for s in ss:
            if f"{array}[" in s:
                index = s.index(f"[")
                s = s[index:]
                s = s.replace("][", "*")
                s = s.replace("[", "")
                s = s.replace("]", "")
                tmp = s.split("*")
                it_per_dim.append(tmp)

        if len(it_per_dim) == 0:
            return []
        return it_per_dim[0]

    def compute_not_copy(self):
        loads = []
        writes = []
        for i, stat in enumerate(self.statements):
            out, inp = stat.split("=")
            out = out.strip().split("[")[0]
            inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
            
            writes += [out]
            loads += inp

        writes = unique_list_in_order(writes)
        loads = unique_list_in_order(loads)

        all_arrays = unique_list_in_order(loads+writes)
        all_arrays = self.remove_init_on_chip(all_arrays)
        for arr in all_arrays:
            if arr in list(self.array_need_more_than_one_copy.keys()) and self.array_need_more_than_one_copy[arr]:
                if arr in list(self.sched_need_different_copy_par_array.keys()):
                    if len(list(self.sched_need_different_copy_par_array[arr])):
                        statement_arr_present = self.array_information[arr]["statements"]
                        all_arr_diff = []
                        for pos1 in self.sched_need_different_copy_par_array[arr]:
                            for pos2 in pos1:
                                all_arr_diff += [pos2]
                        all_arr_diff = unique_list_in_order(all_arr_diff)
                        all_arr_diff = sorted(all_arr_diff)

                        load_per_stat = []
                        tmp = []
                        for stat in statement_arr_present:
                            if stat in all_arr_diff:
                                if len(tmp)  > 0:
                                    load_per_stat.append(tmp)
                                tmp = []
                            tmp += [stat]
                        if len(tmp) > 0:
                            load_per_stat.append(tmp)
                        self.array_dont_need_copy_per_schedule[arr] = [l[-1] for l in load_per_stat]
    
    def find_level(self, id_stat, array):
        need_reuse = False
        depth = 0
        cond = []
        reuse_it = []

        it = self.extract_iteration_per_dim(self.statements[id_stat], array)

        loops = []
        for l in range(1, len(self.schedule[id_stat]), 2):
            loop = int(self.schedule[id_stat][l])
            loops.append(self.iterators[loop])

        already_seen = [f"{i}" for i in it]
        for k, l in enumerate(loops):

            if l not in it:
                need_reuse = True
                cond.append(f"{l} == 0") # FIXME if does not start at 0
            else:
                already_seen.remove(l)
                reuse_it.append(l)
            if len(already_seen) == 0:
                depth = k
                break

        cond = " && ".join(cond)
        reuse_it = "[" + "][".join(reuse_it) + "]"
        return depth, need_reuse, cond, reuse_it
            



class CodeGeneration:
    def __init__(self, data_type, analysis, schedule, array_order, UB, LB, statements, iterators, output, headers, arguments, name_function, pragmas, pragmas_top, optimize_burst, cyclic_buffer, normale_file=False):
        self.analysis = analysis
        self.schedule = schedule
        self.UB = UB
        self.LB = LB
        self.UB_ = self.analysis.UB_
        self.LB_ = self.analysis.LB_
        
        self.array_order = array_order
        self.statements = statements
        self.iterators = iterators
        self.output = output
        self.headers = headers
        self.arguments = arguments
        self.name_function = name_function
        self.pragmas = pragmas
        self.pragmas_top = pragmas_top
        self.optimize_burst = optimize_burst
        self.normale_file = normale_file
        self.cyclic_buffer = cyclic_buffer
        self.constants = []
        self.compute_constants()
        self.data_type = data_type

        self.dataflow = self.analysis.is_memory_bound
        




        self.array_information = {}
        self.pre_treatement_statements()
        self.compute_arrays_information()
        self.array_need_more_than_one_copy = {} # for != statement
        self.sched_need_different_copy_par_array = {}
        self.condition_copy_array_between_statement = {}
        self.array_need_complete_copy_inside_task = {} 
        self.array_need_partial_copy_inside_task = {} 
        self.array_dont_need_copy_per_schedule = {}
        self.compute_array_need_more_than_one_copy()
        self.type = ""
        self.size_arrays = {}
        self.burst_dataflow = {}
        self.compute_burst_dataflow()

        self.tab = "    "
        self.warnings = "\n/*************************************************\n This file was automatically generated by Sisyphus\n*************************************************/\n"
        if self.normale_file:
            self.ast = AST(self.data_type, schedule, UB, LB, statements, iterators, output, headers, arguments, name_function, pragmas, pragmas_top, self.optimize_burst, self.burst_dataflow, self.analysis, normale_file, self.cyclic_buffer, self.array_need_more_than_one_copy, self.sched_need_different_copy_par_array, self.condition_copy_array_between_statement, self.array_need_complete_copy_inside_task,  self.array_need_partial_copy_inside_task,  self.array_dont_need_copy_per_schedule, self)
        else:
            self.ast = AST(self.data_type, schedule, UB, LB, statements, iterators, output, headers, arguments, name_function, pragmas, pragmas_top, self.optimize_burst, self.burst_dataflow, self.analysis, normale_file, self.cyclic_buffer, self.array_need_more_than_one_copy, self.sched_need_different_copy_par_array, self.condition_copy_array_between_statement, self.array_need_complete_copy_inside_task,  self.array_need_partial_copy_inside_task,  self.array_dont_need_copy_per_schedule, self)
        # self.compute_order()
        if normale_file:
            self.generate_code()
        else:
            if self.dataflow:
                self.generate_code_dataflow()
            else:
                self.generate_code()
    

    def compute_array_need_more_than_one_copy(self):

        all_arrays = list(self.array_information.keys())


        # inside same task
        for arr in all_arrays:
            self.array_need_complete_copy_inside_task[arr] = {}
            self.array_need_partial_copy_inside_task[arr] = {}
            self.array_dont_need_copy_per_schedule[arr] = {}
            polyhedrons = self.array_information[arr]["polyhedron"]
            intersections = self.array_information[arr]["intersection"]
            size_per_dim = self.array_information[arr]["size_per_dim"]
            polyhedron_sizes = self.array_information[arr]["polyhedron_size"]
            access = self.array_information[arr]["access"]

            for id_stat in list(polyhedrons.keys()):
                self.array_need_complete_copy_inside_task[arr][id_stat] = False
                self.array_need_partial_copy_inside_task[arr][id_stat]  = False
                if len(polyhedrons[id_stat]) > 1:
                    for i in range(len(polyhedrons[id_stat])):
                        for j in range(i+1, len(polyhedrons[id_stat])):
                            
                            if access[id_stat][i] != access[id_stat][j]:
                                # FIXME not correct
                                try:
                                    access1 = access[id_stat][i]
                                    access2 = access[id_stat][j]
                                    dom1 = self.analysis.dic[id_stat]["constraint"]
                                    dom2 = self.analysis.dic[id_stat]["constraint"]
                                    dom1 = " and ".join(dom1)
                                    dom2 = " and ".join(dom2)
                                    

                                    s1 = isl.Map(f"[i,j] -> {{ {access1} : {dom1} }}")
                                    s2 = isl.Map(f"[i,j] -> {{ {access2} : {dom2} }}")


                                    if intersections[id_stat][i][j] == min(polyhedron_sizes[id_stat][i], polyhedron_sizes[id_stat][j]):
                                        self.array_need_partial_copy_inside_task[arr][id_stat] = True
                                    else:
                                        if polyhedron_sizes[id_stat][i] != polyhedron_sizes[id_stat][j]:
                                            self.array_need_partial_copy_inside_task[arr][id_stat] = True
                                except:
                                    pass


        for arr in all_arrays:
            self.sched_need_different_copy_par_array[arr] = []
            self.condition_copy_array_between_statement[arr] = {}
            polyhedrons = self.array_information[arr]["polyhedron"]
            intersections = self.array_information[arr]["intersection"]
            size_per_dim = self.array_information[arr]["size_per_dim"]
            polyhedron_sizes = self.array_information[arr]["polyhedron_size"]
            access = self.array_information[arr]["access"]
            for k1, id_stat1 in enumerate(list(polyhedrons.keys())):
                for k2, id_stat2 in enumerate(list(polyhedrons.keys())):
                    if k2 > k1:
                        lp1 = polyhedrons[id_stat1]
                        lp2 = polyhedrons[id_stat2]
                        for k11, p1 in enumerate(lp1):
                            for k22, p2 in enumerate(lp2):
                                try:
                                    access1 = access[id_stat1][k11]
                                    access2 = access[id_stat2][k22]

                                    dom1 = self.analysis.dic[id_stat1]["constraint"]
                                    dom2 = self.analysis.dic[id_stat2]["constraint"]
                                    dom1 = " and ".join(dom1)
                                    dom2 = " and ".join(dom2)


                                    iterators1 = [self.iterators[self.schedule[id_stat1][i]] for i in range(1, len(self.schedule[id_stat1]), 2)]
                                    iterators1_bis = [self.iterators[self.schedule[id_stat1][i]] for i in range(1, len(self.schedule[id_stat1]), 2)]
                                    iterators2 = [self.iterators[self.schedule[id_stat2][i]] for i in range(1, len(self.schedule[id_stat2]), 2)]
                                    iterators2_bis = [self.iterators[self.schedule[id_stat2][i]] for i in range(1, len(self.schedule[id_stat2]), 2)]

                                    it_array1 = self.array_information[arr]["iterators"][id_stat1][k11]
                                    it_array2 = self.array_information[arr]["iterators"][id_stat2][k22]

                                    for i1 in range(len(iterators1)):
                                        if iterators1[i1] in it_array1:
                                            pass
                                        else:
                                            ub = self.UB[self.schedule[id_stat1][i1]]
                                            iterators1[i1] = f"{iterators1[i1]}={ub}"
                                            iterators1_bis[i1] = f"{iterators1_bis[i1]}=0"

                                    for i2 in range(len(iterators2)):
                                        if iterators2[i2] in it_array2:
                                            pass
                                        else:
                                            ub = self.UB[self.schedule[id_stat2][i2]]
                                            iterators2[i2] = f"{iterators2[i2]}={ub}"
                                            iterators2_bis[i2] = f"{iterators2_bis[i2]}=0"

                                    s1 = isl.Set(f"[{ ','.join(iterators1) }] -> {{ {access1} : {dom1} }}")
                                    s1_bis = isl.Set(f"[{ ','.join(iterators1_bis) }] -> {{ {access1} : {dom1} }}")
                                    s2 = isl.Set(f"[{ ','.join(iterators2) }] -> {{ {access2} : {dom2} }}")

                                    s2_bis = isl.Set(f"[{ ','.join(iterators2_bis) }] -> {{ {access2} : {dom2} }}")
                                    
                                    nb1 = s1.count_val().to_str()
                                    nb1_bis = s1_bis.count_val().to_str()
                                    nb2 = s2.count_val().to_str()
                                    nb2_bis = s2_bis.count_val().to_str()

                                    nb1 = max(int(nb1), int(nb1_bis))
                                    nb2 = max(int(nb2), int(nb2_bis))


                                    inter = s1.intersect(s2).to_str()

                                    if "false" in inter and abs(nb1 - nb2) > 1:
                                        self.array_need_more_than_one_copy[arr] = True
                                        self.sched_need_different_copy_par_array[arr].append([id_stat1, id_stat2])
                                    else:
                                        self.condition_copy_array_between_statement[arr][id_stat1] = []
                                        index_b = inter.index("[")
                                        index_e = inter.index("]")
                                        inter = inter[index_b+1:index_e]
                                        inter = inter.split(",")
                                        for inte in inter:
                                            if "=" in inte or "<" in inte or ">" in inte:
                                                self.condition_copy_array_between_statement[arr][id_stat1].append(inte)
                                except:
                                    pass   

        


    def compute_burst_dataflow(self):

        pos = []
        for arr in list(self.array_information.keys()):
            size_per_dim = self.array_information[arr]["size_per_dim"]

            if len(size_per_dim) == 0:
                continue
            innermost_dim_size = size_per_dim[-1]
            if arr in list(self.array_order.keys()):
                order = self.array_order[arr]
                if len(order) > 0:

                    innermost_dim_size = size_per_dim[order[-1]]
            for size in [16,8,4,2]:
                if int(innermost_dim_size) % size == 0:
                    pos.append(size)
                    break
        self.burst_dataflow = min(pos)

    def compute_constants(self):
        for stat in self.statements:
            ss = self.multi_split0(stat.replace(";", "").replace(" ", ""), ["+", "-", "*", "/", "="])

            ss = unique_list_in_order(ss)

            for s in ss:
                if "[" not in s:
                    if s not in self.constants:
                        self.constants.append(s)

    def create_tab(self, nb):
        nb = max(0,nb)
        return self.tab * nb

    def compute_arrays_information(self):
        all_arrays = []
        for stat in self.statements:
            if "=" in stat:

                out, inp = stat.split("=")
                out = out.strip().split("[")[0]

                inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)

                all_arrays += [out] 
                all_arrays += inp
        all_arrays = unique_list_in_order(all_arrays)

        for arr in all_arrays:
            arr = arr.replace("[", "").replace("]", "")
            self.array_information[arr] = {"size": 0, "type": "", "W": [], "size_burst": 0, "size_vector": 0, "statements": [], "dim": 0, "loop_to_dim": {}, "part_per_dim": [], "size_per_dim": [], "iterators":{}, "polyhedron":{}, "intersection":{}, "polyhedron_size": {}, "access":{}}
            for i, stat in enumerate(self.statements):

                out, inp = stat.split("=")
                out = out.strip().split("[")[0]
                if f"{arr}[" in stat:
                    self.array_information[arr]["statements"].append(i)
                if f"{arr}" in out:
                    self.array_information[arr]["W"].append(i)
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                self.array_information[arr]["iterators"][id_stat] = []
                self.array_information[arr]["polyhedron"][id_stat] = []
                self.array_information[arr]["polyhedron_size"][id_stat] = []
                self.array_information[arr]["access"][id_stat] = []
                self.array_information[arr]["intersection"][id_stat] = []
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                stat = self.statements[id_stat]
                out, inp = self.extract_array_and_constant(stat, False)
                all_ = [out] + inp
                for id_, al_ in enumerate(all_):

                    if al_.split("[")[0] == arr:

                        if "[" in al_:
                            it = al_[al_.index("[") + 1:-1].split("][")
                            self.array_information[arr]["iterators"][id_stat].append(it)
                            if ("+=" in stat or "-=" in stat or "*=" in stat or "/=" in stat) and id_ == 0: # output
                                self.array_information[arr]["iterators"][id_stat].append(it)

        for arr in all_arrays:
            for arg in self.arguments:
                if arr in arg:
                    self.array_information[arr]["type"] = arg.split(" ")[0].strip()
                    self.array_information[arr]["size"] = self.extract_size_array(arg)
                    self.array_information[arr]["size_per_dim"] = self.extract_size_array_dim(arg)
                    self.array_information[arr]["dim"] = arg.count("[")
                    self.array_information[arr]["part_per_dim"] = [1 for k in range(self.array_information[arr]["dim"])]
                    break
        for arr in all_arrays:
            for stat in self.array_information[arr]["statements"]:
                it_per_dim = []
                ss = self.multi_split(self.statements[stat].replace(";", "").replace(" ", ""), ["+", "-", "*", "/", "="])
                ss = unique_list_in_order(ss)
                for s in ss:
                    tmp = ["" for k in range(self.array_information[arr]["dim"])]
                    if f"{arr}[" in s:
                        index = s.index(f"[")
                        s = s[index:]
                        s = s.replace("][", "*")
                        s = s.replace("[", "")
                        s = s.replace("]", "")
                        tmp = s.split("*")
                        it_per_dim.append(tmp)

                loop_to_it = {}
                for i in range(1, len(self.schedule[stat]), 2):
                    loop = int(self.schedule[stat][i])
                    it = self.iterators[loop]
                    loop_to_it[loop] = it

                it_to_loop = {v: k for k, v in loop_to_it.items()}

                for i, it in enumerate(it_per_dim):
                    for j, it_ in enumerate(it):
                        if it_ in loop_to_it:
                            it_per_dim[i][j] = it_to_loop[it_]

                for pos in range(len(it_per_dim)):
                    for dim in range(len(it_per_dim[pos])):
                        self.array_information[arr]["loop_to_dim"][it_per_dim[pos][dim]] = dim
                for pos in range(len(it_per_dim)):
                    for dim in range(len(it_per_dim[pos])):
                        loop = it_per_dim[pos][dim]
                        if type(loop) == str:
                            continue
                        pragma_loop = self.pragmas[loop]
                        if pragma_loop != [""]:
                            if ";" in pragma_loop:
                                pragma_loop = pragma_loop.split(";")
                                for p in pragma_loop:
                                    if "unroll" in p.lower():
                                        factor = p.split("=")[-1].strip().replace(" ", "")
                                        self.array_information[arr]["part_per_dim"][dim] = max(self.array_information[arr]["part_per_dim"][dim], int(factor))
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                for i, it in enumerate(self.array_information[arr]["iterators"][id_stat]):
                    var1 = []
                    var2 = []

                    cond_arr1 = []
                    cond_arr2 = []
                    for j, it_ in enumerate(it):
                        if it_ != "":
                            if j < len(self.array_information[arr]['size_per_dim'])-1:
                                cond_arr1.append(f"0 <= {it_} < {self.array_information[arr]['size_per_dim'][j]}")
                                var1.append(f"{it_}")
                    cond_arr2 += self.analysis.dic[id_stat]["constraint"]
                    for conf in self.analysis.dic[id_stat]["constraint"]:
                        conf = conf.replace(" ", "").replace("+", "@").replace("-", "@").replace("0", "@").replace("1", "@").replace("2", "@").replace("3", "@").replace("4", "@").replace("5", "@").replace("6", "@").replace("7", "@").replace("8", "@").replace("9", "@").replace("=", "@").replace("<", "@").replace(">", "@")
                        conf = conf.split("@")

                        while "" in conf:
                            conf.remove("")
                        

                        var2 += conf
                    var1 = unique_list_in_order(var1)
                    var2 = unique_list_in_order(var2)

                    var = var1 + var2
                    var = unique_list_in_order(var)
                    cond1 = " and ".join(cond_arr1)
                    cond2 = " and ".join(cond_arr2)
                    # sort var
                    var1 = sorted(var1)
                    var2 = sorted(var2)
                    var = sorted(var)
                    while "" in var:
                        var.remove("")
                    str_1 = f"[{', '.join(var)}] -> {{ [{', '.join(var)}] :{cond1} }}"
                    str_2 = f"[{', '.join(var)}] -> {{ [{', '.join(var)}] :{cond2} }}"

                    try:
                        poly1 = isl.Set(str_1)
                    except:
                        continue
                    

                    try:
                        poly2 = isl.Set(str_2) #domain
                    except:
                        continue

                    poly = {} 

                    self.array_information[arr]["polyhedron"][id_stat].append(poly)
                    self.array_information[arr]["access"][id_stat].append(f"{arr}[{']['.join(it)}]")
                    self.array_information[arr]["polyhedron_size"][id_stat].append(0)
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                self.array_information[arr]["intersection"][id_stat] = {}
                for k1, elmt1 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                    self.array_information[arr]["intersection"][id_stat][k1] = {}
                    for k2, elmt2 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                        if k2!=k1:
                            self.array_information[arr]["intersection"][id_stat][k1][k2] = 0
        for arr in all_arrays:
            for id_stat in range(len(self.statements)):
                for k1, elmt1 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                    for k2, elmt2 in enumerate(self.array_information[arr]["polyhedron"][id_stat]):
                        if k2!=k1:
                            intersection = {} 
                            self.array_information[arr]["intersection"][id_stat][k1][k2] = intersection





    def extract_size_array(self, arg):
        if "[" in arg:
            index = arg.index("[")
            arg = arg[index:]
            arg = arg.replace("][", "*")
            arg = arg.replace("[", "")
            arg = arg.replace("]", "")
            return eval(arg)
        return 1
    
    def extract_size_array_dim(self, arg):
        if "[" in arg:
            index = arg.index("[")
            arg = arg[index:]
            arg = arg.replace("][", "*")
            arg = arg.replace("[", "")
            arg = arg.replace("]", "")
        return arg.split("*")

    def change_type_arguments_to_vector(self, size_vector_for_all_program=None):
        old_arguments = self.arguments
        self.arguments = []
        bits = 32
        for i, arg in enumerate(old_arguments):
            if "float" in arg:
                bits = 32
                self.type = "float"
            elif "int" in arg:
                bits = 32
                self.type = "int"
            elif "double" in arg:
                bits = 32
                self.type = "double"
            else:
                print("not supported for now")
                self.arguments = old_arguments
                continue
            if "[" not in arg:
                self.arguments += [old_arguments[i]]
                continue
            max_size_burst = 512 // bits
            size_burst = 0
            
            size_vector = 0
            size_array = self.extract_size_array(arg)

            name_array = arg.split(" ")[-1].split("[")[0]
            self.size_arrays[name_array] = size_array



            if size_vector_for_all_program is not None:
                size_burst = size_vector_for_all_program
                size_vector = size_array//size_burst
            else:
                if size_array%16 == 0 and 16 <= max_size_burst:
                    size_burst = 16
                    size_vector = size_array//16
                elif size_array%8 == 0 and 8 <= max_size_burst:
                    size_burst = 8
                    size_vector = size_array//8
                elif size_array%4 == 0 and 4 <= max_size_burst:
                    size_burst = 4
                    size_vector = size_array//4
                elif size_array%2 == 0 and 2 <= max_size_burst:
                    size_burst = 2
                    size_vector = size_array//2
                else:
                    self.arguments += [old_arguments[i]]
                    continue
            self.arguments += [f"{self.data_type}{size_burst} v{old_arguments[i].split(' ')[-1].split('[')[0]}[{size_vector}]"]

    def pre_treatement_statements(self):

        array = []
        for arg in self.arguments:
            if "[" in arg:
                array.append(arg.replace(f"{self.data_type}", "").replace(" ", "").split("[")[0])

        for i, stat in enumerate(self.statements):
            for arr in array:


                self.statements[i] = self.statements[i].replace(f"{arr}[0]", f"AAAA{arr}")
            self.statements[i] = self.statements[i].replace("[0]", "")
            for arr in array:
                self.statements[i] = self.statements[i].replace(f"AAAA{arr}", f"{arr}[0]")


    def multi_split0(self, str_, delimiters, delete_array=False):
        for delim in delimiters:
            str_ = str_.replace(delim, "@")
        res = str_.split("@")

        new_res = []
        if delete_array:
            for r in res:
                if "[" in r:
                    r = r.split("[")[0]
                new_res.append(r)
                while "" in res:
                    res.remove("")
            return new_res
        while "" in res:
            res.remove("")
        return res

    def multi_split(self, str_, delimiters, delete_array=False):
        if delete_array:
            new_str = ""
            inside_bracket = False
            for s in str_:
                if s == "[":
                    inside_bracket = True
                if not inside_bracket:
                    new_str += s
                if s == "]":
                    inside_bracket = False
            str_ = new_str

        for delim in delimiters:
            str_ = str_.replace(delim, "@")
        res = str_.split("@")

        new_res = []
        if delete_array:
            for r in res:
                if "[" in r:
                    r = r.split("[")[0]
                new_res.append(r)
                while "" in res:
                    res.remove("")
            return new_res
        while "" in res:
            res.remove("")
        return res
    
    def multi_split2(self, str_, delimiters, delete_array=False):
        for delim in delimiters:
            str_ = str_.replace(delim, "@")
        res = str_.split("@")
        new_res = []
        if delete_array:
            for r in res:
                if "[" in r:
                    r = r.split("[")[0]
                new_res.append(r)
                while "" in res:
                    res.remove("")
            return new_res
        while "" in res:
            res.remove("")
        return res

    def load(self, arg):
        str_ = f"memcpy(v{arg}, {arg}, {self.size_arrays[arg]}*sizeof({self.type}));\n"
        return str_

    def write(self, arg):

        str_ = f"memcpy({arg}, v{arg}, {self.size_arrays[arg]}*sizeof({self.type}));\n"
        return str_

    def array_partition(self, arg):
        name_array = arg.split(" ")[-1].split("[")[0]
        str_ = ""
        for i in range(self.array_information[name_array]["dim"]):
            if self.array_information[name_array]["part_per_dim"][i] != 1:
                str_ += f"#pragma HLS ARRAY_PARTITION variable={name_array} cyclic factor={self.array_information[name_array]['part_per_dim'][i]} dim={i+1}\n"

        return str_

    def generate_code(self):
        code = ""
        for header in self.headers:
            code += f"#include <{header}>\n"

        

        code += self.warnings
        code += "\n"
        code += f"typedef hls::vector<{self.data_type},16> {self.data_type}16;\n"
        code += f"typedef hls::vector<{self.data_type},8> {self.data_type}8;\n"
        code += f"typedef hls::vector<{self.data_type},4> {self.data_type}4;\n"
        code += f"typedef hls::vector<{self.data_type},2> {self.data_type}2;\n"
        code += f"typedef hls::vector<{self.data_type},1> {self.data_type}1;\n"
        code += "\n\n"

        old_arguments = self.arguments.copy()
        if self.optimize_burst:
            self.change_type_arguments_to_vector()
        define_on_chip = []
        define_off_chip = []

        for i, arg in enumerate(old_arguments):
            name = arg.split("[")[0].replace(f"{self.data_type}", "").replace(" ", "")
            if name in self.analysis.chip["off_chip"]:
                define_off_chip.append(arg)
            if name in self.analysis.chip["on_chip"]:
                define_on_chip.append(arg)

        code += f"\nvoid {self.name_function}({', '.join(define_off_chip)}) {{\n\n"
        if not self.normale_file:
            for arg in self.arguments:
                name = arg.split("[")[0].split(" ")[-1]
                code += f"#pragma HLS INTERFACE m_axi port={name} offset=slave bundle=kernel_{name}\n"
            for arg in self.arguments:
                name = arg.split("[")[0].split(" ")[-1]
                code += f"#pragma HLS INTERFACE s_axilite port={name} bundle=control\n"
            for arg in self.arguments:
                name = arg.split("[")[0].split(" ")[-1]
                code += f"#pragma HLS DATA_PACK VARIABLE={name}\n"
            
            code += "#pragma HLS INTERFACE s_axilite port=return bundle=control\n\n"
        
        for arg in define_on_chip:
            code += f"{self.tab}{arg};\n"

        for it in list(set(self.iterators)):
            code += f"{self.tab}int {it};\n"

        if self.optimize_burst:
            for arg in old_arguments:
                code += f"{arg};\n"

            
            for arg in old_arguments:
                code += self.array_partition(arg)

        loads = []
        writes = []
        for i, stat in enumerate(self.statements):
            out, inp = stat.split("=")
            out = out.strip().split("[")[0]
            inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
            
            writes += [out.replace("+", "").replace("/", "").replace("-", "").replace("*", "").replace(" ", "")]
            loads += inp
        while "" in loads:
            loads.remove("")

        
        #FIXME: delete load if initiatlization on chip

        writes = unique_list_in_order(writes)
        loads = unique_list_in_order(loads)


        if not self.normale_file:
            for l in loads:
                if l not in self.constants:
                    code += self.load(l)


        for o in self.ast.order:
            code += f"{o}\n"
        if not self.normale_file:
            for w in writes:

                if w not in self.constants:
                    code += self.write(w)

        code += "}\n"
        
        with open(self.output, "w") as f:
            f.write(code)

    
    def generate_code_dataflow(self):
        code = ""
        main_function = ""
        for header in self.headers:
            code += f"#include <{header}>\n"

        size_array_dim = {}

        code += self.warnings
        code += "\n"
        code += f"typedef hls::vector<{self.data_type},16> {self.data_type}16;\n"
        code += f"typedef hls::vector<{self.data_type},8> {self.data_type}8;\n"
        code += f"typedef hls::vector<{self.data_type},4> {self.data_type}4;\n"
        code += f"typedef hls::vector<{self.data_type},2> {self.data_type}2;\n"
        code += f"typedef hls::vector<{self.data_type},1> {self.data_type}1;\n"
        code += "\n\n"
        old_arguments = self.arguments.copy()

        if self.optimize_burst:
            self.change_type_arguments_to_vector(self.burst_dataflow)

        for i, arg in enumerate(old_arguments):
            if "float" in arg:
                bits = 32
                self.type = "float"
            elif "int" in arg:
                bits = 32
                self.type = "int"
            elif "double" in arg:
                bits = 32
                self.type = "double"
            else:
                print("not supported for now")
                self.arguments = old_arguments
                continue
            if "[" not in arg: # not an array
                self.arguments += [old_arguments[i]]
                continue
            max_size_burst = 512 // bits
            size_burst = 0
            size_vector = 0
            size_array_dim_ = self.extract_size_array_dim(arg)
            name = arg.split("[")[0].split(" ")[-1]
            size_array_dim[name] = size_array_dim_

        cte_declaration = self.find_cte_declaration()

        arguments = []
        for cte in cte_declaration:
            arguments += [f"{self.data_type} {cte}"]
        arguments += self.arguments
        main_function += f"\nvoid {self.name_function}({', '.join(arguments)}) {{\n\n"
        for arg in cte_declaration:
            main_function += f"#pragma HLS INTERFACE m_axi port={arg} offset=slave bundle=cte_{arg}\n"
        for arg in self.arguments:
            name = arg.split("[")[0].split(" ")[-1]
            main_function += f"#pragma HLS INTERFACE m_axi port={name} offset=slave bundle=kernel_{name}\n"
        for arg in cte_declaration:
            main_function += f"#pragma HLS INTERFACE s_axilite port={arg} bundle=control\n"
        for arg in self.arguments:
            name = arg.split("[")[0].split(" ")[-1]
            main_function += f"#pragma HLS INTERFACE s_axilite port={name} bundle=control\n"
        for arg in self.arguments:
            name = arg.split("[")[0].split(" ")[-1]
            main_function += f"#pragma HLS DATA_PACK VARIABLE={name}\n"
        
        main_function += "#pragma HLS INTERFACE s_axilite port=return bundle=control\n\n"
        fifo_per_array = {}
        for arg in old_arguments:
            name = arg.split("[")[0].split(" ")[-1]
            fifo_per_array[name] = []
            in_statements = []

            is_write = len(self.array_information[name]["W"]) > 0

            for i in range(len(self.statements)):
                if f"{name}[" in self.statements[i]:
                    in_statements.append(str(i))
            
            if is_write:
                in_statements.append("off_chip")
            for i in in_statements:
                defi = ""
                if "off_chip" in i:
                    defi = f"fifo_{name}_to_{i}"
                else:
                    defi = f"fifo_{name}_S{i}"
                fifo_per_array[name].append(defi)
                if self.optimize_burst:
                    main_function += f"    hls::stream<{self.type}{self.burst_dataflow}> {defi};\n"
                else:
                    main_function += f"    hls::stream<{self.type}> {defi};\n"


        main_function += "\n"
        main_function += "#pragma HLS DATAFLOW\n"
        main_function += "\n"

        loads = []
        writes = []
        for i, stat in enumerate(self.statements):
            out, inp = stat.split("=")
            out = out.strip().split("[")[0]
            inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
            
            writes += [out]
            loads += inp

        
        #FIXME: delete load if initiatlization on chip

        writes = unique_list_in_order(writes)
        loads = unique_list_in_order(loads)


        all_arrays = unique_list_in_order(loads+writes)
        all_arrays = self.remove_init_on_chip(all_arrays)

        for arr in all_arrays:

            if arr in list(self.array_need_more_than_one_copy.keys()) and self.array_need_more_than_one_copy[arr]:
                pass # FIXME and TODO burst + cyclic
                if arr in list(self.sched_need_different_copy_par_array.keys()):
                    if len(list(self.sched_need_different_copy_par_array[arr])):

                        statement_arr_present = self.array_information[arr]["statements"]

                        all_arr_diff = []
                        for pos1 in self.sched_need_different_copy_par_array[arr]:
                            for pos2 in pos1:
                                all_arr_diff += [pos2]
                        all_arr_diff = unique_list_in_order(all_arr_diff)
                        # sort
                        all_arr_diff = sorted(all_arr_diff)

                        load_per_stat = []
                        tmp = []
                        for stat in statement_arr_present:
                            if stat in all_arr_diff:
                                if len(tmp)  > 0:
                                    load_per_stat.append(tmp)
                                tmp = []
                            tmp += [stat]
                        if len(tmp) > 0:
                            load_per_stat.append(tmp)
                        self.array_dont_need_copy_per_schedule[arr] = [l[-1] for l in load_per_stat]
                        for diff_load in range(len(load_per_stat)):
                            code += self.generate_load_dataflow(arr, f"fifo_{arr}_S{load_per_stat[diff_load][0]}", size_array_dim[arr], diff_load)
                            if self.optimize_burst:
                                main_function += f"    load_{arr}_{diff_load}(fifo_{arr}_S{load_per_stat[diff_load][0]}, v{arr});\n"
                            else:
                                main_function += f"    load_{arr}_{diff_load}(fifo_{arr}_S{load_per_stat[diff_load][0]}, {arr});\n"
            else:
                is_float = False
                try:
                    a = float(arr)
                    is_float = True
                except:
                    pass
                if not is_float:
                    code += self.generate_load_dataflow(arr, fifo_per_array[arr][0], size_array_dim[arr])
                    if self.optimize_burst:
                        main_function += f"    load_{arr}({fifo_per_array[arr][0]}, v{arr});\n"
                    else:
                        main_function += f"    load_{arr}({fifo_per_array[arr][0]}, {arr});\n"


        for k, o in enumerate(self.ast.order_per_loop_body):
            fifo_read = []
            fifo_write = []
            for key in list(fifo_per_array.keys()):
                for j, elmt in enumerate(fifo_per_array[key]):
                    if f"S{k}" in elmt:

                        need_read = True
                        if key in self.dont_need_load and j == 0:
                            need_read = False
                        if need_read:
                            fifo_read.append(fifo_per_array[key][j])

                        if len(fifo_per_array[key]) > j+1:
                            fifo_write += [fifo_per_array[key][j+1]]
                        if self.ast.lastWrite[key] == k:
                            if f"fifo_{key}_to_off_chip" not in fifo_write:
                                fifo_write += [f"fifo_{key}_to_off_chip"]
            
            code += self.generate_code_dataflow_per_loop_body(k, o, fifo_per_array, fifo_read, fifo_write)
            arg = ""
            for t, fr in enumerate(self.cte_declaration_per_stat[k]):
                arg += f"{fr}"
                arg += ", "

            for t, fr in enumerate(fifo_read):
                
                arg += f"{fr}"
                arg += ", "

            for t, fw in enumerate(fifo_write):
                arg += f"{fw}"
                if t != len(fifo_write)-1:
                    arg += ", "

            if arg [-2] == ",":
                arg = arg[:-2]


            main_function += f"    task{k}({arg});\n"

        for arr in writes:
            code += self.generate_write_dataflow(arr, fifo_per_array[arr][-1], size_array_dim[arr])
            if self.optimize_burst:
                main_function += f"    write_{arr}({fifo_per_array[arr][-1]}, v{arr});\n"
            else:
                main_function += f"    write_{arr}({fifo_per_array[arr][-1]}, {arr});\n"
        main_function += "}\n"

        code += main_function

        with open(self.output, "w") as f:
            f.write(code)


    def remove_init_on_chip(self, all_arrays):
        self.dont_need_load = []
        for stat in self.statements:
            out, inp = stat.split("=")
            out = out.strip().split("[")[0]
            inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
            if len(inp) == 0:
                all_arrays.remove(out)
                self.dont_need_load.append(out)
        return all_arrays

    def find_cte_declaration(self):
        self.cte_declaration_per_stat = {}
        cte = []
        for k, stat in enumerate(self.statements):
            self.cte_declaration_per_stat[k] = []
            out, inp = stat.split("=")
            out = out.strip().split("[")[0]
            inp = self.multi_split2(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], False)
            for i in inp:
                if "[" not in i or "[0]" in i:
                    

                    i = i.replace(f"{self.data_type}", "").replace(" ", "")
                    try:
                        ii = i
                        ii = ii.replace("(", "").replace(")", "") 

                        ii = float(ii)
                    except:
                        cte.append(i)
                        self.cte_declaration_per_stat[k].append(i)

        return cte

    def generate_code_dataflow_per_loop_body(self, id_, order, fifo_per_array, fifo_read, fifo_write):
        str_ = f"void task{id_}("
        for k, fr in enumerate(self.cte_declaration_per_stat[id_]):
            str_ += f"{self.type} {fr}"
            str_ += ", "
        for k, fr in enumerate(fifo_read):
            if self.optimize_burst:
                str_ += f"hls::stream<{self.type}{self.burst_dataflow}> &{fr}"
            else:
                str_ += f"hls::stream<{self.type}> &{fr}"
            str_ += ", "
        for k, fw in enumerate(fifo_write):
            if self.optimize_burst:
                str_ += f"hls::stream<{self.type}{self.burst_dataflow}> &{fw}"
            else:
                str_ += f"hls::stream<{self.type}> &{fw}"
            if k != len(fifo_write)-1:
                str_ += ", "
        if str_[-2] == ",":
            str_ = str_[:-2]
        str_ += "){\n"
        for o in order:
            str_ += f"{o}\n"
        str_ += "}\n"
        return str_

    def generate_load_dataflow_special_transfer(self, name_array, name_fifo, size_array, id_ = None):
        str_ = ""
        if id_ is None or id_ == "":
            id_first_stat = self.array_information[name_array]["statements"][0]
        else:

            id_first_stat = self.array_dont_need_copy_per_schedule[name_array][id_]

        iterator = self.array_information[name_array]["iterators"][id_first_stat]
        iterators_schedule = [self.iterators[self.schedule[id_first_stat][i]] for i in range(1, len(self.schedule[id_first_stat]), 2)]

        LB = [self.LB_[self.schedule[id_first_stat][i]] for i in range(1, len(self.schedule[id_first_stat]), 2)]
        UB = [self.UB_[self.schedule[id_first_stat][i]] for i in range(1, len(self.schedule[id_first_stat]), 2)]

        all_cte = False
        try:
            LB = [int(l) for l in LB]
            UB = [int(u) for u in UB]
            all_cte = True
        except:
            pass

        all_arry_copy = False
        if all_cte:
            size_array = list(map(int, self.array_information[name_array]["size_per_dim"]))
            size_array = np.prod(size_array)

            for case in iterator:
                size = 1
                for it in case:
                    
                    for i in range(1, len(self.schedule[id_first_stat]), 2):
                        current_it = self.iterators[self.schedule[id_first_stat][i]]
                        lb = int(self.LB_[self.schedule[id_first_stat][i]])
                        ub = int(self.UB_[self.schedule[id_first_stat][i]])
                        if it == current_it:
                            size *= (ub - lb+1)

                if size == size_array:
                    all_arry_copy = True
                    break



        if all_cte and all_arry_copy:
            return False, str_

        if self.optimize_burst:
            tab = self.create_tab(1)

            size_array = list(map(int, self.array_information[name_array]['size_per_dim']))
            size_array = np.prod(size_array) / self.burst_dataflow
            size_array = int(size_array)
            if id_ is None:
                str_ = f"void load_{name_array}(hls::stream<{self.type}{self.burst_dataflow}> &{name_fifo}, {self.type}{self.burst_dataflow} {name_array}[{size_array}]) {{\n"
            else:
                str_ = f"void load_{name_array}_{id_}(hls::stream<{self.type}{self.burst_dataflow}> &{name_fifo}, {self.type}{self.burst_dataflow} {name_array}[{size_array}]) {{\n"
            str_ += f"{tab}{self.data_type} tmp[{']['.join(self.array_information[name_array]['size_per_dim'])}];\n"
            
            for k,dim in enumerate(self.array_information[name_array]['size_per_dim']):
                tab = self.create_tab(1+k)
                str_ += f"{tab}for (int i{k} = 0; i{k} < {dim}; i{k}++) {{\n"

            str_ += f"{tab}#pragma HLS pipeline II=1 // pip\n"
            str_ += f"{tab}tmp[i0"
            for k,dim in enumerate(self.array_information[name_array]['size_per_dim'][1:]):
                str_ += f"][i{k+1}"
            str_ += f"] = {name_fifo}.read();\n"

            for k,dim in enumerate(self.array_information[name_array]['size_per_dim']):
                tab = self.create_tab(len(self.array_information[name_array]['size_per_dim'])-k)
                str_ += f"{tab}}}\n"
                
            
            str_ += f"}}\n"
        else:

            tab = self.create_tab(1)
            str_ = f"void load_{name_array}_{id_}(hls::stream<{self.type}> &{name_fifo}, {self.type} {name_array}[{']['.join(self.array_information[name_array]['size_per_dim'])}]) {{\n"
            str_ += f"{tab}{self.data_type} tmp[{']['.join(self.array_information[name_array]['size_per_dim'])}];\n"
            
            for k,dim in enumerate(self.array_information[name_array]['size_per_dim']):
                tab = self.create_tab(1+k)
                str_ += f"{tab}for (int i{k} = 0; i{k} < {dim}; i{k}++) {{\n"

            str_ += f"#pragma HLS pipeline II=1\n"
            cond = "Cond"
            

            iterator = iterator[0]

            if not all_cte:
                cond1 = ""
                for i, it in enumerate(iterators_schedule):
                    lb = LB[i]
                    ub = UB[i]
                    try:
                        lb = int(lb)
                    except:
                        pass
                    try:
                        ub = int(ub)
                    except:
                        for it2 in iterator:
                            index = iterator.index(it2)

                            ub = ub.replace(it2, f"i{index}")

                    cond1 += f"i{i} >= {lb} && i{i} <= {ub}"
                    if i != len(iterators_schedule)-1:
                        cond1 += " && "
                cond = f"if ({cond1})"

            elif not all_arry_copy:
                cond = ""
                cond1 = []
                same_it = []
                for k1, ii1 in enumerate(iterator):
                    for k2, ii2 in enumerate(iterator):
                        if k2>k1:
                            if ii1 == ii2:
                                cond1.append(f"i{k1} == i{k2}")
                
                if len(cond1) > 0:
                    cond = "if ("
                    for i, c in enumerate(cond1):
                        cond += c
                        if i != len(cond1)-1:
                            cond += " && "
                    cond += ")"


            write = f"{name_array}[i0"
            for k,dim in enumerate(self.array_information[name_array]['size_per_dim'][1:]):
                write += f"][i{k+1}"
            write += "]"
            str_ += f"{tab}{cond} {name_fifo}.write({write});\n"

            for k,dim in enumerate(self.array_information[name_array]['size_per_dim']):
                tab = self.create_tab(len(self.array_information[name_array]['size_per_dim'])-k)
                str_ += f"{tab}}}\n"
                
            
            str_ += f"}}\n"
        

        return True, str_

    def generate_load_dataflow(self, name_array, name_fifo, size_array, id_ = None):
        # FIXME we need to know the order

        bb, str_ = self.generate_load_dataflow_special_transfer(name_array, name_fifo, size_array, id_)
        if bb:
            return str_

        order=[]
        # FIXME: if we burst and the order of the array does not iterate in last the last dimension we need to find an other way to transfer

        if id_ is None:
            id_ = ""
        else:
            id_ = "_" + str(id_)


        
        
        size_array_str = "][".join(size_array)
        size_array = list(map(int, size_array))
        curr_space = "  "
        if self.optimize_burst:

            size_array_str = str(int(np.prod(size_array) // self.burst_dataflow))
            str_ = f"void load_{name_array}{id_}(hls::stream<{self.type}{self.burst_dataflow}> &{name_fifo}, {self.type}{self.burst_dataflow} {name_array}[{size_array_str}]) {{\n"
        else:
            str_ = f"void load_{name_array}{id_}(hls::stream<{self.type}> &{name_fifo}, {self.type} {name_array}[{size_array_str}]) {{\n"
        if name_array in list(self.array_order.keys()) and self.array_order[name_array] != "":
            order = list(self.array_order[name_array])
            for dim in range(len(size_array)):
                if dim == len(size_array) -1 and self.optimize_burst:
                    str_ += f"{curr_space}for (int i{order[dim]} = 0; i{order[dim]} < {int(size_array[order[dim]]) // self.burst_dataflow}; i{order[dim]}++) {{\n"
                else:
                    str_ += f"{curr_space}for (int i{order[dim]} = 0; i{order[dim]} < {size_array[order[dim]]}; i{order[dim]}++) {{\n"
                if dim == len(size_array)-1:
                    str_ += "#pragma HLS pipeline II=1\n"
                curr_space += "  "
        else:
            for dim in range(len(size_array)):
                if dim == len(size_array) -1 and self.optimize_burst:
                    str_ += f"{curr_space}for (int i{dim} = 0; i{dim} < {int(size_array[dim]) // self.burst_dataflow}; i{dim}++) {{\n"
                else:
                    str_ += f"{curr_space}for (int i{dim} = 0; i{dim} < {size_array[dim]}; i{dim}++) {{\n"
                if dim == len(size_array)-1:
                    str_ += "#pragma HLS pipeline II=1\n"
                curr_space += "  "
        

        str_ += f"{curr_space}{name_fifo}.write("
        str_ += f"{name_array}["
        if self.optimize_burst:
            for dim in range(len(size_array)):
                prod = 1
                if dim != len(size_array)-1:
                    for dim2 in range(dim+1, len(size_array)):
                        if dim2 == len(size_array)-1:
                            prod *= size_array[dim2] // self.burst_dataflow
                        else:
                            prod *= size_array[dim2]
                if prod > 1:
                    str_ += f"i{dim} * {prod}"
                else:
                    str_ += f"i{dim}"
                if dim != len(size_array)-1:
                    str_ += " + "
            str_ += f"]);\n"
        else:
            for dim in range(len(size_array)):
                str_ += f"i{dim}"
                if dim != len(size_array)-1:
                    str_ += "]["
            str_ += f"]);\n"
        curr_space = curr_space[:-2]
        for dim in range(len(size_array)):
            str_ += f"{curr_space}}}\n"
            curr_space = curr_space[:-2]

        str_ += "}\n"
        return str_

    
    def generate_write_dataflow(self, name_array, name_fifo, size_array, order = []):
        size_array_str = "][".join(size_array)
        size_array = list(map(int, size_array))
        curr_space = "  "
        if self.optimize_burst:

            size_array_str = str(int(np.prod(size_array) // self.burst_dataflow))
            str_ = f"void write_{name_array}(hls::stream<{self.type}{self.burst_dataflow}> &{name_fifo}, {self.type}{self.burst_dataflow} {name_array}[{size_array_str}]) {{\n"
        else:
            str_ = f"void write_{name_array}(hls::stream<{self.type}> &{name_fifo}, {self.type} {name_array}[{size_array_str}]) {{\n"
        if len(order) == 0:
            for dim in range(len(size_array)):
                if dim == len(size_array) - 1 and self.optimize_burst:
                    str_ += f"{curr_space}for (int i{dim} = 0; i{dim} < {size_array[dim] // self.burst_dataflow}; i{dim}++) {{\n"
                else:
                    str_ += f"{curr_space}for (int i{dim} = 0; i{dim} < {size_array[dim]}; i{dim}++) {{\n"
                if dim == len(size_array)-1:
                    str_ += "#pragma HLS pipeline II=1\n"
                curr_space += "  "
        else:
            for dim in range(len(size_array)):
                if dim == len(size_array) - 1 and self.optimize_burst:
                    str_ += f"{curr_space}for (int i{order[dim]} = 0; i{order[dim]} < {size_array[order[dim]]//self.burst_dataflow}; i{order[dim]}++) {{\n"
                else:
                    str_ += f"{curr_space}for (int i{order[dim]} = 0; i{order[dim]} < {size_array[order[dim]]}; i{order[dim]}++) {{\n"
                if dim == len(size_array)-1:
                    str_ += "#pragma HLS pipeline II=1\n"
                curr_space += "  "
        str_ += f"{curr_space}{name_array}["
        for dim in range(len(size_array)):
            str_ += f"i{dim}"
            if dim != len(size_array)-1:
                str_ += "]["
        str_ += f"] = {name_fifo}.read();\n"
        curr_space = curr_space[:-2]
        for dim in range(len(size_array)):
            str_ += f"{curr_space}}}\n"
            curr_space = curr_space[:-2]

        str_ += "}\n"
        return str_
    
    def extract_array_and_constant(self, statement, remove_bracket=True):
        out = statement.split("=")[0]
        if remove_bracket:
            out = out.strip().split("[")[0]
        else:
            if len(out) > 0 and "]" in out:

                while out[-1] != "]":
                    out = out[:-1]
        inp = statement.split("=")[1]
        inp = self.multi_split2(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], remove_bracket)
        return out, inp

    def extract_iteration_per_dim(self, stat, array):
        it_per_dim = []
        ss = self.multi_split(stat.replace(";", "").replace(" ", ""), ["+", "-", "*", "/", "="])
        ss = unique_list_in_order(ss)
        for s in ss:
            if f"{array}[" in s:
                index = s.index(f"[")
                s = s[index:]
                s = s.replace("][", "*")
                s = s.replace("[", "")
                s = s.replace("]", "")
                tmp = s.split("*")
                it_per_dim.append(tmp)

        if len(it_per_dim) == 0:
            return []
        return it_per_dim[0]