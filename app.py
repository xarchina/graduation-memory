import streamlit as st
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
from PIL import Image
import io
from datetime import datetime
import random

# ===================== 全局页面配置 =====================
st.set_page_config(page_title="星际班级毕业纪念馆", page_icon="🌌", layout="wide")

# 修复输入框：输入文字黑色，保留原未来风样式
future_css = """
<style>
/* 全局背景渐变 */
.stApp {
    background: linear-gradient(135deg, #05001a 0%, #100030 50%, #001033 100%);
    color: #f0f8ff;
}
/* 标题霓虹发光 */
.main-title {
    font-size: 42px;
    font-weight: 900;
    text-align: center;
    background: linear-gradient(90deg, #00f0ff, #9900ff);
    -webkit-background-clip: text;
    color: transparent;
    text-shadow: 0 0 15px #00ccff88;
    margin-bottom: 10px;
}
.sub-title {
    text-align: center;
    color: #a0ccff;
    font-size: 16px;
    margin-bottom: 30px;
}
/* 卡片容器 科技边框 */
.card-box {
    border: 1px solid #00ccff44;
    border-radius: 12px;
    padding: 20px;
    background: rgba(10, 5, 40, 0.6);
    box-shadow: 0 0 12px #0088ff33;
    margin: 10px 0;
}
/* 按钮霓虹样式 */
.stButton>button {
    background: linear-gradient(90deg, #0077ff, #9922ff);
    color: white !important;
    border: none;
    border-radius: 8px;
    box-shadow: 0 0 8px #00aaff77;
    height: 40px;
    font-weight: bold;
}
.stButton>button:hover {
    box-shadow: 0 0 18px #00ddff;
    transform: scale(1.02);
}

/* 输入框文字改为黑色 */
div[data-baseweb="input"] input {
    background: rgba(20, 10, 50, 0.8) !important;
    color: #000000 !important;
    caret-color: #00f0ff !important;
    border: 1px solid #4488ff99 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 15px !important;
}
div[data-baseweb="textarea"] textarea {
    background: rgba(20, 10, 50, 0.8) !important;
    color: #000000 !important;
    caret-color: #00f0ff !important;
    border: 1px solid #4488ff99 !important;
    border-radius: 6px !important;
    padding: 10px 12px !important;
    font-size: 15px !important;
}
/* 输入框提示文字 */
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: #a0ccff !important;
    opacity: 0.8 !important;
}

hr {
    border-color: #00ccff55;
    box-shadow: 0 0 6px #00ccff44;
}
</style>
"""
st.markdown(future_css, unsafe_allow_html=True)

# ===================== 会话状态初始化 =====================
if "student_list" not in st.session_state:
    st.session_state.student_list = ["张三", "李四", "王五", "赵六", "陈七"]

# 账号系统：{账号: {"pwd":密码, "name":绑定学生姓名}}
if "user_accounts" not in st.session_state:
    st.session_state.user_accounts = {}
# 当前登录账号，None=未登录
if "login_username" not in st.session_state:
    st.session_state.login_username = None

# 原有业务数据
if "forum_messages" not in st.session_state:
    st.session_state.forum_messages = []
if "tag_data" not in st.session_state:
    st.session_state.tag_data = []
if "event_list" not in st.session_state:
    st.session_state.event_list = []

# 漂流瓶数据池
if "bottle_list" not in st.session_state:
    st.session_state.bottle_list = []

# ===================== 页面头部标题 =====================
st.markdown('<div class="main-title">🌌 星际毕业纪念班级空间站</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">属于我们的赛博青春留言馆 · 永久留存班级回忆</div>', unsafe_allow_html=True)

# ===================== 登录校验核心：未登录只展示登录面板，隐藏所有功能 =====================
if st.session_state.login_username is None:
    st.warning("🔐 请先注册/登录账号，解锁全部班级系统功能！")
    tab1, tab2 = st.tabs(["账号登录", "新用户注册"])
    with tab1:
        uname = st.text_input("账号")
        pwd = st.text_input("密码", type="password")
        if st.button("登录系统"):
            if uname in st.session_state.user_accounts and st.session_state.user_accounts[uname]["pwd"] == pwd:
                st.session_state.login_username = uname
                st.rerun()
            else:
                st.error("账号或密码错误，请重新输入")
    with tab2:
        reg_user = st.text_input("注册账号名")
        reg_pwd = st.text_input("设置密码", type="password")
        reg_name = st.selectbox("绑定你的姓名", st.session_state.student_list)
        if st.button("完成注册"):
            if reg_user.strip() == "":
                st.warning("账号不能为空")
            elif reg_user in st.session_state.user_accounts:
                st.warning("该账号已存在，换一个账号")
            elif reg_pwd.strip() == "":
                st.warning("密码不能为空")
            else:
                st.session_state.user_accounts[reg_user] = {"pwd": reg_pwd, "name": reg_name}
                st.success("注册成功！前往登录")
    # 未登录直接终止后续代码，不加载导航与功能
else:
    # 已登录，加载完整系统
    login_name = st.session_state.user_accounts[st.session_state.login_username]["name"]
    st.success(f"✅ 当前已登录账号：{st.session_state.login_username} | 绑定学生：{login_name}")
    if st.button("退出登录"):
        st.session_state.login_username = None
        st.rerun()

    # 获取当前登录人的学生姓名
    current_student = login_name

    # ===================== 顶部导航栏 =====================
    nav_menu = option_menu(
        menu_title=None,
        options=["班级贴吧", "同学标签评价", "个人专属空间", "班级大事件", "星际漂流瓶"],
        icons=["chat-dots", "tag", "person-heart", "calendar-event", "water"],
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"background": "rgba(0,10,40,0.5)", "padding": "5px"},
            "nav-link": {"color":"#b0e0ff", "font-size":"16px"},
            "nav-link-selected": {"background": "linear-gradient(90deg,#0088ff,#9922ff)", "color":"white"}
        }
    )

    # ===================== 1. 班级贴吧 =====================
    if nav_menu == "班级贴吧":
        st.markdown("### 📡 班级自由交流空间站 · 随时发布图文视频回忆")
        with st.container():
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            post_text = st.text_area("写下你的毕业感言、趣事、回忆：", height=100)
            col1, col2 = st.columns(2)
            with col1:
                upload_img = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"])
            with col2:
                upload_video = st.file_uploader("上传短视频", type=["mp4", "mov"])
            submit_btn = st.button("🚀 发布动态")
            st.markdown('</div>', unsafe_allow_html=True)

        if submit_btn and post_text.strip():
            img_bytes = upload_img.read() if upload_img else None
            vid_bytes = upload_video.read() if upload_video else None
            new_msg = {
                "author": current_student,
                "text": post_text,
                "image": img_bytes,
                "video": vid_bytes,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.session_state.forum_messages.insert(0, new_msg)
            st.success("发布成功！已推送至班级空间站！")
            st.rerun()

        st.markdown("## 📜 全班动态墙")
        if len(st.session_state.forum_messages) == 0:
            st.info("暂无动态，快来发布第一条班级回忆吧！")
        else:
            for msg in st.session_state.forum_messages:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"**👤 {msg['author']}** · {msg['time']}")
                st.write(msg["text"])
                if msg["image"]:
                    img = Image.open(io.BytesIO(msg["image"]))
                    st.image(img, width=600)
                if msg["video"]:
                    st.video(io.BytesIO(msg["video"]))
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 2. 同学标签评价 =====================
    elif nav_menu == "同学标签评价":
        st.markdown("### 🏷️ 给同班同学贴标签、写专属评价")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        target_student = st.selectbox("选择你要评价的同学", st.session_state.student_list)
        tag_words = st.text_input("输入性格标签（用空格分隔，例：温柔 搞笑 学霸 运动健将）")
        comment_detail = st.text_area("写下你对TA的专属毕业评价", height=80)
        submit_tag = st.button("✨ 提交标签评价")
        st.markdown('</div>', unsafe_allow_html=True)

        if submit_tag and tag_words.strip() and comment_detail.strip():
            st.session_state.tag_data.append({
                "target": target_student,
                "writer": current_student,
                "tags": tag_words,
                "comment": comment_detail
            })
            st.success(f"成功给 {target_student} 贴上评价！")
            st.rerun()

        st.markdown(f"## 📝 {target_student} 已收到全部评价（仅本人登录可查看完整档案）")
        target_all_tags = [i for i in st.session_state.tag_data if i["target"] == target_student]
        if not target_all_tags:
            st.info(f"暂时还没有人给 {target_student} 写评价~")
        else:
            for item in target_all_tags[:3]:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"来自：{item['writer']} | 标签：`{item['tags']}`")
                st.write(f"简短预览：{item['comment'][:30]}...")
                st.markdown('</div>', unsafe_allow_html=True)
            st.info("完整评价、性格词云、雷达图仅【本人登录账号】后在个人空间查看！")

    # ===================== 3. 个人专属空间 =====================
    elif nav_menu == "个人专属空间":
        st.markdown("### 💫 私人性格档案（隐私区域，仅本人可访问）")
        me = current_student
        my_all_tags = [i for i in st.session_state.tag_data if i["target"] == me]

        if not my_all_tags:
            st.warning("暂时没有同学给你贴标签，快去邀请好友评价你吧！")
        else:
            # 词云生成
            all_tag_text = ""
            tag_count_dict = {}
            for item in my_all_tags:
                all_tag_text += item["tags"] + " "
                tag_list = item["tags"].split(" ")
                for t in tag_list:
                    if t.strip():
                        tag_count_dict[t] = tag_count_dict.get(t, 0) + 1

            wc = WordCloud(
                background_color="#05001a",
                width=800, height=400,
                colormap="cool",
                contour_width=1, contour_color="#00ccff"
            ).generate(all_tag_text)
            st.markdown("#### 🔮 你的性格标签词云")
            st.image(wc.to_image(), width=900)

            # 性格雷达图
            st.markdown("#### 📊 AI综合性格维度雷达图")
            dim_score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
            for tag, cnt in tag_count_dict.items():
                if tag in ["开朗","乐观","阳光"]: dim_score["乐观"] += cnt
                if tag in ["温柔","贴心","细心"]: dim_score["温柔"] += cnt
                if tag in ["搞笑","有趣","沙雕"]: dim_score["有趣"] += cnt
                if tag in ["学霸","自律","努力"]: dim_score["自律"] += cnt
                if tag in ["社牛","外向","开朗"]: dim_score["外向"] += cnt

            labels = list(dim_score.keys())
            values = list(dim_score.values())
            angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
            values += values[:1]
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(projection="polar"))
            ax.plot(angles, values, color="#00ddff", linewidth=3)
            ax.fill(angles, values, color="#0088ff", alpha=0.3)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, color="#b0e0ff", fontsize=12)
            ax.set_facecolor("#05001a")
            fig.patch.set_facecolor("#05001a")
            ax.tick_params(colors="#a0ccff")
            st.pyplot(fig)

            # 全部私人留言
            st.markdown("#### 📩 全班同学给你的全部私密留言")
            for item in my_all_tags:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"评价人：{item['writer']} | 标签：{item['tags']}")
                st.write(f"留言：{item['comment']}")
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 4. 班级大事件 =====================
    elif nav_menu == "班级大事件":
        st.markdown("### 📅 班级共同大事记 · 全体同学可编辑记录")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        event_date = st.date_input("事件发生日期")
        event_title = st.text_input("事件标题（例：百日誓师、毕业合照、运动会夺冠）")
        event_detail = st.text_area("详细记录这件班级大事", height=100)
        add_event = st.button("➕ 新增班级大事")
        st.markdown('</div>', unsafe_allow_html=True)

        if add_event and event_title.strip():
            st.session_state.event_list.append({
                "date": event_date,
                "title": event_title,
                "detail": event_detail,
                "recorder": current_student
            })
            st.success("班级大事已录入档案！")
            st.rerun()

        st.markdown("## 📖 班级时光档案（按时间倒序）")
        sort_events = sorted(st.session_state.event_list, key=lambda x:x["date"], reverse=True)
        if not sort_events:
            st.info("暂无班级大事记，快来记录第一件班级回忆！")
        else:
            for ev in sort_events:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"📆 {ev['date']} | 记录人：{ev['recorder']}")
                st.subheader(ev["title"])
                st.write(ev["detail"])
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 5. 星际漂流瓶 =====================
    elif nav_menu == "星际漂流瓶":
        st.markdown("### 🌊 匿名星际漂流瓶 · 写下心事，随机打捞他人寄语")
        col_throw, col_get = st.columns(2)
        with col_throw:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            bottle_text = st.text_area("写下你的匿名漂流瓶（毕业心事、悄悄话）", height=120)
            if st.button("🫧 投放漂流瓶"):
                if bottle_text.strip():
                    st.session_state.bottle_list.append({
                        "content": bottle_text,
                        "time": datetime.now().strftime("%m-%d %H:%M")
                    })
                    st.success("漂流瓶已丢入星海！")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_get:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.subheader("随机打捞一只漂流瓶")
            if st.button("🔍 打捞星海漂流瓶"):
                if len(st.session_state.bottle_list) == 0:
                    st.info("星海暂无漂流瓶，先投放一个吧！")
                else:
                    random_bottle = random.choice(st.session_state.bottle_list)
                    st.write(f"📅 漂流瓶投递时间：{random_bottle['time']}")
                    st.write(f"💌 瓶中文字：{random_bottle['content']}")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("## 全部漂流瓶库存（仅展示数量，不泄露全部内容）")
        st.info(f"当前星海共有 {len(st.session_state.bottle_list)} 只漂流瓶等待打捞")