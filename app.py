import streamlit as st
from streamlit_option_menu import option_menu
import matplotlib.pyplot as plt
import numpy as np
from wordcloud import WordCloud
from PIL import Image
import io
import base64
from datetime import datetime, timedelta
import random
from supabase import create_client, Client
import streamlit.components.v1 as components

# ===================== 页面基础配置 =====================
st.set_page_config(page_title="石榴16班毕业纪念册", page_icon="🍅", layout="wide")

# 全局暖系CSS（优化滚动、按钮、卡片体验）
warm_css = """
<style>
.stApp {
    background: linear-gradient(140deg, #fff7f2 0%, #ffe9e3 40%, #fde0d8 100%);
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
    background: rgba(255, 255, 255, 0.82);
    box-shadow: 0 2px 10px rgba(200, 60, 60, 0.08);
    margin: 12px 0;
    position: relative;
    transition: 0.2s;
}
.card-box:hover {
    box-shadow: 0 4px 14px rgba(200, 60, 60, 0.12);
}
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
    background: rgba(240,248,255,0.85);
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
/* 手动刷新按钮专用样式 */
.refresh-btn button {
    background: #228be6 !important;
}
.refresh-btn button:hover {
    background: #1971c2 !important;
}
</style>
"""
st.markdown(warm_css, unsafe_allow_html=True)

# ===================== 15秒自动局部刷新Fragment（稳定低负载） =====================
@st.fragment(run_every=timedelta(seconds=15))
def auto_sync_data():
    # 仅清空留言、回复缓存，其余模块不影响，最小请求开销
    st.session_state.cache_ts_forum = None
    st.session_state.cache_ts_replies = None
    st.caption("🔄 系统每15秒自动同步留言数据")

auto_sync_data()

# ===================== Supabase 全局单例 =====================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ===================== 通用工具函数 =====================
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

def cut_long_text(text, max_len=80):
    if len(text) <= max_len:
        return text, False
    return text[:max_len] + "...", True

def ai_calc_person_score(comment_text: str):
    text = comment_text.lower()
    score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
    happy = ["开朗","乐观","阳光","开心","积极","元气","爱笑","治愈"]
    soft = ["温柔","贴心","细心","善良","安静","暖心","细腻"]
    funny = ["搞笑","有趣","好玩","幽默","沙雕","活泼","梗多"]
    hard = ["努力","自律","学霸","认真","踏实","上进","刻苦"]
    out = ["外向","社牛","大方","合群","自来熟","健谈"]
    for word in happy:
        if word in text: score["乐观"] += 1
    for word in soft:
        if word in text: score["温柔"] += 1
    for word in funny:
        if word in text: score["有趣"] += 1
    for word in hard:
        if word in text: score["自律"] += 1
    for word in out:
        if word in text: score["外向"] += 1
    return score

# ===================== Session状态初始化 =====================
if "login_username" not in st.session_state:
    st.session_state.login_username = None
if "show_user_drawer" not in st.session_state:
    st.session_state.show_user_drawer = False
if "current_bottle" not in st.session_state:
    st.session_state.current_bottle = None
if "bottle_anim" not in st.session_state:
    st.session_state.bottle_anim = None

# 数据缓存容器
if "cache_users" not in st.session_state: st.session_state.cache_users = {}
if "cache_forum" not in st.session_state: st.session_state.cache_forum = []
if "cache_replies" not in st.session_state: st.session_state.cache_replies = []
if "cache_tags" not in st.session_state: st.session_state.cache_tags = []
if "cache_profile" not in st.session_state: st.session_state.cache_profile = []
if "cache_msg" not in st.session_state: st.session_state.cache_msg = []
if "cache_events" not in st.session_state: st.session_state.cache_events = []
if "cache_bottles" not in st.session_state: st.session_state.cache_bottles = []

# 缓存时间戳（统一8秒有效期，小于15秒自动刷新间隔）
cache_ts_list = [
    "cache_ts_users","cache_ts_forum","cache_ts_replies","cache_ts_tags",
    "cache_ts_profile","cache_ts_msg","cache_ts_events","cache_ts_bottles"
]
for k in cache_ts_list:
    if k not in st.session_state:
        st.session_state[k] = None

# 分页全局状态（留言分页、单帖子评论分页）
if "forum_page" not in st.session_state:
    st.session_state.forum_page = 1
if "forum_page_size" not in st.session_state:
    st.session_state.forum_page_size = 10  # 每页10条帖子
if "reply_page_map" not in st.session_state:
    st.session_state.reply_page_map = {}  # key=帖子id，value=评论页码
if "reply_page_size" not in st.session_state:
    st.session_state.reply_page_size = 5  # 每条帖子下评论每页5条

# 图表缓存
if "wordcloud_img" not in st.session_state: st.session_state.wordcloud_img = None
if "radar_fig" not in st.session_state: st.session_state.radar_fig = None

CLASS_STUDENTS = [
    '马浩然', '王一帆', '王原穗', '王韵琪', '卢芷清',
    '冯孝楚', '伍梓晨', '刘卓轩', '刘倩影', '汤乐宜',
    '李子杰', '李乐祺', '李辰', '李奕安', '李浩源',
    '李想', '杨宸涵', '吴桂祺', '何泳琳', '邹丝羽',
    '沈君铭', '张睿琪', '陈子昂', '陈天泽', '陈佳宜',
    '武帅宇', '林璟昊', '罗洁颖', '罗钰琳', '罗森耀',
    '罗颢畦', '郑熙潼', '赵宇', '施昕彤', '姚优烨',
    '聂子岚', '莫怀浅', '凌浩宇', '高泓', '高梓铭',
    '黄梓轩', '黄敏霞', '黄灏哲', '戚志邦', '温曈',
    '谢安然', '赖昊林', '蔡芷菡', '潘佳岩', '潘柏晋'
]

# ===================== 懒加载工具函数（统一8秒缓存） =====================
def load_users():
    now = datetime.now()
    if st.session_state.cache_ts_users and (now - st.session_state.cache_ts_users) < timedelta(seconds=8):
        return st.session_state.cache_users
    res = supabase.table("user_accounts").select("*").limit(200).execute()
    user_dict = {}
    for row in res.data:
        user_dict[row["username"]] = {"pwd": row["password"], "name": row["student_name"]}
    st.session_state.cache_users = user_dict
    st.session_state.cache_ts_users = now
    return user_dict

def load_forum():
    now = datetime.now()
    if st.session_state.cache_ts_forum and (now - st.session_state.cache_ts_forum) < timedelta(seconds=8):
        return st.session_state.cache_forum
    # 预加载全部数据，分页前端切片，数据库仅一次请求
    res = supabase.table("forum_messages").select("*").order("id", desc=True).limit(1000).execute()
    st.session_state.cache_forum = res.data
    st.session_state.cache_ts_forum = now
    return res.data

def load_replies():
    now = datetime.now()
    if st.session_state.cache_ts_replies and (now - st.session_state.cache_ts_replies) < timedelta(seconds=8):
        return st.session_state.cache_replies
    res = supabase.table("forum_reply").select("*").limit(2000).execute()
    st.session_state.cache_replies = res.data
    st.session_state.cache_ts_replies = now
    return res.data

def load_tags():
    now = datetime.now()
    if st.session_state.cache_ts_tags and (now - st.session_state.cache_ts_tags) < timedelta(seconds=8):
        return st.session_state.cache_tags
    res = supabase.table("tag_data").select("*").limit(300).execute()
    st.session_state.cache_tags = res.data
    st.session_state.cache_ts_tags = now
    return res.data

def load_profile():
    now = datetime.now()
    if st.session_state.cache_ts_profile and (now - st.session_state.cache_ts_profile) < timedelta(seconds=8):
        return st.session_state.cache_profile
    res = supabase.table("user_profile").select("*").limit(200).execute()
    st.session_state.cache_profile = res.data
    st.session_state.cache_ts_profile = now
    return res.data

def load_msg():
    now = datetime.now()
    if st.session_state.cache_ts_msg and (now - st.session_state.cache_ts_msg) < timedelta(seconds=8):
        return st.session_state.cache_msg
    res = supabase.table("private_msg").select("*").limit(300).execute()
    st.session_state.cache_msg = res.data
    st.session_state.cache_ts_msg = now
    return res.data

def load_events():
    now = datetime.now()
    if st.session_state.cache_ts_events and (now - st.session_state.cache_ts_events) < timedelta(seconds=8):
        return st.session_state.cache_events
    res = supabase.table("class_events").select("*").order("event_date", desc=True).limit(100).execute()
    st.session_state.cache_events = res.data
    st.session_state.cache_ts_events = now
    return res.data

def load_bottle():
    now = datetime.now()
    if st.session_state.cache_ts_bottles and (now - st.session_state.cache_ts_bottles) < timedelta(seconds=8):
        return st.session_state.cache_bottles
    res = supabase.table("bottle_list").select("*").limit(300).execute()
    st.session_state.cache_bottles = res.data
    st.session_state.cache_ts_bottles = now
    return res.data

# ===================== 数据库写入函数 =====================
def add_new_user(uname, pwd, sname):
    supabase.table("user_accounts").insert({
        "username": uname,
        "password": pwd,
        "student_name": sname
    }).execute()
    st.session_state.cache_ts_users = None

def get_user_profile(username):
    prof_list = load_profile()
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
    st.session_state.cache_ts_profile = None

def send_msg(from_user, to_student, content):
    supabase.table("private_msg").insert({
        "sender": from_user,
        "target_student": to_student,
        "content": content,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }).execute()
    st.session_state.cache_ts_msg = None

def get_my_msg(student_name):
    all_msg = load_msg()
    return [m for m in all_msg if m["target_student"] == student_name]

def insert_forum(author, text, img_list, vid, t):
    supabase.table("forum_messages").insert({
        "author": author,
        "text_content": text,
        "images": img_list,
        "video": vid,
        "create_time": t,
        "like_count": 0
    }).execute()
    st.session_state.cache_ts_forum = None

def add_like(post_id):
    supabase.rpc("inc_like", {"pid": post_id}).execute()
    st.session_state.cache_ts_forum = None

def get_replies_by_pid(pid):
    all_r = load_replies()
    target = [r for r in all_r if r["post_id"] == pid]
    target.sort(key=lambda x: x["time"], reverse=False)
    return target

def insert_reply(post_id, writer, text, t):
    supabase.table("forum_reply").insert({
        "post_id": post_id,
        "writer": writer,
        "content": text,
        "time": t
    }).execute()
    st.session_state.cache_ts_replies = None

def insert_tag(target, writer, comment):
    supabase.table("tag_data").insert({
        "target_student": target,
        "writer": writer,
        "comment": comment
    }).execute()
    st.session_state.cache_ts_tags = None

def insert_event(date, title, detail, recorder, img_list):
    supabase.table("class_events").insert({
        "event_date": str(date),
        "title": title,
        "detail": detail,
        "recorder": recorder,
        "images": img_list
    }).execute()
    st.session_state.cache_ts_events = None

def insert_bottle(content, t):
    supabase.table("bottle_list").insert({
        "content": content,
        "create_time": t
    }).execute()
    st.session_state.cache_ts_bottles = None

# ===================== 页面头部：标题 + 手动刷新按钮 =====================
header_col1, header_col2, header_col3 = st.columns([8, 1, 1])
with header_col1:
    st.markdown('<div class="main-title">🍅 石榴16班 · 毕业纪念册</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">十六岁的我们，岁岁常相见</div>', unsafe_allow_html=True)
with header_col2:
    # 手动刷新按钮：一键清空留言缓存，立刻拉取新数据
    st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
    if st.button("🔃 手动刷新", key="manual_refresh"):
        with st.spinner("正在同步最新留言..."):
            st.session_state.cache_ts_forum = None
            st.session_state.cache_ts_replies = None
            load_forum()
            load_replies()
        st.success("✅ 数据已刷新完成！")
    st.markdown('</div>', unsafe_allow_html=True)
with header_col3:
    if st.session_state.login_username:
        if st.button("👤 个人中心"):
            st.session_state.show_user_drawer = not st.session_state.show_user_drawer

# ===================== 右侧抽屉个人中心 =====================
if st.session_state.show_user_drawer and st.session_state.login_username:
    with st.sidebar:
        st.header("👤 个人中心")
        user_dict = load_users()
        user_info = user_dict[st.session_state.login_username]
        current_student = user_info["name"]
        tab_msg, tab_profile, tab_view = st.tabs(["私信信箱", "我的毕业档案", "查看同学档案"])
        # 私信
        with tab_msg:
            st.subheader("发送私信")
            target = st.selectbox("发给哪位同学", CLASS_STUDENTS)
            msg_text = st.text_area("私信内容")
            if st.button("发送") and msg_text.strip():
                send_msg(current_student, target, msg_text)
                st.success("发送成功")
                st.rerun()
            st.divider()
            st.subheader("收件箱")
            msgs = get_my_msg(current_student)
            if not msgs:
                st.info("暂无私信")
            for m in msgs:
                st.write(f"【{m['time']}】来自{m['sender']}：{m['content']}")
        # 个人档案填写
        with tab_profile:
            st.subheader("完善毕业档案")
            prof = get_user_profile(st.session_state.login_username) or {}
            nick = st.text_input("昵称", value=prof.get("nick", ""))
            hobby = st.text_input("爱好", value=prof.get("hobby", ""))
            dream = st.text_input("未来理想", value=prof.get("dream", ""))
            motto = st.text_area("座右铭", value=prof.get("motto", ""))
            contact = st.text_input("联系方式", value=prof.get("contact", ""))
            if st.button("保存档案"):
                save_profile(st.session_state.login_username, {
                    "nick": nick, "hobby": hobby, "dream": dream,
                    "motto": motto, "contact": contact
                })
                st.success("档案已保存")
        # 查看他人档案
        with tab_view:
            view_target = st.selectbox("选择查看同学", CLASS_STUDENTS)
            all_u = load_users()
            view_uname = None
            for k,v in all_u.items():
                if v["name"] == view_target:
                    view_uname = k
                    break
            if view_uname:
                vp = get_user_profile(view_uname)
                if not vp:
                    st.info("该同学未填写档案")
                else:
                    st.markdown(f"""
**昵称：**{vp['nick']}
**爱好：**{vp['hobby']}
**理想：**{vp['dream']}
**座右铭：**{vp['motto']}
""")

# ===================== 登录注册页面 =====================
if st.session_state.login_username is None:
    st.warning("🔐 请先注册/登录账号，查看全部班级内容")
    tab_login, tab_reg = st.tabs(["账号登录", "新生注册"])
    with tab_login:
        uname = st.text_input("账号")
        pwd = st.text_input("密码", type="password")
        if st.button("登录进入纪念册"):
            user_list = load_users()
            if uname in user_list and user_list[uname]["pwd"] == pwd:
                st.session_state.login_username = uname
                st.rerun()
            else:
                st.error("账号或密码错误")
    with tab_reg:
        reg_user = st.text_input("设置账号名")
        reg_pwd = st.text_input("设置密码", type="password")
        reg_stu = st.selectbox("绑定姓名", CLASS_STUDENTS)
        if st.button("完成注册"):
            user_list = load_users()
            if reg_user.strip() == "":
                st.warning("账号不能为空")
            elif reg_user in user_list:
                st.warning("账号已存在")
            elif reg_pwd.strip() == "":
                st.warning("密码不能为空")
            else:
                add_new_user(reg_user, reg_pwd, reg_stu)
                st.success("注册成功，请登录")
else:
    user_dict = load_users()
    user_info = user_dict[st.session_state.login_username]
    current_student = user_info["name"]
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

    # ===================== 1. 班级留言墙（分页优化，解决大量数据卡顿） =====================
    if nav_menu == "班级留言墙":
        st.markdown("### 🍅 石榴16班留言墙 · 分享日常与毕业回忆")
        search_key = st.text_input("🔍 搜索帖子内容", placeholder="输入关键词筛选留言")
        st.divider()

        # 发帖区域
        post_text = st.text_area("写下想和全班分享的话：", height=100, placeholder="在这里写下你的故事...")
        st.subheader("上传图片（最多9张，自动压缩）")
        upload_imgs = st.file_uploader("多选图片", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        upload_video = st.file_uploader("上传短视频", type=["mp4", "mov"])
        submit_btn = st.button("发布这条留言")

        if submit_btn and post_text.strip():
            with st.spinner("发布中..."):
                img_b64_list = []
                if upload_imgs and len(upload_imgs) <=9:
                    for f in upload_imgs:
                        img_b64_list.append(compress_and_encode(f))
                vid_b64 = video_to_b64(upload_video) if upload_video else None
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                insert_forum(current_student, post_text, img_b64_list, vid_b64, now_time)
            st.success("🎉 留言发布成功！自动刷新可见")
            st.rerun()

        # 帖子分页逻辑
        st.markdown("## 📜 全班所有人的留言")
        all_forum_raw = load_forum()
        # 筛选搜索
        forum_filtered = []
        if search_key.strip():
            for item in all_forum_raw:
                if search_key.lower() in item["text_content"].lower():
                    forum_filtered.append(item)
        else:
            forum_filtered = all_forum_raw

        total_post = len(forum_filtered)
        page_size = st.session_state.forum_page_size
        total_page = (total_post + page_size - 1) // page_size

        # 分页控制器
        pg1, pg2, pg3 = st.columns([1,1,3])
        with pg1:
            if st.button("上一页") and st.session_state.forum_page > 1:
                st.session_state.forum_page -= 1
                st.rerun()
        with pg2:
            if st.button("下一页") and st.session_state.forum_page < total_page:
                st.session_state.forum_page += 1
                st.rerun()
        with pg3:
            st.caption(f"共 {total_post} 条留言，当前第 {st.session_state.forum_page}/{total_page} 页（每页{page_size}条）")

        # 切片取当前页数据
        start_idx = (st.session_state.forum_page - 1) * page_size
        end_idx = start_idx + page_size
        forum_data = forum_filtered[start_idx:end_idx]

        if len(forum_data) == 0:
            st.info("暂无匹配留言，换关键词或等待他人发布")
        else:
            for item in forum_data:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                like_num = item.get("like_count", 0)
                all_replies = get_replies_by_pid(item["id"])
                reply_count = len(all_replies)
                full_text = item["text_content"]
                short_text, need_expand = cut_long_text(full_text, 80)

                # 作者+时间
                st.write(f"**{item['author']}** · {item['create_time']}")
                # 正文+全文按钮
                t_col, btn_col = st.columns([8, 1])
                with t_col:
                    st.write(short_text)
                with btn_col:
                    if need_expand and st.button("全文", key=f"expand_{item['id']}"):
                        st.info(f"完整内容：{full_text}")
                # 图片/视频
                img_list = item.get("images", [])
                if len(img_list) > 0:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for b64 in img_list:
                        img_bin = base64.b64decode(b64)
                        st.image(io.BytesIO(img_bin), width=200)
                    st.markdown('</div>', unsafe_allow_html=True)
                vid_b64 = item.get("video")
                if vid_b64:
                    vid_bin = base64.b64decode(vid_b64)
                    st.video(io.BytesIO(vid_bin))
                # 底部交互栏
                col_share, col_msg, col_like = st.columns([1,1,1])
                with col_share:
                    st.write("🔁 转发 0")
                with col_msg:
                    st.write(f"💬 评论 {reply_count}")
                with col_like:
                    st.write(f"❤️ 点赞 {like_num}")

                # hover操作栏
                st.markdown('<div class="post-action-bar">', unsafe_allow_html=True)
                # 点赞按钮
                if st.button("❤️", key=f"like_{item['id']}"):
                    add_like(item["id"])
                    st.rerun()

                # 楼中楼回复输入框（修复KeyError）
                input_key = f"reply_input_{item['id']}"
                if input_key not in st.session_state:
                    st.session_state[input_key] = ""
                reply_input = st.text_input("楼中楼回复", key=input_key, placeholder="写下你的评论...")

                # 提交回复
                if st.button("提交回复", key=f"submit_reply_{item['id']}"):
                    content = reply_input.strip()
                    if not content:
                        st.warning("回复内容不能为空！")
                    else:
                        try:
                            t = datetime.now().strftime("%Y-%m-%d %H:%M")
                            insert_reply(item["id"], current_student, content, t)
                            st.success("回复发送成功！")
                            st.rerun()
                        except Exception as err:
                            st.error(f"回复失败：{str(err)}")

                # 评论分页展示
                if all_replies:
                    # 初始化该帖子评论页码
                    pid = str(item["id"])
                    if pid not in st.session_state.reply_page_map:
                        st.session_state.reply_page_map[pid] = 1
                    rp = st.session_state.reply_page_map[pid]
                    r_size = st.session_state.reply_page_size
                    total_rp = (len(all_replies) + r_size - 1) // r_size
                    r_start = (rp - 1) * r_size
                    r_end = r_start + r_size
                    reply_page_data = all_replies[r_start:r_end]

                    with st.expander(f"展开全部回复 ({reply_count}) — 第{rp}/{total_rp}页"):
                        for r in reply_page_data:
                            st.write(f"{r['writer']} ({r['time']})：{r['content']}")
                        # 评论分页切换
                        r1, r2 = st.columns([1,1])
                        with r1:
                            if st.button("上一页评论", key=f"rp_prev_{pid}") and rp>1:
                                st.session_state.reply_page_map[pid] -= 1
                                st.rerun()
                        with r2:
                            if st.button("下一页评论", key=f"rp_next_{pid}") and rp < total_rp:
                                st.session_state.reply_page_map[pid] += 1
                                st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 2. 给同学写评语 =====================
    elif nav_menu == "给同学写评语":
        st.markdown("### 🏷️ 自由写下评语，AI自动解析性格维度")
        target = st.selectbox("选择评价同学", CLASS_STUDENTS)
        comment_input = st.text_area("写下对TA的心里话、性格描述", height=120, placeholder="温柔、自律、乐观...")
        submit_btn = st.button("保存评语")
        if submit_btn and comment_input.strip():
            with st.spinner("保存中..."):
                insert_tag(target, current_student, comment_input)
            st.success(f"已为{target}保存评语")
            st.rerun()
        st.markdown(f"## 📝 {target} 收到的评语预览")
        all_tag_list = load_tags()
        target_tags = [x for x in all_tag_list if x["target_student"] == target]
        if not target_tags:
            st.info("暂无评语")
        else:
            for t in target_tags[:3]:
                st.write(f"来自：{t['writer']}")
                st.write(f"预览：{t['comment'][:60]}……")
                st.divider()

    # ===================== 3. 我的专属档案 =====================
    elif nav_menu == "我的专属档案":
        st.markdown(f"### 💌 {current_student} 专属毕业档案（仅本人可见）")
        all_tag_list = load_tags()
        my_tags = [x for x in all_tag_list if x["target_student"] == current_student]
        if not my_tags:
            st.warning("暂时没有同学给你写评语")
        else:
            all_comment_text = ""
            total_score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
            for t in my_tags:
                all_comment_text += t["comment"] + " "
                single_score = ai_calc_person_score(t["comment"])
                for k in total_score.keys():
                    total_score[k] += single_score[k]
            # 词云缓存
            if st.session_state.wordcloud_img is None:
                wc = WordCloud(
                    background_color="#fff7f2",
                    width=800, height=400,
                    colormap="Reds",
                    contour_width=1, contour_color="#c83e3e"
                ).generate(all_comment_text)
                st.session_state.wordcloud_img = wc.to_image()
            st.markdown("#### 🔖 大家对你的描述词云")
            st.image(st.session_state.wordcloud_img, width=900)
            # 雷达图
            if st.session_state.radar_fig is None:
                plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'Arial Unicode MS']
                plt.rcParams['axes.unicode_minus'] = False
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
                ax.set_facecolor("#fff7f2")
                fig.patch.set_facecolor("#fff7f2")
                ax.tick_params(colors="#994444")
                st.session_state.radar_fig = fig
            st.markdown("#### 📊 AI综合性格雷达图")
            st.pyplot(st.session_state.radar_fig)
            st.markdown("#### 📩 全班写给你的所有心里话")
            for item in my_tags:
                st.write(f"评价人：{item['writer']}")
                st.write(f"完整留言：{item['comment']}")
                st.divider()

    # ===================== 4. 班级时光大事记 =====================
    elif nav_menu == "班级时光大事记":
        st.markdown("### 📅 班级时光大事记，支持上传配图")
        event_date = st.date_input("事件发生日期")
        event_title = st.text_input("事件标题", placeholder="运动会/研学/毕业班会")
        event_detail = st.text_area("事件详情", height=100)
        event_imgs = st.file_uploader("上传配图（最多9张）", type=["png","jpg","jpeg"], accept_multiple_files=True)
        add_btn = st.button("存入时光册")
        if add_btn and event_title.strip():
            with st.spinner("保存大事记..."):
                img_list = []
                if event_imgs and len(event_imgs) <=9:
                    for f in event_imgs:
                        img_list.append(compress_and_encode(f))
                insert_event(event_date, event_title, event_detail, current_student, img_list)
            st.success("事件保存成功")
            st.rerun()
        st.markdown("## 📖 全部班级大事记")
        event_data = load_events()
        if not event_data:
            st.info("暂无记录")
        else:
            for ev in event_data:
                st.write(f"📆 {ev['event_date']} | 记录人：{ev['recorder']}")
                st.subheader(ev["title"])
                st.write(ev["detail"])
                img_list = ev.get("images", [])
                if len(img_list) > 0:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for b64 in img_list:
                        img_bin = base64.b64decode(b64)
                        st.image(io.BytesIO(img_bin), width=200)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

    # ===================== 5. 星海漂流瓶 =====================
    elif nav_menu == "星海漂流瓶":
        st.markdown("### 🌊 匿名漂流瓶 · 藏起毕业心事")
        col_throw, col_get = st.columns(2)
        with col_throw:
            bottle_text = st.text_area("写下心事投放星海", height=120, placeholder="悄悄留下你的愿望...")
            if st.button("投放漂流瓶"):
                if bottle_text.strip():
                    now_t = datetime.now().strftime("%m-%d %H:%M")
                    insert_bottle(bottle_text, now_t)
                    st.success("投放成功！")
                    st.rerun()
        with col_get:
            st.subheader("随机打捞漂流瓶")
            if st.button("开始打捞"):
                bottle_all = load_bottle()
                if len(bottle_all) == 0:
                    st.info("星海暂无漂流瓶")
                    st.session_state.current_bottle = None
                else:
                    pick = random.choice(bottle_all)
                    st.session_state.current_bottle = pick
                    st.session_state.bottle_anim = True
                    st.rerun()
        total_bottle = len(load_bottle())
        st.info(f"当前星海共有 {total_bottle} 只漂流瓶")
        st.divider()
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