# MMWave Calibrate

Tool to generate the calibrtion matrices for the MMWCAS-RF-EVM radar.

This tool allow to regenrate three types of calibration matrices:
- Coupling calibration
- Phase and amplitude calibration
- Frequency calibration

For generating the coupling calibration, one need to record some data with
the MMWCAS-RF evaluation module, with no target in sight.

For the frequency and phase calibration, at target (more precisely a corner
reflector) should be placed at a knwon distance (knwon as the reference distance)
of the radar and aligned with its center of coordinate.

The recorded data in both cases must be repacked using the
[mmwave-repack](https://gitlab.com/master-emm/thesis/mmwave-repack) tool.

## Installation

Create a virtual environment and install the necessary packages as shown below

```bash
# Create virtual enviroment and enable it
python -m venv venv
source ./venv/bin/activate

# Install requirements
python -m pip install -r requirements.txt
```

## Usage

```bash
# Coupling calibration
python calibrate.py -c -i <path-to-frame> [-o <output-directory>]
python calibrate.py --coupling-calibration -i <path-to-frame> [-o <output-directory>]

# Phase and Frequency calibration
python calibrate.py -w -f <calibration-config-file> -i <path-to-frame> [-o <output-directory>] -ref <target-distance>
```

The following CLI options are optional

```bash
# Number of TX and RX antenna
python calibrate.py ... [-ntx <num-tx-antenna> -nrx <num-rx-antenna>]

# Number of TX and RX antenna
python calibrate.py ... [-ns <num-adc-samples> -nc <num-chirp-loops>]
```

Use the help to see all the possible options.

## Examples

```bash
# Coupling calibration
python calibrate.py -c -i /home/user/calib0/frame_1.bin

# Phase, Amplitude and Frequency calibration
python calibrate.py -w -f config/default-calib.json -i /home/user/calib1/frame_1.bin -ref 5.0
```

**NOTE**: Be careful and make sure to use the appropriate recording for the correcding calibration.

## Reading the calibration files

```python
import numpy as np

ntx: int = 12       # Number of TX antenna
nrx: int = 16       # Number of RX antenna

# Coupling calibration
coupling_calib = np.fromfile("counpling_calibration.bin", dtype=np.float32, count=-1).reshape(ntx, nrx, 2)
coupling_calib = coupling_calib[:, :, 0] + 1j * coupling_calib[:, :, 1]

# Phase calibration
phase_calib = np.fromfile("phase_calibration.bin", dtype=np.float64, count=-1).reshape(ntx, nrx, 2)
phase_calib = phase_calib[:, :, 0] + 1j * phase_calib[:, :, 1]

# Frequency calibration
frequency_calib = np.fromfile("phase_amp_calibration.bin", dtype=np.float64, count=-1).reshape(ntx, nrx)
```
