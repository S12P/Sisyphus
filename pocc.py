# Copyright Sisyphus authors. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import utilities

# POCC_CMD = "apptainer exec /opt/public/apptainer/pocc/pocc.sif pocc"
# POCC_CMD = "/opt/polyopt/default/sources/polyopt-hls/pocc/bin/pocc"
POCC_CMD = "pocc"

import sys
import os
import pocc

def tile(name_file, output_name_file):
    cloogf, cloogl = utilities.compute_cloogl_cloof(name_file)
    cmd = (f"{POCC_CMD} --pluto-fuse maxfuse {name_file} --verbose --output {output_name_file} "
           f"--pluto-tile --pluto-noskew --cloog-cloogl 42 --cloog-cloogf 42 --pluto-bounds 1")
    return utilities.launch(cmd)

def tile_no_codegen(name_file):
    cmd = f"{POCC_CMD} --pluto-fuse maxfuse {name_file} --verbose --pluto-tile -n"
    return utilities.launch(cmd)

def ponos(name_file):
    try:
        cmd = f"timeout 1m {POCC_CMD} --pluto --letsee {name_file} --verbose"
        res = utilities.launch(cmd)
    except Exception as e:
        res = ""
        print(f"Error Ponos {name_file}: {e}")
    return res

def extract_flops(name_file):
    cmd = f"{POCC_CMD} {name_file} --polyfeat --verbose"
    res = utilities.launch(cmd)
    for line in res:
        if "Flops executed" in line:
            gf = line.split(":")[1].split("(")[0].strip()
            return float(gf)
    return 0

def scoplib(file_):
    cmd = f"{POCC_CMD} {file_} --output-scop --verbose"
    return utilities.launch(cmd)

def candl(file_):
    cmd = f"{POCC_CMD} {file_} --candl-dep-isl-simp --verbose -n"
    return utilities.launch(cmd)

def candl_ddv(file_):
    cmd = f"{POCC_CMD} {file_} --candl-ddv --candl-dep-prune --red-commute --verbose -n"
    return utilities.launch(cmd)

def scop(file_):
    cmd = f"{POCC_CMD} {file_} --output-scop"
    utilities.launch(cmd)
    name_file = os.path.splitext(os.path.basename(file_))[0]
    scop_file_path = f"tmp/{name_file}.pocc.c.scop"
    with open(scop_file_path, "r") as f:
        return f.readlines()

def compute_schedule_from_pocc(schedule, source_file):
    # Read the source file and store its lines
    with open(source_file, "r") as file:
        lines = file.readlines()

    pragmas = []
    current_pragma = ""
    
    # Collect pragmas from the file, ignoring specific keywords
    for line in lines:
        if all(keyword not in line for keyword in ["kernel", "off", "loop_tripcount", "scop"]) and "pragma" in line:
            current_pragma += line.replace("#pragma", "").replace("ACCEL", "").strip().lower() + " "
        if "for" in line:
            pragmas.append(current_pragma.strip())
            current_pragma = ""

    # Count the number of 'for' loops and statements in the source file
    num_loops = sum(1 for line in lines if "for" in line)
    num_statements = sum(1 for line in lines if "=" in line and ";" in line)  # FIXME: This may not accurately count all statements

    # Generate a list of factors for loop positions
    factors = [10**i for i in range(2 * num_loops, 0, -1)]
    loop_positions = []
    loop_ids = [[] for _ in range(num_loops)]

    # Process the schedules and map pragmas to loops
    for sched_index, sched in enumerate(schedule):
        accumulated_position = 0
        for i in range(0, len(sched[1]) - 1, 2):
            position, iterator = sched[1][i:i + 2]
            lexical_position = (position + 1) * factors[i] + accumulated_position
            if [lexical_position, iterator] not in loop_positions:
                loop_positions.append([lexical_position, iterator])
                loop_ids[len(loop_positions) - 1].append((sched_index, i // 2))
            else:
                index = loop_positions.index([lexical_position, iterator])
                loop_ids[index].append((sched_index, i // 2))
            accumulated_position = lexical_position

    # Assign pragmas to the corresponding loops in the schedules
    for loop_index in range(len(loop_ids)):
        for sched_index, loop_level in loop_ids[loop_index]:
            schedule[sched_index][2][loop_level] = pragmas[loop_index] if loop_index < len(pragmas) else ""

    return schedule

def parser(source_file):
    # Parse the source file using pocc to get the scop information
    scop_info = scop(source_file)
    if not scop_info:
        return []

    schedules = []
    index = 0
    statement_id = 0

    # Iterate through the scop information
    while index < len(scop_info):
        if "# Scattering function" in scop_info[index] and "is provided" not in scop_info[index]:
            index += 1
            schedule_size = int(scop_info[index].split()[0])  # schedule 2d+1
            dimension = (schedule_size - 1) // 2

            index += 1
            schedule = []
            pragmas = ["" for _ in range(dimension)]
            
            if dimension == 0:
                # Handle case with no dimensions
                if not schedules:
                    schedule.append(0)
                else:
                    schedule.append(int(schedules[-1][1][0]) + 1)
            else:
                # Collect schedule information
                for _ in range(schedule_size):
                    if scop_info[index].split("##")[-1].strip() == "fakeiter":
                        break
                    schedule.append(scop_info[index].split("##")[-1].strip())
                    index += 1

            # Convert every other element in the schedule to integer
            for i in range(0, len(schedule), 2):
                schedule[i] = int(schedule[i])
                
            schedules.append([f"S{statement_id}", schedule, pragmas])
            statement_id += 1

        index += 1

    # Compute the final schedule with pragmas
    schedules = compute_schedule_from_pocc(schedules, source_file)

    return schedules

def compute_schedule(fil):
    os.makedirs("tmp", exist_ok=True)
    return parser(fil)