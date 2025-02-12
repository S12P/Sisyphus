# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import argparse
import argcomplete
import extract
import analysis as analysis_
import computationBound
import generate_code_computation
import generate_code_computation2
import generate_csim
import iscc
import pocc
import parse_vitis_report
import subprocess
import utilities
import post_pass
import ressources as res

# AMPL = "/workspaces/ampl.linux-intel64/ampl"
AMPL = "ampl"

def main():
    parser = argparse.ArgumentParser(description="Sisyphus")
    parser.add_argument("--file", type=str, help="kernel.c")
    parser.add_argument("--no_tree_reduction", action="store_true", help="Do not Use tree reduction")
    parser.add_argument("--no_optimistic_reuse", action="store_true", help="Use to not have optimist DSP constraint")
    parser.add_argument("--csim", action="store_true", help="Launch CSIM")
    parser.add_argument("--no_flattening", action="store_true", help="Add Pragma HLS loop_flatten off above pipeline")
    parser.add_argument("--vitis_2021", action="store_true", help="Use Vitis 2021")
    parser.add_argument("--rtl", action="store_true", help="Launch CSIM")
    parser.add_argument("--double", action="store_true", help="Double data type")
    parser.add_argument("--reuse_nlp", action="store_true", help="Do not rerun NLP")
    parser.add_argument("--vitis", action="store_true", help="Launch Vitis-HLS")
    parser.add_argument("--no_post_pass", action="store_true", help="No Post Pass")
    parser.add_argument("--optimize_shape", action="store_true", help="Create a new dimension for each array, where the added dimension corresponds to the unrolling factor")
    parser.add_argument("--baron", action="store_true", help="Use Baron Solver")
    parser.add_argument("--gurobi", action="store_true", help="Use Gurobi Solver")
    parser.add_argument("--no_distribution", action="store_true", help="Avoid maximal distribution pass")
    parser.add_argument("--print_summary", action="store_true", help="Print Summary of the Report")
    parser.add_argument("--output", type=str, help="Name of the output file")
    parser.add_argument("--timeout_nlp", type=int, default=14400, help="Timeout of the NLP in seconds (default: 14400s)")
    parser.add_argument("--frequency", type=int, default=250, help="Frequency of the kernel in MHz (default: 250MHz)")
    parser.add_argument("--DSP", type=int, default=0, help="Number of DSP")
    parser.add_argument("--ON_CHIP_MEM_SIZE", type=int, default=0, help="ON_CHIP_MEM_SIZE")
    parser.add_argument("--partitioning_max", type=int, default=0, help="partitioning_max")
    parser.add_argument("--MAX_BUFFER_SIZE", type=int, default=0, help="MAX_BUFFER_SIZE")
    parser.add_argument("--timeout_vitis", type=int, default=5*60*60, help="Timeout Vitis in seconds")
    parser.add_argument("--limit_resource", type=int, default=100, help="Percentage of resource to use")
    parser.add_argument("--board", type=str, default="xcu200-fsgd2104-2-e", help="Board to target (default: xcu200-fsgd2104-2-e)")
    parser.add_argument("--folder", type=str, default="sisyphus", help="Name of the folder to store the files. Default is 'sisyphus'")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    vitis_version = "2023.2"
    if args.vitis_2021:
        vitis_version = "2021.1"

    data_type = "float"
    if args.double:
        data_type = "double"

    if not args.file:
        print("Please provide a file")
        return
    print(f"Start in {args.folder}")
    os.makedirs(args.folder, exist_ok=True)
    print("Extracting information from the file")
    # Extract statement information from the file
    schedule, dic, operations, arrays_size, chip, dep, operation_list = extract.compute_statement(args.file)
    
    print("ISCC")
    # Initialize ISCC object
    if args.no_distribution:
        fully_distributed_file = args.file
    else:
        name = args.file.split("/")[-1].split(".")[0]
        fully_distributed_file = f"{args.folder}/{name}_fully_distributed_file.cpp"
        iscc_obj = iscc.ISCC(data_type, args.folder, fully_distributed_file, schedule, dic, operations, arrays_size, chip, dep, operation_list)
    
    # Recompute statement information for a new file
    print("Extract statament")
    schedule, dic, operations, arrays_size, chip, dep, operation_list = extract.compute_statement(fully_distributed_file)
    
    # Save analysis data
    analysis_data = [schedule, dic, operations, arrays_size, dep, operation_list]
    analysis = analysis_.Analysis(data_type, schedule, dic, operations, arrays_size, chip, dep, operation_list)
    
    # Initialize variables for analysis
    UB = analysis.UB
    LB = analysis.LB
    output_file = "output.cpp"
    statements = analysis.statements
    iterators = analysis.iterators
    schedule = analysis.only_schedule
    headers = ['ap_int.h', 'hls_stream.h', 'hls_vector.h', 'cstring']
    arguments = analysis.arguments
    function_name = "kernel_nlp"
    pragmas = [[] for _ in range(len(UB))]
    pragmas_top = False
    optimize_burst = False

    ressource = res.Ressources(data_type)
    if int(args.DSP) > 0:
        ressource.DSP = int(args.DSP)
    if int(args.ON_CHIP_MEM_SIZE) > 0:
        ressource.ON_CHIP_MEM_SIZE = int(args.ON_CHIP_MEM_SIZE)
    if int(args.partitioning_max) > 0:
        ressource.partitioning_max = int(args.partitioning_max)
    if int(args.MAX_BUFFER_SIZE) > 0:
        ressource.MAX_BUFFER_SIZE = int(args.MAX_BUFFER_SIZE)

    nlp_file = f"{args.folder}/nlp.mod"
    nlp_log = f"{args.folder}/nlp.log"

    if not args.reuse_nlp:
        solver = "gurobi"
        if args.baron:
            solver = "baron"
        # Perform computation bound analysis
        computationBound.computationBound(data_type, ressource, solver, nlp_file, args.no_tree_reduction, args.no_optimistic_reuse, args.timeout_nlp, analysis, schedule, UB, LB, statements, iterators, output_file, headers, arguments, function_name, pragmas, pragmas_top, optimize_burst)
        # Run NLP optimization using AMPL
        utilities.run_ampl(AMPL, args.folder)
    
    # Process NLP log and model files
    results, order_array = utilities.process_nlp_results(schedule, nlp_file, nlp_log)

    # Generate final code and run CSIM
    if args.optimize_shape:
        generate_code_computation.GenerateCodeComputation(data_type, args.folder, args.file, nlp_file, nlp_log)
    else:
        generate_code_computation2.GenerateCodeComputation(data_type, args.folder, args.file, nlp_file, nlp_log)
    generate_csim.CSIM(args.rtl, data_type, args.folder, args.file, f"{args.folder}/code_generated.cpp", args.no_tree_reduction, args.frequency, args.board)
    if not args.no_post_pass:
        post_pass.PostPass(args.no_flattening, vitis_version, data_type, fully_distributed_file, args.folder, f"{args.folder}/code_generated.cpp", nlp_file, nlp_log)

    print("Files generated in", args.folder + "/")
    # Run Vitis-HLS if specified
    if args.csim:
        utilities.run_vitis_hls("csim.tcl", args.folder, args.timeout_vitis)

    if args.vitis:
        is_timeout = utilities.run_vitis_hls("vitis.tcl", args.folder, args.timeout_vitis)
        # is_timeout = 1
        cycles, gf, DSP_utilization, BRAM_utilization, LUT_utilization, FF_utilization, URAM_utilization = utilities.print_summary(args.folder, args.file)
        need_to_be_relaunch = False
        if is_timeout == -1:
            print("Error in Vitis-HLS")
            return
        elif is_timeout == 0:
            need_to_be_relaunch = True
            ressource.DSP -= 1000
        elif BRAM_utilization > args.limit_resource and DSP_utilization <= args.limit_resource and FF_utilization <= args.limit_resource and LUT_utilization <= args.limit_resource:
            factor = int(args.limit_resource) / int(BRAM_utilization)
            ressource.ON_CHIP_MEM_SIZE = factor * ressource.ON_CHIP_MEM_SIZE
            need_to_be_relaunch = True
        elif DSP_utilization > args.limit_resource or BRAM_utilization > args.limit_resource or FF_utilization > args.limit_resource or LUT_utilization > args.limit_resource:
            if args.no_optimistic_reuse == True:
                factor = int(args.limit_resource) / max(int(DSP_utilization), int(BRAM_utilization), int(FF_utilization), int(LUT_utilization))
                ressource.DSP = factor * ressource.DSP
            args.no_optimistic_reuse = True
            need_to_be_relaunch = True
        id_ = 0
        while need_to_be_relaunch:
            os.system(f"cp -r {args.folder} {args.folder}_overuse{id_}")
            # Perform computation bound analysis
            computationBound.computationBound(data_type, ressource, solver, nlp_file, args.no_tree_reduction, args.no_optimistic_reuse, args.timeout_nlp, analysis, schedule, UB, LB, statements, iterators, output_file, headers, arguments, function_name, pragmas, pragmas_top, optimize_burst)
            # Run NLP optimization using AMPL
            utilities.run_ampl(AMPL, args.folder)

            # Process NLP log and model files
            results, order_array = utilities.process_nlp_results(schedule, nlp_file, nlp_log)

            # Generate final code and run CSIM
            if args.optimize_shape:
                generate_code_computation.GenerateCodeComputation(data_type, args.folder, args.file, nlp_file, nlp_log)
            else:
                generate_code_computation2.GenerateCodeComputation(data_type, args.folder, args.file, nlp_file, nlp_log)
            generate_csim.CSIM(args.rtl, data_type, args.folder, args.file, f"{args.folder}/code_generated.cpp", args.no_tree_reduction, args.frequency, args.board)
            if not args.no_post_pass:
                post_pass.PostPass(args.no_flattening, vitis_version, data_type, fully_distributed_file, args.folder, f"{args.folder}/code_generated.cpp", nlp_file, nlp_log)
            print("Files generated in", args.folder + "/")
            utilities.run_vitis_hls("csim.tcl", args.folder, args.timeout_vitis)
            utilities.run_vitis_hls("vitis.tcl", args.folder, args.timeout_vitis)
            cycles, gf, DSP_utilization, BRAM_utilization, LUT_utilization, FF_utilization, URAM_utilization = utilities.print_summary(args.folder, args.file)
            need_to_be_relaunch = False
            if BRAM_utilization > args.limit_resource and DSP_utilization <= args.limit_resource and FF_utilization <= args.limit_resource and LUT_utilization <= args.limit_resource:
                factor = int(args.limit_resource) / int(BRAM_utilization)
                ressource.ON_CHIP_MEM_SIZE = factor * ressource.ON_CHIP_MEM_SIZE
                need_to_be_relaunch = True
            elif DSP_utilization > args.limit_resource or BRAM_utilization > args.limit_resource or FF_utilization > args.limit_resource or LUT_utilization > args.limit_resource:
                if args.no_optimistic_reuse == True:
                    factor = int(args.limit_resource) / max(int(DSP_utilization), int(BRAM_utilization), int(FF_utilization), int(LUT_utilization))
                    ressource.DSP = factor * ressource.DSP
                args.no_optimistic_reuse = True
                need_to_be_relaunch = True


if __name__ == "__main__":
    main()