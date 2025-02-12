# Sisyphus

Sisyphus is a framework for automated code transformation and pragma insertion in High-Level Synthesis, leveraging nonlinear programming.

## Disclaimer

This code is provided **as is**, without any guarantees of correctness, reliability, or performance. While we have made efforts to ensure its functionality, **bugs, errors, or unexpected behavior may still occur**.

### Important Notes:
- Use this code **at your own risk**.
- We are not responsible for any issues, damages, or losses resulting from its use.
- If you encounter any problems, feel free to report them, but we **do not guarantee** immediate fixes or support.

We appreciate any feedback or contributions to help improve the project.  
Thank you for your understanding!

## Dependencies

Please install the following packages:  

- **AMD Vitis 2023.2**  
- **AMPL** (with license)  
- **Clang-format**  
- **PoCC**  
- **ISCC**  

### Links and Instructions:
- **AMD Vitis 2023.2**: [Download here](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools/2023-2.html)  
- **AMPL**: [Visit the official website](https://ampl.com)  
- **PoCC and ISCC**:  
  - Use our Docker image:  
    ```sh
    docker pull ghcr.io/ucla-vast/pocc:latest
    ```  
  - Or download directly from SourceForge: [Download PoCC](https://sourceforge.net/projects/pocc/files/)  

> **Important**: The system expects the `pocc` and `iscc` commands to be available.  
> If necessary, create an alias for these commands.
> You can also modify the POCC_CMD and ISCC_CMD variables in pocc.py and iscc.py. 

---



## Run

```sh
cd Sisyphus
python3 main.py --file <C file> --folder <Name Folder> --csim --vitis
```

For example you can run:

```sh
python3 main.py --file cfile/2mm_MEDIUM.c --folder 2mm_result --csim --vitis
```

## Usage

To view the available options, run:

```bash
python3 main.py --help
```

## Artifact Evaluation

To run the artifact evaluation, execute:

```sh
python3 artifact.py
python3 artifact2.py
python3 artifact3.py
```

The results are available at [GitHub Repository](https://github.com/UCLA-VAST/sisyphus-fpga25-artifact).

## Citation

If you use this work, please cite:

### BibTeX
```bibtex
@inproceedings{sisyphus,
      author = {Pouget, St\'{e}phane and Pouchet, Louis-No\"{e}l and Cong, Jason},
      title = {A Unified Framework for Automated Code Transformation and Pragma Insertion},
      year = {2025},
      publisher = {Association for Computing Machinery},
      address = {New York, NY, USA},
      url = {https://doi.org/10.1145/3706628.3708873},
      doi = {10.1145/3706628.3708873},
      booktitle = {Proceedings of the 2025 ACM/SIGDA International Symposium on Field Programmable Gate Arrays},
      location = {Monterey, CA, USA},
      series = {FPGA '25}
}
```

### **Plain Text Citation**

S. Pouget, L.-N. Pouchet, and J. Cong,  
"A Unified Framework for Automated Code Transformation and Pragma Insertion"  
*Proceedings of the 2025 ACM/SIGDA International Symposium on Field Programmable Gate Arrays (FPGA '25)*,  
Monterey, CA, USA, 2025.  
[DOI: 10.1145/3706628.3708873](https://doi.org/10.1145/3706628.3708873)
