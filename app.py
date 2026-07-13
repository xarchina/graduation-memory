import streamlit as st
import base64
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from supabase import create_client, Client
from PIL import Image
import io
from streamlit_option_menu import option_menu
from realtime import AsyncRealtimeClient, RealtimeSubscribeStates
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ===================== 全局基础配置 =====================
st.set_page_config(page_title="石榴16班毕业纪念册", page_icon="🍅", layout="wide")

# 明暗主题切换
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"
theme_toggle = st.sidebar.toggle("🌙 深色模式", value=(st.session_state.theme_mode == "dark"))
if theme_toggle:
    st.session_state.theme_mode = "dark"
else:
    st.session_state.theme_mode = "light"

# 全局CSS 双主题 + 圆形头像 + 卡片私信 + 星光墙样式
if st.session_state.theme_mode == "light":
    bg_gradient = "linear-gradient(140deg, #fff7f2 0%, #ffe9e3 40%, #fde0d8 100%)"
    text_color = "#332222"
    card_bg = "rgba(255,255,255,0.82)"
    input_bg = "#ffffff"
else:
    bg_gradient = "#1a1a2e"
    text_color = "#f0f0f0"
    card_bg = "rgba(30,30,50,0.85)"
    input_bg = "#2d2d44"

warm_css = f"""
<style>
.stApp {{
    background: {bg_gradient};
    color: {text_color};
}}
.main-title {{
    font-size: 40px;
    font-weight: 600;
    text-align: center;
    color: #c83e3e;
    margin-bottom: 8px;
}}
.sub-title {{
    text-align: center;
    color: #994444;
    font-size: 16px;
    margin-bottom: 32px;
}}
.card-box {{
    border: 1px solid #e8a8a8;
    border-radius: 16px;
    padding: 22px;
    background: {card_bg};
    box-shadow: 0 2px 10px rgba(200, 60, 60, 0.08);
    margin: 12px 0;
    position: relative;
    transition: 0.2s;
}}
.card-box:hover {{
    box-shadow: 0 4px 14px rgba(200, 60, 60, 0.12);
}}
/* 圆形头像 */
.avatar-circle {{
    width: 48px;
    height: 48px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #e8a8a8;
    cursor: pointer;
}}
/* 互动栏固定显示 */
.post-action-bar {{
    display:block;
    margin-top:12px;
    padding:10px;
    background:#fff2f2;
    border-radius:10px;
    display:flex;
    gap:30px;
}}
/* 评论输入框默认隐藏 */
.reply-panel {{
    display:none;
    margin-top:10px;
    padding:12px;
    background:#fff0f0;
    border-radius:12px;
}}
.reply-panel.show {{
    display:block;
}}
/* 私信信件卡片 */
.msg-card {{
    border-radius:14px;
    padding:16px;
    margin:8px 0;
    background:rgba(255,240,240,0.7);
}}
.msg-send {{
    background:#d65c5c;
    color:white;
    border-radius:14px 14px 2px 14px;
    padding:8px 12px;
    margin:4px 0 4px auto;
    max-width:70%;
    width:fit-content;
}}
.msg-receive {{
    background:#f0e0e0;
    color:#222;
    border-radius:14px 14px 14px 2px;
    padding:8px 12px;
    margin:4px auto 4px 0;
    max-width:70%;
    width:fit-content;
}}
/* 星光墙头像网格 */
.star-grid {{
    display:grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap:20px;
    margin:20px 0;
}}
.star-card {{
    text-align:center;
    padding:12px;
    border-radius:12px;
    background:{card_bg};
}}
.bottle-show-box {{
    border: 2px solid #87CEEB;
    border-radius: 20px;
    padding: 40px;
    background: rgba(240,248,255,0.85);
    margin: 30px 0;
    min-height: 300px;
}}
.stButton>button {{
    background: linear-gradient(90deg, #d65c5c, #c44444);
    color: white !important;
    border: none;
    border-radius: 10px;
    height: 36px;
    font-weight: 500;
}}
.stButton>button:hover {{
    background: #b83838;
    transform: scale(1.01);
}}
div[data-baseweb="input"] input {{
    background: {input_bg} !important;
    color: {text_color} !important;
    caret-color: #c83e3e !important;
    border: 1px solid #ddbbbb !important;
    border-radius: 8px !important;
    padding: 9px 14px !important;
    font-size: 15px !important;
}}
div[data-baseweb="textarea"] textarea {{
    background: {input_bg} !important;
    color: {text_color} !important;
    caret-color: #c83e3e !important;
    border: 1px solid #ddbbbb !important;
    border-radius: 8px !important;
    padding: 11px 14px !important;
    font-size: 15px !important;
}}
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {{
    color: #996666 !important;
    opacity: 0.85 !important;
}}
hr {{
    border-color: #e2b0b0;
}}
.reply-box {{
    background:#fff0f0;
    padding:10px;
    border-radius:10px;
    margin:8px 0;
}}
.img-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap:8px;
}}
.refresh-btn button {{
    background: #228be6 !important;
}}
.refresh-btn button:hover {{
    background: #1971c2 !important;
}}
.danger-btn button {{
    background-color: #e03131 !important;
}}
.danger-btn button:hover {{
    background-color: #c92a2a !important;
}}
/* 顶部公告栏 */
.notice-bar {{
    background:#ffe066;
    color:#222;
    padding:8px 16px;
    border-radius:8px;
    text-align:center;
    font-weight:500;
    margin:10px 0;
}}
</style>
"""
st.markdown(warm_css, unsafe_allow_html=True)

# ===================== Realtime 实时订阅（替代15秒轮询，降低请求） =====================
if "realtime_client" not in st.session_state:
    st.session_state.realtime_client = None
if "realtime_channel" not in st.session_state:
    st.session_state.realtime_channel = None

async def setup_realtime():
    if st.session_state.realtime_client is not None:
        return
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    realtime_url = f"wss://{url.replace('https://', '').replace('.supabase.co', '')}.supabase.co/realtime/v1/websocket?apikey={key}&vsn=1.0.0"
    client = AsyncRealtimeClient(realtime_url, key)
    st.session_state.realtime_client = client
    await client.connect()
    channel = client.channel("class-forum")
    st.session_state.realtime_channel = channel
    def on_forum_change(payload):
        st.session_state.cache_ts_forum = None
        st.session_state.cache_ts_replies = None
        st.toast("📢 有新留言/回复！")
    channel.on_postgres_changes("*", "public", "forum_messages", on_forum_change)
    channel.on_postgres_changes("INSERT", "public", "forum_reply", on_forum_change)
    await channel.subscribe()

# ===================== Supabase 全局单例 =====================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)
supabase = init_supabase()

# ===================== Session状态初始化 =====================
# 登录
if "login_username" not in st.session_state:
    st.session_state.login_username = None
if "show_user_drawer" not in st.session_state:
    st.session_state.show_user_drawer = False
# 缓存时间戳
cache_ts_list = [
    "cache_ts_users","cache_ts_forum","cache_ts_replies","cache_ts_tags",
    "cache_ts_profile","cache_ts_msg","cache_ts_events","cache_ts_bottles","cache_ts_collect","cache_ts_notice"
]
for k in cache_ts_list:
    if k not in st.session_state:
        st.session_state[k] = None
# 缓存数据容器
cache_data_list = [
    "cache_users","cache_forum","cache_replies","cache_tags",
    "cache_profile","cache_msg","cache_events","cache_bottles","cache_collect","cache_notice"
]
for k in cache_data_list:
    if k not in st.session_state:
        st.session_state[k] = [] if k != "cache_users" else {}
# 分页全局状态
if "forum_page" not in st.session_state: st.session_state.forum_page = 1
if "forum_page_size" not in st.session_state: st.session_state.forum_page_size = 10
if "reply_page_map" not in st.session_state: st.session_state.reply_page_map = {}
if "reply_page_size" not in st.session_state: st.session_state.reply_page_size = 5
if "star_page" not in st.session_state: st.session_state.star_page = 1
if "star_page_size" not in st.session_state: st.session_state.star_page_size = 12
# 弹窗状态
if "open_reply_pid" not in st.session_state: st.session_state.open_reply_pid = None
if "reply_target_id" not in st.session_state: st.session_state.reply_target_id = None
if "view_user_detail" not in st.session_state: st.session_state.view_user_detail = None
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
    return base64.b64encode(buf.getvalue()).decode("utf-8")

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

def get_avatar_html(avatar_b64, student_name, click_key):
    if avatar_b64:
        src = f"data:image/jpeg;base64,{avatar_b64}"
    else:
        # 默认灰色头像占位
        src = "https://via.placeholder.com/48/cccccc/333333?text="+student_name[0]
    return f'<img class="avatar-circle" src="{src}" onclick="window.streamlitApi.setValue(\'{click_key}\', \'{student_name}\')">'

# ===================== 数据加载函数（统一8秒缓存，海量数据优化） =====================
def load_users():
    now = datetime.now()
    if st.session_state.cache_ts_users and (now - st.session_state.cache_ts_users) < timedelta(seconds=8):
        return st.session_state.cache_users
    res = supabase.table("user_accounts").select("*").limit(200).execute()
    user_dict = {}
    for row in res.data:
        user_dict[row["username"]] = row
    st.session_state.cache_users = user_dict
    st.session_state.cache_ts_users = now
    return user_dict

def load_forum():
    now = datetime.now()
    if st.session_state.cache_ts_forum and (now - st.session_state.cache_ts_forum) < timedelta(seconds=8):
        return st.session_state.cache_forum
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

def load_collect():
    now = datetime.now()
    if st.session_state.cache_ts_collect and (now - st.session_state.cache_ts_collect) < timedelta(seconds=8):
        return st.session_state.cache_collect
    res = supabase.table("user_collect").select("*").execute()
    st.session_state.cache_collect = res.data
    st.session_state.cache_ts_collect = now
    return res.data

def load_notice():
    now = datetime.now()
    if st.session_state.cache_ts_notice and (now - st.session_state.cache_ts_notice) < timedelta(seconds=8):
        return st.session_state.cache_notice
    res = supabase.table("system_notice").select("*").order("id", desc=True).limit(1).execute()
    st.session_state.cache_notice = res.data
    st.session_state.cache_ts_notice = now
    return res.data

# ===================== 数据库写入工具 =====================
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
    return {}

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
    return [m for m in all_msg if m["target_student"] == student_name or m["sender"] == student_name]

def insert_forum(author, text, img_list, vid, t, anonymous=False):
    supabase.table("forum_messages").insert({
        "author": author,
        "text_content": text,
        "images": img_list,
        "video": vid,
        "create_time": t,
        "like_count": 0,
        "is_anonymous": anonymous,
        "edit_time": None
    }).execute()
    st.session_state.cache_ts_forum = None

def edit_forum(post_id, new_text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    supabase.table("forum_messages").update({"text_content": new_text, "edit_time": now}).eq("id", post_id).execute()
    st.session_state.cache_ts_forum = None

def add_like(post_id):
    supabase.rpc("inc_like", {"pid": post_id}).execute()
    st.session_state.cache_ts_forum = None

def toggle_collect(username, post_id):
    collect_list = load_collect()
    exist = next((c for c in collect_list if c["username"] == username and c["post_id"] == post_id), None)
    if exist:
        supabase.table("user_collect").delete().eq("id", exist["id"]).execute()
    else:
        supabase.table("user_collect").insert({
            "username": username,
            "post_id": post_id,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }).execute()
    st.session_state.cache_ts_collect = None

def get_collect_posts(username):
    collect_list = load_collect()
    collect_pids = [c["post_id"] for c in collect_list if c["username"] == username]
    all_forum = load_forum()
    return [p for p in all_forum if p["id"] in collect_pids]

def get_replies_by_pid(pid):
    all_r = load_replies()
    target = [r for r in all_r if r["post_id"] == pid]
    target.sort(key=lambda x: x["time"], reverse=False)
    return target

def insert_reply(post_id, writer, text, t, reply_target=None):
    supabase.table("forum_reply").insert({
        "post_id": post_id,
        "writer": writer,
        "content": text,
        "time": t,
        "reply_target": reply_target
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

# ===================== 页面头部标题+手动刷新 =====================
header_col1, header_col2, header_col3 = st.columns([8, 1, 1])
with header_col1:
    st.markdown('<div class="main-title">🍅 石榴16班 · 毕业纪念册</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">十六岁的我们，岁岁常相见</div>', unsafe_allow_html=True)
with header_col2:
    st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
    if st.button("🔃 手动刷新", key="manual_refresh"):
        with st.spinner("同步最新数据..."):
            st.session_state.cache_ts_forum = None
            st.session_state.cache_ts_replies = None
            st.session_state.cache_ts_collect = None
            load_forum()
            load_replies()
        st.success("✅ 数据已刷新")
    st.markdown('</div>', unsafe_allow_html=True)
with header_col3:
    if st.session_state.login_username:
        if st.button("👤 个人中心"):
            st.session_state.show_user_drawer = not st.session_state.show_user_drawer

# 顶部全局公告栏
notice_data = load_notice()
if notice_data:
    st.markdown(f'<div class="notice-bar">📢 班级公告：{notice_data[0]["content"]}</div>', unsafe_allow_html=True)

# ===================== 登录注册页面 =====================
if st.session_state.login_username is None:
    st.warning("🔐 请登录后查看全部班级功能")
    tab_login, tab_reg = st.tabs(["账号登录", "新生注册"])
    with tab_login:
        uname = st.text_input("账号")
        pwd = st.text_input("密码", type="password")
        if st.button("登录进入纪念册"):
            user_list = load_users()
            if uname in user_list and user_list[uname]["password"] == pwd:
                st.session_state.login_username = uname
                # 启动实时订阅
                try:
                    asyncio.run(setup_realtime())
                except Exception as e:
                    st.warning(f"实时连接启动失败：{e}")
                st.rerun()
            else:
                st.error("账号或密码错误")
    with tab_reg:
        reg_user = st.text_input("设置账号名")
        reg_pwd = st.text_input("设置密码", type="password")
        reg_stu = st.selectbox("绑定姓名", CLASS_STUDENTS)
        if st.button("完成注册"):
            user_list = load_users()
            if not reg_user.strip():
                st.warning("账号不能为空")
            elif reg_user in user_list:
                st.warning("账号已存在")
            elif not reg_pwd.strip():
                st.warning("密码不能为空")
            else:
                add_new_user(reg_user, reg_pwd, reg_stu)
                st.success("注册成功，请登录")
else:
    # 登录后逻辑
    user_dict = load_users()
    user_info = user_dict[st.session_state.login_username]
    current_student = user_info["student_name"]
    current_username = st.session_state.login_username
    st.success(f"✅ 欢迎回来，{current_student}")
    if st.button("退出登录"):
        st.session_state.login_username = None
        st.rerun()
    # 顶部横向导航
    nav_menu = option_menu(
        menu_title=None,
        options=["班级留言墙", "给同学写评语", "个人专属档案", "班级星光墙", "班级时光大事记", "星海漂流瓶", "我的收藏留言"],
        icons=["chat-heart", "tag", "person-lines-fill", "stars", "calendar-heart", "water", "bookmark"],
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"background": "rgba(255,245,243,0.6)", "padding": "6px"},
            "nav-link": {"color":"#773333", "font-size":"16px"},
            "nav-link-selected": {"background": "#d65c5c", "color":"white"}
        }
    )

    # ===================== 1. 班级留言墙（朋友圈交互重构） =====================
    if nav_menu == "班级留言墙":
        st.markdown("### 🍅 石榴16班留言墙 · 分享日常与毕业回忆")
        col_search, col_sort = st.columns([4,1])
        with col_search:
            search_key = st.text_input("🔍 搜索帖子/人名", placeholder="关键词筛选留言")
        with col_sort:
            sort_type = st.selectbox("排序方式", ["最新发布", "点赞最多"])
        anonymous_tick = st.checkbox("匿名发布（隐藏你的姓名）")
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
                insert_forum(current_student, post_text, img_b64_list, vid_b64, now_time, anonymous_tick)
            st.success("🎉 留言发布成功！")
            st.rerun()

        # 留言分页处理
        st.markdown("## 📜 全班所有人的留言")
        all_forum_raw = load_forum()
        # 筛选搜索
        forum_filtered = []
        if search_key.strip():
            for item in all_forum_raw:
                if search_key.lower() in item["text_content"].lower() or search_key.lower() in item["author"].lower():
                    forum_filtered.append(item)
        else:
            forum_filtered = all_forum_raw
        # 排序
        if sort_type == "点赞最多":
            forum_filtered.sort(key=lambda x: x["like_count"], reverse=True)
        else:
            forum_filtered.sort(key=lambda x: x["id"], reverse=True)

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
            st.caption(f"共 {total_post} 条留言，第 {st.session_state.forum_page}/{total_page} 页（每页{page_size}条）")
        # 切片取当前页
        start_idx = (st.session_state.forum_page - 1) * page_size
        end_idx = start_idx + page_size
        forum_data = forum_filtered[start_idx:end_idx]

        if len(forum_data) == 0:
            st.info("暂无匹配留言，换关键词或等待他人发布")
        else:
            for item in forum_data:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                # 作者头像+名称
                prof = get_user_profile(item["author"])
                avatar_html = get_avatar_html(prof.get("avatar"), item["author"], "click_avatar_view")
                st.markdown(avatar_html, unsafe_allow_html=True)
                # 点击头像查看主页
                if "click_avatar_view" not in st.session_state:
                    st.session_state.click_avatar_view = ""
                avatar_click = st.session_state.click_avatar_view
                if avatar_click == item["author"]:
                    st.session_state.view_user_detail = item["author"]
                    st.rerun()
                # 作者+时间+编辑标记
                display_name = "匿名用户" if item.get("is_anonymous") else item["author"]
                st.write(f"**{display_name}** · {item['create_time']}")
                if item.get("edit_time"):
                    st.caption(f"（已编辑 {item['edit_time']}）")
                # 本人编辑按钮（发布10分钟内可编辑）
                create_dt = datetime.strptime(item["create_time"], "%Y-%m-%d %H:%M")
                now_dt = datetime.now()
                diff_min = (now_dt - create_dt).total_seconds() / 60
                if item["author"] == current_student and diff_min < 10:
                    edit_text = st.text_area("编辑留言", value=item["text_content"], key=f"edit_{item['id']}")
                    if st.button("保存修改", key=f"save_edit_{item['id']}"):
                        edit_forum(item["id"], edit_text)
                        st.success("修改完成")
                        st.rerun()
                # 正文折叠
                full_text = item["text_content"]
                short_text, need_expand = cut_long_text(full_text, 80)
                t_col, btn_col = st.columns([8, 1])
                with t_col:
                    st.write(short_text)
                with btn_col:
                    if need_expand and st.button("全文", key=f"expand_{item['id']}"):
                        st.info(f"完整内容：{full_text}")
                # 图片视频展示
                img_list = item.get("images", [])
                if len(img_list) > 0:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for b64 in img_list:
                        st.image(io.BytesIO(base64.b64decode(b64)), width=200)
                    st.markdown('</div>', unsafe_allow_html=True)
                vid_b64 = item.get("video")
                if vid_b64:
                    st.video(io.BytesIO(base64.b64decode(vid_b64)))
                # 互动栏：固定展示，无需hover
                st.markdown('<div class="post-action-bar">', unsafe_allow_html=True)
                col_share, col_msg, col_like, col_collect = st.columns([1,1,1,1])
                like_num = item.get("like_count", 0)
                all_replies = get_replies_by_pid(item["id"])
                reply_count = len(all_replies)
                # 转发
                with col_share:
                    st.write("🔁 转发 0")
                # 评论按钮：点击展开输入框
                with col_msg:
                    if st.button(f"💬 评论 {reply_count}", key=f"open_reply_{item['id']}"):
                        if st.session_state.open_reply_pid == item["id"]:
                            st.session_state.open_reply_pid = None
                        else:
                            st.session_state.open_reply_pid = item["id"]
                            st.session_state.reply_target_id = None
                        st.rerun()
                # 点赞按钮
                with col_like:
                    if st.button(f"❤️ 点赞 {like_num}", key=f"like_{item['id']}"):
                        add_like(item["id"])
                        st.rerun()
                # 收藏按钮
                with col_collect:
                    collect_list = load_collect()
                    is_collect = any(c["username"] == current_username and c["post_id"] == item["id"] for c in collect_list)
                    collect_text = "⭐ 已收藏" if is_collect else "☆ 收藏"
                    if st.button(collect_text, key=f"collect_{item['id']}"):
                        toggle_collect(current_username, item["id"])
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                # 评论输入面板（仅点击评论按钮才显示）
                if st.session_state.open_reply_pid == item["id"]:
                    st.markdown('<div class="reply-panel show">', unsafe_allow_html=True)
                    # 回复目标提示（回复某条评论）
                    if st.session_state.reply_target_id:
                        target_reply = next((r for r in all_replies if r["id"] == st.session_state.reply_target_id), None)
                        if target_reply:
                            st.caption(f"正在回复 @{target_reply['writer']}：{target_reply['content'][:30]}...")
                            if st.button("取消回复"):
                                st.session_state.reply_target_id = None
                                st.rerun()
                    # 楼中楼输入框
                    input_key = f"reply_input_{item['id']}"
                    if input_key not in st.session_state:
                        st.session_state[input_key] = ""
                    reply_input = st.text_input("写下你的评论", key=input_key, placeholder="写下你的评论...")
                    if st.button("提交回复", key=f"submit_reply_{item['id']}"):
                        content = reply_input.strip()
                        if not content:
                            st.warning("回复不能为空！")
                        else:
                            t = datetime.now().strftime("%Y-%m-%d %H:%M")
                            insert_reply(item["id"], current_student, content, t, st.session_state.reply_target_id)
                            st.success("评论发送成功！")
                            st.session_state.open_reply_pid = None
                            st.session_state.reply_target_id = None
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                # 评论分页展示
                if all_replies:
                    pid = str(item["id"])
                    if pid not in st.session_state.reply_page_map:
                        st.session_state.reply_page_map[pid] = 1
                    rp = st.session_state.reply_page_map[pid]
                    r_size = st.session_state.reply_page_size
                    total_rp = (len(all_replies) + r_size - 1) // r_size
                    r_start = (rp - 1) * r_size
                    r_end = r_start + r_size
                    reply_page_data = all_replies[r_start:r_end]
                    with st.expander(f"全部评论 ({reply_count}) 第{rp}/{total_rp}页"):
                        for r in reply_page_data:
                            # 评论者头像
                            r_prof = get_user_profile(r["writer"])
                            r_avatar = get_avatar_html(r_prof.get("avatar"), r["writer"], f"click_avatar_{r['id']}")
                            st.markdown(r_avatar, unsafe_allow_html=True)
                            # 回复层级
                            if r.get("reply_target"):
                                target_r = next((rr for rr in all_replies if rr["id"] == r["reply_target"]), None)
                                target_name = target_r["writer"] if target_r else ""
                                st.write(f"{r['writer']} 回复 @{target_name}：{r['content']}")
                            else:
                                st.write(f"{r['writer']}：{r['content']}")
                            st.caption(f"{r['time']}")
                            # 回复这条评论按钮
                            if st.button(f"回复{r['writer']}", key=f"reply_target_{r['id']}"):
                                st.session_state.reply_target_id = r["id"]
                                st.session_state.open_reply_pid = item["id"]
                                st.rerun()
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

    # ===================== 2. 给同学写评语 =====================
    elif nav_menu == "给同学写评语":
        st.markdown("### 🏷️ 自由写下评语，AI自动解析性格雷达图")
        target = st.selectbox("选择评价同学", CLASS_STUDENTS)
        comment_input = st.text_area("写下对TA的心里话、性格描述", height=120, placeholder="温柔、自律、乐观、搞笑...")
        submit_btn = st.button("保存评语")
        if submit_btn and comment_input.strip():
            with st.spinner("保存评语..."):
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

    # ===================== 3. 个人专属档案（头像+简介+私信收件箱华丽卡片） =====================
    elif nav_menu == "个人专属档案":
        st.markdown(f"### 💌 {current_student} 专属毕业档案")
        prof = get_user_profile(current_username)
        # 头像上传编辑
        st.subheader("个人头像")
        avatar_upload = st.file_uploader("上传头像图片", type=["jpg","png","jpeg"])
        avatar_b64 = prof.get("avatar", "")
        if avatar_upload:
            avatar_b64 = compress_and_encode(avatar_upload, max_width=300)
            st.image(io.BytesIO(base64.b64decode(avatar_b64)), width=150)
        elif avatar_b64:
            st.image(io.BytesIO(base64.b64decode(avatar_b64)), width=150)
        # 档案表单
        nick = st.text_input("昵称", value=prof.get("nick", ""))
        brief_desc = st.text_input("个人简短简介（星光墙展示）", value=prof.get("brief_desc", ""))
        hobby = st.text_input("爱好", value=prof.get("hobby", ""))
        dream = st.text_input("未来理想", value=prof.get("dream", ""))
        motto = st.text_area("毕业座右铭", value=prof.get("motto", ""))
        contact = st.text_input("联系方式", value=prof.get("contact", ""))
        birthday = st.text_input("生日", value=prof.get("birthday", ""))
        if st.button("保存全部档案信息"):
            save_profile(current_username, {
                "avatar": avatar_b64,
                "nick": nick,
                "brief_desc": brief_desc,
                "hobby": hobby,
                "dream": dream,
                "motto": motto,
                "contact": contact,
                "birthday": birthday
            })
            st.success("档案已更新保存")
            st.rerun()
        st.divider()
        # 华丽收件箱（卡片式信件）
        st.subheader("📩 我的私信信箱")
        all_my_msg = get_my_msg(current_student)
        if not all_my_msg:
            st.info("你的信箱空空如也，快去和同学发私信吧")
        else:
            # 按对方分组对话
            chat_groups = {}
            for msg in all_my_msg:
                other = msg["target_student"] if msg["sender"] == current_student else msg["sender"]
                if other not in chat_groups:
                    chat_groups[other] = []
                chat_groups[other].append(msg)
            # 每个对话卡片
            for chat_name, msg_list in chat_groups.items():
                with st.expander(f"与 {chat_name} 的对话（共{len(msg_list)}条）"):
                    msg_list.sort(key=lambda x: x["time"])
                    for m in msg_list:
                        if m["sender"] == current_student:
                            st.markdown(f'<div class="msg-send">{m["content"]}<br><small>{m["time"]}</small></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="msg-receive">{m["content"]}<br><small>{m["time"]}</small></div>', unsafe_allow_html=True)
                    # 回复私信
                    reply_text = st.text_input(f"回复 {chat_name}", key=f"reply_msg_{chat_name}")
                    if st.button("发送私信", key=f"send_msg_{chat_name}") and reply_text.strip():
                        send_msg(current_student, chat_name, reply_text)
                        st.success("私信发送成功")
                        st.rerun()
        st.divider()
        # 全班写给我的评语 + 词云雷达图
        all_tag_list = load_tags()
        my_tags = [x for x in all_tag_list if x["target_student"] == current_student]
        if not my_tags:
            st.warning("暂时没有同学给你写评语，去留言墙让大家给你贴标签吧！")
        else:
            all_comment_text = ""
            total_score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
            for t in my_tags:
                all_comment_text += t["comment"] + " "
                single_score = ai_calc_person_score(t["comment"])
                for k in total_score.keys():
                    total_score[k] += single_score[k]
            # 词云
            if st.session_state.wordcloud_img is None:
                wc = WordCloud(background_color="#fff7f2", width=800, height=400, colormap="Reds", contour_width=1, contour_color="#c83e3e").generate(all_comment_text)
                st.session_state.wordcloud_img = wc.to_image()
            st.markdown("#### 🔖 大家对你的描述词云")
            st.image(st.session_state.wordcloud_img, width=900)
            # 雷达图
            if st.session_state.radar_fig is None:
                plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Zen Hei']
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

    # ===================== 4. 班级星光墙（替代查看同学档案，头像网格布局） =====================
    elif nav_menu == "班级星光墙":
        st.markdown("### ⭐ 班级星光墙 · 全体同学一览")
        all_users = load_users()
        all_profiles = load_profile()
        student_list = [v["student_name"] for v in all_users.values()]
        # 分页
        total_stu = len(student_list)
        page_size = st.session_state.star_page_size
        total_page = (total_stu + page_size - 1) // page_size
        pg1, pg2, pg3 = st.columns([1,1,3])
        with pg1:
            if st.button("上一页", key="star_prev") and st.session_state.star_page >1:
                st.session_state.star_page -=1
                st.rerun()
        with pg2:
            if st.button("下一页", key="star_next") and st.session_state.star_page < total_page:
                st.session_state.star_page +=1
                st.rerun()
        with pg3:
            st.caption(f"共{total_stu}位同学，第{st.session_state.star_page}/{total_page}页")
        start = (st.session_state.star_page -1)*page_size
        end = start + page_size
        page_students = student_list[start:end]
        # 网格渲染头像卡片
        st.markdown('<div class="star-grid">', unsafe_allow_html=True)
        for stu_name in page_students:
            # 匹配档案
            stu_prof = next((p for p in all_profiles if p.get("username") and all_users[p["username"]]["student_name"] == stu_name), {})
            avatar_html = get_avatar_html(stu_prof.get("avatar"), stu_name, f"star_click_{stu_name}")
            brief = stu_prof.get("brief_desc", "暂无简介")
            # 点击头像查看详情
            if st.button(f"查看{stu_name}", key=f"star_click_{stu_name}"):
                st.session_state.view_user_detail = stu_name
                st.rerun()
            st.markdown(f"""
            <div class="star-card">
                {avatar_html}
                <h4>{stu_name}</h4>
                <p style="font-size:12px;color:#666;">{brief[:40]}...</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        # 查看同学详情弹窗
        if st.session_state.view_user_detail:
            view_name = st.session_state.view_user_detail
            st.divider()
            st.subheader(f"📖 {view_name} 的个人档案")
            # 查找账号
            view_uname = None
            for un, info in all_users.items():
                if info["student_name"] == view_name:
                    view_uname = un
                    break
            if view_uname:
                vp = get_user_profile(view_uname)
                avatar = vp.get("avatar")
                if avatar:
                    st.image(io.BytesIO(base64.b64decode(avatar)), width=180)
                st.write(f"昵称：{vp.get('nick','未填写')}")
                st.write(f"生日：{vp.get('birthday','未填写')}")
                st.write(f"爱好：{vp.get('hobby','未填写')}")
                st.write(f"理想：{vp.get('dream','未填写')}")
                st.write(f"座右铭：{vp.get('motto','未填写')}")
                st.write(f"联系方式：{vp.get('contact','隐藏')}")
                # 发送私信给TA
                st.subheader("给TA发私信")
                msg_input = st.text_area("私信内容", key=f"star_msg_{view_name}")
                if st.button("发送私信", key=f"send_star_msg_{view_name}") and msg_input.strip():
                    send_msg(current_student, view_name, msg_input)
                    st.success("私信发送成功！")
            if st.button("关闭档案详情"):
                st.session_state.view_user_detail = None
                st.rerun()

    # ===================== 5. 班级时光大事记 =====================
    elif nav_menu == "班级时光大事记":
        st.markdown("### 📅 班级时光大事记，记录每一段回忆")
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
                        st.image(io.BytesIO(base64.b64decode(b64)), width=200)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.divider()

    # ===================== 6. 星海漂流瓶 =====================
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
                    import random
                    pick = random.choice(bottle_all)
                    st.session_state.current_bottle = pick
                    st.rerun()
        total_bottle = len(load_bottle())
        st.info(f"当前星海共有 {total_bottle} 只漂流瓶")
        st.divider()
        if st.session_state.get("current_bottle"):
            b = st.session_state.current_bottle
            st.markdown('<div class="bottle-show-box">', unsafe_allow_html=True)
            st.subheader("🌊 你打捞到的漂流瓶")
            st.write(f"投递时间：{b['create_time']}")
            st.markdown(f"### {b['content']}")
            st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 7. 我的收藏留言 =====================
    elif nav_menu == "我的收藏留言":
        st.markdown("### ⭐ 我收藏的全部留言")
        collect_posts = get_collect_posts(current_username)
        if not collect_posts:
            st.info("你还没有收藏任何留言，去留言墙点击星星收藏喜欢的内容吧")
        else:
            for item in collect_posts:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                display_name = "匿名用户" if item.get("is_anonymous") else item["author"]
                st.write(f"**{display_name}** · {item['create_time']}")
                st.write(item["text_content"])
                if st.button("取消收藏", key=f"uncollect_{item['id']}"):
                    toggle_collect(current_username, item["id"])
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)