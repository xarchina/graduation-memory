import streamlit as st
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
from PIL import Image
import io
from datetime import datetime
import random
from supabase import create_client, Client

# ===================== 全局页面基础配置 =====================
st.set_page_config(page_title="石榴16班毕业纪念册", page_icon="🍅", layout="wide")

# 暖调石榴16班人情味CSS，无冰冷AI赛博风
warm_css = """
<style>
/* 全局柔和渐变背景，石榴暖色系 */
.stApp {
    background: linear-gradient(140deg, #fff7f5 0%, #ffe9e3 40%, #fde0d8 100%);
    color: #332222;
}
/* 主标题石榴红温柔字体 */
.main-title {
    font-size: 40px;
    font-weight: 600;
    text-align: center;
    color: #c83e3e;
    margin-bottom: 8px;
}
.sub-title {
    text-align: center;
    color: #994444;
    font-size: 16px;
    margin-bottom: 32px;
}
/* 柔和卡片，低饱和石榴边框，无强光发光 */
.card-box {
    border: 1px solid #e8a8a8;
    border-radius: 16px;
    padding: 22px;
    background: rgba(255, 255, 255, 0.75);
    box-shadow: 0 2px 10px rgba(200, 60, 60, 0.08);
    margin: 12px 0;
}
/* 柔和石榴按钮，无刺眼霓虹 */
.stButton>button {
    background: linear-gradient(90deg, #d65c5c, #c44444);
    color: white !important;
    border: none;
    border-radius: 10px;
    height: 42px;
    font-weight: 500;
}
.stButton>button:hover {
    background: #b83838;
    transform: scale(1.01);
}

/* 输入框：输入文字黑色，底色浅白柔和 */
div[data-baseweb="input"] input {
    background: #ffffff !important;
    color: #000000 !important;
    caret-color: #c83e3e !important;
    border: 1px solid #ddbbbb !important;
    border-radius: 8px !important;
    padding: 9px 14px !important;
    font-size: 15px !important;
}
div[data-baseweb="textarea"] textarea {
    background: #ffffff !important;
    color: #000000 !important;
    caret-color: #c83e3e !important;
    border: 1px solid #ddbbbb !important;
    border-radius: 8px !important;
    padding: 11px 14px !important;
    font-size: 15px !important;
}
/* 输入框提示浅红灰色，清晰不刺眼 */
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: #996666 !important;
    opacity: 0.85 !important;
}

hr {
    border-color: #e2b0b0;
}
</style>
"""
st.markdown(warm_css, unsafe_allow_html=True)

# ===================== Supabase 云端数据库初始化（全局同步核心） =====================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ===================== 会话基础变量（仅存登录状态，业务数据全部走数据库） =====================
if "login_username" not in st.session_state:
    st.session_state.login_username = None
# 班级名单，石榴16班可自行修改
CLASS_STUDENTS = ["张三", "李四", "王五", "赵六", "陈七"]

# ===================== 数据库通用读写函数 =====================
# 1. 用户账号
def get_all_users():
    res = supabase.table("user_accounts").select("*").execute()
    user_dict = {}
    for row in res.data:
        user_dict[row["username"]] = {"pwd": row["password"], "name": row["student_name"]}
    return user_dict

def add_new_user(uname, pwd, sname):
    supabase.table("user_accounts").insert({
        "username": uname,
        "password": pwd,
        "student_name": sname
    }).execute()

# 2. 班级贴吧
def get_all_forum():
    res = supabase.table("forum_messages").select("*").order("id", desc=True).execute()
    return res.data

def insert_forum(author, text, img, vid, t):
    supabase.table("forum_messages").insert({
        "author": author,
        "text_content": text,
        "image": img,
        "video": vid,
        "create_time": t
    }).execute()

# 3. 标签评价
def get_all_tags():
    res = supabase.table("tag_data").select("*").execute()
    return res.data

def insert_tag(target, writer, tags, comment):
    supabase.table("tag_data").insert({
        "target_student": target,
        "writer": writer,
        "tags": tags,
        "comment": comment
    }).execute()

# 4. 班级大事记
def get_all_events():
    res = supabase.table("class_events").select("*").order("event_date", desc=True).execute()
    return res.data

def insert_event(date, title, detail, recorder):
    supabase.table("class_events").insert({
        "event_date": str(date),
        "title": title,
        "detail": detail,
        "recorder": recorder
    }).execute()

# 5. 漂流瓶
def get_all_bottles():
    res = supabase.table("bottle_list").select("*").execute()
    return res.data

def insert_bottle(content, t):
    supabase.table("bottle_list").insert({
        "content": content,
        "create_time": t
    }).execute()

# ===================== 页面头部标题（石榴16班） =====================
st.markdown('<div class="main-title">🍅 石榴16班 · 毕业纪念册</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">十六岁的我们，岁岁常相见</div>', unsafe_allow_html=True)

# ===================== 强制登录拦截：未登录只显示登录注册，看不到任何功能 =====================
if st.session_state.login_username is None:
    st.warning("🔐 请先注册/登录账号，查看石榴16班全部回忆空间")
    tab_login, tab_reg = st.tabs(["账号登录", "新生注册"])
    with tab_login:
        uname = st.text_input("账号")
        pwd = st.text_input("密码", type="password")
        if st.button("登录进入纪念册"):
            user_list = get_all_users()
            if uname in user_list and user_list[uname]["pwd"] == pwd:
                st.session_state.login_username = uname
                st.rerun()
            else:
                st.error("账号或密码有误，请重新填写")
    with tab_reg:
        reg_user = st.text_input("设置你的账号名")
        reg_pwd = st.text_input("设置登录密码", type="password")
        reg_stu = st.selectbox("绑定你的姓名", CLASS_STUDENTS)
        if st.button("完成注册"):
            user_list = get_all_users()
            if reg_user.strip() == "":
                st.warning("账号不能为空")
            elif reg_user in user_list:
                st.warning("该账号已被注册，换一个吧")
            elif reg_pwd.strip() == "":
                st.warning("密码不能为空")
            else:
                add_new_user(reg_user, reg_pwd, reg_stu)
                st.success("注册成功！去登录进入班级纪念册吧")
    # 未登录直接终止页面渲染
else:
    # 已登录全局变量
    all_user_info = get_all_users()
    login_name = all_user_info[st.session_state.login_username]["name"]
    current_student = login_name
    st.success(f"✅ 欢迎回来，{current_student}")
    if st.button("退出登录"):
        st.session_state.login_username = None
        st.rerun()

    # 顶部导航栏
    nav_menu = option_menu(
        menu_title=None,
        options=["班级留言墙", "给同学写评语", "我的专属档案", "班级时光大事记", "星海漂流瓶"],
        icons=["chat-heart", "tag", "person-lines-fill", "calendar-heart", "water"],
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"background": "rgba(255,245,243,0.6)", "padding": "6px"},
            "nav-link": {"color":"#773333", "font-size":"16px"},
            "nav-link-selected": {"background": "#d65c5c", "color":"white"}
        }
    )

    # ===================== 1. 班级留言墙（原贴吧，全设备同步） =====================
    if nav_menu == "班级留言墙":
        st.markdown("### 🍅 石榴16班留言墙 · 分享日常与毕业回忆")
        with st.container():
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            post_text = st.text_area("写下想和全班分享的话：", height=100)
            col1, col2 = st.columns(2)
            with col1:
                upload_img = st.file_uploader("上传照片", type=["png", "jpg", "jpeg"])
            with col2:
                upload_video = st.file_uploader("上传短视频", type=["mp4", "mov"])
            submit_btn = st.button("发布这条留言")
            st.markdown('</div>', unsafe_allow_html=True)

        if submit_btn and post_text.strip():
            img_byte = upload_img.read() if upload_img else None
            vid_byte = upload_video.read() if upload_video else None
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            insert_forum(current_student, post_text, img_byte, vid_byte, now_time)
            st.success("留言已经贴到班级墙上啦！所有人都能看见")
            st.rerun()

        st.markdown("## 📜 全班所有人的留言")
        forum_data = get_all_forum()
        if len(forum_data) == 0:
            st.info("墙上还空空的，快来写下第一条班级回忆吧")
        else:
            for item in forum_data:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"**{item['author']}** · {item['create_time']}")
                st.write(item["text_content"])
                if item["image"]:
                    img = Image.open(io.BytesIO(item["image"]))
                    st.image(img, width=600)
                if item["video"]:
                    st.video(io.BytesIO(item["video"]))
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 2. 给同学写评语（标签评价） =====================
    elif nav_menu == "给同学写评语":
        st.markdown("### 🏷️ 给班里同学贴上专属小标签、写下心里话")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        target_stu = st.selectbox("选择你想评价的同学", CLASS_STUDENTS)
        tag_input = st.text_input("性格标签（空格隔开，例：温柔 爱笑 学霸 运动少年）")
        comment_input = st.text_area("写下你对TA的毕业心里话", height=80)
        submit_tag = st.button("保存这条评语")
        st.markdown('</div>', unsafe_allow_html=True)

        if submit_tag and tag_input.strip() and comment_input.strip():
            insert_tag(target_stu, current_student, tag_input, comment_input)
            st.success(f"已经给{target_stu}写下专属评语啦")
            st.rerun()

        st.markdown(f"## 📝 {target_stu} 收到的评语预览（完整内容仅本人登录可见）")
        all_tag_list = get_all_tags()
        target_tags = [x for x in all_tag_list if x["target_student"] == target_stu]
        if not target_tags:
            st.info(f"还没有人给{target_stu}写评语哦")
        else:
            for t in target_tags[:3]:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"来自{t['writer']} | 标签：{t['tags']}")
                st.write(f"评语预览：{t['comment'][:30]}……")
                st.markdown('</div>', unsafe_allow_html=True)
            st.info("完整评语、性格词云和雷达图，只有TA本人登录后在「我的专属档案」查看")

    # ===================== 3. 我的专属档案（隐私，仅本人可见） =====================
    elif nav_menu == "我的专属档案":
        st.markdown(f"### 💌 {current_student} 的专属毕业评语档案（仅自己可见）")
        all_tag_list = get_all_tags()
        my_tags = [x for x in all_tag_list if x["target_student"] == current_student]

        if not my_tags:
            st.warning("暂时还没有同学给你写评语，快去邀请大家为你留言吧")
        else:
            # 词云生成
            all_tag_str = ""
            tag_count = {}
            for t in my_tags:
                all_tag_str += t["tags"] + " "
                tag_split = t["tags"].split(" ")
                for word in tag_split:
                    w = word.strip()
                    if w:
                        tag_count[w] = tag_count.get(w, 0) + 1

            wc = WordCloud(
                background_color="#fff7f5",
                width=800, height=400,
                colormap="Reds",
                contour_width=1, contour_color="#c83e3e"
            ).generate(all_tag_str)
            st.markdown("#### 🔖 属于你的性格标签词云")
            st.image(wc.to_image(), width=900)

            # 性格雷达图（暖红色系）
            st.markdown("#### 📊 大家眼中的你 · 性格维度图")
            score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
            for tag, cnt in tag_count.items():
                if tag in ["开朗","乐观","阳光"]: score["乐观"] += cnt
                if tag in ["温柔","贴心","细心"]: score["温柔"] += cnt
                if tag in ["搞笑","有趣","好玩"]: score["有趣"] += cnt
                if tag in ["努力","自律","学霸"]: score["自律"] += cnt
                if tag in ["外向","社牛","大方"]: score["外向"] += cnt

            labels = list(score.keys())
            vals = list(score.values())
            angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
            vals += vals[:1]
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(projection="polar"))
            ax.plot(angles, vals, color="#c83e3e", linewidth=3)
            ax.fill(angles, vals, color="#e87878", alpha=0.3)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, color="#773333", fontsize=12)
            ax.set_facecolor("#fff7f5")
            fig.patch.set_facecolor("#fff7f5")
            ax.tick_params(colors="#994444")
            st.pyplot(fig)

            # 全部私密评语
            st.markdown("#### 📩 全班写给你的所有心里话")
            for item in my_tags:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"评价人：{item['writer']} | 标签：{item['tags']}")
                st.write(f"留言：{item['comment']}")
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 4. 班级时光大事记 =====================
    elif nav_menu == "班级时光大事记":
        st.markdown("### 📅 石榴16班共同大事记，全班都能记录")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        event_date = st.date_input("这件事发生的日期")
        event_title = st.text_input("事件标题（例：百日誓师、全班合照、运动会夺冠）")
        event_detail = st.text_area("详细记录这件难忘的班级小事", height=100)
        add_event_btn = st.button("存入班级时光册")
        st.markdown('</div>', unsafe_allow_html=True)

        if add_event_btn and event_title.strip():
            insert_event(event_date, event_title, event_detail, current_student)
            st.success("这件大事已经存入班级时光档案啦")
            st.rerun()

        st.markdown("## 📖 十六班全部时光记录（由新到旧）")
        event_data = get_all_events()
        if not event_data:
            st.info("还没有记录班级大事，快来写下第一件难忘回忆")
        else:
            for ev in event_data:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"📆 {ev['event_date']} | 记录人：{ev['recorder']}")
                st.subheader(ev["title"])
                st.write(ev["detail"])
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 5. 星海漂流瓶 =====================
    elif nav_menu == "星海漂流瓶":
        st.markdown("### 🌊 匿名漂流瓶 · 藏起不想当面说的毕业心事")
        col_throw, col_get = st.columns(2)
        with col_throw:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            bottle_text = st.text_area("写下你的匿名心事，丢进星海", height=120)
            if st.button("投放漂流瓶"):
                if bottle_text.strip():
                    now_t = datetime.now().strftime("%m-%d %H:%M")
                    insert_bottle(bottle_text, now_t)
                    st.success("你的漂流瓶已经飘向星海啦")
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_get:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.subheader("随机打捞一只陌生漂流瓶")
            if st.button("打捞漂流瓶"):
                bottle_all = get_all_bottles()
                if len(bottle_all) == 0:
                    st.info("星海还没有漂流瓶，先投放一个吧")
                else:
                    pick = random.choice(bottle_all)
                    st.write(f"投递时间：{pick['create_time']}")
                    st.write(f"瓶中文字：{pick['content']}")
            st.markdown('</div>', unsafe_allow_html=True)

        total_bottle = len(get_all_bottles())
        st.info(f"当前星海一共有 {total_bottle} 只漂流瓶等待打捞")