# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import math
from itertools import combinations, product, permutations
import numpy as np
class computationBound:

    def __init__(self, data_type, ressource, solver, nlp_file_name, NO_TREE_REDUCTION, no_optimistic_reuse, timeout_nlp, analysis, schedule, UB, LB, statements, iterators, output, headers, arguments, name_function, pragmas, pragmas_top, optimize_burst):
        self.data_type = data_type
        self.ressource = ressource
        self.solver = solver
        self.TREE_REDUCTION = not NO_TREE_REDUCTION
        self.no_optimistic_reuse = no_optimistic_reuse
        self.timeout_nlp = timeout_nlp
        self.analysis = analysis
        self.schedule = schedule
        self.cyclic_buffer = False
        self.size_cyclic_buffer = 16
        self.nlp_file_name = nlp_file_name
        self.UB = UB
        self.LB = LB
        self.statements = statements
        self.iterators = iterators
        self.output = output
        self.headers = headers
        self.arguments = arguments
        self.name_function = name_function
        self.pragmas = pragmas
        self.pragmas_top = pragmas_top
        self.optimize_burst = optimize_burst
        self.TC = {}
        self.compute_TC()

        self.array_to_focus = self.analysis.array_to_focus

        self.loop_body_independant = {}
        self.compute_loop_body_independant()

        self.info_loops = {}
        self.compute_info_loops()

        self.create_nlp()

        # self.compute()

    def compute_TC(self):
        id_loop = 0
        for i in range(len(self.schedule)):
            TC = self.analysis.dic[i]["TC"]
            for j in range(1, len(self.schedule[i]), 2):
                id_loop = self.schedule[i][j]
                is_cte_lb = True
                try:
                    int(self.analysis.dic[i]["LB_"][self.iterators[id_loop]])
                except:
                    is_cte_lb = False
                if is_cte_lb:
                    self.TC[id_loop] = TC[self.iterators[id_loop]]
                else:
                    self.TC[id_loop] = TC[self.iterators[id_loop]] + int(self.analysis.dic[i]["LB"][self.iterators[id_loop]])




    def compute_other_loops(self, id_):
        others_loops = []
        for id_2 in range(len(self.schedule)):
            if id_2 != id_:
                loops_2 = self.schedule[id_2][1::2]
                others_loops += loops_2
        others_loops = list(set(others_loops))
        return others_loops
    
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
    
    def extract_array(self, statement):
        out = statement.split("=")[0]
        out = out.strip().split("[")[0]
        inp = statement.split("=")[1]
        inp = self.multi_split(inp.strip().replace(";", "").replace(" ", ""), ["+", "-", "*", "/"], True)
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

    def compute_loop_body_independant(self):
        for id_ in range(len(self.schedule)):
            is_independant = True
            loops = self.schedule[id_][1::2]
            others_loops = self.compute_other_loops(id_)
            for loop in loops:
                if loop in others_loops:
                    is_independant = False
                    break
            self.loop_body_independant[id_] = is_independant


    def extract_iterators(self, out):
        iterators = []
        if "[" in out:
            it = out[out.index("[")+1:]
            iterators = it.replace("][", "@").replace("]", "").split("@")

        return iterators

    def compute_info_loops(self):
        self.red_loop = {}
        for id_ in range(len(self.schedule)):
            loops = self.schedule[id_][1::2]
            for loop in loops:
                self.red_loop[loop] = False
        for id_ in range(len(self.schedule)):
            loops = self.schedule[id_][1::2]
            for loop in loops:
                it = self.extract_iterators(self.analysis.dic[id_]["write"][0])
                if self.iterators[loop] not in it:
                    self.red_loop[loop] = True

        for id_ in range(len(self.schedule)):
            loops = self.schedule[id_][1::2]
            info_loops = {}
            statement = self.statements[id_]
            out, inp = self.extract_array(statement)
            op = self.extract_operation(statement)

            info_loops["write"] = self.analysis.dic[id_]["write"]
            it = self.extract_iterators(self.analysis.dic[id_]["write"][0])

            reduction_loop = {}
            for loop in loops:
                reduction_loop[loop] = False
                if self.iterators[loop] not in it:
                    reduction_loop[loop] = True
            info_loops["reduction_loop"] = reduction_loop
            info_loops["read"] = self.analysis.dic[id_]["read"]
            info_loops["operation"] = self.analysis.operations[id_]
            info_loops["arrays_size"] = self.analysis.arrays_size
            self.info_loops[id_] = info_loops


    def create_nlp(self):
        var = []
        constraints = []

        obj = []
        obj2 = []
        param = [f"DSP_avail = {self.ressource.DSP};", f"ON_CHIP_MEM_SIZE = {self.ressource.ON_CHIP_MEM_SIZE};",  f"CONSTRAINT_ARRAY_PARTITIONING_VALUE = {self.ressource.partitioning_max};", "BRAM = 4320;", f"size_data_type = {self.ressource.sizeof};"] #, "optimist_reuse_dsp=1;"]
        if self.no_optimistic_reuse:
            param.append("optimist_reuse_dsp=0;")
        else:
            param.append("optimist_reuse_dsp=1;")
        for key in self.TC:
            param.append(f"TC{key} = {self.TC[key]};")
            for k in range(3):
                var.append(f"TC{key}_{k} integer >= 1 <=TC{key};")

            constraints.append(f"TC{key} = TC{key}_0 * TC{key}_1 * TC{key}_2;")
        loop_UF_per_stat = {}
        if self.TREE_REDUCTION:
            param += ["TREE_REDUCTION=1;"]
        else:
            param += ["TREE_REDUCTION=0;"]

        dico_perm = {}
        for k in range(len(self.schedule)):
            loops = self.schedule[k][1::2]
            all_perm = list(permutations(loops))
            tmp = []
            for id_perm, perm in enumerate(all_perm):
                dico_perm[f"perm{id_perm}_S{k}"] = perm
                var.append(f"perm{id_perm}_S{k} binary; # {perm}")
                tmp.append(f"perm{id_perm}_S{k}")
            constraints.append(f"{' + '.join(tmp)} = 1;")
        
        
        for key in self.TC:
            loop_UF_per_stat[key] = []

            if not self.red_loop[key]:
                var.append(f"loop{key}_UF integer >= 1 <=TC{key};")
                constraints.append(f"loop{key}_UF = 1;")
        for k in range(len(self.schedule)):
            loop_UF_per_stat[k] = []
            loops = self.schedule[k][1::2]
            for loop in loops:
                if not self.red_loop[loop]:
                    loop_UF_per_stat[k].append(f"loop{loop}_UF")
        
        for k in range(len(self.schedule)):
            op = self.analysis.operations[k]
            loops = self.schedule[k][1::2]
            is_red = False
            for loop in loops:
                if self.red_loop[loop]:
                    is_red = True
                    break

            #FIXME suppose the red is + for now
            seq = 0
            par = 0

            if is_red:
                seq = 1 * self.ressource.IL["+"]
            for o in op:
                if o == "+":
                    nb = op[o]
                    if is_red:
                        nb -= 1
                    par += nb * self.ressource.IL["+"]
                elif o == "-":
                    nb = op[o]
                    par += nb * self.ressource.IL["-"]
                elif o == "*":
                    nb = op[o]
                    par += nb * self.ressource.IL["*"]
                elif o == "/":
                    nb = op[o]
                    par += nb * self.ressource.IL["/"]

            if par == 0:
                par = 1 # assignement
            param.append(f"IL_par_S{k} = {par};")
            param.append(f"IL_seq_S{k} = {seq};")
        DSP_used = {}

        DSP_pessimiste = []
        for k in range(len(self.schedule)):
            dsp_used = 0
            DSP_used[k] = 0
            op = self.analysis.operations[k]
            for o in op:
                if o == "+":
                    nb = op[o]
                    dsp_used += nb * self.ressource.DSP_per_operation["+"]
                elif o == "-":
                    nb = op[o]
                    dsp_used += nb * self.ressource.DSP_per_operation["-"]
                elif o == "*":
                    nb = op[o]
                    dsp_used += nb * self.ressource.DSP_per_operation["*"]
                elif o == "/":
                    nb = op[o]
                    dsp_used += nb * self.ressource.DSP_per_operation["/"]
            DSP_used[k] = dsp_used
            param.append(f"DSP_S{k} = {dsp_used};")
        if self.solver == "baron":
            header = ["option solver baron;", f"option baron_options 'maxtime={self.timeout_nlp} trace=nlp.trace sumfile=nlp.sum';"]
        else:
            header = ["option solver gurobi;", f"option gurobi_options 'lim:time={self.timeout_nlp} tech:logfile=gurobi.log qp:nonconvex=2 mip:gap=0.0000000001';"]
        all_DSP = []
        for k in range(len(self.schedule)):
            if DSP_used[k] > 0:
                prod = []
                loops = self.schedule[k][1::2]
                for loop in loops:
                    prod.append(f"TC{loop}_2")
                prod = " * ".join(prod)
                if len(loop_UF_per_stat[k]) > 0:
                    prod += " * " + " * ".join(loop_UF_per_stat[k])
                if self.cyclic_buffer:
                    prod += f" + {self.size_cyclic_buffer} * {self.ressource.DSP_per_operation['+']}"
                constraints.append(f"DSP_S{k} * {prod} <= DSP_avail * II_S{k};")

                if self.ressource.MAX_BUFFER_SIZE > 0:
                    constraints.append(f"{prod} <= {self.ressource.MAX_BUFFER_SIZE};")

                DSP_pessimiste.append(f"(DSP_S{k} * {prod}) / II_S{k}")
                all_DSP.append(f"(DSP_S{k} * {prod}) / II_S{k}")
        constraints.append(f"(1-optimist_reuse_dsp) * {' + '.join(DSP_pessimiste)} <= DSP_avail;")
        for k in range(len(self.schedule)):
            obj += [f"Lat_comp_S{k}"]
            obj2 += [f"Lat_comp_S{k}_no_tree"]
            var += [f"Lat_comp_S{k} >= 0;"]
            var += [f"Lat_comp_S{k}_no_tree >= 0;"]
        

        for k in range(len(self.schedule)):
            var += [f"II_S{k} integer >= 1;"]

        for k in range(len(self.schedule)):
            CG = []
            IL = []
            IL2 = []
            FG = []
            PIP = []

            loops = self.schedule[k][1::2]
            for loop in loops:
                if self.red_loop[loop]:
                    CG.append(f"TC{loop}_0")
                else:
                    CG.append(f"TC{loop}_0 / loop{loop}_UF")
                    constraints.append(f"loop{loop}_UF <= TC{loop}_0;")
                
                PIP.append(f"TC{loop}_1")
            IL.append(f"IL_par_S{k}")
            IL2.append(f"IL_par_S{k}")

            is_red = False
            red_loops = []
            for loop in loops:
                if self.red_loop[loop]:
                    red_loops.append(f"TC{loop}_2")
                    is_red = True
            if is_red:
                if self.cyclic_buffer:
                    IL.append(f"IL_seq_S{k} + {math.ceil(math.log(self.size_cyclic_buffer, 2))} * {self.ressource.DSP_per_operation['+']}")
                    IL2.append(f"IL_seq_S{k} + {math.ceil(math.log(self.size_cyclic_buffer, 2))} * {self.ressource.DSP_per_operation['+']}")
                else:
                    pp = " * ".join(red_loops)
                    IL.append(f"IL_seq_S{k} * log({pp})/log(2)")
                    IL2.append(f"IL_seq_S{k} * {pp}")


            CG = " * ".join(CG)
            IL = " + ".join(IL)
            IL2 = " + ".join(IL2)
            FG = ""
            PIP = " * ".join(PIP)
            
            constraints.append(f"Lat_comp_S{k} = TREE_REDUCTION * ({CG} * ({IL} + II_S{k} * ({PIP} - 1))) + (1-TREE_REDUCTION) * ({CG} * ({IL2} + II_S{k} * ({PIP} - 1))) ")

        is_loop_permutable = {}
        for k in range(len(self.schedule)):
            is_loop_permutable[k] = {}
            for loop in self.schedule[k][1::2]:
                is_loop_permutable[k][loop] = True
        
        for k in range(len(self.schedule)):
            alone = True
            dep = []
            for k2 in range(len(self.schedule)):
                if k2 != k:
                    if len(self.schedule[k]) > 1 and self.schedule[k][1] in self.schedule[k2][1::2]:
                        alone = False
                        dep.append(k2)

            permutable = []
            if not alone:
                for j in range(1, len(self.schedule[k]), 2):
                    curr_loop = self.schedule[k][j]
                    same_one = True
                    for other_sched in dep:
                        if len(self.schedule[other_sched]) > j:
                            if self.schedule[other_sched][j] != curr_loop:
                                same_one = False
                                break
                        else:
                            same_one = False
                            break
                    if same_one:
                        permutable.append(curr_loop)

                all_loops = self.schedule[k][1::2]
                for d in dep:
                    all_loops += self.schedule[d][1::2]
                all_loops = list(set(all_loops)) 
                for loop in all_loops:
                    if loop not in permutable:
                        is_loop_permutable[k][loop] = False



        for k in range(len(self.schedule)):
            is_red = False
            red_loops = []
            loops = self.schedule[k][1::2]
            for loop in loops:
                if self.red_loop[loop]:
                    red_loops.append(f"TC{loop}_1")
                    is_red = True
            if not is_red:
                pos = []
                constraints.append(f"II_S{k} = 1;")
                for loop in loops:
                    if f"is_loop{loop}_pip binary;" not in var:
                        var.append(f"is_loop{loop}_pip binary;")
                    if f"is_loop{loop}_pip" not in pos:
                        pos.append(f"is_loop{loop}_pip")

                    

                    ol = []
                    for other_loops in loops:
                        if other_loops != loop:
                            if is_loop_permutable[k][other_loops]:
                                ol.append(f"TC{other_loops}_1")

                    if len(ol)>0:
                        if is_loop_permutable[k][loop]:
                            if f"is_loop{loop}_pip * {' * '.join(ol)} = is_loop{loop}_pip * 1;" not in constraints:
                                constraints.append(f"is_loop{loop}_pip * {' * '.join(ol)} = is_loop{loop}_pip * 1;")
                    constraints.append(f"is_loop{loop}_pip * TC{loop}_1 >= is_loop{loop}_pip * 2;")
                pos = " + ".join(pos)
                loop_not_maximum_depth_for_the_loop_body = False

                curr_sched = k
                for h in range(len(self.schedule)):
                    if h != k:
                        if len(self.schedule[curr_sched]) > 1 and self.schedule[curr_sched][1] in self.schedule[h][1::2] and len(self.schedule[curr_sched][1::2]) < len(self.schedule[h][1::2]): # the outermost loop is in an other sched
                            loop_not_maximum_depth_for_the_loop_body = True
                if not loop_not_maximum_depth_for_the_loop_body:
                    constraints.append(f"{pos} = 1;")
                else:
                    constraints.append(f"{pos} <= 1;")
            else:
                pos = []
                for loop in loops:
                    if f"is_loop{loop}_pip binary;" not in var:
                        var.append(f"is_loop{loop}_pip binary;")
                    if f"is_loop{loop}_pip" not in pos:
                        pos.append(f"is_loop{loop}_pip")
                    # here the other loops have to be to 1 to have loop pipeline
                    ol = []
                    for other_loops in loops:
                        if other_loops != loop:
                            if is_loop_permutable[k][other_loops]:
                                ol.append(f"TC{other_loops}_1")

                    if is_loop_permutable[k][loop]:
                        if f"is_loop{loop}_pip * {' * '.join(ol)} = is_loop{loop}_pip * 1;" not in constraints:
                            constraints.append(f"is_loop{loop}_pip * {' * '.join(ol)} = is_loop{loop}_pip * 1;")
                    constraints.append(f"is_loop{loop}_pip * TC{loop}_1 >= is_loop{loop}_pip * 2;")
                pos = " + ".join(pos)
                #FIXME depend of the operation
                cons_II = ""
                all_reduction_loop = []
                for i, loop in enumerate(loops):
                    if self.red_loop[loop]:
                        all_reduction_loop.append(f"TC{loop}_2")
                if len(all_reduction_loop) > 0:
                    all_reduction_loop = " * ".join(all_reduction_loop)
                else:
                    all_reduction_loop = "1"
                for i, loop in enumerate(loops):
                    if self.red_loop[loop]:
                        cons_II += f"{self.ressource.IL['+']-1} * is_loop{loop}_pip * TREE_REDUCTION"

                        cons_II += f" + {self.ressource.IL['+']} * {all_reduction_loop} * is_loop{loop}_pip * (1 - TREE_REDUCTION)"
                    else:
                        cons_II += f"1 * is_loop{loop}_pip"
                    if i < len(loops) - 1:
                        cons_II += " + "
                #if not fully distributed
                loop_not_maximum_depth_for_the_loop_body = False
                curr_sched = k
                for h in range(len(self.schedule)):
                    if h != k:
                        if len(self.schedule[curr_sched]) > 1 and self.schedule[curr_sched][1] in self.schedule[h][1::2] and len(self.schedule[curr_sched][1::2]) < len(self.schedule[h][1::2]): # the outermost loop is in an other sched
                            loop_not_maximum_depth_for_the_loop_body = True
                if not loop_not_maximum_depth_for_the_loop_body:
                    constraints.append(f"{pos} = 1;")
                else:
                    constraints.append(f"{pos} <= 1;")
                constraints.append(f"II_S{k} = {cons_II};")

        
                
        # Max Array part and # Array part modulo
        arrays = []
        dim_array = {}
        for key in list(self.analysis.dic.keys()):
            read = self.analysis.dic[key]["read"]
            write = self.analysis.dic[key]["write"]
            for r in read:
                if "[0]" not in r:
                    nb = r.count("[")
                    arrays.append(r.split("[")[0])
                    dim_array[r.split("[")[0]] = nb 
            for w in write:
                if "[0]" not in w:
                    nb = w.count("[")
                    arrays.append(w.split("[")[0])
                    dim_array[w.split("[")[0]] = nb 
        arrays = list(set(arrays))

        self.info_arrays = {}
        for array in arrays:
            self.info_arrays[array] = {}
            for dim in range(dim_array[array]):
                self.info_arrays[array][dim] = []
        for array in arrays:
            for key in list(self.analysis.dic.keys()):
                read = self.analysis.dic[key]["read"]
                write = self.analysis.dic[key]["write"]
                randw = read + write
                for r in randw:
                    if array in r:
                        its = self.extract_iterators(r)


                        loops = self.schedule[key][1::2]
                        for id_dim, it in enumerate(its):
                            for loop in loops:

                                if self.iterators[loop] in it:
                                    cc = ""
                                    if not self.red_loop[loop]:
                                        cc = f"loop{loop}_UF * TC{loop}_2"
                                    else:
                                        cc = f"TC{loop}_2"
                                    
                                    if cc not in self.info_arrays[array][id_dim]:
                                        self.info_arrays[array][id_dim].append(cc)



        # FIXME for partial array we need to multiply by loop which does not iterate the array but above the array

        array_information = {}
        for array in arrays:
            array_information[array] = {"schedule":[], "write": []}
            for sched in range(len(self.schedule)):
                read = self.analysis.dic[sched]["read"]
                write = self.analysis.dic[sched]["write"]
                for r in read:
                    if array == r.split("[")[0]:
                        array_information[array]["schedule"].append(sched)
                for w in write:
                    if array == w.split("[")[0]:
                        if sched not in array_information[array]["schedule"]:
                            array_information[array]["schedule"].append(sched)
                        array_information[array]["write"].append(sched)


            

        id_cte = 0
        # FIXME here we dont need constraint if we transfer the array many times
        id_2 = 0
        for array in arrays:
            l = []
            constraint_array_part = []
            constraint_array_part_per_schedule = {}
            for k in range(len(self.schedule)):
                constraint_array_part_per_schedule[k] = []
            for dim in range(dim_array[array]):
                var.append(f"AP_{array}_{dim} integer >= 1;")
                if dim == dim_array[array] - 1:
                    constraints.append(f"AP_{array}_{dim} = burst_size_{array} * constant{id_2};")
                    var.append(f"constant{id_2} integer >= 1;")
                    id_2 += 1
                
                constraint_array_part.append(f"AP_{array}_{dim}")
                l.append(self.info_arrays[array][dim])
                # FIXME if many iterators then maybe not add
                for elmt in [" + ".join(self.info_arrays[array][dim])]:

                    constraints.append(f"#{elmt} <= AP_{array}_{dim};")
                    cur_sched = -1
                    index = elmt.index("TC")
                    cur_loop = elmt[index:].split("_")[0].replace("TC", "")
                    cur_sced = -1

                    for kl, sched_ in enumerate(self.schedule):
                        if int(cur_loop) in sched_[1::2]:
                            cur_sched = kl
                            break

                    for elmt1 in elmt.split("+"):
                        if f"AP_{array}_{dim} = {elmt1} * cte_{id_cte};" not in constraints:
                            constraints.append(f"AP_{array}_{dim} = {elmt1} * cte_{id_cte};")
                        if f"{elmt1} <= AP_{array}_{dim};" not in constraints:
                            constraints.append(f"{elmt1} <= AP_{array}_{dim};")
                        var.append(f"cte_{id_cte} integer >= 1;")
                        id_cte += 1

                    var.append(f"cte_{id_cte} integer >= 1;")
                    if f"AP_{array}_{dim} <= {self.analysis.arrays_size[array][dim]};" not in constraints:
                        constraints.append(f"AP_{array}_{dim} <= {self.analysis.arrays_size[array][dim]};")
                    str_ = f"#{self.analysis.arrays_size[array][dim]} = AP_{array}_{dim} * cte_{id_cte};"
                    if str_ not in constraints:
                        constraints.append(str_)
                    id_cte += 1
                    

            cc = " * ".join(constraint_array_part)
            constraints.append(f"{cc} <= CONSTRAINT_ARRAY_PARTITIONING_VALUE;")

        # Communication latency
        # for array in arrays:
        obj += [f"Lat_comm"]
        obj2 += [f"Lat_comm"]
        var += [f"Lat_comm >= 0;"]

        first_time_array_appear = {}
        is_write = {}
        for array in arrays:
            first_time_array_appear[array] = -1
            is_write[array] = False
            for key in list(self.analysis.dic.keys()):
                read = self.analysis.dic[key]["read"]
                write = self.analysis.dic[key]["write"]
                randw = read + write
                for r in randw:
                    if array in r:
                        if r in write:
                            is_write[array] = True
                        if first_time_array_appear[array] == -1:
                            first_time_array_appear[array] = key
                        break


        for array in arrays:
            var.append(f"transfer_{array}_total binary;")
        footprint_array = {}
        burst_size = {}
        list_foot = []
        already_seen = []
        initialization = {}
        for array in arrays:
            initialization[array] = False
            for key in list(self.analysis.dic.keys()):
                write = self.analysis.dic[key]["write"][0]
                if array == write.split("[")[0]:
                    read = self.analysis.dic[key]["read"]
                    if len(read) == 0:
                        initialization[array] = True
                        break
        constraint_per_array_per_schedule = {}
        constraint_per_array_per_schedule_lat = {}
        
        id_cte_burst = 0
        for array in arrays:

            if array in self.analysis.chip["on_chip"]:
                continue
            constraint_per_array_per_schedule[array] = {}
            constraint_per_array_per_schedule_lat[array] = {}
            
            for key in list(self.analysis.dic.keys()):
                current_con = []
                constraint_per_array_per_schedule[array][key] = []
                constraint_per_array_per_schedule_lat[array][key] = []
                write = self.analysis.dic[key]["write"]
                read = self.analysis.dic[key]["read"]
                wr = write + read
                all_access = []
                last_iterators = []
                for w in wr:
                    
                    if array == w.split("[")[0]:

                        all_access += self.extract_iterators(w)
                        last_iterators += [self.extract_iterators(w)[-1]]

                all_access = list(set(all_access))
                
                for it in all_access:
                    for id_perm in range(len(list(dico_perm.keys()))):
                        perm_id = list(dico_perm.keys())[id_perm]
                        if f"S{key}" not in perm_id:
                            continue
                        for l1, loop in enumerate(dico_perm[perm_id]):
                            if self.iterators[loop] == it:
                                if array in self.analysis.chip["on_chip"]:
                                    continue
                                if f"transfer_{array}_S{key}_under_loop{loop} binary;" not in var:
                                    var.append(f"transfer_{array}_S{key}_under_loop{loop} binary;")
                                    current_con.append(f"transfer_{array}_S{key}_under_loop{loop}")

                                # need to said it is full transferred if TC_{loop} = 1
                                constraints.append(f"transfer_{array}_S{key}_under_loop{loop} * TC{loop}_0 >= transfer_{array}_S{key}_under_loop{loop} * 2;")

                                cur_array_size = self.analysis.arrays_size[array].copy()

                            
                                
                                curr_size = ""
                                curr_lat = ""
                                last_dim = int(cur_array_size[-1])
                                id_loop_terate_last_dim = -1
                                if len(list(set(last_iterators))) == 1:
                                    for l_bis in range(len(self.schedule[key][1::2])):
                                        if self.iterators[self.schedule[key][1::2][l_bis]] == last_iterators[0]:
                                            id_loop_terate_last_dim = l_bis
                                            break
                                else:
                                    pass
                                    #FIXME todo
                                for l2, loop2 in enumerate(dico_perm[perm_id]):
                                    if l2 <= l1:
                                        if self.iterators[loop2] in all_access:
                                            curr_size += f"TC{loop2}_0 * "
                                curr_size += f"1"
                                if f"burst_{array}_S{key}_under_loop{loop} integer >= 1 <=burst_size_tot_{array};" not in var:
                                    var.append(f"burst_{array}_S{key}_under_loop{loop} integer >= 1 <=burst_size_tot_{array};")
                                    constraints.append(f"burst_{array}_S{key}_under_loop{loop} = 1;")


                                

                                str__ = f"{perm_id} * transfer_{array}_S{key}_under_loop{loop} * footprint_{array}_S{key} / {curr_size}"
                                if str__ not in constraint_per_array_per_schedule[array][key]:
                                    constraint_per_array_per_schedule[array][key].append(str__)
                                time_transfer = 1

                                is_write_ = loop in array_information[array]["write"]
                                is_last_schedule = key == array_information[array]["schedule"][-1]
                                is_first_schedule = key == array_information[array]["schedule"][0]
                                if  is_first_schedule and initialization[array]:
                                    time_transfer = 1
                                elif is_last_schedule and not is_write_:
                                    time_transfer = 1
                                elif is_last_schedule and is_write_:
                                    time_transfer = 2
                                else:
                                    time_transfer = 2
                                str__ = f"transfer_{array}_S{key}_under_loop{loop} * footprint_{array}_S{key}  / burst_{array}_S{key}_under_loop{loop}"
                                if str__ not in constraint_per_array_per_schedule_lat[array][key]:
                                    constraint_per_array_per_schedule_lat[array][key].append(str__)
                if len(current_con) >= 1:
                    constraints.append(f"{' + '.join(current_con)} + transfer_{array}_total = 1;")
        
        constraint_per_schedule = {}
        array_already_seen = []
        for k in range(len(self.schedule)):
            current_con = []
            constraint_per_schedule[k] = []
            arry_in_sched = []
            write = self.analysis.dic[k]["write"]
            read = self.analysis.dic[k]["read"]
            wr = write + read
            for w in wr:
                for array in arrays:
                    if array == w.split("[")[0]:
                        arry_in_sched.append(array)
                        array_already_seen.append(array)
            arry_in_sched = list(set(arry_in_sched))
            # TODO for all perm
            for array in array_already_seen:
                if array in self.analysis.chip["off_chip"]:

                    if f"footprint_tot_{array}" not in current_con:
                        if array_information[array]["schedule"][-1] >= k:
                            if f"transfer_{array}_total * footprint_tot_{array}" not in current_con:
                                current_con += [f"transfer_{array}_total * footprint_tot_{array}"]
                            # current_con += [f"footprint_tot_{array}"]
            for array in arry_in_sched:
                if array in self.analysis.chip["on_chip"]:
                    current_con += [str(np.prod(self.analysis.arrays_size[array]))]
                else:
                    current_con += constraint_per_array_per_schedule[array][k]
            
            if len(current_con) >= 1:
                constraints.append(f"{' + '.join(current_con)} <= ON_CHIP_MEM_SIZE;")

        for key in list(self.analysis.dic.keys()):
            current_arrays = []
            read = self.analysis.dic[key]["read"]
            write = self.analysis.dic[key]["write"]
            randw = read + write
            for r in randw:
                for array in arrays:
                    if array == r.split("[")[0]:
                        if array not in current_arrays:
                            current_arrays.append(array)
            for array in current_arrays:
                param.append(f"footprint_{array}_S{key} = {np.prod(self.analysis.arrays_size[array])};")

        sum_footprint = 0
        for array in arrays:
            footprint_array[array] = 0
            burst_size[array] = 1
            if array in self.analysis.chip["on_chip"]:
                continue
            if array not in already_seen:
                for key in list(self.analysis.dic.keys()):
                    read = self.analysis.dic[key]["read"]
                    write = self.analysis.dic[key]["write"]
                    randw = read + write
                    for r in randw:
                        if array not in already_seen:
                            if array in r:

                                # only last dimension
                                footprint_array[array] = np.prod(self.analysis.arrays_size[array])
                                if self.data_type == "float":
                                    if self.analysis.arrays_size[array][-1] % 16 == 0:
                                        burst_size[array] =  16
                                    elif self.analysis.arrays_size[array][-1] % 8 == 0:
                                        burst_size[array] =  8
                                    elif self.analysis.arrays_size[array][-1] % 4 == 0:
                                        burst_size[array] =  4
                                    elif self.analysis.arrays_size[array][-1] % 2 == 0:
                                        burst_size[array] =  2
                                    else:
                                        burst_size[array] =  1
                                else:
                                    if self.analysis.arrays_size[array][-1] % 8 == 0:
                                        burst_size[array] =  8
                                    elif self.analysis.arrays_size[array][-1] % 4 == 0:
                                        burst_size[array] =  4
                                    elif self.analysis.arrays_size[array][-1] % 2 == 0:
                                        burst_size[array] =  2
                                    else:
                                        burst_size[array] =  1

                                param.append(f"footprint_tot_{array} = {footprint_array[array]};")
                                sum_footprint += footprint_array[array]*32
                                param.append(f"burst_size_tot_{array} = {burst_size[array]};")
                                var.append(f"burst_size_{array} integer >= 1 <={burst_size[array]};")
                                var.append(f"cte_burst_size_{array} integer >= 1;")
                                if self.data_type == "float":
                                    for k in [16, 8, 4, 2, 1]:
                                        var.append(f"is_burst_size_{array}_{k} binary;")
                                else:
                                    for k in [8, 4, 2, 1]:
                                        var.append(f"is_burst_size_{array}_{k} binary;")

                                str_ = ""
                                str_2 = ""
                                if self.data_type == "float":
                                    for k in [16, 8, 4, 2, 1]:
                                        str_ += f"is_burst_size_{array}_{k}"
                                        str_2 += f"is_burst_size_{array}_{k} * {k}"
                                        if k != 1:
                                            str_ += " + "
                                            str_2 += " + "
                                else:
                                    for k in [8, 4, 2, 1]:
                                        str_ += f"is_burst_size_{array}_{k}"
                                        str_2 += f"is_burst_size_{array}_{k} * {k}"
                                        if k != 1:
                                            str_ += " + "
                                            str_2 += " + "
                                dim = len(self.analysis.arrays_size[array])
                                constraints.append(f"{str_} = 1;")
                                constraints.append(f"burst_size_{array} = {str_2};")
                                constraints.append(f"AP_{array}_{dim-1} >= {str_2};")
                                if self.data_type == "float":
                                    for k in [16, 8, 4, 2, 1]:
                                        if k > burst_size[array]:
                                            constraints.append(f"is_burst_size_{array}_{k} = 0;")
                                else:
                                    for k in [8, 4, 2, 1]:
                                        if k > burst_size[array]:
                                            constraints.append(f"is_burst_size_{array}_{k} = 0;")

                                
                                str_ = ""
                                str_ += f"AP_{array}_{dim-1} = ("
                                if self.data_type == "float":
                                    for k in [16, 8, 4, 2, 1]:
                                        str_ += f"is_burst_size_{array}_{k} * {k}"
                                        if k != 1:
                                            str_ += " + "
                                else:
                                    for k in [8, 4, 2, 1]:
                                        str_ += f"is_burst_size_{array}_{k} * {k}"
                                        if k != 1:
                                            str_ += " + "
                                str_ += f") * cte_burst_size_{array};"
                                constraints.append(str_)
                                curr_cons_lat = []
                                curr_cons = []
                                for sched in range(len(self.schedule)):
                                    if sched in constraint_per_array_per_schedule[array]:
                                        for c in constraint_per_array_per_schedule[array][sched]:
                                            if c not in curr_cons:
                                                curr_cons.append(c)
                                    if sched in constraint_per_array_per_schedule_lat[array]:
                                        for c in constraint_per_array_per_schedule_lat[array][sched]:
                                            if c not in curr_cons_lat:
                                                curr_cons_lat.append(c)

                                already_seen.append(array)
                                break
        const_comm = []
        on_chip = math.ceil(sum_footprint/16000/1024) * 1024 * 16000 // 32

        for k in range(len(self.schedule)):
            con_read = []
            con_read2 = []
            con_write = []
            con_write2 = []
            var_r = f"Lat_comm_read_S{k}"
            var_w = f"Lat_comm_write_S{k}"

            var.append(f"{var_r};")
            var.append(f"{var_w};")
            const_comm.append(var_r)
            const_comm.append(var_w)

            larray = []
            read = self.analysis.dic[k]["read"]
            write = self.analysis.dic[k]["write"]
            randw = read + write
            ORIGINAL_CALL = ""
            array_write = write[0].split("[")[0]
            for r in randw:
                for array in arrays:
                    if array == r.split("[")[0]:
                        ORIGINAL_CALL = r
                        if array in self.analysis.chip["off_chip"]:
                            larray.append(array)
            larray = list(set(larray))

            first_time_see = []
            for arr in larray:
                if first_time_array_appear[arr] == k:
                    first_time_see.append(f"transfer_{arr}_total * footprint_tot_{arr}/burst_size_{arr}")
            if len(first_time_see) > 0:
                con_read.append(self.write_list_of_max(first_time_see))
                con_read2.append(f"max(" + ", ".join(first_time_see) + ")")

            last_time_see = []
            for arr in larray:
                if array_information[arr]["schedule"][-1] == k:
                    if len(array_information[arr]["write"]) > 0:
                        last_time_see.append(f"transfer_{arr}_total * footprint_tot_{arr}/burst_size_{arr}")

            if len(last_time_see) > 0:
                con_write.append(self.write_list_of_max(last_time_see))
                con_write2.append(" + ".join(last_time_see))



            for id_perm in range(len(list(dico_perm.keys()))):
                perm_id = list(dico_perm.keys())[id_perm]
                if f"S{k}" not in perm_id:
                    continue
                for loop in dico_perm[perm_id]:
                    read_level = []
                    write_level = []
                    write_array = self.analysis.dic[k]["write"][0].split("[")[0]
                    
                    
                    for array in arrays:

                        ORIGINAL_CALL = ""
                        read = self.analysis.dic[k]["read"]
                        write = self.analysis.dic[k]["write"]
                        randw = read + write
                        for r in randw:
                            if array == r.split("[")[0]:
                                ORIGINAL_CALL = r
                                break
                        tcc = []
                        tcc_iterated = []
                        for schedd in dico_perm[perm_id]:
                            iterate_array = False
                            it_loop = self.iterators[schedd]
                            it_array = self.extract_iterators(ORIGINAL_CALL)
                            for it__ in it_array:
                                if it_loop  in it__:
                                    iterate_array = True
                            if not iterate_array:

                                tcc += [f"TC{schedd}_0"]
                            else:
                                tcc_iterated += [f"TC{schedd}_0"]
                            if schedd == loop:
                                break
                        if len(tcc) == 0:
                            tcc = "1"
                        else:
                            tcc = " * ".join(tcc)
                        if len(tcc_iterated) == 0:
                            tcc_iterated = "1"
                        else:
                            tcc_iterated = " * ".join(tcc_iterated)

                        if f"transfer_{array}_S{k}_under_loop{loop} binary;" in var:
                            read_level.append(f"{perm_id} * transfer_{array}_S{k}_under_loop{loop} * {tcc} * {tcc_iterated} * footprint_{array}_S{k} / {tcc_iterated} / burst_{array}_S{k}_under_loop{loop}")
                            if array_information[array]["schedule"][-1] < k or array == write_array:
                                write_level.append(f"{perm_id} * transfer_{array}_S{k}_under_loop{loop} * {tcc} * footprint_{array}_S{k}  / burst_{array}_S{k}_under_loop{loop}")

                    if len(read_level) > 0:
                        con_read.append(self.write_list_of_max(read_level))
                        con_read2.append(" + ".join(read_level))
                    if len(write_level) > 0:
                        con_write.append(self.write_list_of_max(write_level))
                        con_write2.append(" + ".join(write_level))

            
            
            if len(con_read) > 0:
                constraints.append(f"#{var_r} = {' + '.join(con_read)};")
                constraints.append(f"{var_r} = {' + '.join(con_read2)};")
            else:
                constraints.append(f"{var_r} = 0;")
            if len(con_write) > 0:
                constraints.append(f"#{var_w} = {' + '.join(con_write)};")
                constraints.append(f"{var_w} = {' + '.join(con_write2)};")
            else:
                constraints.append(f"{var_w} = 0;")


            


        constraints.append(f"Lat_comm = {' + '.join(const_comm)};")


        id_ceil = 0
        BRAM_CONSTRAINTS = []
        for k in range(len(self.schedule)):
            lstr_ = []
            
            
            for array in arrays:
                if array in self.analysis.chip["on_chip"]:
                    continue
                if k <= max(array_information[array]["schedule"]) and k >= min(array_information[array]["schedule"]):
                    str_ = ""
                    str_ceil = ""
                    dim = len(self.analysis.arrays_size[arr])


                    str_ceil += f"transfer_{array}_total * footprint_tot_{array} / ("
                    for dd in range(dim):
                        str_ceil += f"AP_{array}_{dd} * "
                    str_ceil += f"16000 / size_data_type"
                    str_ceil += ")"
                    all_access = []
                    read = self.analysis.dic[k]["read"]
                    write = self.analysis.dic[k]["write"]
                    randw = read + write
                    for r in randw:
                        if array in r:
                            all_access += self.extract_iterators(r)
                    for l1, loop in enumerate(self.schedule[k][1::2]):
                        if f"transfer_{array}_S{k}_under_loop{loop} binary;" in var:
                            str_ceil += " + "
                            tc = ""
                            for l2, loop2 in enumerate(self.schedule[k][1::2]):
                                if l2 <= l1:
                                    if self.iterators[loop2] in all_access:
                                        tc += f"TC{loop2}_0 * "
                            tc += "1"
                            str_ceil += f"transfer_{array}_S{k}_under_loop{loop} * footprint_{array}_S{k} / ({tc}) / ("
                            for dd in range(dim):
                                str_ceil += f"AP_{array}_{dd} * "
                            str_ceil += f"16000 / size_data_type"
                            str_ceil += ")"

                    var.append(f"ceil{id_ceil} integer >= 0;")
                    constraints.append(f"#{str_ceil} <= ceil{id_ceil};") # AMPL does not like these constraints lol
                    cc = ""
                    for kk in range(dim):
                        cc += f"AP_{array}_{kk}"
                        if kk < dim - 1:
                            cc += " * "

                    str_ += f"ceil{id_ceil} * "


                    id_ceil += 1
                    for kk in range(dim):
                        str_ += f"AP_{array}_{kk}"
                        if kk < dim - 1:
                            str_ += " * "
                    lstr_.append(str_)
                    if str_ not in BRAM_CONSTRAINTS:
                        BRAM_CONSTRAINTS.append(str_)
            if len(lstr_) > 0:
                if f"{' + '.join(lstr_)} <= BRAM;" not in constraints:
                    constraints.append(f"#{' + '.join(lstr_)} <= BRAM;")

        if len(BRAM_CONSTRAINTS) > 0:
            constraints.append(f"#{' + '.join(BRAM_CONSTRAINTS)} <= BRAM;")
        
        f = open(self.nlp_file_name, "w")
        for head in header:
            f.write(head + "\n")
        f.write("\n")

        for arr in arrays:
            f.write(f"#Size array {arr}: {self.analysis.arrays_size[arr]}\n")

        for k in range(len(self.schedule)):
            read = self.analysis.dic[k]["read"]
            write = self.analysis.dic[k]["write"]
            randw = read + write
            for r in randw:
                it = self.extract_iterators(r)

                for j in range(1, len(self.schedule[k]), 2):
                    if self.iterators[self.schedule[k][j]] in it:
                        dim = it.index(self.iterators[self.schedule[k][j]])
                        f.write(f"#loop_{self.schedule[k][j]} iterates Array {r.split('[')[0]} in dim {dim}\n")
        
        for k in range(len(self.schedule)):
            f.write(f"#schedule {' '.join(list(map(str, self.schedule[k])))}\n")
            iter_ = []
            for l in range(1, len(self.schedule[k]), 2):
                iter_.append(self.iterators[self.schedule[k][l]])
            f.write(f"#iterators {' '.join(iter_)}\n")
            for l in range(1, len(self.schedule[k]), 2):
                f.write(f"#loop_{self.schedule[k][l]} := {self.red_loop[self.schedule[k][l]]}\n")
        
        
        
        # if red loop in loop body which have nn cte tc then can not be pipelined
        for k in range(len(self.schedule)):
            loops = self.schedule[k][1::2]
            contains_at_leat_one_loop_w_nn_cte_tc = False
            LB_ = self.analysis.dic[k]["LB_"]
            UB_ = self.analysis.dic[k]["UB_"]

            for key in list(LB_.keys()):
                try:
                    int(LB_[key])
                except:
                    contains_at_leat_one_loop_w_nn_cte_tc = True
                    break
            for key in list(UB_.keys()):
                try:
                    int(UB_[key])
                except:
                    contains_at_leat_one_loop_w_nn_cte_tc = True
                    break

            if contains_at_leat_one_loop_w_nn_cte_tc:
                for l in loops:
                    if self.red_loop[l]:
                        constraints.append(f"TC{l}_1 = 1;")

        
        
        for p in param:
            if "#" in p:
                p = p.replace("#", "")
                f.write(f"#param {p}\n")
            else:
                f.write("param " + p + "\n")
        f.write("\n")
        for v in var:
            f.write("var " + v + "\n")
        f.write("\n")

        f.write(f"minimize cost: {' + '.join(obj)};\n")
        f.write("\n")

        for k, c in enumerate(constraints):
            if ";" not in c:
                c = c + ";"
            if "#" in c:
                c = c.replace("#", "")
                f.write(f"#subject to con{k}: " + c + "\n")
            else:
                f.write(f"subject to con{k}: " + c + "\n")

        f.write("solve;\n")
        for k in var:
            k = k.split(" ")[0]
            f.write(f"display " + k + ";\n")
        f.write("display _total_solve_time;\n")
        f.close()
        
    def write_list_of_max(self, l):
        if len(l) == 1:
            return l[0]

        else:
            cc = []
            ll = []
            for i in range(len(l)):
                c = l[i].split("*")[0]
                l_ = " * ".join(l[i].split("*")[1:])
                cc.append(c)
                ll.append(l_)

            prod_ = list(product(*[[0,1] for i in range(0, len(ll))]))
            x = tuple([0 for k in range(len(ll))])

            prod_.remove(x)

            
            str_ = []
            for pos in prod_:
                if sum(pos) == 0:
                    continue

                else:
                    c = []
                    l = []
                    for i, p in enumerate(pos):
                        if p == 1:
                            c.append(cc[i])
                            l.append(ll[i])
                        else:
                            c.append(f"(1 - {cc[i]})")
                    if sum(pos) == 1:
                        str_ += [f"{' * '.join(c)} * {l[0]}"]
                    else:
                        str_ += [f"{' * '.join(c)} * {self.create_max_constraint2(l)}"]


            return " + ".join(str_)


    def create_max_constraint2(self, l):
        if len(l) == 1:
            return l[0]
        elif len(l) == 2:
            return self.create_max_constraint(l[0], l[1])
        else:
            current_const = self.create_max_constraint(l[0], l[1])
            for i in range(2, len(l)):
                current_const = self.create_max_constraint(current_const, l[i])
            return current_const

    def create_max_constraint(self, v1, v2):
        v1 = v1.replace(" ", "")
        v2 = v2.replace(" ", "")
        str_ = f"({v1} + {v2} + abs({v1} - {v2}))/2"
        return str_
    
    def create_min_constraint(self, v1, v2):
        str_ = f"({v1} + {v2} - abs({v1}-{v2}))/2"
        return str_
