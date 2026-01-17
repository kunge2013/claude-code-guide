#!/usr/bin/env python3
"""
简历模板知识库 - Web 界面
基于 Streamlit 的可视化界面
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
from resume_agent import ResumeTemplateAgent

# 初始化 session state
if 'agent' not in st.session_state:
    with st.spinner('正在初始化 AI Agent...'):
        st.session_state.agent = ResumeTemplateAgent()
        st.session_state.messages = []

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []


def get_all_templates():
    """获取所有模板列表"""
    try:
        df = pd.read_excel(
            os.path.join(os.path.dirname(__file__), "9b1af114-6719-4148-8194-412b68c0d44d-tmp.xlsx")
        )
        return df
    except Exception as e:
        return None


# 侧边栏 - 所有模板列表
with st.sidebar:
    st.title("📋 所有模板")

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
    1. 在输入框中输入简历类型
    2. 点击"查询"按钮
    3. 获取模板下载链接
    4. 点击链接下载到本地

    **支持的关键词示例:**
    - 人事行政
    - 互联网
    - 大学生
    - 教师
    - 医生护士
    - 财会金融
    - 研究生
    - 通用
    """)

    st.divider()

    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

# 主界面
st.title("📄 简历模板知识库 Agent")
st.markdown(f"**模型**: {st.session_state.agent.config.ANTHROPIC_DEFAULT_HAIKU_MODEL} | **API**: 智谱 AI")

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

    # 生成回复
    with st.chat_message("assistant"):
        with st.spinner("正在查询..."):
            response = st.session_state.agent.query(user_input)

        # 解析回复并美化显示
        if "**模板名称**:" in response and "**下载地址**:" in response:
            # 提取模板名称和下载链接
            lines = response.split('\n')
            template_name = None
            download_link = None

            for line in lines:
                if "**模板名称**:" in line:
                    template_name = line.split("**模板名称**:")[-1].strip()
                elif "**下载地址**:" in line:
                    download_link = line.split("**下载地址**:")[-1].strip()

            if template_name and download_link:
                st.success(f"### 📄 {template_name}")

                # 显示下载链接和提取码
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.text_input("下载链接", download_link, disabled=True)

                with col2:
                    if 'pwd=' in download_link:
                        pwd = download_link.split('pwd=')[-1]
                        st.code(f"提取码: {pwd}", language=None)

                st.link_button("🔗 点击下载", download_link, type="primary")

                # 显示额外的提示信息
                remaining_text = response.replace(f"**模板名称**: {template_name}", "") \
                                         .replace(f"**下载地址**: {download_link}", "")

                if remaining_text.strip() and not remaining_text.startswith("抱歉"):
                    with st.expander("💡 更多信息"):
                        st.markdown(remaining_text)
            else:
                st.markdown(response)
        else:
            st.markdown(response)

    # 添加助手回复到历史
    st.session_state.messages.append({"role": "assistant", "content": response})

# 底部信息
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    基于 LangChain + 智谱 AI GLM-4.7 | 简历模板知识库 v1.0
</div>
""", unsafe_allow_html=True)
