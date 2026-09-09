# CLOUD GPU QUALIFICATION REPORT

Experiment ID: CLOUD_GPU_QUALIFICATION_20260906_183611
Repository HEAD: 8f444de1d0fb35d09912a9e6bf27cebde8125f0d
Working tree: Clean working state for ML production modules

============================================================
LOCAL REFERENCE
============================================================

GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU (GA107, Ampere)
VRAM: 6,143.5 MB GDDR6 (96-bit bus, 168 GB/s bandwidth)
Current sustained throughput: 32.15 samples/sec post-reboot mean (Run A: 32.50, Run B: 31.80, CV: 2.18%)
Reference protocol: Canonical Step2B 300-batch sustained training benchmark (ResNet34UNet, 512x512, batch 8, num_workers 4, AMP FP16, AdamW, CombinedBCEAndDiceLoss, 78.05 W sustained power, 1,897.4 MHz clock, 82°C peak temperature, 0% thermal throttling)

============================================================
LIGHTNING
============================================================

Account access: ACCOUNT-SPECIFIC AVAILABILITY UNKNOWN (No local ~/.lightning credentials found; requires user login/API key)
Free credits: Platform provides 15 to 30 free Studio credits ($1.00/credit) on account registration
Credit expiry: Perpetual until consumed or subject to platform policy changes
Storage: 10 GB persistent storage included free per Studio workspace; excess storage billed at $0.10/GB/month against credit balance

L4:
Available? YES (Platform standard available Studio SKU; account quota pending user login)
VRAM: 24 GB GDDR6 with ECC (300 GB/s bandwidth)
Free/paid: Deducted from free credits at $0.79/hour (~19 to 38 hours total training capacity on free credits)
Session limitations: Configurable auto-sleep on inactivity (15 to 60 minutes)
Concurrency: 1 active GPU Studio on free/entry tier
Persistent storage: Full Studio filesystem (/teamspace/studios/this_studio/) persists across stops/reboots
Dataset strategy: Option A: Store 47.6 GB directly on Studio disk ($3.76/month in credits). Option B: Stream via Lightning Data / WebDataset from Cloudflare R2 bucket. Option C: Mount 10 GB representative spatial subset for architecture tuning.

T4:
Available? YES (Platform standard entry Studio SKU)
VRAM: 16 GB GDDR6 (320 GB/s bandwidth)
Free/paid: Deducted from free credits at $0.55/hour (~27 to 54 hours total training capacity on free credits)
Session limitations: Configurable auto-sleep on inactivity (15 to 60 minutes)
Concurrency: 1 active GPU Studio on free/entry tier
Persistent storage: Full Studio filesystem persists across stops/reboots
Dataset strategy: Same as Lightning L4

A100:
Available? YES (A100 40GB @ $2.19/hr and A100 80GB @ $2.71/hr)
Free/paid: Paid / high credit consumption rate
Do NOT use yet: STRICTLY ENFORCED. Rapidly drains free credits (15 credits consumed in 5.5 - 6.8 hours); unnecessary for ResNet34UNet Phase 2.2 scale.

============================================================
KAGGLE
============================================================

Account access: ACCOUNT-SPECIFIC AVAILABILITY UNKNOWN (No local ~/.kaggle/kaggle.json found; requires user API token and SMS phone verification for GPU access)

T4:
Available? YES (Standard Kaggle notebook accelerator)
VRAM: 16 GB GDDR6 (320 GB/s bandwidth)
Quota: 30.0 hours/week recurring free GPU quota (resets every Saturday at 00:00 UTC; $0.00 monetary cost forever)
Runtime: 12.0 hours maximum continuous execution per session (supports headless background Save & Run All)
Dataset strategy: Optimal: Upload Trujillo dataset once as a Private Kaggle Dataset (up to 100 GB allowed); instantly mounted read-only at /kaggle/input/trujillo-sar-tiles/ with 0-second mount overhead and 0 repeated uploads.

T4x2:
Available? YES (Multi-GPU notebook accelerator option)
GPU count: 2 discrete NVIDIA Tesla T4 GPUs
VRAM/GPU: 16 GB GDDR6
Total VRAM: 32 GB GDDR6
Quota: Deducts from standard 30 hours/week quota pool
Runtime: 12.0 hours maximum continuous execution per session
DDP feasibility: Fully feasible via PyTorch DistributedDataParallel (torchrun --nproc_per_node=2, NCCL backend). Caution: Interconnect is standard PCIe (no NVLink); gradient synchronization overhead must be empirically measured.
Dataset strategy: Identical optimal 100 GB private dataset mount at /kaggle/input/trujillo-sar-tiles/.

============================================================
AZURE
============================================================

Student access: AUDITED WITHOUT DEPLOYMENT ($0.00 spent; az CLI not installed locally)
Credit: $100 annual student credit pool
GPU quota: 0 vCPUs default quota for all GPU VM families (NCasT4_v3, NCv3, NV). Microsoft policy explicitly rejects GPU quota increases on Student and Free subscriptions without upgrading to Pay-As-You-Go.
Candidate GPU families: Standard_NC4as_T4_v3 (1x T4 16GB, ~$0.526/hr), Standard_NC6s_v3 (1x V100 16GB, ~$3.06/hr)
Do NOT deploy anything: COMPLIED. Zero Azure resources created. Retained strictly as RESERVE ONLY (non-viable for free training).

============================================================
DATASET STRATEGY
============================================================

Trujillo dataset size:
~47.6 GB uncompressed (28,414 tiles/masks); 40.7 GB compressed (01_Train_Val_Oil_Spill_images.7z); 1.2 MB split manifest.

Lightning strategy:
- Primary: Upload 47.6 GB extracted dataset or 40.7 GB archive to Studio persistent storage. Storage cost is $3.76/month in credits for the 37.6 GB over the free 10 GB allowance.
- Secondary / Streaming: Package tiles into WebDataset tar shards and stream via Lightning Data from Cloudflare R2 bucket with zero egress fees.
- Rapid Validation: Upload a balanced spatial subset (8-10 GB) fitting entirely within the 10 GB free storage tier for initial multi-epoch validation.

Kaggle strategy:
- Optimal Architecture: Create a single Private Kaggle Dataset named 'trujillo-sar-tiles' (40.7 GB compressed or 47.6 GB uncompressed) via Kaggle web UI or 'kaggle datasets create'.
- Mount: Attached as read-only input at /kaggle/input/trujillo-sar-tiles/.
- Advantages: 100 GB free private storage quota; 0-second mount latency; zero local scratch disk consumption in /kaggle/working; zero repeated uploads across notebook sessions.

Azure strategy:
- Non-viable due to 0 vCPU GPU quota lock. Azure Blob Storage + BlobFuse2 would cost ~$0.95/month for storage but cannot be attached to a GPU VM under Student subscription rules.

============================================================
CLOUD BENCHMARK DESIGN
============================================================

Comparable benchmark (Tier A):
- Batch size: 8 (exact match with local RTX 3050 baseline)
- Workload: ResNet34UNet, 512x512, in_channels=2, AMP FP16, AdamW, CombinedBCEAndDiceLoss, 300 batches, 10 warmup batches
- Metric: Samples/sec, step time (ms), step CV (%), peak VRAM (MB)
- Comparison target: Local post-reboot baseline = 32.15 samples/sec

Capacity benchmark (Tier B):
- Batch scaling evaluation: Discover maximum throughput and saturation point before VRAM exhaustion
- Candidate batches:
  * RTX 3050 (6 GB): Batch 8 (32.15 samp/s)
  * T4 (16 GB): Batch 8, 16, 24
  * L4 (24 GB): Batch 8, 16, 24, 32, 48
- Metric: Throughput vs batch size, VRAM headroom, step efficiency

DDP benchmark (Tier D):
- Multi-GPU evaluation: Kaggle T4x2 (2x 16GB)
- Protocol: PyTorch DDP via 'torchrun --nproc_per_node=2' with NCCL backend
- Batches: Per-GPU batch 8 (effective batch 16) and per-GPU batch 16 (effective batch 32)
- Metric: Aggregate throughput, scaling efficiency (%) = Aggregate / (Single_T4 * 2)

Metrics:
- Throughput (samples/sec)
- Mean Step Time & Latency Variance (ms)
- Peak Allocated VRAM & Reserved VRAM (MB)
- Host-to-Device Transfer & DataLoader Wait Time (ms)
- GPU SM Utilization (%)

============================================================
CANDIDATE MATRIX
============================================================

| Candidate | Access Status | VRAM | Free Compute Quota | Data Practicality (47.6 GB) | Session Reliability | Setup Difficulty | Expected Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Lightning AI L4** | Pending Login | 24 GB | 15-30 credits (~19-38 hrs) | Billable credits ($3.76/mo) or R2 stream | High (Studio persistence) | Low (VS Code / CLI) | **PRIMARY** |
| **Lightning AI T4** | Pending Login | 16 GB | 15-30 credits (~27-54 hrs) | Billable credits ($3.76/mo) or R2 stream | High (Studio persistence) | Low (VS Code / CLI) | **SECONDARY** |
| **Kaggle T4 Single** | Pending Login | 16 GB | 30 hrs/wk recurring ($0.00) | Optimal (100 GB private mount) | High (12h continuous) | Low (Jupyter / CLI) | **TERTIARY (SUSTAINED)** |
| **Kaggle T4x2 Multi**| Pending Login | 32 GB | 30 hrs/wk recurring ($0.00) | Optimal (100 GB private mount) | High (12h continuous) | Medium (torchrun DDP) | **MULTI-GPU CANDIDATE** |
| **Local RTX 3050** | Verified Active | 6 GB | Unlimited local power | Local NVMe SSD (instant) | 100% controlled | Fully operational (32.15 s/s) | **LOCAL REFERENCE / FALLBACK** |
| **Azure for Students**| Blocked Quota | 16 GB | $100 credit (0 GPU quota) | Blob Storage (~$0.95/mo) | N/A (VMs blocked) | High (Pay-As-You-Go req) | **RESERVE ONLY (NON-VIABLE)** |

============================================================
OBSERVED FACTS
============================================================

1. The local reference machine (Dell G15 5530, RTX 3050 6GB) achieves 32.15 samples/sec sustained mean post-reboot under canonical Step 2B conditions (78.05 W sustained power, 1,897.4 MHz, 82°C peak temperature, zero thermal throttling).
2. No local credentials or CLI tools exist on the development machine for Lightning AI, Kaggle, or Azure (~/.lightning, ~/.kaggle, ~/.azure absent; environment variables unset).
3. Lightning AI provides 15 to 30 free Studio credits upon registration; L4 instances cost $0.79/hr (19-38 hours compute) and T4 instances cost $0.55/hr (27-54 hours compute).
4. Lightning AI free persistent disk is capped at 10 GB; storing the 47.6 GB Trujillo dataset requires 37.6 GB of billable storage costing $3.76/month in credits.
5. Kaggle provides 30 hours per week of recurring free GPU compute (T4 and T4x2) with zero monetary cost and a 12-hour maximum execution runtime per session.
6. Kaggle provides up to 100 GB of free private dataset storage mounted read-only at /kaggle/input/ with zero runtime copy penalty to /kaggle/working.
7. Azure for Students assigns a default quota of 0 vCPUs to GPU VM families (NCasT4_v3, NCv3), and Microsoft policy blocks quota increases on student subscriptions without credit-card pay-as-you-go conversion.
8. Zero Azure credits and zero paid cloud resources were consumed during this qualification task ($0.00 spent).

============================================================
INFERENCES
============================================================

1. Kaggle represents the most operationally sustainable zero-cost training platform for Ocean Sentinel, because its 30 hours/week recurring quota never expires and its 100 GB private dataset limit natively accommodates the 47.6 GB Trujillo dataset without credit consumption or repeated uploads.
2. Lightning AI L4 represents the highest single-GPU performance potential due to 24 GB GDDR6 VRAM (enabling batch 32 vs local batch 8) and 4th Gen Ada Lovelace Tensor Cores supporting native FP16/TF32.
3. Kaggle T4x2 cannot be assumed to provide 2x throughput over single T4 because PCIe bus interconnect without NVLink imposes gradient synchronization overhead during DistributedDataParallel all-reduce steps.
4. Kaggle single T4 (Turing architecture, 8.1 FP32 TFLOPS) may not outperform the local RTX 3050 (Ampere architecture, 9.1 FP32 TFLOPS) clock-for-clock at batch 8; however, its 16 GB VRAM allows batch 16, which is expected to yield higher aggregate throughput.
5. Azure for Students is non-viable as a free GPU compute target and must remain strictly an architectural reserve.

============================================================
UNVERIFIED
============================================================

1. The exact user account credentials and active free credit balances for Lightning AI and Kaggle remain UNVERIFIED until user credential integration.
2. The empirical throughput (samples/sec) of Lightning L4, Lightning T4, Kaggle T4, and Kaggle T4x2 on the exact Ocean Sentinel graph remains UNVERIFIED until the CAO authorizes benchmark execution.
3. The real read throughput of Kaggle's virtualized /kaggle/input/ filesystem when reading 28,414 small image tiles during high-throughput training remains UNVERIFIED.
4. The exact DDP scaling efficiency of 2x T4 across virtualized PCIe on Kaggle remains UNVERIFIED.

============================================================
FINAL RECOMMENDATION
============================================================

Primary benchmark target:
    Lightning AI L4 (1x 24GB)

Secondary:
    Lightning AI T4 (1x 16GB)

Tertiary (Best Sustainable Free Target):
    Kaggle T4 Single (1x 16GB)

Multi-GPU:
    Kaggle T4x2 (2x 16GB = 32GB total VRAM via PyTorch DDP)

Reserve:
    Azure (Strict Reserve Only - 0 GPU quota on student accounts)

Local fallback:
    Dell G15 RTX 3050 6GB (authoritative baseline: 32.15 samples/sec)

Reason:
    Lightning AI L4 offers the modern Ada Lovelace architecture, 24 GB VRAM (enabling 4x larger batch size than local), and 19-38 hours of compute on free credits.
    Kaggle T4 / T4x2 provides the most reliable long-term training capacity with 30 hours/week recurring quota and a zero-cost 100 GB private dataset architecture that completely solves the 47.6 GB Trujillo storage challenge without draining credits.
    Both targets must be qualified via empirical benchmarking before making a permanent production training commitment.

============================================================
NEXT STEP
============================================================

1. Present this qualification report to the Chief Architect Officer (CAO) for review and authorization.
2. Prompt the user to provide either Kaggle API credentials (kaggle.json with phone-verified GPU access) or Lightning AI credentials (lightning login) depending on CAO prioritization.
3. Upon CAO authorization, execute the controlled Comparable (Tier A) and Capacity (Tier B) cloud benchmarks using a standardized non-training benchmark script to empirically measure throughput against the local 32.15 samples/sec reference.
4. DO NOT execute model training or benchmarks automatically.

STOP.
WAIT FOR CAO REVIEW.
