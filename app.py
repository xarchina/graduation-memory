import streamlit as st
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
from PIL import Image
import io
import base64
from datetime import datetime
import random
from supabase import create_client, Client
import streamlit.components.v1 as components

# ===================== 全局页面基础配置 =====================
st.set_page_config(page_title="石榴16班毕业纪念册", page_icon="🍅", layout="wide")

# 悬浮卡片CSS（hover才显示点赞回复栏）
warm_css = """
<style>
.stApp {
    background: linear-gradient(140deg, #fff7f5 0%, #ffe9e3 40%, #fde0d8 100%);
    color: #332222;
}
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
.card-box {
    border: 1px solid #e8a8a8;
    border-radius: 16px;
    padding: 22px;
    background: rgba(255, 255, 255, 0.75);
    box-shadow: 0 2px 10px rgba(200, 60, 60, 0.08);
    margin: 12px 0;
    position: relative;
}
/* 点赞回复栏默认隐藏，hover卡片显示 */
.post-action-bar {
    display: none;
    margin-top:12px;
    padding:10px;
    background:#fff2f2;
    border-radius:10px;
}
.card-box:hover .post-action-bar {
    display:block;
}
.bottle-show-box {
    border: 2px solid #87CEEB;
    border-radius: 20px;
    padding: 40px;
    background: rgba(240,248,255,0.8);
    margin: 30px 0;
    min-height: 300px;
}
.stButton>button {
    background: linear-gradient(90deg, #d65c5c, #c44444);
    color: white !important;
    border: none;
    border-radius: 10px;
    height: 36px;
    font-weight: 500;
}
.stButton>button:hover {
    background: #b83838;
    transform: scale(1.01);
}
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
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: #996666 !important;
    opacity: 0.85 !important;
}
hr {
    border-color: #e2b0b0;
}
.reply-box {
    background:#fff0f0;
    padding:10px;
    border-radius:10px;
    margin:8px 0;
}
.img-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap:8px;
}
</style>
"""
st.markdown(warm_css, unsafe_allow_html=True)

# ===================== 全局5秒自动刷新 =====================
st.markdown("""
<script>
setInterval(()=>window.location.reload(),5000)
</script>
""", unsafe_allow_html=True)
st.caption("🍅 每5秒自动同步全班数据")

# ===================== Supabase 全局单例（只初始化一次，解决重复连接卡顿） =====================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ===================== 工具函数：图片压缩 + base64编码 =====================
def compress_and_encode(img_file, max_width=1080, quality=70):
    img = Image.open(img_file)
    w, h = img.size
    if w > max_width:
        scale = max_width / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64

def video_to_b64(vid_file):
    raw = vid_file.read()
    return base64.b64encode(raw).decode("utf-8")

# ===================== AI语义打分工具（自由评语自动分类5维度，无需手动标签） =====================
def ai_calc_person_score(comment_text: str):
    text = comment_text.lower()
    score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
    # 乐观关键词
    happy = ["开朗","乐观","阳光","开心","积极","元气","爱笑","治愈"]
    # 温柔关键词
    soft = ["温柔","贴心","细心","善良","安静","暖心","细腻"]
    # 有趣关键词
    funny = ["搞笑","有趣","好玩","幽默","沙雕","活泼","梗多"]
    # 自律关键词
    hard = ["努力","自律","学霸","认真","踏实","上进","刻苦"]
    # 外向关键词
    out = ["外向","社牛","大方","合群","自来熟","健谈"]
    for word in happy:
        if word in text:
            score["乐观"] += 1
    for word in soft:
        if word in text:
            score["温柔"] += 1
    for word in funny:
        if word in text:
            score["有趣"] += 1
    for word in hard:
        if word in text:
            score["自律"] += 1
    for word in out:
        if word in text:
            score["外向"] += 1
    return score

# ===================== 会话变量初始化（全局缓存所有数据库数据，减少循环查询，解决卡顿） =====================
if "login_username" not in st.session_state:
    st.session_state.login_username = None
if "show_user_drawer" not in st.session_state:
    st.session_state.show_user_drawer = False
if "current_bottle" not in st.session_state:
    st.session_state.current_bottle = None
if "bottle_anim" not in st.session_state:
    st.session_state.bottle_anim = False
# 全局数据缓存，页面一次性加载，不再循环重复请求数据库
if "cache_users" not in st.session_state:
    st.session_state.cache_users = {}
if "cache_forum" not in st.session_state:
    st.session_state.cache_forum = []
if "cache_replies" not in st.session_state:
    st.session_state.cache_replies = []
if "cache_tags" not in st.session_state:
    st.session_state.cache_tags = []
if "cache_profile" not in st.session_state:
    st.session_state.cache_profile = []
if "cache_msg" not in st.session_state:
    st.session_state.cache_msg = []
if "cache_events" not in st.session_state:
    st.session_state.cache_events = []
if "cache_bottles" not in st.session_state:
    st.session_state.cache_bottles = []
# 词云、雷达图缓存，避免重复渲染
if "wordcloud_img" not in st.session_state:
    st.session_state.wordcloud_img = None
if "radar_fig" not in st.session_state:
    st.session_state.radar_fig = None

CLASS_STUDENTS = ["张三", "李四", "王五", "赵六", "陈七"]

# ===================== 统一全局数据加载函数（只执行一次，全部存入缓存，大幅降低并发请求） =====================
def load_all_cache_data():
    # 1. 用户账号
    res = supabase.table("user_accounts").select("*").execute()
    user_dict = {}
    for row in res.data:
        user_dict[row["username"]] = {"pwd": row["password"], "name": row["student_name"]}
    st.session_state.cache_users = user_dict

    # 2. 论坛帖子
    res_forum = supabase.table("forum_messages").select("*").order("id", desc=True).execute()
    st.session_state.cache_forum = res_forum.data

    # 3. 所有回复
    res_reply = supabase.table("forum_reply").select("*").execute()
    st.session_state.cache_replies = res_reply.data

    # 4. 评价评语
    res_tag = supabase.table("tag_data").select("*").execute()
    st.session_state.cache_tags = res_tag.data

    # 5. 个人档案
    res_prof = supabase.table("user_profile").select("*").execute()
    st.session_state.cache_profile = res_prof.data

    # 6. 私信
    res_msg = supabase.table("private_msg").select("*").execute()
    st.session_state.cache_msg = res_msg.data

    # 7. 大事记
    res_event = supabase.table("class_events").select("*").order("event_date", desc=True).execute()
    st.session_state.cache_events = res_event.data

    # 8. 漂流瓶
    res_bottle = supabase.table("bottle_list").select("*").execute()
    st.session_state.cache_bottles = res_bottle.data

# 页面进入自动加载一次全量缓存数据
load_all_cache_data()

# ===================== 数据库写入函数（仅新增/修改时调用，只读全部走缓存不请求数据库） =====================
# 1. 用户账号
def add_new_user(uname, pwd, sname):
    supabase.table("user_accounts").insert({
        "username": uname,
        "password": pwd,
        "student_name": sname
    }).execute()

# 2. 个人毕业档案
def get_user_profile(username):
    prof_list = st.session_state.cache_profile
    for p in prof_list:
        if p["username"] == username:
            return p
    return None

def save_profile(uname, data):
    old = get_user_profile(uname)
    if old:
        supabase.table("user_profile").update(data).eq("username", uname).execute()
    else:
        data["username"] = uname
        supabase.table("user_profile").insert(data).execute()

# 3. 私信系统
def send_msg(from_user, to_student, content):
    supabase.table("private_msg").insert({
        "sender": from_user,
        "target_student": to_student,
        "content": content,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }).execute()

def get_my_msg(student_name):
    all_msg = st.session_state.cache_msg
    return [m for m in all_msg if m["target_student"] == student_name]

# 4. 论坛主帖
def insert_forum(author, text, img_list, vid, t):
    supabase.table("forum_messages").insert({
        "author": author,
        "text_content": text,
        "images": img_list,
        "video": vid,
        "create_time": t,
        "like_count": 0
    }).execute()

def add_like(post_id):
    supabase.rpc("inc_like", {"pid": post_id}).execute()

# 5. 论坛回复
def get_replies_by_pid(pid):
    all_r = st.session_state.cache_replies
    return [r for r in all_r if r["post_id"] == pid]

def insert_reply(post_id, writer, text, t):
    supabase.table("forum_reply").insert({
        "post_id": post_id,
        "writer": writer,
        "content": text,
        "time": t
    }).execute()

# 6. 标签评价（取消手动标签输入，只写评语，AI自动打分）
def insert_tag(target, writer, comment):
    supabase.table("tag_data").insert({
        "target_student": target,
        "writer": writer,
        "comment": comment
    }).execute()

# 7. 班级大事记
def insert_event(date, title, detail, recorder, img_list):
    supabase.table("class_events").insert({
        "event_date": str(date),
        "title": title,
        "detail": detail,
        "recorder": recorder,
        "images": img_list
    }).execute()

# 8. 漂流瓶
def insert_bottle(content, t):
    supabase.table("bottle_list").insert({
        "content": content,
        "create_time": t
    }).execute()

# ===================== 页面顶部：标题 + 右上角个人中心按钮 =====================
header_col1, header_col2 = st.columns([9, 1])
with header_col1:
    st.markdown('<div class="main-title">🍅 石榴16班 · 毕业纪念册</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">十六岁的我们，岁岁常相见</div>', unsafe_allow_html=True)
with header_col2:
    if st.session_state.login_username:
        if st.button("👤 个人中心"):
            st.session_state.show_user_drawer = not st.session_state.show_user_drawer

# ===================== 右上角侧边抽屉：个人中心（半屏） =====================
if st.session_state.show_user_drawer and st.session_state.login_username:
    with st.sidebar:
        st.header("👤 个人中心")
        user_info = st.session_state.cache_users[st.session_state.login_username]
        current_student = user_info["name"]
        tab_msg, tab_profile, tab_view = st.tabs(["私信信箱", "我的毕业档案", "查看同学档案"])

        # 1. 私信系统
        with tab_msg:
            st.subheader("发送私信")
            target = st.selectbox("发给哪位同学", CLASS_STUDENTS)
            msg_text = st.text_area("私信内容")
            if st.button("发送") and msg_text.strip():
                send_msg(current_student, target, msg_text)
                st.success("发送成功")
                st.rerun()
            st.divider()
            st.subheader("我的收件箱")
            msgs = get_my_msg(current_student)
            if not msgs:
                st.info("暂无私信")
            for m in msgs:
                st.write(f"【{m['time']}】来自{m['sender']}：{m['content']}")

        # 2. 个人毕业档案填写
        with tab_profile:
            st.subheader("完善毕业纪念档案")
            prof = get_user_profile(st.session_state.login_username) or {}
            nick = st.text_input("昵称", value=prof.get("nick", ""))
            hobby = st.text_input("爱好", value=prof.get("hobby", ""))
            dream = st.text_input("未来理想", value=prof.get("dream", ""))
            motto = st.text_area("人生座右铭", value=prof.get("motto", ""))
            contact = st.text_input("联系方式", value=prof.get("contact", ""))
            if st.button("保存档案"):
                save_profile(st.session_state.login_username, {
                    "nick": nick, "hobby": hobby, "dream": dream,
                    "motto": motto, "contact": contact
                })
                st.success("档案已保存")

        # 3. 查看他人档案
        with tab_view:
            view_target = st.selectbox("选择查看同学", CLASS_STUDENTS)
            all_u = st.session_state.cache_users
            view_uname = None
            for k,v in all_u.items():
                if v["name"] == view_target:
                    view_uname = k
                    break
            if view_uname:
                vp = get_user_profile(view_uname)
                if not vp:
                    st.info("该同学暂未填写档案")
                else:
                    st.markdown(f"""
                    **昵称：**{vp['nick']}
                    **爱好：**{vp['hobby']}
                    **理想：**{vp['dream']}
                    **座右铭：**{vp['motto']}
                    """)

# ===================== 登录拦截 =====================
if st.session_state.login_username is None:
    st.warning("🔐 请先注册/登录账号，查看石榴16班全部回忆空间")
    tab_login, tab_reg = st.tabs(["账号登录", "新生注册"])
    with tab_login:
        uname = st.text_input("账号")
        pwd = st.text_input("密码", type="password")
        if st.button("登录进入纪念册"):
            user_list = st.session_state.cache_users
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
            user_list = st.session_state.cache_users
            if reg_user.strip() == "":
                st.warning("账号不能为空")
            elif reg_user in user_list:
                st.warning("该账号已被注册，换一个吧")
            elif reg_pwd.strip() == "":
                st.warning("密码不能为空")
            else:
                add_new_user(reg_user, reg_pwd, reg_stu)
                st.success("注册成功！去登录进入班级纪念册吧")
else:
    all_user_info = st.session_state.cache_users
    login_name = all_user_info[st.session_state.login_username]["name"]
    current_student = login_name
    st.success(f"✅ 欢迎回来，{current_student}")
    if st.button("退出登录"):
        st.session_state.login_username = None
        st.rerun()

    # 顶部导航
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

    # ===================== 1. 班级留言墙（hover显示点赞回复、多图9张、搜索） =====================
    if nav_menu == "班级留言墙":
        st.markdown("### 🍅 石榴16班留言墙 · 分享日常与毕业回忆")
        search_key = st.text_input("🔍 搜索帖子内容")
        st.divider()

        # 发布区域：最多9张图+视频
        with st.container():
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            post_text = st.text_area("写下想和全班分享的话：", height=100)
            st.subheader("上传图片（最多9张，自动压缩）")
            upload_imgs = st.file_uploader("多选图片", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
            upload_video = st.file_uploader("上传短视频", type=["mp4", "mov"])
            submit_btn = st.button("发布这条留言")
            st.markdown('</div>', unsafe_allow_html=True)

        if submit_btn and post_text.strip():
            img_b64_list = []
            if upload_imgs and len(upload_imgs) <=9:
                for f in upload_imgs:
                    img_b64_list.append(compress_and_encode(f))
            vid_b64 = video_to_b64(upload_video) if upload_video else None
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            insert_forum(current_student, post_text, img_b64_list, vid_b64, now_time)
            st.success("留言发布成功")
            st.rerun()

        # 帖子列表
        st.markdown("## 📜 全班所有人的留言")
        all_forum = st.session_state.cache_forum
        # 搜索过滤
        forum_data = []
        if search_key.strip():
            for item in all_forum:
                if search_key.lower() in item["text_content"].lower():
                    forum_data.append(item)
        else:
            forum_data = all_forum

        if len(forum_data) == 0:
            st.info("暂无匹配帖子")
        else:
            for item in forum_data:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                like_num = item.get("like_count", 0)
                st.write(f"**{item['author']}** · {item['create_time']} | ❤️ 点赞：{like_num}")
                st.write(item["text_content"])

                # 展示多图
                img_list = item.get("images", [])
                if len(img_list)>0:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for b64 in img_list:
                        img_bin = base64.b64decode(b64)
                        st.image(io.BytesIO(img_bin), width=200)
                    st.markdown('</div>', unsafe_allow_html=True)
                vid_b64 = item.get("video")
                if vid_b64:
                    vid_bin = base64.b64decode(vid_b64)
                    st.video(io.BytesIO(vid_bin))

                # ========== hover才显示的点赞+回复区域 ==========
                st.markdown('<div class="post-action-bar">', unsafe_allow_html=True)
                col_like, col_reply = st.columns([1,3])
                with col_like:
                    if st.button(f"❤️ 点赞 #{item['id']}", key=f"like_{item['id']}"):
                        add_like(item["id"])
                        st.rerun()
                with col_reply:
                    reply_text = st.text_input("写下回复", key=f"reply_input_{item['id']}")
                    if st.button("提交回复", key=f"reply_btn_{item['id']}") and reply_text.strip():
                        t = datetime.now().strftime("%Y-%m-%d %H:%M")
                        insert_reply(item["id"], current_student, reply_text, t)
                        st.rerun()
                # 展示全部回复
                replies = get_replies_by_pid(item["id"])
                if replies:
                    st.divider()
                    st.subheader("楼中楼回复")
                    for r in replies:
                        st.write(f"{r['writer']}({r['time']})：{r['content']}")
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 2. 给同学写评语（取消固定标签，自由输入，AI自动算分） =====================
    elif nav_menu == "给同学写评语":
        st.markdown("### 🏷️ 自由写下对同学的评价，AI自动分析性格维度")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        target_stu = st.selectbox("选择你想评价的同学", CLASS_STUDENTS)
        comment_input = st.text_area("写下你对TA的毕业心里话/性格描述（自由填写）", height=120)
        submit_tag = st.button("保存这条评语")
        st.markdown('</div>', unsafe_allow_html=True)

        if submit_tag and comment_input.strip():
            insert_tag(target_stu, current_student, comment_input)
            st.success(f"已为{target_stu}保存评语，AI会自动解析性格标签")
            st.rerun()

        st.markdown(f"## 📝 {target_stu} 收到的评语预览（完整内容仅本人登录可见）")
        all_tag_list = st.session_state.cache_tags
        target_tags = [x for x in all_tag_list if x["target_student"] == target_stu]
        if not target_tags:
            st.info(f"还没有人给{target_stu}写评语哦")
        else:
            for t in target_tags[:3]:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"来自{t['writer']}")
                st.write(f"评语预览：{t['comment'][:60]}……")
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 3. 我的专属档案（AI自动计算性格雷达图） =====================
    elif nav_menu == "我的专属档案":
        st.markdown(f"### 💌 {current_student} 的专属毕业评语档案（仅自己可见）")
        all_tag_list = st.session_state.cache_tags
        my_tags = [x for x in all_tag_list if x["target_student"] == current_student]

        if not my_tags:
            st.warning("暂时还没有同学给你写评语，快去邀请大家为你留言吧")
        else:
            # 合并所有评语文本，生成词云
            all_comment_str = ""
            total_score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
            for t in my_tags:
                all_comment_str += t["comment"] + " "
                single_score = ai_calc_person_score(t["comment"])
                # 累加所有评语得分
                for k in total_score.keys():
                    total_score[k] += single_score[k]

            # 词云缓存，不重复生成
            if st.session_state.wordcloud_img is None:
                wc = WordCloud(
                    background_color="#fff7f5",
                    width=800, height=400,
                    colormap="Reds",
                    contour_width=1, contour_color="#c83e3e"
                ).generate(all_comment_str)
                st.session_state.wordcloud_img = wc.to_image()
            st.markdown("#### 🔖 大家对你的描述词云")
            st.image(st.session_state.wordcloud_img, width=900)

            # 雷达图缓存
            if st.session_state.radar_fig is None:
                labels = list(total_score.keys())
                vals = list(total_score.values())
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
                st.session_state.radar_fig = fig
            st.markdown("#### 📊 AI综合性格维度雷达图")
            st.pyplot(st.session_state.radar_fig)

            # 全部私密评语
            st.markdown("#### 📩 全班写给你的所有心里话")
            for item in my_tags:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"评价人：{item['writer']}")
                st.write(f"完整留言：{item['comment']}")
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 4. 班级时光大事记（支持多图上传） =====================
    elif nav_menu == "班级时光大事记":
        st.markdown("### 📅 石榴16班共同大事记，全班都能记录（支持上传图片）")
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        event_date = st.date_input("这件事发生的日期")
        event_title = st.text_input("事件标题（例：百日誓师、全班合照）")
        event_detail = st.text_area("详细记录这件难忘的班级小事", height=100)
        event_imgs = st.file_uploader("上传配图（最多9张）", type=["png","jpg","jpeg"], accept_multiple_files=True)
        add_event_btn = st.button("存入班级时光册")
        st.markdown('</div>', unsafe_allow_html=True)

        if add_event_btn and event_title.strip():
            img_list = []
            if event_imgs and len(event_imgs) <=9:
                for f in event_imgs:
                    img_list.append(compress_and_encode(f))
            insert_event(event_date, event_title, event_detail, current_student, img_list)
            st.success("这件大事已经存入班级时光档案啦")
            st.rerun()

        st.markdown("## 📖 十六班全部时光记录（由新到旧）")
        event_data = st.session_state.cache_events
        if not event_data:
            st.info("还没有记录班级大事，快来写下第一件难忘回忆")
        else:
            for ev in event_data:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"📆 {ev['event_date']} | 记录人：{ev['recorder']}")
                st.subheader(ev["title"])
                st.write(ev["detail"])
                img_list = ev.get("images", [])
                if len(img_list)>0:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for b64 in img_list:
                        img_bin = base64.b64decode(b64)
                        st.image(io.BytesIO(img_bin), width=200)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 5. 星海漂流瓶（打捞动画+独立大展示区） =====================
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
                bottle_all = st.session_state.cache_bottles
                if len(bottle_all) == 0:
                    st.info("星海还没有漂流瓶，先投放一个吧")
                    st.session_state.current_bottle = None
                else:
                    pick = random.choice(bottle_all)
                    st.session_state.current_bottle = pick
                    st.session_state.bottle_anim = True
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        total_bottle = len(st.session_state.cache_bottles)
        st.info(f"当前星海一共有 {total_bottle} 只漂流瓶等待打捞")
        st.divider()

        # 独立大区域展示漂流瓶
        if st.session_state.current_bottle:
            if st.session_state.bottle_anim:
                components.html("""
                <div style="text-align:center;font-size:40px;color:#4488cc;">
                🫧 海浪翻涌，漂流瓶缓缓浮起...
                </div>
                """, height=80)
            st.markdown('<div class="bottle-show-box">', unsafe_allow_html=True)
            st.subheader("🌊 你打捞到的漂流瓶")
            b = st.session_state.current_bottle
            st.write(f"投递时间：{b['create_time']}")
            st.markdown(f"### {b['content']}")
            st.markdown('</div>', unsafe_allow_html=True)