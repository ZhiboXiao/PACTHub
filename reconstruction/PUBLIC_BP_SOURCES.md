# Public BP: source-to-code map

**BP 实现说明：实际使用的内部 BP 重建程序属于保密内容，不对外分发。** 本公开包默认接入基于 Xu 和 Wang（2005）公开文献及其勘误编写的基础 UBP，保留 PAdata 和 JSON 接口，并在输出中记录公开算法的实际参数。FOV 分割与选择、声速评分与选择、信号处理、几何与 MB 实现均保留。详见 [公开 BP](PUBLIC_BP.md)、[文献来源](PUBLIC_BP_SOURCES.md) 与 [流程伪代码](PIPELINE_PSEUDOCODE.md)。

The source for this implementation is the published algorithm, not an external software repository. The Python numerical core was written for this revision.

| Source | Implemented content | Code |
|---|---|---|
| Xu & Wang (2005), Eq. (20) | `b(t) = 2[p(t) - t dp(t)/dt]` | `literature_ubp.temporal_term` |
| Eq. (21) and Sec. III | Solid-angle-normalized surface back-projection | `UBPProjector.evaluate` numerator / coverage |
| Eq. (22) | `A n·(x-s)/r³`, inward surface normal | `UBPProjector.evaluate` geometry and `omega` |
| Sec. IV, uniform sphere | Independent analytical pressure for a constant-pressure sphere | `examples/public_bp_demo.py`, `tests/test_literature_ubp.py` |
| Xu & Wang (2007), erratum | Proof corrections around Eqs. (12)–(18); implemented results unchanged | Checked against Eqs. (20)–(22) |

The following choices specify the discrete implementation: second-order finite differences, linear time interpolation, equal quadrature areas by default, zero signal outside the recording, float64 geometry and accumulation, and signed float32 output. They are documented numerical choices, not additional equations claimed from the paper.

The dataset's signal preprocessing, frame indexing, detector coordinates, physical time convention and grid are interface inputs. `bp_adapter.py` translates these from the existing PAdata / JSON contract; `literature_ubp.py` receives numerical arrays in millimetres and seconds. Geometry corrections and image-display parameters are not inferred from the UBP paper.

## Verified records

1. M. Xu and L. V. Wang. *Universal back-projection algorithm for photoacoustic computed tomography*. Physical Review E **71**, 016706 (2005). [DOI](https://doi.org/10.1103/PhysRevE.71.016706).
2. M. Xu and L. V. Wang. Erratum. Physical Review E **75**, 059903 (2007). [DOI](https://doi.org/10.1103/PhysRevE.75.059903).

The publisher DOI records, Crossref metadata and [Caltech author repository](https://authors.library.caltech.edu/records/8vsyr-zwm40) were checked on 2026-10-28. The archive provides the paper and erratum. Machine-readable citations are in `BP_REFERENCES.bib`.

## Validation basis

Analytical temporal signals, area quadrature and the paper's uniform-sphere pressure test the numerical equations. CPU/GPU comparisons test implementation consistency. The real leaf acquisition `20241115_104329` tests the existing two-JSON data interface. It is a measured-data demonstration, not an absolute-pressure calibration or proof of image-quality superiority.

The numerical core uses no private BP module or custom BP CUDA extension. Existing dataset I/O and geometry handling are reused. This is a documented literature-based rewrite; earlier code had been read during previous work in this conversation, so formal clean-room development is not asserted.
