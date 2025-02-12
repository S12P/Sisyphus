# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

class CSIM:
    def __init__(self, rtl, data_type, fold, original_file, new_file, no_tree_red, freq, board):
        self.rtl = rtl
        self.data_type = data_type
        self.fold = fold
        self.original_file = original_file
        self.new_file = new_file
        self.diff = 0.0001
        self.no_tree_red = no_tree_red
        self.freq = freq
        self.board = board
        self.original_code = self.read_file(original_file)
        self.new_code = self.read_file(new_file)
        self.generate()
        

    def read_file(self, file):
        f = open(file, "r")
        code = f.readlines()
        f.close()
        return code
    
    def extract_iterator(self, string):
        if "[" not in string:
            return []
        index = string.find("[")
        string = string[index:]
        string = string.replace("][", "!")
        string = string.replace("[", "")
        string = string.replace("]", "")
        string = string.split("!")
        return string

    def extract_name(self, string):
        string = string.replace(f"{self.data_type}16", "").replace(f"{self.data_type}8", "").replace(f"{self.data_type}4", "").replace(f"{self.data_type}2", "").replace(f"{self.data_type}", "").replace(f"{self.data_type}1", "").replace("int", "").replace("void", "").replace(" ", "")
        return string.split("[")[0]
    
    def extract_data_type(self, string):
        #FIXME 
        
        if f"{self.data_type}2" in string:
            return f"{self.data_type}2"
        elif f"{self.data_type}4" in string:
            return f"{self.data_type}4"
        elif f"{self.data_type}8" in string:
            return f"{self.data_type}8"
        elif f"{self.data_type}16" in string:
            return f"{self.data_type}16"
        elif f"{self.data_type}1" in string:
            return f"{self.data_type}1"
        elif f"{self.data_type}" in string:
            return f"{self.data_type}1"
        
        if "int" in string:
            return "int"
        return "void"

    def extract_arguments(self, code):
        arguments = []
        last_void = 0
        for line in code:
            if "void" in line:
                last_void = code.index(line)
        l = code[last_void]
        index_open = l.index("(")
        index_close = l.index(")")
        arguments = l[index_open+1:index_close].split(",")
        if "n" in arguments:
            arguments.remove("n")
        if "m" in arguments:
            arguments.remove("m")
        return arguments

    def extract_call(self, code):
        arguments = []
        last_void = 0
        for line in code:
            if "void" in line:
                last_void = code.index(line)
        l = code[last_void].replace("{", "").replace("\n", "")
        return l

    def extract_name_function(self, code):
        arguments = []
        last_void = 0
        for line in code:
            if "void" in line:
                last_void = code.index(line)
        l = code[last_void].split("(")[0].split(" ")[-1].replace("\n", "")
        return l

    def extract_headers(self, code):
        headers = []
        for line in code:
            if "#include" in line:
                headers.append(line)
        return headers

    def create_tab(self, nb):
        nb = max(0,nb)
        return "    " * nb

    def write_csim_tcl(self):
        str_ = f"""
catch {{::common::set_param -quiet hls.xocc.mode csynth}};

open_project csim.prj
set_top csim
add_files "{self.new_file.split("/")[-1]}" -cflags " -O3 -D XILINX "
add_files -tb "csim.cpp"
open_solution -flow_target vitis solution
set_part {self.board}
create_clock -period {self.freq}MHz -name default
csim_design
close_project
puts "HLS completed successfully"
exit
        """
        f = open(f"{self.fold}/csim.tcl", "w")
        f.write(str_)
        f.close()

    def write_tcl(self):
        str_tmp = "csynth_design\nexport_design\n"
        if self.rtl:
            str_tmp = f"""
csim_design
csynth_design
cosim_design
export_design -flow impl
get_clock_period -name ap_clk -ns
            """
        if not self.no_tree_red:
            str_ = f"""
catch {{::common::set_param -quiet hls.xocc.mode csynth}};

open_project kernel_nlp
set_top kernel_nlp
add_files "{self.new_file.split("/")[-1]}" -cflags " -O3 -D XILINX "
add_files -tb "csim.cpp"
open_solution -flow_target vitis solution
set_part {self.board}
create_clock -period {self.freq}MHz -name default

config_dataflow -strict_mode warning

config_export -disable_deadlock_detection=true

config_rtl -m_axi_conservative_mode=1
config_interface -m_axi_addr64

config_interface -m_axi_auto_max_ports=0
config_export -format ip_catalog -ipname kernel_nlp
config_compile -unsafe_math_optimizations

{str_tmp}
close_project
puts "HLS completed successfully"
exit
            """
        else:
            str_ = f"""
catch {{::common::set_param -quiet hls.xocc.mode csynth}};

open_project kernel_nlp
set_top kernel_nlp
add_files "{self.new_file.split("/")[-1]}" -cflags " -O3 -D XILINX "
add_files -tb "csim.cpp"
open_solution -flow_target vitis solution
set_part {self.board}
create_clock -period {self.freq}MHz -name default

config_dataflow -strict_mode warning

config_export -disable_deadlock_detection=true

config_rtl -m_axi_conservative_mode=1
config_interface -m_axi_addr64

config_interface -m_axi_auto_max_ports=0
config_export -format ip_catalog -ipname kernel_nlp

{str_tmp}
close_project
puts "HLS completed successfully"
exit
            """
        f = open(f"{self.fold}/vitis.tcl", "w")
        f.write(str_)
        f.close()

    def generate(self):
        code = []
        original_headers = self.extract_headers(self.original_code)
        new_headers = self.extract_headers(self.new_code)
        headers = list(set(original_headers + new_headers))
        code += headers
        output_file = self.new_file.split(".")[0]
        output_file_ = output_file.split("/")[-1]
        code += f'#include "{output_file_}.h"\n\n'

        code += f"typedef hls::vector<{self.data_type},16> {self.data_type}16;\n"
        code += f"typedef hls::vector<{self.data_type},8> {self.data_type}8;\n"
        code += f"typedef hls::vector<{self.data_type},4> {self.data_type}4;\n"
        code += f"typedef hls::vector<{self.data_type},2> {self.data_type}2;\n"
        code += f"typedef hls::vector<{self.data_type},1> {self.data_type}1;\n"

        code += self.original_code

        # code += """extern "C" { \n"""
        code += "\n"
        code +=  self.extract_call(self.new_code) + ";\n"
        code += "\n"
        # code += "}\n"
        f = open(f"{output_file}.h", "w")
        f.write(f"typedef hls::vector<{self.data_type},16> {self.data_type}16;\n")
        f.write(f"typedef hls::vector<{self.data_type},8> {self.data_type}8;\n")
        f.write(f"typedef hls::vector<{self.data_type},4> {self.data_type}4;\n")
        f.write(f"typedef hls::vector<{self.data_type},2> {self.data_type}2;\n")
        f.write(f"typedef hls::vector<{self.data_type},1> {self.data_type}1;\n")
        f.write(self.create_tab(1) + self.extract_call(self.new_code) + ";\n")
        f.close()

        

        original_arg = self.extract_arguments(self.original_code)
        new_arg = self.extract_arguments(self.new_code)


        

        code += "int main(){\n"
        code += self.create_tab(1) + 'printf("Starting C-simulation...\\n");\n'
        for arg in original_arg:
            data_type = f"{self.data_type}"
        code += f"    {data_type} val;\n"
        for arg in original_arg:
            data_type = f"{self.data_type}"
            name = self.extract_name(arg).replace(" ", "") 
            array_size = self.extract_iterator(arg)
            if data_type == "int":
                continue
            if len(array_size) == 0:
                code += f"{self.create_tab(1)}{data_type} {name}_ori;\n"
                code += f"{self.create_tab(1)}{data_type} {name}_new;\n"
            else:
                code += f"{self.create_tab(1)}{data_type} {name}_ori[{']['.join(array_size)}];\n"
                code += f"{self.create_tab(1)}{data_type} {name}_new[{']['.join(array_size)}];\n"

        for arg in original_arg:
            data_type = f"{self.data_type}"
            if data_type == "int":
                continue
            name = self.extract_name(arg).replace(" ", "") 
            array_size = self.extract_iterator(arg)

            if len(array_size) == 0:
                code += f"    val = (({data_type})rand() / RAND_MAX);\n"
                code += f"    {name}_ori = val;\n"
                code += f"    {name}_new = val;\n"
            else:
                it = [] 
                for k, dim in enumerate(array_size):
                    tab = self.create_tab(1+k)
                    code += f"{tab}for(int i{k} = 0; i{k} < {dim}; i{k}++){{\n"
                    it += [f"i{k}"]
                tab = self.create_tab(1+len(array_size))
                code += f"{tab}val = (({data_type})rand() / RAND_MAX);\n"
                code += f"{tab}{name}_ori[{']['.join(it)}] = val;\n"
                code += f"{tab}{name}_new[{']['.join(it)}] = val;\n"
                for k in range(len(array_size)):
                    tab = self.create_tab(len(array_size) - k)
                    code += f"{tab}}}\n"

        original_name = self.extract_name_function(self.original_code)
        new_name = self.extract_name_function(self.new_code)

        code += f"{self.create_tab(1)}{original_name}("
        for k, arg in enumerate(original_arg):
            data_type = self.extract_data_type(arg).replace(" ", "") 
            name = self.extract_name(arg).replace(" ", "") 
            code += f"{name}_ori"
            if k < len(original_arg) - 1:
                code += ", "
        code += ");\n"

        code += f"{self.create_tab(1)}{new_name}("
        for k, arg in enumerate(new_arg):
            data_type = self.extract_data_type(arg).replace(" ", "") 
            if "[" not in arg:
                data_type = f"{self.data_type}"
            if data_type != f"{self.data_type}":
                name = f"({data_type} *) "
            else:
                name = ""
            name += self.extract_name(original_arg[k]).replace(" ", "") 
            code += f"{name}_new"
            if k < len(new_arg) - 1:
                code += ", "
        code += ");\n"

        for arg in original_arg:
            data_type = self.extract_data_type(arg).replace(" ", "") 
            name = self.extract_name(arg).replace(" ", "") 
            array_size = self.extract_iterator(arg)

            if len(array_size) == 0:
                code += f"{self.create_tab(1)}if(abs({name}_ori - {name}_new) > {self.diff}){{\n"
                code += f"{self.create_tab(2)}printf(\"Error in {name}...\\n\");\n"
                code += f"{self.create_tab(2)}return 1;\n"
                code += f"{self.create_tab(1)}}}\n"
            else:
                it = [] 
                for k, dim in enumerate(array_size):
                    tab = self.create_tab(1+k)
                    code += f"{tab}for(int i{k} = 0; i{k} < {dim}; i{k}++){{\n"
                    it += [f"i{k}"]
                tab = self.create_tab(1+len(array_size))
                tabp1 = self.create_tab(2+len(array_size))
                code += f"{tab}if(abs({name}_ori[{']['.join(it)}] - {name}_new[{']['.join(it)}])/{name}_ori[{']['.join(it)}] > {self.diff}){{\n"
                code += f"{tabp1}printf(\"Error in {name}"
                for k, dim in enumerate(array_size):
                    code += f"[%d]"
                code += f"...\\n\""
                for k, dim in enumerate(array_size):
                    code += f", i{k}"
                code += ");\n"
                code += f"{tabp1}return 1;\n"
                code += f"{tab}}}\n"
                for k in range(len(array_size)):
                    tab = self.create_tab(len(array_size) - k)
                    code += f"{tab}}}\n"
        code += f"""{self.create_tab(1)}printf(\"C-simulation passed!\\n\");\n"""
        code += f"{self.create_tab(1)}return 0;\n"
        code += "}\n"

        f = open(f"{self.fold}/csim.cpp", "w")
        code = "".join(code)
        f.write(code)
        f.close()

        self.write_csim_tcl()
        self.write_tcl()