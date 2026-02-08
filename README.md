# paper-analysis-agent
The scientific literature analysis system based on Gradio uses the DeepSeek API to analyze scientific literature and offers a wide range of visualization analysis and report generation functions.
## 安装说明

在运行上述代码前，需要先安装必要的依赖库：

```bash
pip install gradio requests pandas matplotlib plotly pdfplumber python-docx
```

## 系统功能说明

### 1. **核心功能**

- **文件上传**：支持PDF、TXT、DOCX、DOC格式的科研文献
- **智能摘要提取**：自动识别并提取文献摘要部分（500字以内）
- **深度分析**：通过DeepSeek API分析文献框架、创新点、不足和改进方向
- **数据可视化**：生成多种可视化图表（柱状图、饼状图、雷达图）
- **报告生成**：生成完整的Markdown格式分析报告

### 2. **UI界面特点**

- 现代化、美观的界面设计
- 响应式布局，适合展示宣传
- 清晰的标签页组织，信息层次分明
- 自定义CSS样式，提升视觉效果

### 3. **可视化图表**

- **柱状图**：展示创新点、不足、改进方向的数量统计
- **饼状图**：展示研究领域分布
- **雷达图**：综合评估文献质量

### 4. **使用流程**

1. 输入DeepSeek API密钥
2. 上传科研文献文件
3. 点击"开始分析"按钮
4. 查看分析结果、可视化图表和完整报告
5. 可保存报告为Markdown文件

## 配置说明

1. **API密钥配置**：
   - 将代码中的`DEFAULT_API_KEY`替换为您自己的DeepSeek API密钥
   - 或直接在界面中输入API密钥

2. **服务器配置**：
   - 默认运行在`http://localhost:7860`
   - 可通过修改`server_port`参数更改端口
   - 设置`share=True`可生成公共访问链接

## 注意事项

1. 确保DeepSeek API密钥有效且有足够余额
2. 文献文件应包含可提取的文本内容
3. 分析结果基于AI模型生成，建议人工审核
4. 系统使用摘要部分进行分析，以节省token消耗
