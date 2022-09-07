"""Calibrate.

Tool for generation calibration data for mmwave-cas radar
"""
import os
import json
import argparse
import numpy as np


def coupling_calibration(filename: str, ntx: int, nrx: int,
                         nc: int, ns: int) -> np.array:
    """Generate coupling calibration.

    In order to compute an application independent coupling calibration,
    the mutually induced coupling between the antenna is estimated as

    Arguemnts:
        filename (str): Path to the frame to use for calibration purpose.
        ntx (int): Number of transmission antenna
        nrx (int): Number of reception antenna
        nc (int): Number of chirp loop per frame
        ns (int): Number of samples per chirp
    """
    frame = np.fromfile(filename, dtype=np.int16, count=-1).reshape(
        ntx, nrx, nc, ns, 2
    )
    frame = np.mean(frame, axis=(2, 3))
    return frame


def waveform_calibration(filename: str, cfg: str, **kwargs) -> np.array:
    """Generate phase/amplitude and frequency calibration matrices.

    Arguments:
        filename (str): Path to the frame to use for calibration
        cfg (str): Calibration configuration file
    """
    config = {}
    with open(cfg,"r") as fh:
        config = json.load(fh)
    ntx: int = config["ntx"]
    nrx: int = config["nrx"]
    nc: int = config["numChirpLoops"]
    ns: int = config["numAdcSamples"]

    fslope: float = config["frequencySlope_Mhz_us"] * 1e+12     # Hz/s
    fsample: float = config["adcSamplingFrequency_ksps"] * 1e3  # Hz

    # Speed of light
    C: float = 299792458                                        # m/s

    rmax: float = fsample * C / (2 * fslope)    # Max range
    rres: float = rmax / ns                     # Range resolution

    # Reference distance of the target object used for calibration
    ref: float = kwargs.get("ref")                              # m

    # Range bin interval were the target is expected to be located
    # A window of +/- 1m around the expected position is used
    ref_bins = int((ref - 1) / rres), int((ref + 1) / rres)

    frame = np.fromfile(
        filename, dtype=np.int16, count=-1
    ).reshape(ntx, nrx, nc, ns, 2)
    frame = frame[:, :, :, :, 0] + 1j * frame[:, :, :, :, 1]    # I + jQ

    rfft = np.fft.fft(frame, ns, -1)
    rfft = np.sum(rfft, -2)

    peaks_idx = np.argmax(rfft[:, :, ref_bins[0]:ref_bins[1]], axis=-1)
    peaks = np.max(rfft[:, :, ref_bins[0]:ref_bins[1]], axis=-1)

    # Phase and amplitude calibration
    peaks = peaks[0, 0] / peaks
    phase_calib = np.zeros((ntx, nrx, 2), dtype=np.float64)
    phase_calib[:, :, 0] = np.real(peaks)
    phase_calib[:, :, 1] = np.imag(peaks)

    # Frequency calibration
    dpeak_idx: int = peaks_idx - peaks_idx[0, 0]
    freq_calib = 2 * np.pi * (dpeak_idx / ref) * (fsample / fslope)

    return freq_calib, phase_calib



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="calibrate.py",
        description="Calibration matrix genertion tool for MMWave CAS radar"
    )
    parser.add_argument(
        "-i", "--input",
        help="Path to the input file to use for the calibration",
        type=str,
    )
    parser.add_argument(
        "-o", "--output",
        help="Location to store the calibration files",
        type=str,
    )
    parser.add_argument(
        "-ref", "--reference",
        help="Reference distance used for the calibrtion",
        type=float,
    )

    parser.add_argument(
        "-ns", "--num-samples",
        help="Number of samples per frame",
        type=int,
        default=256,
    )
    parser.add_argument(
        "-nc", "--num-chirp-loops",
        help="Number of chirp loop per frame",
        type=int,
        default=16,
    )
    parser.add_argument(
        "-ntx", "--num-tx",
        help="Number of TX antenna",
        type=int,
        default=12,
    )
    parser.add_argument(
        "-nrx", "--num-rx",
        help="Number of RX antenna",
        type=int,
        default=16,
    )

    parser.add_argument(
        "-c", "--coupling-calibration",
        help="Generate coupling calibration matrix",
        action="store_true",
    )
    parser.add_argument(
        "-f", "--calibration-config",
        help="Calibartion configuration file",
        type=str
    )
    parser.add_argument(
        "-w", "--waveform-calibration",
        help="Generate coupling calibration matrix",
        action="store_true",
    )

    args = parser.parse_args()

    calib_context = {
        "ntx": args.num_tx,
        "nrx": args.num_rx,
    }

    if args.input is None:
        print("[ERROR] No input file!")
        exit(1)

    if args.output is None:
        args.output = os.sep.join(args.input.split(os.sep)[:-1])
        args.output += os.sep + "calibration"

    if not os.path.exists(args.output):
        os.makedirs(args.output, exist_ok=True)

    if args.coupling_calibration:
        if not args.input:
            print("[ERROR] No input file provided")
            exit(1)
        print("\n"
            "Make sure that the input frame provided was recorded\n"
            "when no target was in reach of the radar sensor.\n"
        )
        ack = str(input("Do you want to continue, Y/N? "))
        if ack.lower() == 'y':
            coupling_calib = coupling_calibration(
                args.input,
                args.num_tx,
                args.num_rx,
                args.num_chirp_loops,
                args.num_samples
            )
            calib_context["data"] = "coupling_calibration.bin"
            coupling_calib.astype(np.float32).tofile(
                os.path.join(args.output, calib_context["data"])
            )
            with open(os.path.join(args.output, "coupling_cfg.json"), "w") as fh:
                json.dump(calib_context, fh, indent=2)
            print("[INFO] Coupling calibration file generated!")
        else:
            print("[INFO] No calibration data generated!")
        exit(0)
    elif args.waveform_calibration:
        if (not args.input) or (not args.calibration_config):
            print("[ERROR] Missing input or calibration configuration file")
            exit(1)
        if args.reference is None:
            print("[ERROR] Missing distance to reference target")
            exit(1)
        print("\n"
            "Make sure that the input frame provided was recorded\n"
            "with a target (reflector) placed at the reference distance given.\n"
        )
        ack = str(input("Do you want to continue, Y/N? "))
        if ack.lower() == 'y':
            freq_calib, phase_calib = waveform_calibration(
                args.input,
                args.calibration_config,
                ref=args.reference,
            )
            calib_context["data"] = {
                "frequency": "frequency_calibration.bin",
                "phase": "phase_amp_calibration.bin"
            }
            freq_calib.astype(np.float64).tofile(
                os.path.join(args.output, calib_context["data"]["frequency"])
            )
            phase_calib.astype(np.float64).tofile(
                os.path.join(args.output, calib_context["data"]["phase"])
            )
            with open(os.path.join(args.output, "waveform_calib_cfg.json"), "w") as fh:
                json.dump(calib_context, fh, indent=2)
            print("[INFO] Frequency and Phase calibration files generated!")
        else:
            print("[INFO] No calibration data generated!")
        exit(0)

    parser.print_help()
