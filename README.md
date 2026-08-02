# 经济增长因素跨国研究

## 研究问题

各国长期人均 GDP 增长率差异的决定因素是什么？本项目采用 Barro 型条件收敛框架，构建 1960–2019 年全球跨国面板，系统检验初始收入水平、人力资本、物质资本投资、制度质量、贸易开放度及地理禀赋等因素对经济增长的影响。

## 研究设计

- **模型框架**：条件收敛增长回归（Barro 1991; Barro & Sala-i-Martin 2004）
- **被解释变量**：人均 GDP 增长率（5 年非重叠平均）
- **面板结构**：5 年期，1960–2019，共 12 期
- **样本范围**：全球全样本，人口 >= 100 万且覆盖 >= 6 期
- **估计方法**：面板 OLS + 固定效应 + 系统 GMM（稳健性）

## 数据来源

| 来源 | 变量 | 覆盖 |
|------|------|------|
| Penn World Table 10.01 | GDP、人口、投资率、TFP、人力资本指数 | 1950–2019 |
| Barro-Lee v3.0 | 受教育年限（5 年间隔） | 1950–2040（含预测） |
| Polity5 | 民主程度（polity2） | 1800–2018 |
| WGI | 法治指数 | 1996–2022 |
| WDI | 通胀、预期寿命、生育率、城市化、债务 | 1960–2022 |
| CEPII GeoDist | 内陆国、纬度 | 截面 |

## 目录结构

```
经济增长因素/
├── README.md
├── data/
│   ├── raw/                  # 各来源原始下载文件
│   └── processed/            # 清洗合并后的分析数据
├── code/
│   ├── 01_download_pwt.py
│   ├── 02_download_barro_lee.py
│   ├── 03_download_polity5.py
│   ├── 04_download_wdi.py
│   ├── 05_geo_data.py
│   ├── 06_merge_panel.py
│   └── 07_summary_stats.py
├── literature/               # 文献笔记
├── output/
│   ├── tables/
│   └── figures/
└── paper/                    # 论文草稿
```

## 运行说明

环境要求 Python 3.10+，安装依赖：

```bash
pip install pandas numpy wbdata pyreadstat openpyxl requests
```

按编号顺序运行脚本：

```bash
python code/01_download_pwt.py
python code/02_download_barro_lee.py
python code/03_download_polity5.py
python code/04_download_wdi.py
python code/05_geo_data.py
python code/06_merge_panel.py
python code/07_summary_stats.py
```
