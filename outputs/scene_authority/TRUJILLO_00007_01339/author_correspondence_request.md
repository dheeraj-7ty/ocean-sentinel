# Primary Author Correspondence Request: Sentinel-1 SAFE Scene Identification & Duplicate Clarification

**To**: Rubicel Trujillo-Acatitla, José Tuxpan-Vargas, Cesaré Ovando-Vázquez, Erandi Monterrubio-Martínez  
**Reference Dataset**: *Sentinel-1 SAR Oil spill image dataset for train, validate, and test deep learning models* (Zenodo DOIs: 10.5281/zenodo.8346860, 10.5281/zenodo.8253899, 10.5281/zenodo.13761290)  
**Reference Publication**: *Marine oil spill detection and segmentation in SAR data with two steps Deep Learning framework*, Marine Pollution Bulletin 204 (2024) 116549  
**Subject**: Primary Forensics Inquiry & SAFE Identification: Duplicate Image Rasters (00007.tif & 01339.tif) with Differing Masks  

---

Dear Dr. Trujillo-Acatitla and Co-Authors,

We are conducting scientific verification and reproducible evaluations utilizing your published Sentinel-1 SAR Oil Spill dataset. During rigorous forensic audit of the raster data, our verification team established a material finding regarding files `00007.tif` and `01339.tif`:

1. **Byte-for-Byte Identical Image Rasters**:
   - `data/raw/trujillo_2024/images/Oil/00007.tif` and `data/raw/trujillo_2024/images/Oil/01339.tif` are 100% byte-for-byte identical (file size: `41,857,591` bytes; canonical SHA-256: `927b382ebffc2f84447a17b80b30e6c3f1f6758fcb8d6e7a13e7c4de70932405`).
   - Their raster arrays are bitwise equal (`np.array_equal` returns True across all bands and pixels).

2. **Divergent Annotation Masks**:
   - Despite sharing identical source imagery, their corresponding annotation masks in `masks/Mask_oil/` differ significantly:
     - `00007.tif` mask has `70,772` positive oil spill pixels (SHA-256: `4d2638e21b23f84e733fd1fcd7ee43290297a01dc8d7523407a0b2c765ab4866`).
     - `01339.tif` mask has `74,906` positive oil spill pixels (SHA-256: `81ed3665ce12bb82bc269a4d57cb8488a513efe17d8e6b9586c5058b2dff76d8`).
     - Absolute pixel difference between the masks is `5,058` pixels.

3. **Scientific Implication**:
   - Because the underlying radar rasters are identical ($T_0 \equiv T_1$), `00007` and `01339` cannot be interpreted as a physical temporal SAR observation sequence without primary author clarification. Any apparent difference between them is an annotation variance / labeling difference, not physical SAR change over time.

To resolve dataset provenance and ensure proper scientific use, we kindly request your guidance on the following questions:

1. **Underlying Acquisition**: Do `00007.tif` and `01339.tif` intentionally represent the exact same underlying Sentinel-1 SAR acquisition (e.g. independently annotated duplicate samples or cross-split evaluation replicates)?
2. **Original SAFE Product ID & Timestamp**: What is the original Copernicus Sentinel-1 SAFE/product identifier and exact acquisition timestamp (UTC) for this shared SAR image?
3. **Master Patch-to-Source Mapping**: Is a master index or cross-reference table available that maps patch filenames to source Sentinel-1 SAFE granules, relative orbits, pass directions, and acquisition timestamps?
4. **Distinct Multi-Temporal Pairs**: Could you identify one or more pairs of image patches in the dataset known by the authors to originate from genuinely distinct Sentinel-1 acquisitions over the same geographic footprint, suitable for valid temporal change analysis?

Thank you very much for your time, foundational dataset contribution, and assistance.

Sincerely,  
Ocean Sentinel Research & Verification Team  
