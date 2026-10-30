/* PACTHub bilingual interface. All content is text, never executable HTML. */
'use strict';
(() => {
  const messages = {
  "resource.reconstructionTitle": {
    "zh": "BP / MB 重建流程",
    "en": "BP / MB reconstruction"
  },
  "resource.reconstructionDescription": {
    "zh": "从 PAdata 出发，完成 FOV、声速选择与三维重建；沿用每个采集的两份 JSON 参数。",
    "en": "From PAdata to FOV and sound-speed selection, BP and MB volumes, using each acquisition’s two JSON files."
  },
  "resource.reconstructionDownload": {
    "zh": "下载重建代码 ↓",
    "en": "Download reconstruction code ↓"
  },
  "pub.title": {
    "zh": "数据背后的研究。",
    "en": "The research behind the data."
  },
  "pub.intro": {
    "zh": "从全景成像、全身解剖到生物过程追踪，阅读相关研究并获取引文。",
    "en": "Three papers on panoramic imaging, whole-body anatomy and longitudinal biological applications."
  },
  "pub.preview": {
    "zh": "查看论文首页",
    "en": "View first page"
  },
  "pub.read": {
    "zh": "阅读原文",
    "en": "Read article"
  },
  "pub.copy": {
    "zh": "复制引用",
    "en": "Copy citation"
  },
  "pub.citation": {
    "zh": "完整引文",
    "en": "Full citation"
  },
  "pub.copied": {
    "zh": "引文已复制",
    "en": "Citation copied"
  },
  "pub.selected": {
    "zh": "引文已选中，可按 Ctrl+C 复制",
    "en": "Citation selected. Press Ctrl+C to copy."
  },
  "pub.credit": {
    "zh": "论文首页版权归各论文作者所有。",
    "en": "Article first pages © their respective authors."
  },
  "pub.all": {
    "zh": "下载全部引文",
    "en": "Download all citations"
  },
  "pub.close": {
    "zh": "关闭论文首页",
    "en": "Close article preview"
  },
  "pub.zoom": {
    "zh": "论文首页 · 点击图片放大",
    "en": "Article first page · Click the page to enlarge"
  },
  "pub.fit": {
    "zh": "点击图片恢复全页视图",
    "en": "Click the page to fit the full page"
  },
  "pub.toggleZoom": {
    "zh": "放大或恢复论文首页",
    "en": "Enlarge or fit article first page"
  },
  "pub.topic.panopact": {
    "zh": "3D-PanoPACT",
    "en": "3D-PanoPACT"
  },
  "pub.topic.panopaus": {
    "zh": "3D-PanoPAUS",
    "en": "3D-PanoPAUS"
  },
  "pub.topic.liver": {
    "zh": "肝再生追踪",
    "en": "Liver regeneration"
  },
  "q.measured": {
    "zh": "06 · 小鼠实例",
    "en": "06 · Measured mouse"
  },
  "q.captionLabel": {
    "zh": "视频字幕",
    "en": "Video captions"
  },
  "q.play": {
    "zh": "播放",
    "en": "Play"
  },
  "q.pause": {
    "zh": "暂停",
    "en": "Pause"
  },
  "q.restart": {
    "zh": "重新播放 ↺",
    "en": "Restart ↺"
  },
  "q.timeline": {
    "zh": "Q 视频进度",
    "en": "Q video timeline"
  },
  "q.mouseValues": {
    "zh": "小鼠计算数值 ↗",
    "en": "Mouse values ↗"
  },
  "resource.drive": {
    "zh": "打开 Google Drive ↗",
    "en": "Open Google Drive ↗"
  },
  "overview.space": {
    "zh": "结构 / 空间",
    "en": "STRUCTURE / SPACE"
  },
  "overview.time": {
    "zh": "信号 / 时间",
    "en": "SIGNAL / TIME"
  },
  "overview.workflow": {
    "zh": "重建 / 评测",
    "en": "RECONSTRUCT / EVALUATE"
  },
  "film.alt": {
    "zh": "扫描加旋转小鼠：三维旋转、全身视角与细血管局部",
    "en": "Scan and rotation mouse: 3D orbit, whole-body view and vascular detail"
  },
  "film.specimen": {
    "zh": "扫描 + 旋转",
    "en": "SCAN + ROTATION"
  },
  "film.chapters": {
    "zh": "选择视频阶段",
    "en": "View video stages"
  },
  "film.orbit": {
    "zh": "三维旋转",
    "en": "3D orbit"
  },
  "film.whole": {
    "zh": "全身视角",
    "en": "Whole body"
  },
  "film.detail": {
    "zh": "细血管局部",
    "en": "Vessel detail"
  },
  "film.play": {
    "zh": "播放小鼠展示视频",
    "en": "Play the specimen film"
  },
  "film.pause": {
    "zh": "暂停小鼠展示视频",
    "en": "Pause the specimen film"
  },
  "film.replay": {
    "zh": "重新播放小鼠展示视频",
    "en": "Replay the specimen film"
  },
  "film.timeline": {
    "zh": "视频进度",
    "en": "Video timeline"
  },
  "zoom.open": {
    "zh": "放大查看 ↗",
    "en": "Enlarge image ↗"
  },
  "zoom.close": {
    "zh": "关闭放大视图",
    "en": "Close enlarged view"
  },
  "zoom.in": {
    "zh": "放大",
    "en": "Zoom in"
  },
  "zoom.out": {
    "zh": "缩小",
    "en": "Zoom out"
  },
  "zoom.reset": {
    "zh": "适应窗口",
    "en": "Fit to window"
  },
  "zoom.hint": {
    "zh": "滚轮缩放 · 拖动查看 · 双击放大 / 复位 · Esc 返回",
    "en": "Scroll to zoom · Drag to pan · Double-click to zoom / reset · Esc to return"
  },
  "gallery.legend": {
    "zh": "相对深度",
    "en": "Relative depth"
  },
  "gallery.legendNote": {
    "zh": "代表样本 / 统一视图",
    "en": "Representative specimens / Consistent views"
  },
  "sample.displayAdjusted": {
    "zh": "项目图像 · 展示亮度调整",
    "en": "Project image · display brightness adjusted"
  },
  "sample.imageProvided": {
    "zh": "项目提供图像",
    "en": "Project-supplied image"
  },
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
    "zh": "动态成像",
    "en": "Applications"
  },
  "ui.006": {
    "zh": "论文与引用",
    "en": "Publications"
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
    "zh": "三维光声数据，\n触手可及",
    "en": "3D photoacoustic data,\nwithin reach."
  },
  "hero.statistics": {
    "zh": "数据规模与人工智能数据底座",
    "en": "Dataset scale and AI foundation"
  },
  "hero.samples": {
    "zh": "样本",
    "en": "Samples"
  },
  "hero.exposures": {
    "zh": "曝光",
    "en": "Exposures"
  },
  "hero.foundation": {
    "zh": "数据底座",
    "en": "Data foundation"
  },
  "hero.foundationLink": {
    "zh": "了解人工智能数据底座与完整重建流程",
    "en": "Explore the AI data foundation and reconstruction pipeline"
  },
  "ui.011": {
    "zh": "标准化 PAdata、统一 JSON 参数接口与完整重建流程，连接数据准备、模型开发和定量评测。",
    "en": "Standardized PAdata, a unified JSON parameter interface and a complete pipeline connect data preparation, model development and quantitative evaluation."
  },
  "ui.012": {
    "zh": "探索数据集",
    "en": "Explore the dataset"
  },
  "ui.013": {
    "zh": "探索完整流程",
    "en": "Explore the pipeline"
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
    "zh": "01 / 数据特性",
    "en": "01 / DATA CHARACTERISTICS"
  },
  "ui.021": {
    "zh": "看见成像过程。",
    "en": "See imaging in action."
  },
  "ui.022": {
    "zh": "从全身覆盖到细血管分支，",
    "en": "Whole-body coverage. Fine vascular detail."
  },
  "ui.023": {
    "zh": "让空间结构与时间变化一同呈现。",
    "en": "Spatial structure, followed through time."
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
    "zh": "按样本类型或采集方式浏览，切换三维、深度和灰度视图。",
    "en": "Browse specimens and switch between 3D, depth and intensity views."
  },
  "ui.036": {
    "zh": "统一深度配色，查看灰度与三维视图。",
    "en": "One depth palette. Explore intensity and 3D views."
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
    "zh": "筛选采集模式",
    "en": "Filter by acquisition mode"
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
    "zh": "颜色表示深度，灰度表示强度。",
    "en": "Colour encodes depth; grayscale shows intensity."
  },
  "ui.056": {
    "zh": "下载样本索引",
    "en": "Download sample index"
  },
  "ui.076": {
    "zh": "05 / 资源",
    "en": "05 / RESOURCES"
  },
  "ui.077": {
    "zh": "研究，从这里继续。",
    "en": "Take the research further."
  },
  "ui.078": {
    "zh": "获取数据与重建代码。",
    "en": "Download the data and reconstruction code."
  },
  "ui.079": {
    "zh": "代表性样本已存档于 Zenodo。",
    "en": "Representative samples are archived on Zenodo."
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
    "zh": "重建流程",
    "en": "Reconstruction guide"
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
    "zh": "06 / 论文",
    "en": "06 / PUBLICATIONS"
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
    "zh": "数据集、基准评测及重建流程的论文与引用信息。",
    "en": "Publication and citation information for the dataset, benchmark and reconstruction pipelines."
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
    "zh": "07 / 团队与贡献",
    "en": "07 / PEOPLE & CONTRIBUTIONS"
  },
  "ui.102": {
    "zh": "团队与联系",
    "en": "Team & contact"
  },
  "ui.103": {
    "zh": "研究团队与交流。",
    "en": "Research team and contact."
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
    "zh": "研究团队",
    "en": "Research team"
  },
  "ui.107": {
    "zh": "团队信息待补充。",
    "en": "Team details will be added here."
  },
  "ui.108": {
    "zh": "贡献",
    "en": "Contribute"
  },
  "ui.109": {
    "zh": "联系与反馈",
    "en": "Contact & feedback"
  },
  "ui.110": {
    "zh": "通过 GitHub Issues 反馈数据和使用问题。",
    "en": "Share data and usage feedback through GitHub Issues."
  },
  "ui.111": {
    "zh": "联系与贡献 · 待补充",
    "en": "Contact and contribute · Pending"
  },
  "ui.112": {
    "zh": "三维光声成像 · Benchmark + Pipeline",
    "en": "3D photoacoustic imaging · Benchmark + Pipeline"
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
    "zh": "PACTHub：面向光声人工智能的结构化数据基座，提供统一 JSON 参数接口、FOV 与声速选择、BP / MB 重建和定量评测。",
    "en": "PACTHub: a structured data foundation for photoacoustic AI, with a unified JSON parameter interface, FOV and sound-speed selection, BP / MB reconstruction and quantitative evaluation."
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
    "zh": "采集编号",
    "en": "Acquisition ID"
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
  },
  "animal": {
    "zh": "动物",
    "en": "Animal"
  },
  "human": {
    "zh": "人手",
    "en": "Human hand"
  },
  "rotation": {
    "zh": "旋转",
    "en": "Rotation"
  },
  "scan": {
    "zh": "扫描 + 旋转",
    "en": "Scan + rotation"
  },
  "all-modes": {
    "zh": "全部采集模式",
    "en": "All acquisition modes"
  },
  "view.depth": {
    "zh": "深度编码",
    "en": "Depth MIP"
  },
  "view.gray": {
    "zh": "灰度强度",
    "en": "Intensity MIP"
  },
  "view.volume": {
    "zh": "三维视图",
    "en": "3D view"
  },
  "sample.mode": {
    "zh": "采集模式",
    "en": "Acquisition mode"
  },
  "sample.viewNote": {
    "zh": "灰度为强度，颜色为相对深度。三维视图使用斜向最大强度投影。",
    "en": "Grayscale represents intensity; colour represents relative depth. The 3D view uses oblique maximum-intensity ray casting."
  },
  "overview.oneTitle": {
    "zh": "血管结构，跨越尺度",
    "en": "Vascular structure, across scales"
  },
  "overview.oneText": {
    "zh": "从全身结构逐步放大，观察细小血管分支。",
    "en": "Explore whole-body anatomy down to fine vascular branches."
  },
  "overview.twoTitle": {
    "zh": "沿时间，观察变化",
    "en": "Follow change over time"
  },
  "overview.twoText": {
    "zh": "连续成像记录同一位置的信号变化。",
    "en": "Follow changes in the same anatomy over time."
  },
  "overview.threeTitle": {
    "zh": "从数据到重建",
    "en": "From data to reconstruction"
  },
  "overview.threeText": {
    "zh": "统一 JSON 参数连接 PAdata、三维重建与定量评估。",
    "en": "One JSON interface connects PAdata, 3D reconstruction and evaluation."
  },
  "temporal.eyebrow": {
    "zh": "03 / 连续成像",
    "en": "03 / TEMPORAL IMAGING"
  },
  "temporal.title": {
    "zh": "让变化，随时间展开。",
    "en": "Watch the signal unfold."
  },
  "temporal.intro": {
    "zh": "框选位置，查看信号随时间的变化。",
    "en": "Select a region to follow its signal over time."
  },
  "temporal.series": {
    "zh": "成像序列",
    "en": "Image sequence"
  },
  "temporal.unit": {
    "zh": "强度读数",
    "en": "Intensity readout"
  },
  "temporal.relative": {
    "zh": "相对首帧",
    "en": "Relative to first frame"
  },
  "temporal.linear": {
    "zh": "配准后 BP 均值",
    "en": "Registered BP mean"
  },
  "temporal.image": {
    "zh": "成像",
    "en": "Imaging"
  },
  "temporal.traces": {
    "zh": "强度曲线",
    "en": "Intensity traces"
  },
  "temporal.frame": {
    "zh": "时间点",
    "en": "Timepoint"
  },
  "temporal.play": {
    "zh": "播放",
    "en": "Play"
  },
  "temporal.pause": {
    "zh": "暂停",
    "en": "Pause"
  },
  "temporal.restart": {
    "zh": "回到开始",
    "en": "Restart"
  },
  "temporal.speed": {
    "zh": "播放速度",
    "en": "Playback speed"
  },
  "temporal.scrub": {
    "zh": "逐帧浏览时间序列",
    "en": "Scrub through measured timepoints"
  },
  "temporal.relativeAxis": {
    "zh": "相对强度 I(t) / I(0)",
    "en": "Relative intensity I(t) / I(0)"
  },
  "temporal.linearAxis": {
    "zh": "BP 区域均值 / a.u.",
    "en": "Mean BP intensity / a.u."
  },
  "temporal.timeAxis": {
    "zh": "时间 / min",
    "en": "Time / min"
  },
  "temporal.chartAlt": {
    "zh": "用户框选区域在各采样时刻的平均强度曲线",
    "en": "Mean intensity over time for user-selected image regions"
  },
  "temporal.region": {
    "zh": "区域",
    "en": "Region"
  },
  "temporal.summary": {
    "zh": "{frames} 个时间点 · {minutes} min",
    "en": "{frames} timepoints · {minutes} min"
  },
  "temporal.note": {
    "zh": "区域均值来自配准后的 BP MIP，相对强度为 I(t)/I(0)。",
    "en": "Traces use mean intensity from registered BP MIPs; relative intensity is I(t)/I(0)."
  },
  "temporal.csv": {
    "zh": "下载区域强度 CSV",
    "en": "Download intensity CSV"
  },
  "temporal.metadata": {
    "zh": "查看时序元数据",
    "en": "View sequence metadata"
  },
  "temporal.loading": {
    "zh": "正在加载连续成像…",
    "en": "Loading measured image sequences…"
  },
  "temporal.error": {
    "zh": "时序数据未加载，请刷新页面重试。",
    "en": "Could not load the image sequences. Refresh to retry."
  },
  "pipeline.eyebrow": {
    "zh": "04 / BENCHMARK + PIPELINE",
    "en": "04 / BENCHMARK + PIPELINE"
  },
  "pipeline.title": {
    "zh": "结构化数据，\n为人工智能设计数据底座。",
    "en": "Structured data.\nA foundation for AI."
  },
  "pipeline.input": {
    "zh": "结构化输入",
    "en": "Structured inputs"
  },
  "pipeline.inputText": {
    "zh": "通过统一 JSON 参数读取 PAdata。",
    "en": "Load PAdata through a unified JSON interface."
  },
  "pipeline.recon": {
    "zh": "参数驱动重建",
    "en": "Reconstruction"
  },
  "pipeline.reconText": {
    "zh": "选择视野与声速，运行 BP 或 MB。",
    "en": "Select the FOV and sound speed, then run BP or MB."
  },
  "pipeline.eval": {
    "zh": "定量评估",
    "en": "Quantitative evaluation"
  },
  "pipeline.evalText": {
    "zh": "输出三维体与 MIP，并计算图像质量指标。",
    "en": "Export 3D volumes and MIPs, then measure image quality."
  },
  "q.kicker": {
    "zh": "结构质量 · 逐步计算",
    "en": "STRUCTURE, STEP BY STEP"
  },
  "q.title": {
    "zh": "Q 是如何计算的",
    "en": "How Q is calculated."
  },
  "q.intro": {
    "zh": "从结构对比到真实小鼠，完整展示 Q 的计算与应用。",
    "en": "From controlled structures to a measured mouse: follow the calculation and application of Q in one sequence."
  },
  "q.videoAlt": {
    "zh": "Q 计算过程：结构区域、重叠计算与真实小鼠实例",
    "en": "Q calculation, from structural support to a measured-mouse example"
  },
  "q.chapters": {
    "zh": "视频章节",
    "en": "Video chapters"
  },
  "q.pair": {
    "zh": "01 · 输入对比",
    "en": "01 · Pair"
  },
  "q.contrast": {
    "zh": "02 · 局部对比度",
    "en": "02 · Contrast"
  },
  "q.support": {
    "zh": "03 · 结构区域",
    "en": "03 · Support"
  },
  "q.overlap": {
    "zh": "04 · 重叠计算",
    "en": "04 · Overlap"
  },
  "q.complement": {
    "zh": "05 · 指标互补",
    "en": "05 · Complement"
  },
  "q.note": {
    "zh": "使用论文中的血管模拟体和真实小鼠，在三维体中计算。Q 补充 PSNR、全图 SSIM 和 L1。",
    "en": "Calculated in 3D using the manuscript’s vascular control and measured mouse. Q complements PSNR, full-image SSIM and L1."
  },
  "q.values": {
    "zh": "计算参数与数值 ↗",
    "en": "Calculation and values ↗"
  },
  "q.download": {
    "zh": "下载视频 ↓",
    "en": "Download video ↓"
  },
  "q.mouseKicker": {
    "zh": "小鼠实例 / 16 秒",
    "en": "MEASURED MOUSE / 16 SECONDS"
  },
  "q.mouseTitle": {
    "zh": "在真实小鼠上计算 Q。",
    "en": "Q on a real mouse."
  },
  "q.mouseIntro": {
    "zh": "GT → 局部背景 → 正对比度 → 弱／强结构 → 待评估图像的重叠计算。",
    "en": "GT → local background → positive contrast → weak / strong support → test-image overlap."
  },
  "q.mouseAlt": {
    "zh": "真实小鼠的 Q 计算过程",
    "en": "Measured mouse Q calculation"
  },
  "q.mouseNote": {
    "zh": "使用论文中的小鼠三维体。待评估图像与 GT 对比，Q = 82.53。",
    "en": "The manuscript mouse volume, calculated in 3D. Test image versus GT: Q = 82.53."
  },
  "sample.displaySpacing": {
    "zh": "显示网格 / mm（校准值）",
    "en": "Display grid / mm (calibrated)"
  },
  "sample.releaseId": {
    "zh": "官方发布编号",
    "en": "Official release ID"
  },
  "sample.officialRelease": {
    "zh": "3D-PanoPACT 官方数据",
    "en": "3D-PanoPACT official data"
  },
  "single": {
    "zh": "单次曝光",
    "en": "Single exposure"
  },
  "sample.volumeArray": {
    "zh": "原始三维数组 / HDF5 维度",
    "en": "Source 3D array / HDF5 dimensions"
  },
  "temporal.drawHint": {
    "zh": "拖动框选，可移动位置或调整大小。",
    "en": "Draw a region, then move or resize it."
  },
  "temporal.loadingMips": {
    "zh": "正在加载定量 MIP…",
    "en": "Loading quantitative MIPs…"
  },
  "temporal.preparing": {
    "zh": "正在准备实时区域计算…",
    "en": "Preparing real-time region measurements…"
  },
  "temporal.dataError": {
    "zh": "定量 MIP 加载失败，请刷新页面重试。",
    "en": "Quantitative MIPs could not load. Refresh to retry."
  },
  "temporal.limit": {
    "zh": "最多同时比较 6 个区域；删除一个后可继续添加。",
    "en": "Compare up to 6 regions. Remove one to add another."
  },
  "temporal.empty": {
    "zh": "在左侧图像框选一个区域",
    "en": "Draw a region on the image"
  },
  "temporal.noValues": {
    "zh": "等待有效区域读数",
    "en": "Waiting for valid region measurements"
  },
  "temporal.examples": {
    "zh": "示例区域",
    "en": "Example regions"
  },
  "temporal.clear": {
    "zh": "清空选框",
    "en": "Clear regions"
  },
  "temporal.remove": {
    "zh": "删除区域",
    "en": "Remove region"
  },
  "temporal.hide": {
    "zh": "隐藏曲线",
    "en": "Hide trace"
  },
  "temporal.show": {
    "zh": "显示曲线",
    "en": "Show trace"
  },
  "film.collection": {
    "zh": "流程演示视频",
    "en": "Workflow videos"
  },
  "film.github": {
    "zh": "在 GitHub 打开重建代码下载页面",
    "en": "Open the reconstruction download on GitHub"
  },
  "film.openCalibration": {
    "zh": "播放完整的 FOV 与声速选择视频",
    "en": "Play the complete FOV and sound-speed video"
  },
  "film.openQ": {
    "zh": "播放完整的 Q 计算视频",
    "en": "Play the complete Q calculation video"
  },
  "film.calibrationAlt": {
    "zh": "实测 BP 候选重建及声速聚焦评分曲线",
    "en": "Measured BP candidates and sound-speed focus curve"
  },
  "film.qAlt": {
    "zh": "Q 视频第一帧：线状仿体的配对比较",
    "en": "First frame of the Q video: paired line-phantom comparison"
  },
  "film.calibrationTitle": {
    "zh": "视野与声速选择",
    "en": "FOV & sound-speed selection"
  },
  "film.method": {
    "zh": "重建流程",
    "en": "RECONSTRUCTION"
  },
  "film.benchmark": {
    "zh": "定量评测",
    "en": "BENCHMARK"
  },
  "film.calibrationIntro": {
    "zh": "展示视野定位、方向校正与声速选择。",
    "en": "Follow FOV positioning, orientation and sound-speed selection."
  },
  "film.qIntro": {
    "zh": "从线条仿体到小鼠血管，演示 Q 的计算。",
    "en": "Follow the Q calculation from a line phantom to mouse vessels."
  },
  "film.calibrationNote": {
    "zh": "同一采集的 20 帧 BP；所有声速在确定后的 40 × 80 × 20 mm FOV 内重建，统一使用 −12.145° Z 轴校正与显示窗。",
    "en": "20-exposure BP from one acquisition. Every speed is reconstructed on the final 40 × 80 × 20 mm FOV with the same −12.145° Z correction and display window."
  },
  "film.close": {
    "zh": "关闭视频",
    "en": "Close video"
  },
  "film.videoAlt": {
    "zh": "完整流程视频",
    "en": "Full workflow video"
  },
  "film.fullscreen": {
    "zh": "全屏",
    "en": "Full screen"
  },
  "film.captionLoading": {
    "zh": "正在加载章节与字幕…",
    "en": "Loading chapters and captions…"
  },
  "film.captionUnavailable": {
    "zh": "字幕暂时不可用，可继续观看视频。",
    "en": "Captions are unavailable; video playback remains available."
  },
  "film.locate": {
    "zh": "01 · 视野定位",
    "en": "01 · Locate"
  },
  "film.orient": {
    "zh": "02 · 候选方向",
    "en": "02 · Orient"
  },
  "film.sweep": {
    "zh": "03 · 声速扫描",
    "en": "03 · Sweep"
  },
  "film.select": {
    "zh": "04 · 评分选速",
    "en": "04 · Select"
  },
  "github.pipeline": {
    "zh": "流程代码",
    "en": "Pipeline code"
  },
  "github.scope": {
    "zh": "FOV · 声速 · BP · MB",
    "en": "FOV · Sound speed · BP · MB"
  },
  "github.resourcesKicker": {
    "zh": "代码与文档",
    "en": "CODE & DOCUMENTATION"
  },
  "github.resourcesTitle": {
    "zh": "在 GitHub 获取完整 workflow。",
    "en": "Get the workflow on GitHub."
  },
  "github.resourcesDescription": {
    "zh": "统一参数接口、处理代码与使用说明。",
    "en": "A shared parameter interface, processing code and guide."
  },
  "github.open": {
    "zh": "访问 GitHub",
    "en": "Open GitHub"
  },
  "foundation.nav": {
    "zh": "重建流程",
    "en": "Pipeline"
  },
  "foundation.data": {
    "zh": "结构化数据",
    "en": "Structured data"
  },
  "foundation.json": {
    "zh": "统一 JSON 接口",
    "en": "Unified JSON interface"
  },
  "foundation.pipeline": {
    "zh": "完整 pipeline",
    "en": "Complete pipeline"
  },
  "foundation.lede": {
    "zh": "统一 JSON 参数连接 PAdata、BP／MB 重建与定量评测，为 AI 研究提供可复用的数据与流程。",
    "en": "A unified JSON interface connects PAdata, BP / MB reconstruction and quantitative evaluation for reusable AI research workflows."
  },
  "foundation.sample": {
    "zh": "采集编号 · 存储轴 · 数据形状",
    "en": "Acquisition ID · storage axes · shape"
  },
  "foundation.params": {
    "zh": "几何 · FOV · 声速 · BP / MB 设置",
    "en": "Geometry · FOV · sound speed · BP / MB settings"
  },
  "foundation.preprocess": {
    "zh": "参数核对与信号预处理",
    "en": "Validation & preprocessing"
  },
  "foundation.fov": {
    "zh": "FOV 选择",
    "en": "FOV selection"
  },
  "foundation.speed": {
    "zh": "声速选择",
    "en": "Sound-speed selection"
  },
  "foundation.volume": {
    "zh": "三维体 + 物理坐标",
    "en": "3D volumes + physical coordinates"
  },
  "foundation.effective": {
    "zh": "保留有效参数与处理记录",
    "en": "Effective parameters & processing records"
  },
  "foundation.metrics": {
    "zh": "定量评测",
    "en": "Quantitative evaluation"
  },
  "foundation.q": {
    "zh": "Q 补充结构质量评价",
    "en": "Q complements structural assessment"
  },
  "foundation.benefit": {
    "zh": "连接数据与 AI 研究",
    "en": "CONNECT DATA TO AI RESEARCH"
  },
  "foundation.batch": {
    "zh": "批量数据准备",
    "en": "Batch data preparation"
  },
  "foundation.reproduce": {
    "zh": "可复现重建",
    "en": "Reproducible reconstruction"
  },
  "foundation.benchmark": {
    "zh": "统一方法评测",
    "en": "Consistent benchmarking"
  },
  "resource.zenodo": {
    "zh": "打开 Zenodo ↗",
    "en": "Open Zenodo ↗"
  },
  "cite.kicker": {
    "zh": "使用与引用",
    "en": "USE & CITATION"
  },
  "cite.title": {
    "zh": "使用数据集，请引用",
    "en": "Using the dataset? Please cite."
  },
  "cite.intro": {
    "zh": "请引用 Zenodo 数据记录及发布后的数据集论文。",
    "en": "Please cite the Zenodo record and the dataset paper when available."
  },
  "cite.data": {
    "zh": "01 / 数据记录",
    "en": "01 / DATA RECORD"
  },
  "cite.subset": {
    "zh": "代表性样本集",
    "en": "Representative sample subset"
  },
  "cite.record": {
    "zh": "查看数据记录",
    "en": "View data record"
  },
  "cite.copy": {
    "zh": "复制引用",
    "en": "Copy citation"
  },
  "cite.paper": {
    "zh": "02 / 数据集论文",
    "en": "02 / DATASET PAPER"
  },
  "cite.paperTitle": {
    "zh": "PACTHub 数据集论文",
    "en": "PACTHub dataset paper"
  },
  "cite.forthcoming": {
    "zh": "待发布",
    "en": "Forthcoming"
  },
  "cite.paperDescription": {
    "zh": "介绍数据集、统一参数接口与 benchmark + pipeline。",
    "en": "The dataset, unified parameter interface and benchmark + pipeline."
  },
  "cite.paperPending": {
    "zh": "论文发布后将在此补充 arXiv 链接与引文。",
    "en": "The arXiv link and citation will be added here on publication."
  },
  "cite.readPaper": {
    "zh": "阅读数据集论文",
    "en": "Read dataset paper"
  },
  "cite.license": {
    "zh": "Zenodo 样本集采用 CC BY 4.0；其他资源的许可见各自发布页面。",
    "en": "The Zenodo subset is licensed under CC BY 4.0. Other resources carry the terms stated on their release pages."
  },
  "params.representative": {
    "zh": "代表字段 · 可点击展开",
    "en": "SELECTED FIELDS · CLICK TO EXPLORE"
  },
  "params.inputs": {
    "zh": "数据入口",
    "en": "Data input"
  },
  "params.signal": {
    "zh": "信号与选帧",
    "en": "Signal & frames"
  },
  "params.grid": {
    "zh": "物理空间",
    "en": "Physical space"
  },
  "params.recon": {
    "zh": "重建算法",
    "en": "Reconstruction"
  },
  "params.sample": {
    "zh": "示例采集",
    "en": "Example acquisition"
  },
  "params.hint": {
    "zh": "点击左侧参数组，查看字段与处理过程的对应。",
    "en": "Select a parameter group to see how its fields drive processing."
  },
  "params.workflow": {
    "zh": "同一接口，接入完整流程",
    "en": "ONE INTERFACE · COMPLETE PROCESS"
  },
  "params.prepare": {
    "zh": "读取 PAdata",
    "en": "Read PAdata"
  },
  "params.signalStep": {
    "zh": "预处理与选帧",
    "en": "Preprocess & select frames"
  },
  "params.fovStep": {
    "zh": "选择 FOV",
    "en": "Select FOV"
  },
  "params.speedStep": {
    "zh": "选择声速",
    "en": "Select sound speed"
  },
  "params.runStep": {
    "zh": "BP / MB 重建",
    "en": "BP / MB reconstruction"
  },
  "params.outputs": {
    "zh": "三维体 · MIP · 生效参数",
    "en": "3D volumes · MIPs · effective parameters"
  },
  "params.configure": {
    "zh": "01 / 准备配置",
    "en": "01 / CONFIGURE"
  },
  "params.configureText": {
    "zh": "沿用采集参数，接入自动 FOV、声速选择及 MB。",
    "en": "Use the acquisition settings; enable FOV / sound-speed selection and MB."
  },
  "params.run": {
    "zh": "02 / 运行",
    "en": "02 / RUN"
  },
  "params.runText": {
    "zh": "切换重建方法，数据入口和参数接口保持一致。",
    "en": "Switch reconstruction methods through the same data and parameter interface."
  },
  "params.copy": {
    "zh": "复制命令",
    "en": "Copy commands"
  },
  "params.both": {
    "zh": "BP + MB",
    "en": "BP + MB"
  },
  "params.methodLabel": {
    "zh": "选择示例重建方法",
    "en": "Select the example reconstruction method"
  },
  "params.inputTitle": {
    "zh": "从字段定位到数值数组",
    "en": "Fields locate the numerical array"
  },
  "params.inputText": {
    "zh": "pa_files 定位 PA 文件，pa_variable 指定其中的数组。文件路径相对参数 JSON 解析，采集更换后仍使用同一读取接口。",
    "en": "pa_files locates the PA file; pa_variable identifies its array. Paths resolve relative to the parameter JSON, so acquisitions share one loading interface."
  },
  "params.signalTitle": {
    "zh": "选哪些信号，使用哪些曝光",
    "en": "Select the signals and exposures"
  },
  "params.signalText": {
    "zh": "signal 定义采样与带通，frames 保留原始帧号。示例明确选择 50 帧中的 20 帧，同一组信号进入后续重建。",
    "en": "signal defines sampling and filtering; frames retains original frame indices. This example explicitly selects 20 of 50 exposures for reconstruction."
  },
  "params.gridTitle": {
    "zh": "参数直接定义三维物理空间",
    "en": "Parameters define the physical 3D grid"
  },
  "params.gridText": {
    "zh": "space_mm 定义视场，center_mm 定位中心，shape_xyz 记录网格点数。geometry 记录 Z 轴方向修正。",
    "en": "space_mm sets the field of view, center_mm locates its centre, and shape_xyz records the grid size. geometry carries the Z-axis orientation correction."
  },
  "params.reconTitle": {
    "zh": "共享几何与声速，选择 BP 或 MB",
    "en": "Shared geometry and sound speed; BP or MB"
  },
  "params.reconText": {
    "zh": "reconstruction 定义声速和 BP 参数；mb 在同一文件中提供模型与求解器设置。两种方法共用采集、帧号、FOV 和声速。",
    "en": "reconstruction defines sound speed and BP settings; mb provides model and solver settings in the same file. Both methods share the acquisition, frames, FOV and sound speed."
  },
  "params.stored": {
    "zh": "实际存储数组 · F × T × C",
    "en": "STORED ARRAY · F × T × C"
  },
  "params.frames": {
    "zh": "帧",
    "en": "frames"
  },
  "params.time": {
    "zh": "采样点",
    "en": "time samples"
  },
  "params.channels": {
    "zh": "通道",
    "en": "channels"
  },
  "params.band": {
    "zh": "带通范围",
    "en": "PASSBAND"
  },
  "params.frameSelect": {
    "zh": "选择帧",
    "en": "SELECTED FRAMES"
  },
  "params.xyz": {
    "zh": "X × Y × Z · mm",
    "en": "X × Y × Z · mm"
  },
  "params.voxels": {
    "zh": "网格点",
    "en": "grid points"
  },
  "params.gridSchematic": {
    "zh": "物理网格示意",
    "en": "PHYSICAL GRID SCHEMATIC"
  },
  "params.shared": {
    "zh": "同一采集 · 帧号 · FOV · 声速",
    "en": "SAME ACQUISITION · FRAMES · FOV · SOUND SPEED"
  },
  "params.bpModel": {
    "zh": "加权反投影",
    "en": "Weighted backprojection"
  },
  "params.mbModel": {
    "zh": "有限圆盘模型",
    "en": "Finite-disk model"
  },
  "params.bpPost": {
    "zh": "有符号复合 → 非负截断",
    "en": "Signed compound → nonnegative"
  },
  "params.mbReg": {
    "zh": "数据一致性 + L1 / TV / L2",
    "en": "Data consistency + L1 / TV / L2"
  },
  "params.loading": {
    "zh": "正在载入参数示例…",
    "en": "Loading the parameter example…"
  },
  "params.error": {
    "zh": "参数示例暂时无法载入，请刷新页面。",
    "en": "The parameter example could not be loaded. Please refresh the page."
  },
  "params.copied": {
    "zh": "命令已复制",
    "en": "Commands copied"
  },
  "params.selected": {
    "zh": "命令已选中，可直接复制",
    "en": "Commands selected; copy the selected text"
  },
  "workflow.demo": {
    "zh": "参数如何驱动处理",
    "en": "PARAMETERS IN MOTION"
  },
  "workflow.signal": {
    "zh": "带通滤波",
    "en": "Bandpass filter"
  },
  "workflow.frames": {
    "zh": "曝光选择",
    "en": "Exposure selection"
  },
  "workflow.grid": {
    "zh": "生成三维网格",
    "en": "Build the 3D grid"
  },
  "workflow.geometry": {
    "zh": "位置与方向",
    "en": "Position & orientation"
  },
  "workflow.play": {
    "zh": "播放",
    "en": "Play"
  },
  "workflow.pause": {
    "zh": "暂停",
    "en": "Pause"
  },
  "workflow.restart": {
    "zh": "重新播放",
    "en": "Replay"
  },
  "workflow.timeline": {
    "zh": "流程动画进度",
    "en": "Workflow animation timeline"
  },
  "workflow.framesUnit": {
    "zh": "帧",
    "en": "frames"
  },
  "workflow.origin": {
    "zh": "初始位置",
    "en": "Initial position"
  },
  "workflow.pose": {
    "zh": "目标位置",
    "en": "Target position"
  },
  "workflow.position": {
    "zh": "位置",
    "en": "Position"
  },
  "workflow.orientation": {
    "zh": "方向",
    "en": "Orientation"
  },
  "workflow.schematic": {
    "zh": "参数示意",
    "en": "PARAMETER SCHEMATIC"
  },
  "workflow.loading": {
    "zh": "正在载入流程动画…",
    "en": "Loading the workflow animation…"
  },
  "workflow.error": {
    "zh": "流程动画暂时无法载入，请刷新重试。",
    "en": "The workflow could not be loaded. Refresh to try again."
  },
  "workflow.jump": {
    "zh": "播放此步骤",
    "en": "Play this step"
  },
  "workflow.hz": {
    "zh": "频率 / MHz",
    "en": "Frequency / MHz"
  },
  "workflow.auto": {
    "zh": "流程演示",
    "en": "Workflow playback"
  },
  "workflow.interactive": {
    "zh": "点击参数，重播对应操作",
    "en": "Select a parameter to replay its operation"
  },
  "workflow.skip": {
    "zh": "直接交互",
    "en": "Explore parameters"
  },
  "workflow.replayAll": {
    "zh": "重播完整流程",
    "en": "Replay full workflow"
  },
  "workflow.full": {
    "zh": "完整参数 · 可展开与滚动",
    "en": "FULL PARAMETERS · EXPAND & SCROLL"
  },
  "sample.candidateIds": {
    "zh": "候选数据集采集 ID",
    "en": "Candidate dataset acquisition IDs"
  },
  "library.structure.title": {
    "en": "Structure, in detail",
    "zh": "看见结构细节"
  },
  "library.structure.text": {
    "en": "From the whole volume to fine vascular branches.",
    "zh": "从完整三维体，逐步放大至细小血管。"
  },
  "library.motion.title": {
    "en": "Anatomy in motion",
    "zh": "捕捉生理动态"
  },
  "library.motion.text": {
    "en": "Grayscale and depth views follow the same motion.",
    "zh": "灰度与深度编码，同步呈现生理运动。"
  },
  "library.rotation.title": {
    "en": "Rotation compounding",
    "zh": "旋转复合"
  },
  "library.rotation.text": {
    "en": "A leaf, reconstructed from 1 to 20 exposures.",
    "zh": "从 1 到 20 次曝光，看叶脉结构逐步呈现。"
  },
  "library.temporal.title": {
    "en": "Follow the signal",
    "zh": "追踪时序变化"
  },
  "library.temporal.text": {
    "en": "Imaging and regional intensity evolve together.",
    "zh": "成像与区域强度曲线，随时间同步演化。"
  },
  "library.measure": {
    "en": "Measure your own region",
    "zh": "框选区域，查看曲线"
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
