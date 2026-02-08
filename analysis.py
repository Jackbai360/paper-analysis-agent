# 导入必要的库
import gradio as gr
import requests
import json
import os
import re
from typing import Dict, List, Tuple, Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')  # 使用非交互式后端
import io
import base64
import pdfplumber
import docx
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import uuid

# 配置DeepSeek API
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
# 请替换为您的DeepSeek API密钥
DEFAULT_API_KEY = "sk-"  # 在实际使用中请替换为您的API密钥

# 系统配置
MAX_ABSTRACT_LENGTH = 500  # 摘要最大长度
MAX_TOKENS = 2000  # 最大token数
TEMPERATURE = 0.3  # 温度参数


class LiteratureAnalyzer:
    """文献分析器类"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def extract_text_from_file(self, file_path: str) -> str:
        """从文件提取文本"""
        text = ""
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == '.pdf':
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
            elif file_extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            elif file_extension in ['.docx', '.doc']:
                doc = docx.Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            else:
                raise ValueError(f"不支持的文件格式: {file_extension}")
        except Exception as e:
            raise Exception(f"文件读取失败: {str(e)}")

        return text

    def extract_abstract(self, text: str, max_length: int = MAX_ABSTRACT_LENGTH) -> str:
        """从文本中提取摘要部分"""
        # 尝试寻找摘要部分
        abstract_patterns = [
            r"摘要[：:]\s*(.*?)(?=\n\s*(?:关键词|引言|ABSTRACT))",
            r"ABSTRACT[：:]\s*(.*?)(?=\n\s*(?:Keywords|Introduction|摘要))",
            r"Summary[：:]\s*(.*?)(?=\n\s*(?:Keywords|Introduction))",
        ]

        abstract = ""
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                break

        # 如果没有找到摘要，取前500个字符作为摘要
        if not abstract:
            abstract = text[:500].strip()

        # 限制摘要长度
        if len(abstract) > max_length:
            abstract = abstract[:max_length] + "..."

        return abstract

    def call_deepseek_api(self, prompt: str, system_prompt: str = None) -> str:
        """调用DeepSeek API"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "stream": False
        }

        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"API调用失败: {response.status_code}"
                if response.text:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', '未知错误')}"
                raise Exception(error_msg)

        except requests.exceptions.Timeout:
            raise Exception("API请求超时，请稍后重试")
        except Exception as e:
            raise Exception(f"API调用错误: {str(e)}")

    def analyze_literature(self, text: str, file_name: str) -> Dict:
        """分析文献内容"""
        # 提取摘要
        abstract = self.extract_abstract(text)

        # 系统提示词
        system_prompt = """你是一个专业的科研文献分析专家。请以结构化的方式分析科研文献，提供以下内容：
        1. 文献的基本信息（标题、作者、发表年份等）
        2. 研究框架和方法论
        3. 主要创新点和贡献
        4. 研究的不足和局限性
        5. 未来改进方向和建议
        6. 研究领域和关键词

        请确保分析专业、准确，并以结构化的JSON格式返回结果。"""

        # 用户提示词
        prompt = f"""请分析以下科研文献的摘要部分：

文献名称：{file_name}
摘要内容：{abstract}

请提供详细的分析报告，包括：
1. 文献基本信息
2. 研究框架和方法论
3. 主要创新点和贡献（至少3点）
4. 研究的不足和局限性（至少3点）
5. 未来改进方向和建议（至少3点）
6. 研究领域和关键词

请以JSON格式返回，包含以下字段：
- basic_info: 对象，包含title, authors, year, journal等字段
- framework: 字符串，描述研究框架和方法论
- innovations: 数组，每个元素是一个创新点
- limitations: 数组，每个元素是一个不足
- improvements: 数组，每个元素是一个改进方向
- fields: 数组，研究领域
- keywords: 数组，关键词
- summary: 字符串，简要总结

确保JSON格式正确，可以直接解析。"""

        # 调用API
        response = self.call_deepseek_api(prompt, system_prompt)

        # 尝试从响应中提取JSON
        try:
            # 查找JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                analysis_result = json.loads(json_str)
            else:
                # 如果没有找到JSON，创建默认结构
                analysis_result = {
                    "basic_info": {"title": file_name, "authors": "未知", "year": "未知", "journal": "未知"},
                    "framework": response[:200] + "..." if len(response) > 200 else response,
                    "innovations": ["创新点1", "创新点2", "创新点3"],
                    "limitations": ["不足1", "不足2", "不足3"],
                    "improvements": ["改进方向1", "改进方向2", "改进方向3"],
                    "fields": ["研究领域1", "研究领域2"],
                    "keywords": ["关键词1", "关键词2", "关键词3"],
                    "summary": response[:300] + "..." if len(response) > 300 else response
                }
        except json.JSONDecodeError:
            # 如果JSON解析失败，创建默认结构
            analysis_result = {
                "basic_info": {"title": file_name, "authors": "未知", "year": "未知", "journal": "未知"},
                "framework": "未能解析API响应",
                "innovations": ["创新点1", "创新点2", "创新点3"],
                "limitations": ["不足1", "不足2", "不足3"],
                "improvements": ["改进方向1", "改进方向2", "改进方向3"],
                "fields": ["研究领域1", "研究领域2"],
                "keywords": ["关键词1", "关键词2", "关键词3"],
                "summary": response[:300] + "..." if len(response) > 300 else response
            }

        # 添加摘要到结果中
        analysis_result["abstract"] = abstract

        return analysis_result

    def create_visualizations(self, analysis_result: Dict) -> Dict:
        """创建可视化图表"""
        vis_data = {}

        # 提取数据
        innovations = analysis_result.get("innovations", [])
        limitations = analysis_result.get("limitations", [])
        improvements = analysis_result.get("improvements", [])
        fields = analysis_result.get("fields", [])
        keywords = analysis_result.get("keywords", [])

        # 1. 创新点、不足和改进方向的柱状图
        fig1 = go.Figure()

        categories = ['创新点', '不足', '改进方向']
        values = [len(innovations), len(limitations), len(improvements)]

        colors = ['#2E86AB', '#A23B72', '#F18F01']

        fig1.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=values,
            textposition='auto',
        ))

        fig1.update_layout(
            title='分析结果统计',
            xaxis_title='分析类别',
            yaxis_title='数量',
            template='plotly_white',
            height=400
        )

        vis_data['bar_chart'] = fig1

        # 2. 研究领域饼状图
        if fields:
            field_counts = {}
            for field in fields:
                if field in field_counts:
                    field_counts[field] += 1
                else:
                    field_counts[field] = 1

            field_labels = list(field_counts.keys())
            field_values = list(field_counts.values())

            fig2 = go.Figure(data=[go.Pie(
                labels=field_labels,
                values=field_values,
                hole=0.3,
                marker_colors=px.colors.qualitative.Set3
            )])

            fig2.update_layout(
                title='研究领域分布',
                template='plotly_white',
                height=400
            )

            vis_data['field_pie'] = fig2

        # 3. 关键词词云数据准备
        if keywords:
            keyword_counts = {}
            for keyword in keywords:
                if keyword in keyword_counts:
                    keyword_counts[keyword] += 1
                else:
                    keyword_counts[keyword] = 1

            # 取前10个关键词
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            keyword_labels = [k[0] for k in sorted_keywords]
            keyword_values = [k[1] for k in sorted_keywords]

            # 创建水平条形图
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=keyword_values,
                y=keyword_labels,
                orientation='h',
                marker_color='#2E86AB',
                text=keyword_values,
                textposition='auto',
            ))

            fig.update_layout(
                title='关键词排名',
                xaxis_title='出现次数',
                yaxis_title='关键词',
                template='plotly_white',
                height=max(300, len(keyword_labels) * 25),  # 动态调整高度
                margin=dict(l=10, r=10, t=50, b=10)
            )

            vis_data['keyword_simple_hbar'] = fig

        # 4. 综合分析雷达图
        if innovations and limitations and improvements:
            categories = ['创新性', '完整性', '可行性', '影响力', '实用性']

            # 简单评分逻辑（实际应用中可根据具体分析调整）
            innovation_score = min(len(innovations) * 20, 100)
            limitation_score = max(100 - len(limitations) * 15, 20)
            improvement_score = min(len(improvements) * 25, 100)

            scores = [
                innovation_score,  # 创新性
                max(70, limitation_score),  # 完整性
                improvement_score,  # 可行性
                innovation_score * 0.7 + improvement_score * 0.3,  # 影响力
                improvement_score * 0.8 + innovation_score * 0.2,  # 实用性
            ]

            fig3 = go.Figure(data=go.Scatterpolar(
                r=scores,
                theta=categories,
                fill='toself',
                line_color='#2E86AB',
                fillcolor='rgba(46, 134, 171, 0.3)'
            ))

            fig3.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )
                ),
                title='文献质量综合评估',
                template='plotly_white',
                height=400,
                showlegend=False
            )

            vis_data['radar_chart'] = fig3

        return vis_data

    def generate_report(self, analysis_result: Dict, visualizations: Dict, file_name: str) -> str:
        """生成分析报告"""
        report_id = str(uuid.uuid4())[:8]
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建报告内容
        report = f"""# 科研文献分析报告
## 报告信息
- 报告ID: {report_id}
- 生成时间: {current_time}
- 分析文献: {file_name}

## 文献基本信息
"""

        basic_info = analysis_result.get("basic_info", {})
        for key, value in basic_info.items():
            report += f"- {key}: {value}\n"

        report += f"""
## 摘要
{analysis_result.get('abstract', '无摘要')}

## 研究框架和方法论
{analysis_result.get('framework', '无框架信息')}

## 主要创新点和贡献
"""

        for i, innovation in enumerate(analysis_result.get("innovations", []), 1):
            report += f"{i}. {innovation}\n"

        report += """
## 研究的不足和局限性
"""

        for i, limitation in enumerate(analysis_result.get("limitations", []), 1):
            report += f"{i}. {limitation}\n"

        report += """
## 未来改进方向和建议
"""

        for i, improvement in enumerate(analysis_result.get("improvements", []), 1):
            report += f"{i}. {improvement}\n"

        report += """
## 研究领域
"""

        for field in analysis_result.get("fields", []):
            report += f"- {field}\n"

        report += """
## 关键词
"""

        for keyword in analysis_result.get("keywords", []):
            report += f"- {keyword}\n"

        report += f"""
## 总结
{analysis_result.get('summary', '无总结信息')}

---
*本报告由星火Agent科研文献分析系统生成*
"""

        return report


def analyze_document(api_key, file_obj, use_custom_prompt, custom_prompt):
    """分析文档的主函数"""
    # 检查API密钥
    if not api_key or api_key == "your-api-key-here":
        return "请提供有效的API密钥", None, None, None, None, None, None

    # 保存上传的文件
    if file_obj is None:
        return "请上传文献文件", None, None, None, None, None, None

    file_path = file_obj.name
    file_name = os.path.basename(file_path)

    try:
        # 初始化分析器
        analyzer = LiteratureAnalyzer(api_key)

        # 提取文本
        text = analyzer.extract_text_from_file(file_path)

        if not text.strip():
            return "无法从文件中提取文本，请检查文件格式", None, None, None, None, None, None

        # 分析文献
        analysis_result = analyzer.analyze_literature(text, file_name)

        # 创建可视化
        visualizations = analyzer.create_visualizations(analysis_result)

        # 生成报告
        report = analyzer.generate_report(analysis_result, visualizations, file_name)

        # 准备输出
        basic_info = analysis_result.get("basic_info", {})
        basic_info_str = "\n".join([f"{k}: {v}" for k, v in basic_info.items()])

        framework = analysis_result.get("framework", "无框架信息")

        innovations = analysis_result.get("innovations", [])
        innovations_str = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(innovations)])

        limitations = analysis_result.get("limitations", [])
        limitations_str = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(limitations)])

        improvements = analysis_result.get("improvements", [])
        improvements_str = "\n".join([f"{i + 1}. {item}" for i, item in enumerate(improvements)])

        abstract = analysis_result.get("abstract", "无摘要信息")

        # 获取可视化图表
        bar_chart = visualizations.get('bar_chart')
        field_pie = visualizations.get('field_pie')
        radar_chart = visualizations.get('radar_chart')
        keyword_simple_hbar = visualizations.get('keyword_simple_hbar')
        return (
            "分析完成！",
            basic_info_str,
            abstract,
            framework,
            innovations_str,
            limitations_str,
            improvements_str,
            report,
            bar_chart,
            field_pie,
            radar_chart,
            keyword_simple_hbar
        )

    except Exception as e:
        error_msg = f"分析过程中出现错误: {str(e)}"
        return error_msg, None, None, None, None, None, None, None, None, None, None


def save_report(report_text):
    """保存报告到文件"""
    if not report_text:
        return "无报告可保存"

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"literature_analysis_report_{timestamp}.md"

    # 保存文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_text)
        return f"报告已保存为: {filename}"
    except Exception as e:
        return f"保存报告失败: {str(e)}"


def create_demo():
    """创建Gradio界面"""

    # 自定义CSS样式
    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: auto;
    }
    .title {
        text-align: center;
        background: linear-gradient(90deg, #2E86AB, #A23B72);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 30px;
    }
    .section {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        border-left: 5px solid #2E86AB;
    }
    .section-title {
        font-weight: bold;
        color: #2E86AB;
        margin-bottom: 10px;
    }
    .info-box {
        background-color: #e8f4fc;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 15px;
    }
    .visualization-box {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    """

    # 主题配置
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="purple",
    ).set(
        button_primary_background_fill="#2E86AB",
        button_primary_background_fill_hover="#1B6B8F",
        button_primary_text_color="white",
    )

    with gr.Blocks(theme=theme, css=custom_css) as demo:
        # 标题
        gr.Markdown("<div class='title'>基于星火Agent的科研文献分析助手</div>")
        gr.Markdown("<div class='subtitle'>上传科研文献，智能分析框架、创新点与改进方向</div>")

        with gr.Row():
            with gr.Column(scale=1):
                # API密钥输入
                gr.Markdown("### 第一步：配置API密钥")
                api_key = gr.Textbox(
                    label="API密钥",
                    value=DEFAULT_API_KEY,
                    type="password",
                    placeholder="请输入您的 API密钥"
                )

                # 文件上传
                gr.Markdown("### 第二步：上传文献文件")
                file_input = gr.File(
                    label="选择文献文件",
                    file_types=[".pdf", ".txt", ".docx", ".doc"],
                    file_count="single"
                )

                # 高级选项
                with gr.Accordion("高级选项", open=False):
                    use_custom_prompt = gr.Checkbox(label="使用自定义提示词", value=False)
                    custom_prompt = gr.Textbox(
                        label="自定义提示词",
                        placeholder="请输入自定义的分析提示词...",
                        lines=3,
                        visible=False
                    )

                    def toggle_custom_prompt(checkbox):
                        return gr.Textbox(visible=checkbox)

                    use_custom_prompt.change(
                        fn=toggle_custom_prompt,
                        inputs=use_custom_prompt,
                        outputs=custom_prompt
                    )

                # 分析按钮
                analyze_btn = gr.Button("开始分析", variant="primary", size="lg")

                # 状态显示
                status = gr.Textbox(label="分析状态", interactive=False)

            with gr.Column(scale=2):
                # 结果展示标签页
                with gr.Tabs():
                    with gr.TabItem("📊 数据看板"):
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 分析结果统计")
                                bar_chart = gr.Plot(label="柱状图")
                            with gr.Column():
                                gr.Markdown("### 研究领域分布")
                                field_pie = gr.Plot(label="饼状图")


                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 文献质量综合评估")
                                radar_chart = gr.Plot(label="雷达图")
                            with gr.Column():
                                gr.Markdown("### 关键词重要性")
                                keyword_simple_hbar = gr.Plot(label="水平图")

                    with gr.TabItem("📝 分析结果"):
                        gr.Markdown("### 文献基本信息")
                        basic_info = gr.Textbox(label="基本信息", lines=3, interactive=False)

                        gr.Markdown("### 文献摘要")
                        abstract = gr.Textbox(label="摘要", lines=4, interactive=False)

                        gr.Markdown("### 研究框架和方法论")
                        framework = gr.Textbox(label="框架", lines=4, interactive=False)

                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("### 创新点和贡献")
                                innovations = gr.Textbox(label="创新点", lines=5, interactive=False)
                            with gr.Column():
                                gr.Markdown("### 不足和局限性")
                                limitations = gr.Textbox(label="不足", lines=5, interactive=False)

                        gr.Markdown("### 改进方向和建议")
                        improvements = gr.Textbox(label="改进方向", lines=5, interactive=False)

                    with gr.TabItem("📄 完整报告"):
                        report_output = gr.Textbox(label="分析报告", lines=20, interactive=False)
                        save_btn = gr.Button("保存报告", variant="secondary")
                        save_status = gr.Textbox(label="保存状态", interactive=False)

                        # 保存报告按钮事件
                        save_btn.click(
                            fn=save_report,
                            inputs=report_output,
                            outputs=save_status
                        )

        # 分析按钮事件
        analyze_btn.click(
            fn=analyze_document,
            inputs=[api_key, file_input, use_custom_prompt, custom_prompt],
            outputs=[
                status,
                basic_info,
                abstract,
                framework,
                innovations,
                limitations,
                improvements,
                report_output,
                bar_chart,
                field_pie,
                radar_chart,
                keyword_simple_hbar

            ]
        )

        # 示例和说明
        with gr.Accordion("使用说明", open=False):
            gr.Markdown("""
            ### 使用步骤：
            1. **输入API密钥**：在左侧输入您的API密钥
            2. **上传文献**：支持PDF、TXT、DOCX、DOC格式
            3. **开始分析**：点击"开始分析"按钮，系统将自动提取摘要并进行分析
            4. **查看结果**：在右侧标签页中查看分析结果、可视化图表和完整报告

            ### 系统功能：
            - **智能摘要提取**：自动从文献中提取摘要部分（500字以内）
            - **结构化分析**：分析文献框架、创新点、不足和改进方向
            - **数据可视化**：生成柱状图、饼状图、雷达图等可视化图表
            - **报告生成**：生成完整的分析报告，支持保存为Markdown格式

            ### 注意事项：
            - 确保API密钥有效且有余额
            - 文献文件应包含摘要部分
            - 分析结果基于AI模型生成，仅供参考
            """)

    return demo


# 主程序
if __name__ == "__main__":
    # 创建Gradio应用
    demo = create_demo()

    # 启动应用
    demo.launch(
        server_name="127.0.0.1",
        server_port=7863,
        share=False,  # 设置为True可生成公共链接
        debug=False
    )