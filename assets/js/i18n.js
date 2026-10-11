/* PACTHub bilingual interface. All content is text, never executable HTML. */
'use strict';
(() => {
  const messages = {
"overview.mouseAlt":{"zh": "项目提供的小鼠三维成像展示", "en": "Project-supplied mouse imaging visualization"},
"overview.mouseCaption":{"zh": "项目图像 · 小鼠成像", "en": "Project image · mouse imaging"},
"overview.beforeAlt":{"zh": "增强前图像局部", "en": "Detail from the before image"},
"overview.afterAlt":{"zh": "增强后图像的相同局部", "en": "Matching detail from the after image"},
"overview.compareCaption":{"zh": "项目对比图 · 同一区域局部", "en": "Project comparison · matching crops"},
"overview.leafAlt":{"zh": "项目提供的叶片样本局部", "en": "Detail from the project-supplied leaf sample"},
"overview.handAlt":{"zh": "项目提供的手部样本局部", "en": "Detail from the project-supplied hand sample"},
"overview.reuseCaption":{"zh": "样本预览 · 叶片 / 手部", "en": "Sample previews · leaf / hand"},

"enhancement.title":{"zh": "增强前后，直观对比。", "en": "Before and after, side by side."},
"enhancement.help":{"zh": "拖动中间分界线查看增强前后；也可使用方向键、Home 和 End。", "en": "Drag the divider to compare, or use the arrow keys, Home and End."},
"enhancement.slider":{"zh": "增强前后分界线", "en": "Before and after comparison divider"},
"enhancement.before":{"zh": "增强前", "en": "Before"},
"enhancement.after":{"zh": "增强后", "en": "After"},
"enhancement.gt":{"zh": "GT · 参考图像", "en": "GT · Reference"},
"enhancement.gtAlt":{"zh": "GT 参考图像，与上方保持相同方向和视野", "en": "GT reference image, matching the orientation and field of view above"},
"enhancement.note":{"zh": "项目提供图像 · 统一旋转 90° · 完整视野 · 未作额外亮度调整", "en": "Project-supplied images · Rotated 90° together · Full field of view · No added brightness adjustments"},
"enhancement.value":{"zh": "增强前 {value}%，增强后 {after}%", "en": "Before {value}%, after {after}%"},

  "sample.displayAdjusted": {"zh":"项目图像 · 展示亮度调整", "en":"Project image · display brightness adjusted"},
"sample.imageProvided":{"zh": "项目提供图像", "en": "Project-supplied image"},"sample.showOriginal":{"zh": "查看完整原图 ↗", "en": "View full original ↗"},"sample.showFramed":{"zh": "返回展示视图 ↩", "en": "Back to framed view ↩"},
  "ui.001": {
    "zh": "跳转到主要内容",
    "en": "Skip to main content"
  },
  "ui.002": {
    "zh": "菜单",
    "en": "Menu"
  },
  "ui.003": {
    "zh": "概览",
    "en": "Overview"
  },
  "ui.004": {
    "zh": "数据样本",
    "en": "Samples"
  },
  "ui.005": {
    "zh": "增强方法",
    "en": "Method"
  },
  "ui.006": {
    "zh": "论文与引用",
    "en": "Publication"
  },
  "ui.007": {
    "zh": "关于",
    "en": "About"
  },
  "ui.008": {
    "zh": "获取资源",
    "en": "Get resources"
  },
  "ui.009": {
    "zh": "三维光声断层成像",
    "en": "3D PHOTOACOUSTIC TOMOGRAPHY"
  },
  "ui.010": {
    "zh": "让三维光声数据，触手可及。",
    "en": "3D photoacoustic data,\nwithin reach."
  },
  "ui.011": {
    "zh": "连接三维数据、图像增强与可复现研究。",
    "en": "Connecting 3D data, image enhancement and reproducible research."
  },
  "ui.012": {
    "zh": "探索数据集",
    "en": "Explore the dataset"
  },
  "ui.013": {
    "zh": "了解增强方法",
    "en": "Discover the method"
  },
  "ui.014": {
    "zh": "项目提供视频 · 三维影像展示",
    "en": "Project-provided video · 3D visualization"
  },
  "ui.015": {
    "zh": "前端预览 · 研究材料待接入",
    "en": "Website preview · Research materials pending"
  },
  "ui.016": {
    "zh": "内容清单 ↗",
    "en": "Content checklist ↗"
  },
  "ui.017": {
    "zh": "向下探索",
    "en": "Explore below"
  },
  "ui.018": {
    "zh": "显示静态封面",
    "en": "Static poster displayed"
  },
  "ui.019": {
    "zh": "播放背景",
    "en": "Play background"
  },
  "ui.020": {
    "zh": "01 / 数据集",
    "en": "01 / THE DATASET"
  },
  "ui.021": {
    "zh": "一个入口，连接数据与方法。",
    "en": "One place for data and methods."
  },
  "ui.022": {
    "zh": "围绕三维光声成像，组织样本、方法与研究资料，",
    "en": "Explore 3D photoacoustic samples, methods and research resources."
  },
  "ui.023": {
    "zh": "让数据的理解、使用和引用拥有清晰的路径。",
    "en": "A clear path to understanding, using and citing the data."
  },
  "ui.024": {
    "zh": "理解数据",
    "en": "Understand the data"
  },
  "ui.025": {
    "zh": "从样本预览到采集信息，了解数据结构、空间尺度与适用场景。",
    "en": "From sample previews to acquisition details, explore data structures, spatial scales and intended use."
  },
  "ui.026": {
    "zh": "数据与背景",
    "en": "DATA & CONTEXT"
  },
  "ui.027": {
    "zh": "探索增强方法",
    "en": "Explore image enhancement"
  },
  "ui.028": {
    "zh": "连接配套图像增强算法，呈现方法思路、使用流程与评估依据。",
    "en": "Explore the accompanying enhancement method, its workflow and the basis for evaluation."
  },
  "ui.029": {
    "zh": "方法与评估",
    "en": "METHOD & EVALUATION"
  },
  "ui.030": {
    "zh": "延续研究",
    "en": "Build on the research"
  },
  "ui.031": {
    "zh": "从数据获取到文档与引用，为复现、比较和后续工作提供入口。",
    "en": "Find data access, documentation and citations for reproduction, comparison and future work."
  },
  "ui.032": {
    "zh": "获取与复现",
    "en": "ACCESS & REPRODUCIBILITY"
  },
  "ui.033": {
    "zh": "02 / 探索数据",
    "en": "02 / EXPLORE THE DATA"
  },
  "ui.034": {
    "zh": "从一个样本开始。",
    "en": "Start with a sample."
  },
  "ui.035": {
    "zh": "按类型、划分或关键词探索。",
    "en": "Explore by category, split or keyword."
  },
  "ui.036": {
    "zh": "打开样本，查看完整原图与来源记录。",
    "en": "Open a sample for the full original image and provenance."
  },
  "ui.037": {
    "zh": "全部",
    "en": "All"
  },
  "ui.038": {
    "zh": "仿体",
    "en": "Phantom"
  },
  "ui.039": {
    "zh": "仿真",
    "en": "Simulation"
  },
  "ui.040": {
    "zh": "搜索样本编号、名称或标签",
    "en": "Search sample IDs, names or tags"
  },
  "ui.041": {
    "zh": "按数据划分筛选",
    "en": "Filter by dataset split"
  },
  "ui.042": {
    "zh": "全部划分",
    "en": "All splits"
  },
  "ui.043": {
    "zh": "训练集",
    "en": "Train"
  },
  "ui.044": {
    "zh": "验证集",
    "en": "Validation"
  },
  "ui.045": {
    "zh": "测试集",
    "en": "Test"
  },
  "ui.046": {
    "zh": "未指定",
    "en": "Unspecified"
  },
  "ui.047": {
    "zh": "正在读取样本索引…",
    "en": "Loading the sample index…"
  },
  "ui.048": {
    "zh": "样本集合",
    "en": "SAMPLE COLLECTION"
  },
  "ui.049": {
    "zh": "没有匹配的样本",
    "en": "No matching samples"
  },
  "ui.050": {
    "zh": "试试其他关键词，或清除当前筛选条件。",
    "en": "Try another keyword or clear the current filters."
  },
  "ui.051": {
    "zh": "清除筛选",
    "en": "Clear filters"
  },
  "ui.052": {
    "zh": "暂时无法读取样本索引",
    "en": "The sample index could not be loaded"
  },
  "ui.053": {
    "zh": "请检查样本文件是否存在。",
    "en": "Please check that the sample file exists."
  },
  "ui.054": {
    "zh": "重新加载",
    "en": "Try again"
  },
  "ui.055": {
    "zh": "六个样本均为验证集；展示亮度适度调整，详情可查看原图。",
    "en": "All six samples are in Validation. Display brightness is gently adjusted; full originals are available in details."
  },
  "ui.056": {
    "zh": "下载样本索引",
    "en": "Download sample index"
  },
  "ui.057": {
    "zh": "03 / 图像增强",
    "en": "03 / IMAGE ENHANCEMENT"
  },
  "ui.058": {
    "zh": "让数据与方法相互连接。",
    "en": "Bring data and methods together."
  },
  "ui.059": {
    "zh": "配套图像增强算法",
    "en": "Accompanying image enhancement method"
  },
  "ui.060": {
    "zh": "从输入，到更清晰的表达。",
    "en": "From input to clearer representation."
  },
  "ui.061": {
    "zh": "围绕三维光声图像增强，集中展示方法思路、输入输出约定与可复现流程。具体方法、实验结果和使用资料将在此补充。",
    "en": "An introduction to the 3D photoacoustic image enhancement method, input/output conventions and reproducible workflow. Method details, experimental results and usage resources are pending."
  },
  "ui.062": {
    "zh": "方法资料准备中",
    "en": "Method resources in preparation"
  },
  "ui.063": {
    "zh": "代码仓库 · 待补充",
    "en": "Code repository · Pending"
  },
  "ui.064": {
    "zh": "模型权重 · 待补充",
    "en": "Model weights · Pending"
  },
  "ui.065": {
    "zh": "可复现的工作流程",
    "en": "A REPRODUCIBLE WORKFLOW"
  },
  "ui.066": {
    "zh": "输入",
    "en": "INPUT"
  },
  "ui.067": {
    "zh": "标准化数据",
    "en": "Standardized data"
  },
  "ui.068": {
    "zh": "数据结构 · 空间尺度 · 输入约定",
    "en": "Data structure · Spatial scale · Input conventions"
  },
  "ui.069": {
    "zh": "增强",
    "en": "ENHANCEMENT"
  },
  "ui.070": {
    "zh": "图像增强",
    "en": "Image enhancement"
  },
  "ui.071": {
    "zh": "方法概览 · 运行环境 · 推理流程",
    "en": "Method overview · Environment · Inference workflow"
  },
  "ui.072": {
    "zh": "评估",
    "en": "EVALUATION"
  },
  "ui.073": {
    "zh": "结果与评估",
    "en": "Results and evaluation"
  },
  "ui.074": {
    "zh": "视觉对比 · 评估协议 · 适用范围",
    "en": "Visual comparison · Evaluation protocol · Scope"
  },
  "ui.075": {
    "zh": "展示结构示意，具体流程以实际方法为准。",
    "en": "Illustrative structure only. The actual method will define the workflow."
  },
  "ui.076": {
    "zh": "04 / 研究资源",
    "en": "04 / RESOURCES"
  },
  "ui.077": {
    "zh": "研究，从这里继续。",
    "en": "Take the research further."
  },
  "ui.078": {
    "zh": "数据、示例与方法资源集中于此。",
    "en": "Find data, examples and method resources here."
  },
  "ui.079": {
    "zh": "经确认的下载入口将在资料补充后开放。",
    "en": "Verified download links will open when the materials are ready."
  },
  "ui.080": {
    "zh": "待发布",
    "en": "Not yet released"
  },
  "ui.081": {
    "zh": "数据集",
    "en": "Dataset"
  },
  "ui.082": {
    "zh": "标准化的三维光声成像数据与配套索引。",
    "en": "Standardized 3D photoacoustic imaging data and its accompanying index."
  },
  "ui.083": {
    "zh": "资料准备中",
    "en": "Resources in preparation"
  },
  "ui.084": {
    "zh": "开始之前",
    "en": "READ BEFORE YOU START"
  },
  "ui.085": {
    "zh": "先了解数据，再开始实验。",
    "en": "Understand the data before you begin."
  },
  "ui.086": {
    "zh": "数据说明",
    "en": "Data guide"
  },
  "ui.087": {
    "zh": "算法使用说明",
    "en": "Method guide"
  },
  "ui.088": {
    "zh": "元数据规范",
    "en": "Metadata schema"
  },
  "ui.089": {
    "zh": "使用前请确认适用许可、版本与引用方式。",
    "en": "Check the license, version and citation before use."
  },
  "ui.090": {
    "zh": "使用许可待补充",
    "en": "License pending"
  },
  "ui.091": {
    "zh": "05 / 论文与引用",
    "en": "05 / PUBLICATION"
  },
  "ui.092": {
    "zh": "理解工作，也让来源清晰。",
    "en": "Understand the work. Credit its source."
  },
  "ui.093": {
    "zh": "论文与相关研究",
    "en": "Publication and related research"
  },
  "ui.094": {
    "zh": "研究论文与引用",
    "en": "Research paper and citation"
  },
  "ui.095": {
    "zh": "这里将收录数据集与配套方法的正式论文、作者信息及引用方式。",
    "en": "The official dataset and method papers, author details and citation will be provided here."
  },
  "ui.096": {
    "zh": "阅读论文 · 待补充",
    "en": "Read the paper · Pending"
  },
  "ui.097": {
    "zh": "引用",
    "en": "CITATION"
  },
  "ui.098": {
    "zh": "复制引用",
    "en": "Copy citation"
  },
  "ui.099": {
    "zh": "正式引用信息将在论文资料确认后提供。",
    "en": "The official citation will be provided once publication details are confirmed."
  },
  "ui.100": {
    "zh": "暂未提供可用引用",
    "en": "No citation available yet"
  },
  "ui.101": {
    "zh": "06 / 团队与贡献",
    "en": "06 / PEOPLE & CONTRIBUTIONS"
  },
  "ui.102": {
    "zh": "共同推进，持续探索。",
    "en": "Explore further, together."
  },
  "ui.103": {
    "zh": "认识项目背后的研究者。",
    "en": "Meet the researchers behind the project."
  },
  "ui.104": {
    "zh": "让反馈与贡献拥有明确的入口。",
    "en": "Find a clear path for feedback and contributions."
  },
  "ui.105": {
    "zh": "研究团队",
    "en": "Research team"
  },
  "ui.106": {
    "zh": "由研究者，共同构建。",
    "en": "Built together by researchers."
  },
  "ui.107": {
    "zh": "团队成员、所属机构与分工将在这里介绍。",
    "en": "Team members, affiliations and roles will be introduced here."
  },
  "ui.108": {
    "zh": "参与贡献",
    "en": "Contribute"
  },
  "ui.109": {
    "zh": "为后续研究留下更多可能。",
    "en": "Make room for what comes next."
  },
  "ui.110": {
    "zh": "欢迎围绕数据使用、方法复现与文档改进提供反馈。项目联系与贡献方式将在确认后开放。",
    "en": "Feedback on data use, method reproduction and documentation is welcome. Contact and contribution details will open once confirmed."
  },
  "ui.111": {
    "zh": "联系与贡献 · 待补充",
    "en": "Contact and contribute · Pending"
  },
  "ui.112": {
    "zh": "三维光声成像 · 数据与方法",
    "en": "3D photoacoustic imaging · Data and methods"
  },
  "ui.113": {
    "zh": "网站内容清单",
    "en": "Website content checklist"
  },
  "ui.114": {
    "zh": "光声断层成像研究",
    "en": "PHOTOACOUSTIC TOMOGRAPHY RESEARCH"
  },
  "ui.115": {
    "zh": "返回顶部",
    "en": "Back to top"
  },
  "ui.116": {
    "zh": "样本详情",
    "en": "SAMPLE DETAILS"
  },
  "ui.117": {
    "zh": "索引元数据 · 无体数据附件",
    "en": "Index metadata · No volume data attached"
  },
  "ui.118": {
    "zh": "导出样本索引 ↓",
    "en": "Export sample index ↓"
  },
  "a11y.home": {
    "zh": "PACTHub 首页",
    "en": "PACTHub home"
  },
  "a11y.nav": {
    "zh": "主导航",
    "en": "Main navigation"
  },
  "a11y.categoryFilter": {
    "zh": "样本类型筛选",
    "en": "Filter by sample category"
  },
  "a11y.search": {
    "zh": "搜索样本…",
    "en": "Search samples…"
  },
  "a11y.sampleList": {
    "zh": "样本列表",
    "en": "Sample collection"
  },
  "a11y.pipeline": {
    "zh": "方法展示结构示意",
    "en": "Illustrative method workflow"
  },
  "a11y.copyCitation": {
    "zh": "复制正式引用",
    "en": "Copy the official citation"
  },
  "a11y.closeSample": {
    "zh": "关闭样本详情",
    "en": "Close sample details"
  },
  "a11y.playVideo": {
    "zh": "播放背景视频",
    "en": "Play background video"
  },
  "meta.title": {
    "zh": "PACTHub · 三维光声成像研究资源",
    "en": "PACTHub · 3D Photoacoustic Imaging Research"
  },
  "meta.description": {
    "zh": "PACTHub：三维光声成像数据、图像增强方法与研究资源的统一入口。当前为前端预览，研究内容将陆续补充。",
    "en": "PACTHub brings together 3D photoacoustic imaging data, image enhancement methods and research resources. Website preview; research materials are pending."
  },
  "a11y.language": {
    "zh": "语言",
    "en": "Language"
  },
  "missing": {
    "zh": "待填写",
    "en": "Not provided"
  },
  "phantom": {
    "zh": "仿体",
    "en": "Phantom"
  },
  "simulation": {
    "zh": "仿真",
    "en": "Simulation"
  },
  "in-vivo": {
    "zh": "在体",
    "en": "In vivo"
  },
  "ex-vivo": {
    "zh": "离体",
    "en": "Ex vivo"
  },
  "other": {
    "zh": "其他",
    "en": "Other"
  },
  "train": {
    "zh": "训练集",
    "en": "Train"
  },
  "validation": {
    "zh": "验证集",
    "en": "Validation"
  },
  "test": {
    "zh": "测试集",
    "en": "Test"
  },
  "unspecified": {
    "zh": "未指定",
    "en": "Unspecified"
  },
  "all": {
    "zh": "全部",
    "en": "All"
  },
  "video.static": {
    "zh": "显示静态封面，背景视频尚未接入。",
    "en": "Static poster displayed. No background video is configured."
  },
  "video.pause": {
    "zh": "暂停背景",
    "en": "Pause background"
  },
  "video.retry": {
    "zh": "重试播放",
    "en": "Retry playback"
  },
  "video.play": {
    "zh": "播放背景",
    "en": "Play background"
  },
  "video.pauseAria": {
    "zh": "暂停背景视频",
    "en": "Pause background video"
  },
  "video.retryAria": {
    "zh": "重新播放背景视频",
    "en": "Retry background video"
  },
  "video.playAria": {
    "zh": "播放背景视频",
    "en": "Play background video"
  },
  "video.loading": {
    "zh": "背景视频正在加载。",
    "en": "Loading the background video."
  },
  "video.blocked": {
    "zh": "自动播放未开始。可以使用播放背景按钮，或继续浏览静态封面。",
    "en": "Autoplay did not start. Use Play background or continue with the static poster."
  },
  "video.notStarted": {
    "zh": "视频尚未开始播放。可以再次点击播放背景。",
    "en": "Video playback did not start. You can try Play background again."
  },
  "video.paused": {
    "zh": "背景视频已暂停。",
    "en": "Background video paused."
  },
  "video.playing": {
    "zh": "背景视频正在播放，无声音。",
    "en": "Background video playing without sound."
  },
  "video.failed": {
    "zh": "背景视频暂不可用，已显示静态封面。可以重试播放。",
    "en": "Background video unavailable. The static poster is shown. You can retry playback."
  },
  "video.motion": {
    "zh": "已根据减少动态效果设置暂停背景视频。",
    "en": "Background video paused to respect reduced-motion preferences."
  },
  "video.preference": {
    "zh": "已按减少动态效果或节省流量设置显示静态封面，可手动播放。",
    "en": "The static poster is shown for reduced-motion or data-saving preferences. You can play the video manually."
  },
  "sample.demoAlt": {
    "zh": "{title}：抽象矢量示意，非真实扫描",
    "en": "{title}: abstract vector illustration, not a real scan"
  },
  "sample.alt": {
    "zh": "{title}预览",
    "en": "Preview of {title}"
  },
  "sample.previewError": {
    "zh": "预览暂不可用",
    "en": "Preview unavailable"
  },
  "sample.demo": {
    "zh": "示意样本",
    "en": "Demo sample"
  },
  "sample.noPreview": {
    "zh": "预览暂未提供",
    "en": "No preview provided"
  },
  "sample.voxels": {
    "zh": "体素",
    "en": "VOXELS"
  },
  "sample.detail": {
    "zh": "查看详情",
    "en": "View details"
  },
  "sample.detailAria": {
    "zh": "查看 {id} {title} 详情",
    "en": "View details for {id} {title}"
  },
  "sample.count": {
    "zh": "显示 {count} / {total} 个样本",
    "en": "Showing {count} of {total} samples"
  },
  "sample.demoMetadata": {
    "zh": "示意样本 · 合成元数据",
    "en": "Demo sample · Synthetic metadata"
  },
  "sample.category": {
    "zh": "样本类型",
    "en": "Sample category"
  },
  "sample.split": {
    "zh": "数据划分",
    "en": "Dataset split"
  },
  "sample.dimensions": {
    "zh": "数组维度 / voxels",
    "en": "Array dimensions / voxels"
  },
  "sample.axes": {
    "zh": "轴顺序",
    "en": "Axis order"
  },
  "sample.spacing": {
    "zh": "体素间距 / mm（与轴顺序一致）",
    "en": "Voxel spacing / mm (in axis order)"
  },
  "sample.wavelength": {
    "zh": "激发波长 / nm",
    "en": "Excitation wavelength / nm"
  },
  "sample.intensity": {
    "zh": "强度单位",
    "en": "Intensity unit"
  },
  "sample.version": {
    "zh": "数据版本",
    "en": "Data version"
  },
  "sample.provenance": {
    "zh": "来源与处理记录",
    "en": "Provenance and processing"
  },
  "sample.source": {
    "zh": "公开来源编号",
    "en": "Public source ID"
  },
  "sample.acquisition": {
    "zh": "采集",
    "en": "Acquisition"
  },
  "sample.reconstruction": {
    "zh": "重建",
    "en": "Reconstruction"
  },
  "sample.standardization": {
    "zh": "现有标准化说明",
    "en": "Existing standardization reference"
  },
  "sample.files": {
    "zh": "样本文件",
    "en": "Sample files"
  },
  "sample.noFiles": {
    "zh": "尚未接入任何体数据文件或下载链接。",
    "en": "No volume data files or download links are available yet."
  },
  "sample.exportDemo": {
    "zh": "导出示意索引 ↓",
    "en": "Export demo index ↓"
  },
  "sample.export": {
    "zh": "导出样本索引 ↓",
    "en": "Export sample index ↓"
  },
  "sample.fileCount": {
    "zh": "已接入 {count} 个文件链接",
    "en": "{count} file links available"
  },
  "sample.metadataOnly": {
    "zh": "索引元数据 · 无体数据附件",
    "en": "Index metadata · No volume data attached"
  },
  "resource.pending": {
    "zh": "{label} · 待补充",
    "en": "{label} · Pending"
  },
  "resource.repository": {
    "zh": "代码仓库",
    "en": "Code repository"
  },
  "resource.weights": {
    "zh": "模型权重",
    "en": "Model weights"
  },
  "resource.available": {
    "zh": "可访问",
    "en": "Available"
  },
  "resource.unreleased": {
    "zh": "待发布",
    "en": "Not yet released"
  },
  "resource.version": {
    "zh": "版本 / {version}",
    "en": "VERSION / {version}"
  },
  "resource.download": {
    "zh": "访问下载",
    "en": "Open download"
  },
  "resource.preparing": {
    "zh": "资料准备中",
    "en": "Resources in preparation"
  },
  "resource.paper": {
    "zh": "阅读论文",
    "en": "Read the paper"
  },
  "resource.contribute": {
    "zh": "联系与贡献",
    "en": "Contact and contribute"
  },
  "citation.ready": {
    "zh": "使用本资源时，请引用对应版本。",
    "en": "Please cite the corresponding version when using this resource."
  },
  "citation.copied": {
    "zh": "已复制引用。",
    "en": "Citation copied."
  },
  "citation.selected": {
    "zh": "已选中引用，请使用系统复制快捷键或长按复制。",
    "en": "Citation selected. Use your system copy shortcut or long-press to copy."
  },
  "citation.unavailable": {
    "zh": "暂未提供可用引用",
    "en": "No citation available yet"
  },
  "license.named": {
    "zh": "许可 / {license}",
    "en": "License / {license}"
  },
  "license.pending": {
    "zh": "使用许可待补充",
    "en": "License pending"
  },
  "load.loading": {
    "zh": "正在读取索引…",
    "en": "Loading the index…"
  },
  "load.failed": {
    "zh": "索引读取失败",
    "en": "Index could not be loaded"
  },
  "load.detail": {
    "zh": "无法读取 data/samples.json（{reason}）。本地预览请在项目根目录运行 python3 -m http.server 8000，再打开 http://localhost:8000。",
    "en": "Could not load data/samples.json ({reason}). For a local preview, run python3 -m http.server 8000 from the project root, then open http://localhost:8000."
  },
  "load.invalid": {
    "zh": "索引结构不符合要求",
    "en": "Invalid index structure"
  },
  "load.general": {
    "zh": "文件不可用或 JSON 格式错误",
    "en": "File unavailable or invalid JSON"
  },
  "config.warning": {
    "zh": "网站配置未加载，当前显示默认占位信息。请检查 data/site-config.json。",
    "en": "Site configuration could not be loaded. Default placeholder content is shown. Please check data/site-config.json."
  },
  "meta.suffix": {
    "zh": "三维光声成像研究资源",
    "en": "3D Photoacoustic Imaging Research"
  },
  "offline.doc": {
    "zh": "离线文档",
    "en": "Offline documentation"
  },
  "offline.close": {
    "zh": "关闭文档",
    "en": "Close document"
  },
  "offline.overline": {
    "zh": "PACTHUB / 使用说明",
    "en": "PACTHUB / DOCUMENTATION"
  }
};
  const storageKey = 'pacthub-language';
  let language = 'en';
  try { const saved = window.localStorage.getItem(storageKey); if (saved === 'zh' || saved === 'en') language = saved; } catch { /* Private browsing/file URLs may deny storage. */ }
  const localize = (value) => {
    if (typeof value === 'string') return value;
    if (!value || typeof value !== 'object' || Array.isArray(value)) return '';
    for (const key of [language, 'zh', 'en']) if (typeof value[key] === 'string' && value[key].trim()) return value[key];
    return '';
  };
  function t(key, params = {}) {
    const text = localize(messages[key]) || key;
    return text.replace(/\{(\w+)\}/g, (match, name) => Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match);
  }
  function apply(root = document) {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    const select = (selector) => [ ...(root.matches?.(selector) ? [root] : []), ...root.querySelectorAll(selector) ];
    select('[data-i18n]').forEach((el) => {
      if (!messages[el.dataset.i18n]) return;
      let params = {}; try { params = JSON.parse(el.getAttribute('data-i18n-params') || '{}'); } catch { /* Treat invalid params as absent. */ }
      el.textContent = t(el.dataset.i18n, params);
    });
    for (const attr of ['aria-label', 'title', 'placeholder', 'content', 'alt']) {
      select(`[data-i18n-${attr}]`).forEach((el) => {
        const key = el.getAttribute(`data-i18n-${attr}`);
        if (messages[key]) el.setAttribute(attr, t(key));
      });
    }
    select('[data-language]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.language === language));
    });
  }
  function setLanguage(next) {
    if (next !== 'zh' && next !== 'en') return;
    try { window.localStorage.setItem(storageKey, next); } catch { /* Choice still works for this page. */ }
    if (next === language) return;
    language = next; apply();
    document.dispatchEvent(new CustomEvent('pact:languagechange', { detail: { language } }));
  }
  function register(zh, en) {
    for (const key of new Set([...Object.keys(zh), ...Object.keys(en)])) messages[key] = { zh: zh[key], en: en[key] };
    apply();
  }
  window.PACTI18N = { get language() { return language; }, t, localize, setLanguage, register, apply };
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-language]');
    if (button) setLanguage(button.dataset.language);
  });
  apply();
})();
