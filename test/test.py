import os
import sys
import glob
import time
import random
import argparse
import pyfiglet
import textwrap
import subprocess

from tools.injector import random_bitflips, white_noise_bitflips, scratch_emulation

CPU_VOLTAGE = 1.2
CPU_CAPACITANCE = 1e-9

def get_cpu_ticks() -> int:
    with open("/proc/stat", "r") as f:
        line = f.readline()
    parts = line.split()[1:]
    return sum(map(int, parts))

def get_cpu_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read()) / 1000.0
    except FileNotFoundError:
        return -1.0

def get_cpu_freq() -> float:
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
            return int(f.read().strip()) / 1e6
    except FileNotFoundError:
        return -1.0

def estimate_energy(cpu_time: float, freq_ghz: float) -> float:
    freq_hz = freq_ghz * 1e9
    return CPU_CAPACITANCE * (CPU_VOLTAGE ** 2) * freq_hz * cpu_time

def _clean_tools(coder: str, decoder: str, generator: str) -> None:
    for tool in [coder, decoder, generator]:
        if os.path.exists(tool):
            os.remove(tool)

def _bit_differences(ffile: str, sfile: str) -> int:
    chunk_size = 8192
    diff_bits = 0
    with open(ffile, "rb") as f1, open(sfile, "rb") as f2:
        while True:
            b1 = f1.read(chunk_size)
            b2 = f2.read(chunk_size)
            if not b1 and not b2:
                break
            if len(b1) < len(b2):
                b1 += b'\x00' * (len(b2) - len(b1))
            elif len(b2) < len(b1):
                b2 += b'\x00' * (len(b1) - len(b2))
            for byte1, byte2 in zip(b1, b2):
                diff_bits += bin(byte1 ^ byte2).count('1')
    return diff_bits

def _fill_file(path: str, size: int) -> list[int]:
    content = []
    with open(path, "wb") as f:
        for _ in range(size):
            byte = random.randint(0, 255)
            f.write(byte.to_bytes(1, "little"))
            content.append(byte)
    return content

def _launch_tool(tool: str, args: list[str]) -> tuple[float, float, int, float, float]:
    start_time = time.perf_counter()
    start_proc_time = time.process_time()
    start_ticks = get_cpu_ticks()
    start_temp = get_cpu_temp()
    
    subprocess.run([tool, *args], check=True)
    
    end_time = time.perf_counter()
    end_proc_time = time.process_time()
    end_ticks = get_cpu_ticks()
    end_temp = get_cpu_temp()
    freq_ghz = get_cpu_freq()
    
    elapsed = end_time - start_time
    cpu_time = end_proc_time - start_proc_time
    tick_diff = end_ticks - start_ticks
    temp_diff = end_temp - start_temp
    energy = estimate_energy(cpu_time, freq_ghz)
    
    return elapsed, cpu_time, tick_diff, temp_diff, energy

def _build_tools(gcc: str, basedir: str, coder: str, decoder: str, generator: str) -> None:
    for tool in [coder, decoder, generator]:
        c_file = f"{tool}.c"
        if os.path.exists(tool):
            os.remove(tool)
        c_files = glob.glob(f"{basedir}/src/*.c")
        subprocess.run([gcc, f"-I{basedir}/include", "-O2", "-Wall", "-o", tool, *c_files, c_file], check=True)

def _print_statistics(size: int, diff: int, enctime: float, dectime: float, cpu_enc: float, cpu_dec: float, ticks_enc: int, ticks_dec: int, temp_enc: float, temp_dec: float, energy_enc: float, energy_dec: float) -> None:
    total_bits = size * 8
    percent_error = (diff / total_bits) * 100 if total_bits > 0 else 0
    print("=" * 80)
    print(f"{'Statistic':<40} | {'Value'}")
    print("-" * 80)
    print(f"{'Original file size (bytes)':<40} | {size}")
    print(f"{'Total bits':<40} | {total_bits}")
    print(f"{'Bit differences':<40} | {diff}")
    print(f"{'Percentage errors':<40} | {percent_error:.6f}%")
    print(f"{'Encoding time (s)':<40} | {enctime:.6f}")
    print(f"{'Decoding time (s)':<40} | {dectime:.6f}")
    print(f"{'Encoding CPU time (s)':<40} | {cpu_enc:.6f}")
    print(f"{'Decoding CPU time (s)':<40} | {cpu_dec:.6f}")
    print(f"{'Encoding CPU ticks':<40} | {ticks_enc}")
    print(f"{'Decoding CPU ticks':<40} | {ticks_dec}")
    print(f"{'Temp Δ Encoding (°C)':<40} | {temp_enc:+.2f}")
    print(f"{'Temp Δ Decoding (°C)':<40} | {temp_dec:+.2f}")
    print(f"{'Estimated CPU energy Encoding (J)':<40} | {energy_enc:.6f}")
    print(f"{'Estimated CPU energy Decoding (J)':<40} | {energy_dec:.6f}")
    print("=" * 80)

def _print_parity_info() -> None:
    print("parity_bits=2 => Hamming 3,1")
    print("parity_bits=3 => Hamming 7,4")
    print("parity_bits=4 => Hamming 15,11")
    print("parity_bits=5 => Hamming 31,26")
    print("parity_bits=6 => Hamming 63,57")
    print("parity_bits=7 => Hamming 127,120")
    print("parity_bits=8 => Hamming 255,247")
    print("parity_bits=9 => Hamming 511,502")

def _print_welcome(parser: argparse.ArgumentParser) -> None:
    print("Welcome! Avaliable arguments:\n")
    help_text = parser.format_help()
    options_start = help_text.find("optional arguments:")
    if options_start != -1:
        print(textwrap.indent(help_text[options_start:], "    "))
    else:
        print(textwrap.indent(help_text, "    "))

if __name__ == "__main__":
    ascii_banner = pyfiglet.figlet_format("Hamming codes!")
    print(ascii_banner)
    
    parser = argparse.ArgumentParser(description="Inject bitflips into disk image.")
    parser.add_argument("--gcc", type=str, default="gcc-14")
    parser.add_argument("--hamm-api", type=str, default="..")
    parser.add_argument("--coder", type=str, default="tools/file2hamm")
    parser.add_argument("--decoder", type=str, default="tools/hamm2file")
    parser.add_argument("--file-gen", type=str, default="tools/gen_file")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--file-size", type=str, default="512")
    parser.add_argument("--parity-bits", type=str, default="2")
    parser.add_argument("--parity-help", action="store_true")
    parser.add_argument("--src-file", type=str, default="image.img")
    parser.add_argument("--coded-file", type=str, default="image.hamm")
    parser.add_argument("--decoded-file", type=str, default="decoded.img")
    parser.add_argument("--strategy", type=str, default="none")
    parser.add_argument("--scratch-length", type=int, default=1024)
    parser.add_argument("--flip-prob", type=float, default=.5)
    parser.add_argument("--width", type=int, default=1)
    parser.add_argument("--intensity", type=float, default=.7)
    parser.add_argument("--flips-size", type=int, default=10)
    args = parser.parse_args()

    if len(sys.argv) == 1:
        _print_welcome(parser)
    if args.parity_help:
        _print_parity_info()
        exit(1)

    _build_tools(args.gcc, args.hamm_api, args.coder, args.decoder, args.file_gen)

    diff = enctime = dectime = cpu_enc = cpu_dec = energy_enc = energy_dec = 0.0
    ticks_enc = ticks_dec = 0
    temp_enc = temp_dec = 0.0

    for _ in range(args.repeat):
        _launch_tool(args.file_gen, ["--fs", args.file_size, "--out", args.src_file])
        _fill_file(args.src_file, int(args.file_size))
        
        enc_elapsed, enc_cpu, enc_ticks, enc_temp, enc_energy = _launch_tool(args.coder, ["--pb", args.parity_bits, "--target", args.src_file, "--out", args.coded_file])
        enctime += enc_elapsed
        cpu_enc += enc_cpu
        ticks_enc += enc_ticks
        temp_enc += enc_temp
        energy_enc += enc_energy

        if args.strategy == "random":
            random_bitflips(args.coded_file, args.flips_size)
        elif args.strategy == "wnoise":
            white_noise_bitflips(args.coded_file, args.flip_prob)
        elif args.strategy == "scratch":
            scratch_emulation(args.coded_file, args.scratch_length, args.width, args.intensity)
        
        dec_elapsed, dec_cpu, dec_ticks, dec_temp, dec_energy = _launch_tool(args.decoder, ["--pb", args.parity_bits, "--target", args.coded_file, "--out", args.decoded_file])
        dectime += dec_elapsed
        cpu_dec += dec_cpu
        ticks_dec += dec_ticks
        temp_dec += dec_temp
        energy_dec += dec_energy

        diff += _bit_differences(args.src_file, args.decoded_file)

    repeats = args.repeat
    _print_statistics(
        size=int(args.file_size),
        diff=diff / repeats,
        enctime=enctime / repeats,
        dectime=dectime / repeats,
        cpu_enc=cpu_enc / repeats,
        cpu_dec=cpu_dec / repeats,
        ticks_enc=ticks_enc // repeats,
        ticks_dec=ticks_dec // repeats,
        temp_enc=temp_enc / repeats,
        temp_dec=temp_dec / repeats,
        energy_enc=energy_enc / repeats,
        energy_dec=energy_dec / repeats
    )

    _clean_tools(args.coder, args.decoder, args.file_gen)
