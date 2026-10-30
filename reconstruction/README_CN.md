# PA 数据集标准处理与 BP／MB 重建

本程序直接使用公开数据集已经整理的 **`sample_metadata.json` 与 `reconstruction_parameters.json`**。保留原有 `schema_version=1.0.0` 和 `defaults` 字段结构，并兼容带内嵌逐帧配准的 `1.0.0+starnet-rigid-v3`。

流程为：**PAdata → 参数与数组检查 → 预处理及选帧 → FOV 选择 → 声速选择 → BP／MB → 三维体、MIP 与生效参数**。数据目录叫 `PA`、`PA_Data` 或其他名称均可，程序按 JSON 中的路径读取。

**BP 实现说明：实际使用的内部 BP 重建程序属于保密内容，不对外分发。** 本公开包默认接入基于 Xu 和 Wang（2005）公开文献及其勘误编写的基础 UBP，保留 PAdata 和 JSON 接口，并在输出中记录公开算法的实际参数。FOV 分割与选择、声速评分与选择、信号处理、几何与 MB 实现均保留。详见 [公开 BP](PUBLIC_BP.md)、[文献来源](PUBLIC_BP_SOURCES.md) 与 [流程伪代码](PIPELINE_PSEUDOCODE.md)。

## 1. 输入文件和参数来源

| 文件 | 用途 | 读取约定 |
|---|---|---|
| `sample_metadata.json` | 采集编号、日期、信号存储轴、实际形状、数据类型、总帧数 | 与信号数组和另一份 JSON 交叉核对 |
| `reconstruction_parameters.json` | 信号、帧号、几何、网格、声速、FOV、投影与算法参数 | **唯一的计算参数入口** |
| `PA/…_PA.mat` 或 `.h5` | 标准化 PA 测量数据 | HDF5 变量 `pa_data`，物理存储为 `[frame,time,channel]`，当前为 1024 通道 |
| `Calibration/…_detector.mat` | 1024×3 探测器坐标，单位 mm | 现有公开参数通过 `inputs.detector_file` 引用；也可内嵌至参数 JSON |

公开版移除了旧实现的 `inputs.entrypoint`。本接口在验证标准 PA 输入后于内存中适配该实现标记，原 JSON 不需要增加这一字段。`inputs.pa_files` 和 `acquisition_groups[].pa_file` 均相对所属参数 JSON 解析；不会从目录名推断波长、角度、声速或曝光数。

**严格两份参数文件的方式：**将坐标写入 `defaults.geometry.detector_xyz_mm`，同时令 `inputs.detector_file=null`。这样一次重建只需 PA 数据与这两个 JSON。坐标仍依次应用原 JSON 的符号、偏移和旋转，不能把已经旋转后的坐标再当作基坐标写入。

## 2. 每一步读取哪些字段

| 阶段 | 既有参数字段 | 执行内容 |
|---|---|---|
| 输入 | `inputs.pa_variable`、`pa_files`、`selected_group_id`、`acquisition_groups` | 唯一确定当前采集对应的 PA 数据 |
| 选帧 | `defaults.frames.indices_1based`、`count` | 保留原始 1-based 帧号和指定顺序；旋转角仍使用原帧号 |
| 信号处理 | `defaults.signal` | 按记录执行带通、极性、能量归一化、时间截取及可选解析信号 |
| 时钟 | `sampling_frequency_hz`、`predelay_samples`、`time_samples_1based` | 保留原有截取后时钟约定；不额外叠加截取偏移 |
| 探测器几何 | `defaults.geometry` | 坐标单位、轴符号、基坐标偏移、基旋转、逐帧旋转、附加 Z 旋转 |
| 帧配准 | `frame_registration.transforms` | 同时变换探测器位置与物理接收方向；使用 JSON 内嵌的 R、t |
| FOV | `defaults.grid`、`defaults.fov_detection` | 使用记录的物理网格，或在大视场 BP 上估计中心与长轴 |
| 声速 | `defaults.reconstruction.single_speed_m_s`、`sweep_m_s`、`defaults.speed_selection` | 记录声速重建，或固定数据和几何扫描候选声速 |
| BP | `defaults.reconstruction` | 公开 UBP 使用线性时间插值、几何立体角权重与有符号输出，实际选项写入输出参数 |
| MB | **新增 `defaults.mb`** | 有限圆盘前向／伴随模型、匹配 FIR、迭代与正则化参数 |
| 输出 | `defaults.projection`、`defaults.output.save_volume` | 原单位浮点三维体、指定 Z 支撑的 XY-MIP、坐标轴与预览 |

网格保留原来的采样约定：默认点数为 `round(FOV×resolution)`，端点包含在网格内；源程序型 `source_intervals_plus_one` 使用区间数加一。两个规则不能互换。修改中心、范围或密度后，程序重算派生的 `shape_xyz` 和 `extent_xyz_mm`。

## 3. 使用入口

安装基础依赖：`pip install -r requirements.txt`。公开 UBP 支持 NumPy CPU 与 CuPy CUDA（默认）；CPU 使用 `--backend cpu`。MB 需要 CUDA PyTorch、Ninja 和 nvcc。

先检查已经下载的采集文件夹：

```bash
python reconstruct.py inspect "/data/2024/2024-12-13/20241213_151351"
```

从原 JSON 读取采集参数并调用公开 UBP：

```bash
python reconstruct.py run "/data/2024/2024-12-13/20241213_151351" --methods bp --out runs/BP_recorded --device 0
```

生成含坐标与 MB 配置的新参数副本，然后运行 BP、MB：

```bash
python reconstruct.py configure "/data/2024/2024-12-13/20241213_151351" --out profiles/mouse --embed-detectors --with-mb
python reconstruct.py run profiles/mouse --methods bp mb --out runs/BP_MB --device 0
```

将 FOV 和声速选择接入同一流程：

```bash
python reconstruct.py configure "/data/2024/2024-12-13/20241213_151351" --out profiles/mouse_auto --embed-detectors --with-mb --auto-fov --auto-speed
python reconstruct.py run profiles/mouse_auto --methods bp mb --out runs/full_pipeline --device 0
```

`configure` 只生成新的两份 JSON，不复制 PA 数据，也不改原始文件。所有物理参数在生成的 `reconstruction_parameters.json` 中编辑。命令行只选择输入／输出位置、执行方法、CPU／GPU 后端及设备。

## 4. FOV 选择

`fov_detection.enabled=false` 时，直接采用 `grid` 中已确认的中心和范围。开启时，用 `large_space_mm`、`large_resolution_px_mm` 和参考声速计算大视场 BP，随后调用既有的局部对比度、血管连续性与 PCA 长轴算法。

`reference_speed_m_s=null` 表示使用该采集已记录的声速。大视场原点由记录中心变换回未附加 Z 旋转的坐标系，或由同区段的 `large_center_mm` 显式提供。自动结果中的旋转同时作用于探测器几何与重建中心；输出图像本身不通过二维旋转代替重建。

新增 `fov_detection.apply_to_run` 控制是否应用候选几何。结构超出目标视场、方向不稳定或触及搜索边界时，保留原参数并在结果中列出原因。算法从 XY-MIP 估计 XY 中心与长轴，Z 中心沿用参数。分割副本使用原有 4σ／最多 1% 上尾处理，不改变用于 BP／MB 的 RF 或重建体。`target_space_mm` 来自当前 JSON，不固定成某一个样本的尺寸。

## 5. 声速选择

候选值直接来自 `reconstruction.sweep_m_s`。整个扫描保持帧号、几何、预处理、Z 范围与显示前强度一致，评分使用完整浮点 MIP。保留旧参数中命名的两个方法：`full_global_normalized_gradient` 和 `morphology_v2`。评分函数沿用既有非学习实现。

新增 `speed_selection.apply_method` 指定本次执行采用哪一个方法的有效候选；为 null 时只输出候选。`--auto-speed` 将其写为 `full_global_normalized_gradient`。边界峰、并列峰或证据不足时继续使用已记录声速，并记录状态。`automatic_speed_writeback` 保持 false；选定的本次有效声速写入结果下的新参数副本，原始文件不变。

可在该区段设置 `resolution_px_mm`，用于声速扫描网格；省略时使用最终重建网格。该值同样取自参数 JSON。选择的是重建的有效声速，不是组织声速分布图。

## 6. MB 配置及与 BP 的关系

公开的旧版 JSON 尚无 MB 区段。`--with-mb` 在同一个文件中增加下列完整配置，数值来自此前提供的 V3 基础配置：

```json
"mb": {
  "sensor_radius_mm": 1.75,
  "radial_order": 3,
  "angular_order": 16,
  "fir_order": 128,
  "fir_beta": 8.0,
  "mask_first_samples": 0,
  "matched_channel_demean": false,
  "iterations": 5,
  "power_iterations": 2,
  "l1_relative": 0.02,
  "tv_relative": 0.005,
  "l2_relative": 0.003,
  "sensor_batch_size": 1024
}
```

此配置放在 `defaults` 内。1.75 mm 为该 V3 配置的接收器半径；更换探测器时应据实修改，不能从坐标球面半径推算。迭代次数和正则化强度是明确写出的基础配置，不代表逐样本调优结果。

MB 使用提供代码中的有限圆盘 CUDA 前向／伴随算子和非负迭代求解。目标函数包含数据一致性、L1、TV 与 L2 项。信号使用原 JSON 的频带，但通过匹配的有限长 FIR 进入数据和前向模型；不会读取另一个 FIR／EIR 参数文件。当前已发布参数均为单声速，本入口对应单声速 MB。

选择 `--methods bp mb` 时导出以下三类结果。BP_matched 同样使用公开 UBP：

| 结果目录 | 含义 |
|---|---|
| `BP/` | 原 JSON 的 Butterworth／能量归一化／截取顺序，调用公开 UBP |
| `MB/` | 同一采集、帧号、几何、FOV 与声速，使用匹配 FIR 的 MB |
| `BP_matched/` | 与 MB **完全相同的预处理 RF、FIR 和支持掩膜**进行 BP，用于直接比较算法 |

接入 BP 与 MB 可能具有不同的算子幅值约定；各自输出保持浮点数值，预览 PNG 的亮度归一化不回写到定量体。

仅运行 MB：

```bash
python reconstruct.py run profiles/mouse --methods mb --out runs/MB --device 0
```

自动 FOV 与声速选择默认由公开 UBP 生成候选重建。

## 7. 输出与再次运行

`profile/` 只含本次有效的两份 JSON，路径重新相对该文件夹表示；FOV／声速选择已关闭，直接复用选定结果。通过 `python reconstruct.py run runs/full_pipeline/profile ...` 可再次执行同样参数。

每种重建保存 `mip.npz`、`xymip.png`、参数与计时；`save_volume=true` 时保存 `volume.h5`。体数据轴顺序为 **ZYX**，MIP 为 **YX**，`axis_x/y/z` 单位 mm。MB 另存迭代残差和目标函数。选择阶段保留大视场、候选声速 MIP、分割支撑与选择记录。输出的诊断 JSON 是运行产物，不是后续执行必须另外读取的参数文件。

## 8. 当前数据覆盖和需要补充的内容

本地公开包审计包含 1,469 个采集：WXH 840、MF 468、HH 146、StarNet 10、20261014 连续采集 5。**1,327 个采集的现有参数通过接口结构检查；142 个仍保留原发布文件的暂缓重建状态。** 程序不会用其他样本的声速或几何填补它们。

扫描数据在公开包中按采集位置分别发布；当前入口对每个位置执行同一 BP／MB 流程。全扫描拼接需要所有位置的位移、顺序与融合窗。这些内容应内嵌到同一个 `reconstruction_parameters.json` 的 `scan` 区段；仅有某一位置的两份 JSON 时，不从时间编号猜测轨迹。

现阶段必须补充或确认的是：

1. **探测器坐标**：使用公共 Calibration 文件，或通过 `--embed-detectors` 内嵌。下载数据时同时取得该采集引用的实际 Calibration 文件；也可使用已经内嵌坐标的参数副本。
2. **MB 区段**：按上述方式写入旧版参数文件；不增加第三份 options 文件。
3. **142 个暂缓采集**：补齐原参数缺项并解除其对应的 hold，才能纳入可运行样本。

本地验证覆盖公开 UBP 的解析球体、插值、权重、CPU/CUDA 一致性，以及 PAdata/JSON、几何、MB 输入与公开 UBP 回放；见 `validation_report.json`。完整分辨率由每个采集的 `grid` 原参数决定。
