# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os


class PostPass:
    def __init__(self, no_flattening, vitis_version, data_type, fully_distributed_file, folder, output, nlp_file, nlp_log):
        self.vitis_version = vitis_version
        self.no_flattening = no_flattening
        self.data_type = data_type
        self.folder = folder
        self.fully_distributed_file = fully_distributed_file
        self.output = output
        self.nlp_file = nlp_file
        self.nlp_log = nlp_log
        self.info_log = {}
        self.extract_info()
        self.reorder()
        self.pre_pass_simplify_reduction_specific_case()
        self.simplify_reduction_specific_case()

        self.transform_when_loop_are_non_constant()
        self.transform_for_2021()
        self.apply_no_flattening()

    def apply_no_flattening(self):
        if not self.no_flattening:
            return
        f = open(self.output, "r")
        lines = f.readlines()
        f.close()

        last_for = -1
        last_last_for = -1

        for k, line in enumerate(lines):
            if "for" in line:
                last_last_for = last_for
                last_for = k
            if "#pragma" in line and "pipeline" in line:
                if last_last_for != -1:
                    lines[last_last_for] += f"#pragma HLS loop_flatten off\n"
        f = open(self.output, "w")
        f.writelines(lines)
        f.close()


    def transform_for_2021(self):
        if "2021" not in self.vitis_version:
            return
        f = open(self.output, "r")
        lines = f.readlines()
        f.close()
        for k, line in enumerate(lines):
            if "#pragma HLS" in line and "inline" in line:
                lines[k] = ""
        for k, line in enumerate(lines):
            if "void" in line and "kernel_nlp" not in line:
                lines[k] += "#pragma HLS inline\n"


        id_task = 0
        for k, line in enumerate(lines):
            if "void task" in line:
                id_task = line.split("task")[-1].split("(")[0]
            if "for" in line and "#pragma" in lines[k+1] and "pipeline" in lines[k+1]:
                lines[k+1] = f"#pragma HLS pipeline II={self.info_log[f'II_S{id_task}']}\n"
        f = open(self.output, "w")
        f.writelines(lines)
        f.close()

    def transform_when_loop_are_non_constant(self):
        f = open(self.fully_distributed_file, "r")
        lines = f.readlines()
        f.close()

        id_stat = 0
        already_seen = False
        nb_bracket = 0
        non_cte_found = []
        for k, line in enumerate(lines):
            if "{" in line and "void" not in line:
                nb_bracket += 1
                already_seen = True
            if "}" in line:
                nb_bracket -= 1
            if nb_bracket == 0 and already_seen:
                id_stat += 1
            if "for" in line:
                lb, ub, inc = line.split("(")[-1].split(")")[0].split(";")
                lb_ = lb.replace("<", "!").replace(">", "!").replace("=", "!").split("!")[-1]
                val_lb = lb_.replace(" ", "")
                ub_ = ub.replace("<", "!").replace(">", "!").replace("=", "!").split("!")[-1]
                val_ub = ub_.replace(" ", "")

                try:
                    int(val_lb)
                except:
                    if ">" not in lb and "<" not in lb:
                        lb = lb.replace("=", ">=")
                    non_cte_found.append((id_stat, "lb", lb))

                try:
                    int(val_ub)
                except:
                    non_cte_found.append((id_stat, "ub", ub))

        all_cte_per_loop_body = {}

        for case in non_cte_found:
            id_stat = case[0]
            all_cte_per_loop_body[id_stat] = []
        for case in non_cte_found:
            id_stat = case[0]
            all_cte_per_loop_body[id_stat].append(case[2])

        for case in list(all_cte_per_loop_body.keys()):
            id_stat = case
            all_cte_str = " && ".join(all_cte_per_loop_body[id_stat])
            task, start, end = self.extract_task(f"task{id_stat}")
            tab = "    "

            for k, line in enumerate(task):

                if "for" in line:
                    tab += "    "
                if "=" in line and "[" in line:
                    symbol = " ="
                    if "+=" in line:
                        symbol = "+="
                    elif "-=" in line:
                        symbol = "-="
                    elif "*=" in line:
                        symbol = "*="
                    elif "/=" in line:
                        symbol = "/="
                    output = line.split(symbol)[0].replace(" ", "")
                    input = line.split(symbol)[1]
                    if symbol != " =":
                        op = symbol.replace("=", "")
                        input = f"{output} {op} {input}"
                    str_ = input.replace(";", "").replace("\n", "").replace(" ", "")
                    arg, op = self.extract_arg(str_)
                    header = []

                    task[k] = f"//{task[k]}{tab}{output} = compute_operation_task{case}("
                    task[k] += f"{output}, "
                    header += [f"{self.data_type} output"]

                    iterator_of_cond = []
                    all_cte = all_cte_str.replace("&&", "").replace("<", "!").replace(">", "!").replace("=", "!").replace(" ", "").replace("+", "!").replace("-", "!").replace("/", "!").replace("*", "!").split("!")
                    all_cte = [x for x in all_cte if x != ""]
                    all_cte = list(set(all_cte))

                    all_cte_new = []
                    for elemt in all_cte:
                        try:
                            int(elemt)
                        except:
                            all_cte_new.append(elemt)
                    all_cte = all_cte_new

                    

                    for j in range(len(arg)):
                        task[k] += f"{arg[j]}"
                        header += [f"{self.data_type} arg{j}"]
                        if j != len(arg) - 1:
                            task[k] += ", "
                    for j in range(len(all_cte)):
                        task[k] += f", {all_cte[j]}"
                        header += [f"int {all_cte[j]}"]
                    task[k] += ");\n"
                    break
            compute_fct = [f"{self.data_type} compute_operation_task{case}("]
            for k, line in enumerate(header):
                compute_fct.append(f"    {line}")
                if k != len(header) - 1:
                    compute_fct[-1] += ","
            operation = ""
            last_op = -1
            for k, line in enumerate(op):
                operation += f"arg{k} {line} "
                last_op = k
            operation += f"arg{last_op+1}"
            
            compute_fct.append(") {\n")
            compute_fct.append(f"    if ({all_cte_str}){{\n")
            compute_fct.append(f"        return {operation};\n")
            compute_fct.append("    }\n")
            compute_fct.append(f"    else{{\n")
            compute_fct.append(f"        return output;\n")
            compute_fct.append("    }\n")
            compute_fct.append("}\n")

        
            self.lines = self.lines[:start] + compute_fct + task + self.lines[end+1:]
            f = open(self.output, "w")
            f.writelines(self.lines)
            f.close()

    def extract_arg(self, str_):
        inside_bracket = False
        arg = []
        op = []
        arg_ = ""
        for c in str_:
            if c == "[":
                inside_bracket = True
            if c == "]":
                inside_bracket = False
            if (c == "+" or c == "-" or c == "*" or c == "/" ) and not inside_bracket:
                op += [c]
                arg.append(arg_)
                arg_ = ""
            else:
                arg_ += c
        arg.append(arg_)
        return arg, op

    def extract_task(self, name):
        nb_bracket = 0
        for k, line in enumerate(self.lines):
            if f"void {name}" in line:
                start = k
                break
        for k, line in enumerate(self.lines[start:]):
            if "{" in line:
                nb_bracket += 1
            if "}" in line:
                nb_bracket -= 1
            if nb_bracket == 0:
                end = k + start
                break
        return self.lines[start:end+1], start, end

    def extract_info(self):
        f = open(self.nlp_file, "r")
        lines = f.readlines()
        f.close()

        schedule = []
        iterators = {}
        is_red = {}
        tc = {}

        for k, line in enumerate(lines):
            if "#schedule" in line:
                sched_stat = lines[k].replace("\n", "").replace("#schedule ", "").split(" ")
                schedule.append(sched_stat)
                it_line = lines[k+1].replace("\n", "").replace("#iterators ", "").split(" ")
                for id_loop in range(1, len(sched_stat), 2):
                    iterators[sched_stat[id_loop]] = it_line[(id_loop-1)//2]
                for j in range(k+2, k+2+len(it_line)):
                    name = lines[j].split("_")[-1].split(" :")[0]
                    if "False" in lines[j]:
                        is_red[name] = False
                    else:
                        is_red[name] = True
            if "param" in line and "TC" in line:
                id_loop = line.split("TC")[-1].split(" =")[0]
                val = line.split(" = ")[-1].split(";")[0]
                tc[id_loop] = val
        
        self.schedule, self.iterators, self.is_red, self.tc = schedule, iterators, is_red, tc

        f = open(self.nlp_log, "r")
        lines = f.readlines()
        f.close()

        for k, line in enumerate(lines):
            if "=" in line and "trace" not in line and "sumfile" not in line and "maxtime" not in line:
                try:
                    key = line.split(" = ")[0]
                    val = line.split(" = ")[1].replace("\n", "")
                    self.info_log[key] = val
                except:
                    pass
    
    def extract_statements(self):
        l = []
        inside = False
        for k, line in enumerate(self.lines):
            if "void kernel_nlp" in line:
                inside = False
            elif "void" in line and "task" in line:
                inside = True
            if inside:
                if "=" in line and "[" in line:
                    l += [line.replace("\n", "").replace(";", "").replace(" ", "")]
        return l

    def pre_pass_simplify_reduction_specific_case(self):
        for statement in range(len(self.schedule)):
            task, start, end = self.extract_task(f"task{statement}")
            loops = []
            first = -1
            end_ = -1
            for k, line in enumerate(task):
                if "for" in line:
                    if f"2 <" in line:
                        if "unroll" in task[k+1]:
                            loops.append(line)
                if "unroll" in line:
                    end_ = k
                if "for" in line and "2 <" in line:
                    if first == -1:
                        first = k
            par = []
            seq = []
            loops_sched = self.schedule[statement][1::2]
            for line in loops:
                name_it = line.split("int ")[-1].split(" = ")[0].replace("2", "")
                id_loop = -1
                for loop in loops_sched:
                    if self.iterators[loop] == name_it:
                        id_loop = loop
                if self.is_red[id_loop]:
                    seq.append(line)
                else:
                    par.append(line)
            
            for k in range(first, end_+1):
                task[k] = ""
            
            for k in range(len(par)):
                task.insert(first+k, par[k])
            for k in range(len(seq)):
                task.insert(first+k+len(par), seq[k])

            self.lines = self.lines[:start] + task + self.lines[end+1:]
        f = open(self.output, "w")
        f.writelines(self.lines)
        f.close()


    def simplify_reduction_specific_case(self):

        for statement in range(len(self.schedule)):
            is_one_red = False
            loops = self.schedule[statement][1::2]
            for loop in loops:
                if self.is_red[loop]:
                    is_one_red = True
            if not is_one_red:
                continue
            
            all_are_fully_unrolled = True
            for loop in loops:
                if self.is_red[loop]:
                    if self.info_log[f"TC{loop}_0"] != "1" or self.info_log[f"TC{loop}_1"] != "1":
                        all_are_fully_unrolled = False
            if not all_are_fully_unrolled:
                continue

            is_init_on_chip = False
            statements = self.extract_statements()
            curr_out = statements[statement].split("=")[0].split("[")[0].replace(" ", "")
            for statement2 in statements:
                out_, in_ = statement2.split("=")
                if curr_out in out_ and "0" in in_:
                    is_init_on_chip = True
                is_in_float = False
                try:
                    float(in_)
                    is_in_float = True
                except:
                    pass
                if curr_out in out_ and is_in_float:
                    is_init_on_chip = True

            if not is_init_on_chip:
                task, start, end = self.extract_task(f"task{statement}")

                arg_fct = []
                start_red = -1
                end_red = -1
                after_pip = False
                nb_bracket = 0
                tab = ""
                first_for = -1
                last_bracket = -1
                for k, line in enumerate(task):
                    if "void" in line:
                        arg_fct = line.split("(")[1].split(")")[0].split(", ")
                    if "for" in line:
                        tab += "    "
                        if first_for == -1:
                            first_for = k
                    if "#pragma HLS pipeline" in line:
                        after_pip = True
                    if after_pip:
                        if "for" in line:
                            name_it = line.split("int ")[-1].split(" = ")[0].replace("2", "")
                            id_loop = -1
                            for loop in loops:
                                if self.iterators[loop] == name_it:
                                    id_loop = loop
                            if self.is_red[id_loop]:
                                start_red = k
                                break
                task.insert(start_red, f"{tab}{self.data_type} red = 0;\n")
                output = ""
                already_seen = False
                for k, line in enumerate(task[start_red:]):
                    if "{" in line:
                        nb_bracket += 1
                        tab += "    "
                        already_seen = True
                    if "}" in line:
                        tab = tab[:-4]
                        nb_bracket -= 1
                        # last_bracket = k
                    if nb_bracket == 0 and already_seen:
                        end_red = k + start_red + 1
                        break
                    if "=" in line and "[" in line:
                        symbol = " ="
                        if "+=" in line:
                            symbol = "+="
                        elif "-=" in line:
                            symbol = "-="
                        elif "*=" in line:
                            symbol = "*="
                        elif "/=" in line:
                            symbol = "/="
                        output = line.split(symbol)[0].replace(" ", "")
                        input = line.split(symbol)[1]
                        input = input.replace(output, "")
                        task[k+start_red] = f"{tab}red += {input}"
                index_bracket = output.index("[")
                assignement = output[:index_bracket] + "_red" + output[index_bracket:]
                task.insert(end_red, f"{tab}{assignement} = red;\n")

                arg_output = ""
                for arg in arg_fct:
                    if curr_out in arg and f"{self.data_type}" in arg:
                        if f"{self.data_type}1" not in arg and f"{self.data_type}2" not in arg and f"{self.data_type}4" not in arg and f"{self.data_type}8" not in arg and f"{self.data_type}16" not in arg:
                            arg_output = arg
                            new_arg = arg.replace(curr_out, f"{curr_out}_red")

                            task.insert(first_for, f"{tab}{new_arg};\n")
                            break

                last_bracket = -1
                for k, line in enumerate(task):
                    if "}" in line:
                        last_bracket = k
                copy_array = ""
                tab = ""
                index_br = arg_output.index("[")
                size = arg_output[index_br+1:-1].split("][")
                size = list(map(int, size))
                for id_dim in range(len(size)):
                    copy_array += f"{tab}for (int i{id_dim} = 0; i{id_dim} < {size[id_dim]}; i{id_dim}++) {{\n"
                    tab += "    "
                copy_array += "#pragma HLS pipeline II=1\n"
                copy_array += f"{tab}    {curr_out}[i0"
                for id_dim in range(1, len(size)):
                    copy_array += f"][i{id_dim}"
                copy_array += f"] += {curr_out}_red[i0"
                for id_dim in range(1, len(size)):
                    copy_array += f"][i{id_dim}"
                copy_array += f"];\n"
                for id_dim in range(len(size)):
                    
                    copy_array += f"{tab}}}\n"
                    tab = tab[:-4]

                task.insert(last_bracket, f"    {copy_array}")

                self.lines = self.lines[:start] + task + self.lines[end+1:]
            else:
                task, start, end = self.extract_task(f"task{statement}")
                start_red = -1
                end_red = -1
                after_pip = False
                nb_bracket = 0
                tab = ""
                for k, line in enumerate(task):
                    if "for" in line:
                        tab += "    "
                    if "#pragma HLS pipeline" in line:
                        after_pip = True
                    if after_pip:
                        if "for" in line:
                            name_it = line.split("int ")[-1].split(" = ")[0].replace("2", "")
                            id_loop = -1
                            for loop in loops:
                                if self.iterators[loop] == name_it:
                                    id_loop = loop
                            if self.is_red[id_loop]:
                                start_red = k
                                break
                task.insert(start_red, f"{tab}{self.data_type} red = 0;\n")
                output = ""
                already_seen = False
                for k, line in enumerate(task[start_red:]):
                    if "{" in line:
                        nb_bracket += 1
                        tab += "    "
                        already_seen = True
                    if "}" in line:
                        tab = tab[:-4]
                        nb_bracket -= 1
                    if nb_bracket == 0 and already_seen:
                        end_red = k + start_red + 1
                        break
                    if "=" in line and "[" in line:
                        symbol = "="
                        if "+=" in line:
                            symbol = "+="
                        elif "-=" in line:
                            symbol = "-="
                        elif "*=" in line:
                            symbol = "*="
                        elif "/=" in line:
                            symbol = "/="
                        output = line.split(symbol)[0].replace(" ", "")
                        input = line.split(symbol)[1]
                        input = input.replace(output, "")
                        task[k+start_red] = f"{tab}red += {input}"
                task.insert(end_red, f"{tab}{output} = red;\n")


                self.lines = self.lines[:start] + task + self.lines[end+1:]
        
        f = open(self.output, "w")
        f.writelines(self.lines)
        f.close()

    def reorder(self):
        f = open(self.output, "r")
        self.lines = f.readlines()
        f.close()

        # save the original file 
        os.system(f"cp {self.output} {self.output}.original")

        # search all the function name
        functions = []
        arg = {}
        for line in self.lines:
            if "void" in line:
                functions.append(line.split(" ")[1].split("(")[0])
        for fct in functions:
            arg[fct] = self.get_arg_fct(fct)
        

        # for all function != kernel_nlp remove the argument of kernel_nlp in the function arg
        for fct in functions:
            if fct != "kernel_nlp":
                for i in range(len(arg[fct])):
                    if arg[fct][i] in arg["kernel_nlp"]:
                        arg[fct][i] = ""
        for fct in functions: # lol change that
            if fct != "kernel_nlp":
                while "" in arg[fct]:
                    arg[fct].remove("")
    
        # extract in order call of functions in kernel_nlp
        order = []
        inside = False
        for line in self.lines:
            if "void kernel_nlp" in line:
                inside = True
            
            if inside:
                if "#pragma" not in line:
                    if "void" not in line:
                        if f"{self.data_type}" not in line:
                            if "{" not in line and "}" not in line:
                                if "(" in line and ")" in line:
                                    if len(line) >= 4:
                                        name = line.split("(")[0].split(" ")[-1]
                                        order.append((name, line.replace("\n", "")))
        matrix_dep = [[0 for i in range(len(order))] for j in range(len(order))]
        for i in range(len(order)):
            for j in range(len(order)):
                matrix_dep[i][j] = self.are_independant(arg[order[i][0]], arg[order[j][0]])
        
        new_order = []

        # put load
        for i in range(len(order)):
            if "load" in order[i][0]:
                new_order.append(order[i][1])
        
        #put comp
        for i in range(len(order)):
            if "task" in order[i][0]:
                new_order.append(order[i][1])

        # put store
        for i in range(len(order)):
            if "store" in order[i][0]:
                new_order.append(order[i][1])

        id_ = 0
        inside = False
        for k, line in enumerate(self.lines):
            if "void kernel_nlp" in line:
                inside = True
            
            if inside:
                if "#pragma" not in line:
                    if "void" not in line:
                        if f"{self.data_type}" not in line:
                            if "{" not in line and "}" not in line:
                                if "(" in line and ")" in line:
                                    if len(line) >= 4:
                                        self.lines[k] = new_order[id_] + "\n"
                                        id_ += 1

        f = open(self.output, "w")
        f.writelines(self.lines)
        f.close()

    def get_arg_fct(self, name):
        for line in self.lines:
            if f"void {name}" in line:
                return line.split("(")[1].split(")")[0].split(", ")

    def are_independant(self, fct1, fct2):
        for arg1 in fct1:
            for arg2 in fct2:
                if arg1 == arg2:
                    return False
        return True


