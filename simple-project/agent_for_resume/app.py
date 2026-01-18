#!/usr/bin/env python3
"""
简历模板知识库 - Web 界面
基于 Streamlit 的可视化界面，支持三种检索模式切换
"""
import os
import streamlit as st
import pandas as pd

# 配置页面
st.set_page_config(
    page_title="简历模板知识库",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="expanded"
)

# 取消代理设置（避免 API 调用问题）
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    if proxy_var in os.environ:
        del os.environ[proxy_var]

# 导入 agent 模块
from resume_agent import ResumeTemplateAgent, Config
from resume_agent.strategies import StrategyFactory


def get_all_templates():
    """获取所有模板列表"""
    try:
        df = pd.read_excel(
            os.path.join(os.path.dirname(__file__), "9b1af114-6719-4148-8194-412b68c0d44d-tmp.xlsx")
        )
        return df
    except Exception as e:
        return None


def search_with_mode(query: str, mode: str) -> str:
    """
    使用指定模式进行搜索

    Args:
        query: 搜索查询
        mode: 检索模式 (fuzzy/vector/hybrid)

    Returns:
        格式化的搜索结果
    """
    try:
        config = Config()
        strategy = StrategyFactory.create_strategy(mode, config)
        result = strategy.search(query)

        if not result.matches:
            df = get_all_templates()
            if df is not None:
                available = "\n".join([f"- {t}" for t in df['问题'].tolist()])
                return f"""抱歉，未找到"{query}"相关的简历模板。

目前可用的简历模板包括：
{available}

请尝试以上关键词之一。"""
            return f"抱歉，未找到\"{query}\"相关的简历模板。"

        # 过滤有下载链接的结果
        valid_matches = [m for m in result.matches if m.download_link]

        if not valid_matches:
            df = get_all_templates()
            if df is not None:
                available = "\n".join([f"- {t}" for t in df['问题'].tolist()])
                return f"""抱歉，未找到"{query}"相关的简历模板。

目前可用的简历模板包括：
{available}

请尝试以上关键词之一。"""
            return f"抱歉，未找到\"{query}\"相关的简历模板。"

        # 格式化结果
        output_lines = []
        for match in valid_matches:
            output_lines.append(f"""**模板名称**: {match.template_name}
**下载地址**: {match.download_link}""")

        return "\n\n".join(output_lines)

    except Exception as e:
        return f"查询时出错: {str(e)}"


# 初始化 session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 默认检索模式
if 'search_mode' not in st.session_state:
    st.session_state.search_mode = 'vector'

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎛️ 控制面板")

    # 检索模式选择器
    st.subheader("🔍 检索模式")

    mode_options = {
        "fuzzy": {
            "label": "🔤 模糊匹配",
            "desc": "基于字符串相似度的快速匹配，适合精确关键词"
        },
        "vector": {
            "label": "🔍 向量检索",
            "desc": "基于语义理解的智能搜索，适合自然语言查询"
        },
        "hybrid": {
            "label": "🔄 混合检索",
            "desc": "结合两种方式的优势，准确率最高"
        }
    }

    # 创建选择器
    selected_mode = st.radio(
        "选择检索模式：",
        options=list(mode_options.keys()),
        format_func=lambda x: mode_options[x]["label"],
        index=list(mode_options.keys()).index(st.session_state.search_mode),
        key="mode_selector"
    )

    # 更新模式
    if selected_mode != st.session_state.search_mode:
        st.session_state.search_mode = selected_mode
        st.rerun()

    # 显示当前模式的说明
    st.info(mode_options[selected_mode]["desc"])

    # 模式配置信息
    with st.expander("⚙️ 模式配置", expanded=False):
        if selected_mode == "vector":
            st.metric("向量阈值", f"{Config.VECTOR_THRESHOLD}")
            st.metric("返回数量", Config.VECTOR_TOP_K)
        elif selected_mode == "hybrid":
            col1, col2 = st.columns(2)
            with col1:
                st.metric("向量权重", f"{Config.HYBRID_WEIGHT_VECTOR}")
            with col2:
                st.metric("模糊权重", f"{Config.HYBRID_WEIGHT_FUZZY}")

    st.divider()

    # 所有模板列表
    st.subheader("📋 所有模板")
    df = get_all_templates()
    if df is not None:
        for idx, row in df.iterrows():
            template_name = row['问题']
            download_link = row['答案']

            with st.expander(f"📄 {template_name}", expanded=False):
                st.text_input("下载链接", download_link, key=f"link_{idx}", disabled=True)

                # 提取码
                if 'pwd=' in download_link:
                    pwd = download_link.split('pwd=')[-1]
                    st.code(f"提取码: {pwd}", language=None)

                st.link_button("🔗 点击下载", download_link)

    st.divider()

    st.markdown("""
    ### 💡 使用说明
    1. **选择检索模式**（上方切换）
    2. 输入简历类型关键词
    3. 查看匹配结果
    4. 点击链接下载模板

    **支持的关键词:**
    - 人事行政、互联网
    - 大学生、研究生
    - 教师、医生护士
    - 财会金融、通用
    """)

    st.divider()

    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

# ==================== 主界面 ====================
st.title("📄 简历模板知识库 Agent")

# 显示当前配置
mode_display = {
    "fuzzy": "🔤 模糊匹配",
    "vector": "🔍 向量检索",
    "hybrid": "🔄 混合检索"
}

# 使用列布局显示配置信息
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown(f"**模型**: {Config.ANTHROPIC_DEFAULT_HAIKU_MODEL}")
with col2:
    st.markdown(f"**检索模式**: {mode_display[st.session_state.search_mode]}")
with col3:
    # 添加一个刷新按钮
    if st.button("🔄 刷新"):
        st.rerun()

st.divider()

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 输入框
user_input = st.chat_input("请输入您需要的简历类型...")

if user_input:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 使用当前选择的模式进行搜索
    with st.chat_message("assistant"):
        with st.spinner(f"正在使用 {mode_display[st.session_state.search_mode]} 查询..."):
            response = search_with_mode(user_input, st.session_state.search_mode)

        # 显示匹配的模板信息
        if "**模板名称**:" in response and "**下载地址**:" in response:
            # 提取所有匹配的模板
            results = response.split("\n\n")

            for idx, result in enumerate(results, 1):
                lines = result.split('\n')
                template_name = None
                download_link = None

                for line in lines:
                    if "**模板名称**:" in line:
                        template_name = line.split("**模板_name**:")[-1].strip()
                        if "**模板名称**:" in template_name:
                            template_name = template_name.split("**模板名称**:")[-1].strip()
                    elif "**下载地址**:" in line:
                        download_link = line.split("**下载地址**:")[-1].strip()

                # 解析修复
                for line in lines:
                    if "**模板名称**:" in line:
                        template_name = line.split("**模板名称**:")[-1].strip()
                    elif "**下载地址**:" in line:
                        download_link = line.split("**下载地址**:")[-1].strip()

                if template_name and download_link:
                    if idx > 1:
                        st.divider()

                    st.success(f"### 📄 {template_name}")

                    # 显示下载链接和提取码
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.text_input("下载链接", download_link, disabled=True, key=f"dl_{idx}")

                    with col2:
                        if 'pwd=' in download_link:
                            pwd = download_link.split('pwd=')[-1]
                            st.code(f"提取码: {pwd}", language=None)

                    st.link_button("🔗 点击下载", download_link, type="primary")
        else:
            st.markdown(response)

        # 显示检索模式信息
        st.caption(f"💡 使用 {mode_display[st.session_state.search_mode]} 模式检索")

    # 添加助手回复到历史
    st.session_state.messages.append({"role": "assistant", "content": response})

# ==================== 底部信息 ====================
st.divider()
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 0.8em;'>
        基于 LangChain + 智谱 AI GLM-4.7 | 简历模板知识库 v2.0<br>
        支持 🔤 模糊匹配 | 🔍 向量检索 | 🔄 混合检索
    </div>
    """, unsafe_allow_html=True)
