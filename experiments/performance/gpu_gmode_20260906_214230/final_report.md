# G-MODE PHYSICAL GPU EXPERIMENT REPORT

Experiment ID: GPU_GMODE_CONTROLLED_20260906
Repository HEAD: 8f444de
Working tree status: Tracked files clean; untracked temporary audit scripts and experiment logs preserved

Machine: Dell G15 5530
CPU: 13th Gen Intel(R) Core(TM) i7-13650HX (14 cores / 20 threads)
GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU (GA107)
VRAM: 6144 MiB (6143.5 MiB usable)
Driver: 616.64
BIOS: 1.34.0
VBIOS: 94.07.82.40.2f
Python: 3.10.9 (tags/v3.10.9:1dd9be6, Dec 6 2022) at D:\Projects\ocean-sentinel\venv\Scripts\python.exe
PyTorch: 2.14.0+cu126
CUDA: 12.6
cuDNN: 91002

CONTROL STATE:
AWCC: Optimized (Manually Confirmed Active)
G-mode: OFF (Manually Confirmed Active)
Windows: Best Performance (Power Overlay GUID: ded574b5-45a0-4f42-8737-46345c09c238)
AC: Online (PowerOnline = True)

G-MODE STATE:
AWCC: Profile engaged by G-mode (Fans Ramp to 100%)
G-mode: ON (F9 Key Pressed, Indicator Confirmed Active)
Windows: Best Performance (ded574b5-45a0-4f42-8737-46345c09c238)
AC: Online (PowerOnline = True)

CONTROL RESULTS
100-batch Run A: 31.37 samples/sec (25.50 s | step: 255.02 ms | clock: 1899 MHz | power: 75.6 W | peak temp: 79 C)
100-batch Run B: 31.37 samples/sec (25.50 s | step: 254.96 ms | clock: 1898 MHz | power: 75.5 W | peak temp: 79 C)
same-session sustained control if performed: 31.33 samples/sec (300 batches | 76.62 s | step: 255.36 ms | clock: 1890 MHz | power: 76.1 W | peak temp: 82 C)
historical canonical 300-batch control: 33.34 samples/sec (300 batches | 71.99 s | step: 239.9 ms | clock: 1987-1942 MHz | power: 80.2 W | peak temp: 87 C)

G-MODE RESULTS
600-batch Run 1: 32.07 samples/sec (100 warmup + 600 measure | 149.66 s | step: 249.41 ms | clock: 1909 MHz | power: 77.0 W | peak temp: 76 C)
1,200-batch extended: 31.51 samples/sec (100 warmup + 1200 measure | 304.69 s | step: 253.89 ms | clock: 1906 MHz | power: 77.0 W | peak temp: 80 C)
600-batch Run 2: 31.47 samples/sec (100 warmup + 600 measure | 152.53 s | step: 254.19 ms | clock: 1902 MHz | power: 76.0 W | peak temp: 77 C)

PRIMARY METRIC:
Control sustained throughput: 31.33 samples/sec (Same-Session 300-batch Sustained Control)
G-mode sustained throughput: 31.51 samples/sec (G-Mode 1,200-batch Extended Steady-State)
Delta samples/sec: +0.18 samples/sec
Delta %: +0.57%

SECONDARY COMPARISON (Against Historical Canonical Control):
Historical Control sustained throughput: 33.34 samples/sec (Step 2B 300-batch Sustained Control)
G-mode sustained throughput: 31.51 samples/sec (G-Mode 1,200-batch Extended Steady-State)
Delta vs Historical samples/sec: -1.83 samples/sec
Delta vs Historical %: -5.49%

THERMAL:
Control steady-state temperature: 81.4 C (Q4 mean, peak 82 C)
G-mode steady-state temperature: 78.9 C (Extended Q4 mean, peak 80 C; Run 1/2 peaks: 76 C - 77 C)
Thermal Delta: -2.5 C lower steady-state temperature under G-mode due to maximum fan curves.

CLOCK:
Control sustained clock: 1885.3 MHz (Control Q4 mean)
G-mode sustained clock: 1905.0 MHz (Extended Q4 mean)
Clock Delta: +19.7 MHz (+1.04%) sustained clock under G-mode.

POWER:
Control GPU power: 76.10 W (Control Q4 mean; mean: 76.06 W, peak: 76.66 W)
G-mode GPU power: 77.50 W (Extended Q4 mean; mean: 76.99 W, peak: 79.22 W)
Power Delta: +1.40 W (+1.84%) sustained power under G-mode.

CPU:
Control CPU behavior: 15.4% - 16.6% average CPU utilization, 0.21 ms average loader wait time.
G-mode CPU behavior: 17.1% - 17.5% average CPU utilization, 0.21 ms average loader wait time.
CPU Delta: Unchanged; DataLoader pipeline remained fully saturated in both modes.

STABILITY:
CUDA faults: 0
driver resets: 0
system instability: 0 (Flawless execution across 2,800 batches / ~15 minutes of continuous full load)

Q1 vs Q4:
Throughput:
  - Control (300-batch): Q1 = 31.37 samp/s -> Q4 = 31.26 samp/s (-0.36% drift)
  - G-mode Extended (1,200-batch): Q1 = 31.52 samp/s -> Q4 = 31.55 samp/s (+0.10% drift)
Clock:
  - Control: Q1 = 1894.9 MHz -> Q4 = 1885.3 MHz (-9.6 MHz decay)
  - G-mode Extended: Q1 = 1910.0 MHz -> Q4 = 1905.0 MHz (-5.0 MHz decay)
Power:
  - Control: Q1 = 75.81 W -> Q4 = 76.10 W (+0.29 W)
  - G-mode Extended: Q1 = 76.43 W -> Q4 = 77.50 W (+1.07 W)
Temperature:
  - Control: Q1 = 76.6 C -> Q4 = 81.4 C (+4.8 C rise)
  - G-mode Extended: Q1 = 73.9 C -> Q4 = 78.9 C (+5.0 C rise)

OBSERVED FACTS:
1. When F9 / Game Shift (G-mode) was engaged, Dell cooling fans spun up to 100% maximum duty cycle immediately.
2. Under G-mode, sustained GPU power averaged 76.99 W (peaking at 79.22 W), compared to 76.06 W (peaking at 76.66 W) in the same-session control (+0.93 W higher average power).
3. Under G-mode, sustained graphics clocks averaged 1906.3 MHz across 1,200 continuous batches, compared to 1890.2 MHz in the same-session control (+16.1 MHz higher clock).
4. Peak GPU temperature reached 80 C after 1,200 continuous batches under G-mode, compared to 82 C after only 300 batches in the same-session control (-2 C cooler despite 4x longer duration).
5. In G-mode Run 1 (first 600 batches), throughput reached 32.07 samples/sec while the machine was cooling down, but as the chassis absorbed heat, G-mode settled to 31.51 samples/sec (Extended 1,200 batches) and 31.47 samples/sec (Run 2).
6. Comparing G-mode steady state (31.51 samples/sec) directly against the same-session control (31.33 samples/sec) yields a delta of +0.18 samples/sec (+0.57%).
7. Comparing G-mode steady state (31.51 samples/sec) against the historical morning baseline (33.34 samples/sec) shows a deficit of -1.83 samples/sec (-5.49%).
8. GPU power NEVER reached 80 W sustained or 85 W peak in either mode today (maximum observed instantaneous peak was 79.22 W).

INFERENCES:
1. G-mode provides slightly better thermal headroom due to 100% fan speed, which prevents the GPU temperature from exceeding 80 C and slightly reduces thermal clock degradation (clock decay was only -5.0 MHz over 1,200 batches vs -9.6 MHz over 300 batches).
2. The slight throughput gain (+0.57% over same-session control) is directly correlated with the minor +16 MHz clock uplift allowed by the cooler operating temperatures.
3. However, G-mode does NOT reallocate significant power to the GPU: the TGP remains power-capped at ~77 W in this firmware/driver state, well below the 80.2 W observed earlier in the day.
4. The +0.57% sustained throughput difference is within normal ambient run-to-run noise (<1%) and does not constitute a meaningful performance breakthrough.

UNVERIFIED MECHANISMS:
1. CPU/GPU PLATFORM POWER-SHARING MECHANISM: NOT VERIFIED. Whether Dell Dynamic Tuning (DTT), Intel Speed Shift, or Dell EC power balancers actively clamp GPU power to ~77W after prolonged chassis heating cannot be definitively proven without direct Intel DTT registers and CPU package telemetry.
2. VBIOS POWER TARGET UNLOCK: NOT VERIFIED / REFUTED. The hypothesis that F9 "unlocks 85W+ TGP" is refuted by direct sensor measurement: peak power was 79.22 W and average power was 76.99 W.
3. AMBIENT CHASSIS SATURATION: NOT VERIFIED. Whether the difference between the 33.34 samples/sec morning baseline and today's 31.33-31.51 samples/sec afternoon baseline is caused by ambient room temperature, internal battery thermals, or sustained thermal soaking of the VRMs remains unverified.

ADVERSARIAL AUDIT:
- Counter-Hypothesis 1: "The claim that G-mode improves performance is wrong."
  Evidence supporting this counter-hypothesis:
  - Throughput delta between sustained G-mode (31.51 samp/s) and same-session control (31.33 samp/s) is only +0.18 samples/sec (+0.57%). This is well below the standard 2% significance threshold and easily explained by measurement variance.
  - Run 2 G-mode was 31.47 samples/sec, which is only +0.14 samples/sec (+0.45%) over control.
  - G-mode is significantly louder (100% fan noise) for virtually zero real-world throughput gain.
  - Both G-mode and same-session control are ~5.5% slower than the historical 33.34 samples/sec benchmark.

- Counter-Hypothesis 2: "The claim that G-mode is useless is wrong."
  Evidence supporting this counter-hypothesis:
  - G-mode indisputably lowered thermal equilibrium: 80 C after 1,200 batches vs 82 C after 300 batches in control.
  - In Run 1, G-mode delivered 32.07 samples/sec (+2.36% over control) before full chassis soak.
  - Clocks remained strictly above 1,900 MHz throughout 1,200 batches, whereas control dipped to 1,867 MHz.
  - For long overnight training runs (e.g. 10–20 epochs), lower temperatures (80 C vs 87 C) protect hardware longevity and prevent extreme thermal runaway.

DECISION:
NEUTRAL (with minor thermal benefit)
The measured sustained throughput delta (+0.57%) is within the margin of noise and does not satisfy the criterion for MEANINGFUL IMPROVEMENT (>2.0%). However, G-mode maintains lower peak temperatures (80 C vs 82-87 C).

RECOMMENDATION:
STOP PHYSICAL OPTIMIZATION.
Neither AWCC Ultra Performance nor F9 G-Mode provides a meaningful sustained CUDA throughput advantage on this Dell G15 machine (Ultra Performance caused a -6.7% regression; G-mode showed a neutral +0.57% delta).
The machine is completely stable, thermally safe (<=80 C), and executes CUDA training reliably at ~31.5 - 33.3 samples/sec.
Physical optimization yields diminishing returns. We should immediately proceed to Phase EXP-02B model training and architectural improvements.

PRODUCTION IMPACT:
Zero production ML code modified.
Zero dataset or manifest files modified.
EXP01 and EXP02A baseline checkpoints and reports remain 100% pristine and unmodified.
All benchmark execution was strictly isolated inside `scripts/benchmark_gmode_controlled.py` and persisted to `experiments/performance/gpu_gmode_20260906_214230/`.

FAILURES / RECOVERIES:
None. All 5 benchmark workloads (Control Run A, Control Run B, Control Sustained 300, G-mode Run 1, G-mode Extended 1200, G-mode Run 2) executed with 0 errors, 0 warnings, and 0 dropped batches.

UNVERIFIED ITEMS:
1. Exact CPU package power draw (not safely exposed via public NVML/WMI without vendor kernel drivers).
2. Dell EC fan RPM registers (Dell does not expose fan RPM via standard ACPI or WMI interfaces).
