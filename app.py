import streamlit as st
import base64
import asyncio
import random
from datetime import datetime, timedelta
from supabase import create_client, Client
from PIL import Image
import io
from streamlit_option_menu import option_menu
from realtime import AsyncRealtimeClient
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ==============================================
# 【第一优先级：全部SessionState初始化，杜绝KeyError】
# ==============================================
# 登录开关
st.session_state.setdefault("login_username", None)
st.session_state.setdefault("show_user_drawer", False)

# 缓存时间戳键列表
cache_ts_keys = [
    "cache_ts_users", "cache_ts_forum", "cache_ts_replies", "cache_ts_tags",
    "cache_ts_profile", "cache_ts_msg", "cache_ts_events", "cache_ts_bottles",
    "cache_ts_collect", "cache_ts_notice"
]
for key in cache_ts_keys:
    if key not in st.session_state:
        st.session_state[key] = None

# 缓存数据容器键列表
cache_data_keys = [
    "cache_users", "cache_forum", "cache_replies", "cache_tags",
    "cache_profile", "cache_msg", "cache_events", "cache_bottles",
    "cache_collect", "cache_notice"
]
for key in cache_data_keys:
    if key not in st.session_state:
        if key == "cache_users":
            st.session_state[key] = {}
        else:
            st.session_state[key] = []

# 分页、弹窗、临时状态
st.session_state.setdefault("forum_page", 1)
st.session_state.setdefault("forum_page_size", 10)
st.session_state.setdefault("reply_page_map", {})
st.session_state.setdefault("reply_page_size", 5)
st.session_state.setdefault("star_page", 1)
st.session_state.setdefault("star_page_size", 12)
st.session_state.setdefault("open_reply_pid", None)
st.session_state.setdefault("reply_target_id", None)
st.session_state.setdefault("view_user_detail", None)
# 图表缓存
st.session_state.setdefault("wordcloud_img", None)
st.session_state.setdefault("radar_fig", None)
# 漂流瓶临时存储
st.session_state.setdefault("current_bottle", None)

# ==============================================
# 页面基础配置
# ==============================================
st.set_page_config(page_title="石榴16班毕业纪念册", page_icon="🍅", layout="wide")

# 深色模式
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"
dark_toggle = st.sidebar.toggle("🌙 深色模式", value=(st.session_state.theme_mode == "dark"))
st.session_state.theme_mode = "dark" if dark_toggle else "light"

# 全局CSS样式
bg_grad = "linear-gradient(140deg, #fff7f2 0%, #ffe9e3 40%, #fde0d8 100%)" if st.session_state.theme_mode == "light" else "#1a1a2e"
text_c = "#332222" if st.session_state.theme_mode == "light" else "#f0f0f0"
card_bg = "rgba(255,255,255,0.7)" if st.session_state.theme_mode == "light" else "rgba(30,30,50,0.7)"
input_bg = "#ffffff" if st.session_state.theme_mode == "light" else "#2d2d44"

st.markdown(f"""
<style>
.stApp {{background: {bg_grad}; color:{text_c};}}
.main-title {{font-size:34px;font-weight:600;text-align:center;color:#c83e3e;margin:6px 0;}}
.sub-title {{text-align:center;color:#994444;font-size:14px;margin-bottom:24px;opacity:0.8;}}
.card-box {{border:none;border-radius:12px;padding:18px;background:{card_bg};box-shadow:0 1px 6px rgba(200,60,60,0.06);margin:10px 0;transition:0.2s;}}
.card-box:hover {{box-shadow:0 2px 10px rgba(200,60,60,0.1);transform:translateY(-2px);}}
.avatar-circle {{width:44px;height:44px;border-radius:50%;object-fit:cover;border:1px solid #e8a8a8;cursor:pointer;}}
.post-action-bar {{display:flex;gap:24px;margin-top:10px;padding:8px;background:rgba(255,242,242,0.5);border-radius:8px;}}
.reply-panel {{display:none;margin-top:8px;padding:10px;background:rgba(255,240,240,0.6);border-radius:10px;}}
.reply-panel.show {{display:block;}}
.msg-send {{background:#d65c5c;color:white;border-radius:12px 12px 2px 12px;padding:6px 10px;margin:3px 0 3px auto;max-width:70%;width:fit-content;}}
.msg-receive {{background:rgba(240,224,224,0.8);color:#222;border-radius:12px 12px 12px 2px;padding:6px 10px;margin:3px auto 3px 0;max-width:70%;width:fit-content;}}
.star-grid {{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:16px;margin:16px 0;}}
.star-card {{text-align:center;padding:10px;border-radius:10px;background:{card_bg};}}
.bottle-show-box {{border:1px solid #87CEEB;border-radius:16px;padding:30px;background:rgba(240,248,255,0.7);margin:24px 0;min-height:240px;}}
.stButton>button {{background:linear-gradient(90deg,#d65c5c,#c44444);color:white !important;border:none;border-radius:8px;height:32px;font-weight:400;font-size:14px;padding:0 12px;}}
.stButton>button:hover {{background:#b83838;transform:scale(1.01);}}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {{background:{input_bg} !important;color:{text_c} !important;caret-color:#c83e3e;border:1px solid rgba(221,187,187,0.6) !important;border-radius:6px;padding:8px 12px;font-size:14px;}}
div[data-baseweb="input"] input::placeholder, div[data-baseweb="textarea"] textarea::placeholder {{color:#996666;opacity:0.7;}}
hr {{border-color:rgba(226,176,176,0.4);margin:16px 0;}}
.reply-box {{background:rgba(255,240,240,0.5);padding:8px;border-radius:8px;margin:6px 0;}}
.img-grid {{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0;}}
.refresh-btn button {{background:#228be6 !important;}}
.danger-btn button {{background:#e03131 !important;}}
.notice-bar {{background:#ffe066;color:#222;padding:6px 12px;border-radius:6px;text-align:center;font-weight:400;margin:8px 0;}}
.media-preview {{cursor:pointer;opacity:0.9;}}
.media-preview:hover {{opacity:1;}}
</style>""", unsafe_allow_html=True)

# ==============================================
# Realtime 实时订阅
# ==============================================
if "realtime_client" not in st.session_state:
    st.session_state.realtime_client = None

async def setup_realtime():
    if st.session_state.realtime_client:
        return
    try:
        url, key = st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
        rt_url = f"wss://{url.replace('https://','').replace('.supabase.co','')}.supabase.co/realtime/v1/websocket?apikey={key}&vsn=1.0.0"
        client = AsyncRealtimeClient(rt_url, key)
        st.session_state.realtime_client = client
        await client.connect()
        channel = client.channel("class-forum")
        st.session_state.realtime_channel = channel

        def on_update(_):
            st.session_state.cache_ts_forum = None
            st.session_state.cache_ts_replies = None
            st.toast("📢 新留言/评论更新")

        channel.on_postgres_changes("*", "public", "forum_messages", on_update)
        channel.on_postgres_changes("INSERT", "public", "forum_reply", on_update)
        await channel.subscribe()
    except Exception as e:
        st.warning(f"实时消息连接失败：{str(e)}")

# ==============================================
# Supabase 单例
# ==============================================
@st.cache_resource
def init_supabase() -> Client:
    u, k = st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    return create_client(u, k)
supabase = init_supabase()

# ==============================================
# 班级名单
# ==============================================
CLASS_STUDENTS = [
    '马浩然', '王一帆', '王原穗', '王韵琪', '卢芷清','冯孝楚', '伍梓晨', '刘卓轩', '刘倩影', '汤乐宜',
    '李子杰', '李乐祺', '李辰', '李奕安', '李浩源','李想', '杨宸涵', '吴桂祺', '何泳琳', '邹丝羽',
    '沈君铭', '张睿琪', '陈子昂', '陈天泽', '陈佳宜','武帅宇', '林璟昊', '罗洁颖', '罗钰琳', '罗森耀',
    '罗颢畦', '郑熙潼', '赵宇', '施昕彤', '姚优烨','聂子岚', '莫怀浅', '凌浩宇', '高泓', '高梓铭',
    '黄梓轩', '黄敏霞', '黄灏哲', '戚志邦', '温曈','谢安然', '赖昊林', '蔡芷菡', '潘佳岩', '潘柏晋'
]

# ==============================================
# 通用工具函数
# ==============================================
def safe_slice(text, max_len=40, suffix="..."):
    if not isinstance(text, str) or text is None:
        return "暂无简介"
    return text[:max_len] + suffix if len(text) > max_len else text

def compress_encode(img_file, max_w=1080, quality=70):
    img = Image.open(img_file).convert("RGB")
    w, h = img.size
    if w > max_w:
        img = img.resize((int(max_w), int(h * max_w / w)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()

def file_to_b64(file):
    return base64.b64encode(file.read()).decode()

def video_b64(vid):
    return base64.b64encode(vid.read()).decode()

def cut_text(text, max_len=80):
    s = safe_slice(text, max_len, "...")
    return s, len(text) > max_len

def calc_score(comment):
    text = comment.lower()
    score = {"乐观":0, "温柔":0, "有趣":0, "自律":0, "外向":0}
    word_map = {
        "乐观":["开朗","乐观","阳光","开心","元气"],
        "温柔":["温柔","贴心","细心","善良","暖心"],
        "有趣":["搞笑","有趣","幽默","活泼","梗多"],
        "自律":["努力","自律","认真","上进","踏实"],
        "外向":["外向","社牛","大方","合群","健谈"]
    }
    for key, words in word_map.items():
        for w in words:
            if w in text:
                score[key] += 1
    return score

def avatar_html(b64, name, click_key):
    src = f"data:image/jpeg;base64,{b64}" if b64 else f"https://via.placeholder.com/44/cccccc/333?text={name[0]}"
    return f'<img class="avatar-circle media-preview" src="{src}" onclick="window.streamlitApi.setValue(\'{click_key}\', \'{name}\')">'

def media_popup_b64(b64, mime="image/jpeg", name="预览"):
    data_url = f"data:{mime};base64,{b64}"
    return f'<a href="{data_url}" target="_blank" style="margin-right:8px;">🔍高清新窗口</a><a href="{data_url}" download="{name}" target="_blank">⬇️下载</a>'

# ==============================================
# 数据加载函数（内部兜底初始化，彻底解决KeyError）
# ==============================================
def load_data(table_name, limit=1000):
    now = datetime.now()
    ts_key = f"cache_ts_{table_name}"
    data_key = f"cache_{table_name}"

    # 函数内强制初始化，双重保险
    if ts_key not in st.session_state:
        st.session_state[ts_key] = None
    if data_key not in st.session_state:
        st.session_state[data_key] = {} if table_name == "users" else []

    # 缓存有效期8秒
    if st.session_state[ts_key] and (now - st.session_state[ts_key]) < timedelta(seconds=8):
        return st.session_state[data_key]

    res = supabase.table(table_name).select("*").limit(limit).execute()
    if table_name == "users":
        data = {row["username"]: row for row in res.data}
    else:
        data = res.data

    st.session_state[data_key] = data
    st.session_state[ts_key] = now
    return data

# 各表快捷加载
def load_users(): return load_data("users", 200)
def load_forum(): return load_data("forum_messages", 1000)
def load_replies(): return load_data("forum_reply", 2000)
def load_tags(): return load_data("tag_data", 300)
def load_profile(): return load_data("user_profile", 200)
def load_msg(): return load_data("private_msg", 300)
def load_events(): return load_data("class_events", 100)
def load_bottle(): return load_data("bottle_list", 300)
def load_collect(): return load_data("user_collect")
def load_notice(): return load_data("system_notice", 1)

def load_post_files(post_id=None):
    res = supabase.table("post_files").select("*")
    if post_id:
        res = res.eq("post_id", post_id)
    return res.execute().data

# ==============================================
# 数据库写入操作
# ==============================================
def create_user(uname, pwd, sname):
    supabase.table("user_accounts").insert({"username": uname, "password": pwd, "student_name": sname}).execute()
    st.session_state.cache_ts_users = None

def get_profile(username):
    profs = load_profile()
    return next((p for p in profs if p["username"] == username), {})

def save_profile(uname, data):
    old = get_profile(uname)
    if old:
        supabase.table("user_profile").update(data).eq("username", uname).execute()
    else:
        data["username"] = uname
        supabase.table("user_profile").insert(data).execute()
    st.session_state.cache_ts_profile = None

def send_private_msg(sender, target, content):
    supabase.table("private_msg").insert({
        "sender": sender,
        "target_student": target,
        "content": content,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }).execute()
    st.session_state.cache_ts_msg = None

def get_my_conversations(student):
    msgs = load_msg()
    chats = {}
    for m in msgs:
        other = m["target_student"] if m["sender"] == student else m["sender"]
        chats.setdefault(other, []).append(m)
    return chats

def publish_post(author, text, imgs, vid, files, ptype="normal", vote_data=None, anon=False):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    res = supabase.table("forum_messages").insert({
        "author": author,
        "text_content": text,
        "images": imgs,
        "video": vid,
        "create_time": now,
        "like_count": 0,
        "is_anonymous": anon,
        "edit_time": None,
        "post_type": ptype,
        "vote_data": vote_data
    }).execute()
    post_id = res.data[0]["id"]
    for f in files:
        supabase.table("post_files").insert({
            "post_id": post_id,
            "file_name": f.name,
            "file_b64": file_to_b64(f),
            "upload_time": now
        }).execute()
    st.session_state.cache_ts_forum = None

def edit_post(pid, new_text):
    supabase.table("forum_messages").update({
        "text_content": new_text,
        "edit_time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }).eq("id", pid).execute()
    st.session_state.cache_ts_forum = None

def like_post(pid):
    supabase.rpc("inc_like", {"pid": pid}).execute()
    st.session_state.cache_ts_forum = None

def toggle_collect(uname, pid):
    collects = load_collect()
    exist = next((c for c in collects if c["username"] == uname and c["post_id"] == pid), None)
    if exist:
        supabase.table("user_collect").delete().eq("id", exist["id"]).execute()
    else:
        supabase.table("user_collect").insert({
            "username": uname,
            "post_id": pid,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }).execute()
    st.session_state.cache_ts_collect = None

def get_collected_posts(uname):
    pids = [c["post_id"] for c in load_collect() if c["username"] == uname]
    return [p for p in load_forum() if p["id"] in pids]

def get_post_replies(pid):
    replies = [r for r in load_replies() if r["post_id"] == pid]
    replies.sort(key=lambda x: x["time"])
    return replies

def add_reply(pid, writer, text, target_rid=None):
    supabase.table("forum_reply").insert({
        "post_id": pid,
        "writer": writer,
        "content": text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "reply_target": target_rid
    }).execute()
    st.session_state.cache_ts_replies = None

def add_tag(target, writer, comment):
    supabase.table("tag_data").insert({"target_student": target, "writer": writer, "comment": comment}).execute()
    st.session_state.cache_ts_tags = None

def add_event(date, title, detail, recorder, imgs):
    supabase.table("class_events").insert({
        "event_date": str(date),
        "title": title,
        "detail": detail,
        "recorder": recorder,
        "images": imgs
    }).execute()
    st.session_state.cache_ts_events = None

def throw_bottle(content):
    supabase.table("bottle_list").insert({
        "content": content,
        "create_time": datetime.now().strftime("%m-%d %H:%M")
    }).execute()
    st.session_state.cache_ts_bottles = None

# ==============================================
# 页面头部区域
# ==============================================
header_left, header_mid, header_right = st.columns([7, 2, 1])
with header_left:
    st.markdown('<div class="main-title">🍅 石榴16班 · 毕业纪念册</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">十六岁的我们，岁岁常相见</div>', unsafe_allow_html=True)
with header_mid:
    st.markdown('<div class="refresh-btn">', unsafe_allow_html=True)
    if st.button("🔃 刷新数据", key="main_refresh"):
        st.session_state.cache_ts_forum = None
        st.session_state.cache_ts_replies = None
        st.session_state.cache_ts_collect = None
        load_forum()
        load_replies()
        st.success("✅ 已同步最新内容")
    st.markdown('</div>', unsafe_allow_html=True)
with header_right:
    if st.session_state.login_username and st.button("👤 个人中心"):
        st.session_state.show_user_drawer = not st.session_state.show_user_drawer

# 公告栏
notice_data = load_notice()
if notice_data:
    st.markdown(f'<div class="notice-bar">📢 班级公告：{notice_data[0]["content"]}</div>', unsafe_allow_html=True)

# ==============================================
# 登录注册模块
# ==============================================
if not st.session_state.login_username:
    st.warning("🔐 登录后解锁全部班级功能")
    tab_login, tab_reg = st.tabs(["账号登录", "新生注册"])
    with tab_login:
        u_in = st.text_input("账号")
        p_in = st.text_input("密码", type="password")
        if st.button("登录纪念册"):
            users = load_users()
            if u_in in users and users[u_in]["password"] == p_in:
                st.session_state.login_username = u_in
                try:
                    asyncio.run(setup_realtime())
                except Exception as e:
                    st.warning(f"实时连接失败：{e}")
                st.rerun()
            else:
                st.error("账号或密码错误")
    with tab_reg:
        reg_u = st.text_input("设置账号")
        reg_p = st.text_input("设置密码", type="password")
        reg_name = st.selectbox("绑定姓名", CLASS_STUDENTS)
        if st.button("完成注册"):
            users = load_users()
            if not reg_u.strip():
                st.warning("账号不能为空")
            elif reg_u in users:
                st.warning("账号已存在")
            elif not reg_p.strip():
                st.warning("密码不能为空")
            else:
                create_user(reg_u, reg_p, reg_name)
                st.success("注册成功，请登录")
else:
    user_dict = load_users()
    curr_uname = st.session_state.login_username
    curr_student = user_dict[curr_uname]["student_name"]
    st.success(f"✅ 欢迎回来，{curr_student}")
    if st.button("退出登录"):
        st.session_state.login_username = None
        st.rerun()

    # 顶部导航
    nav = option_menu(
        menu_title=None,
        options=["班级留言墙", "给同学写评语", "个人专属档案", "班级星光墙", "班级时光大事记", "星海漂流瓶", "我的收藏留言"],
        icons=["chat-heart", "tag", "person-lines-fill", "stars", "calendar-heart", "water", "bookmark"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"background": "rgba(255,245,243,0.5)", "padding": "4px"},
            "nav-link": {"color": "#773333", "font-size": "15px"},
            "nav-link-selected": {"background": "#d65c5c", "color": "white"}
        }
    )

    # ===================== 1. 班级留言墙 =====================
    if nav == "班级留言墙":
        st.markdown("### 🍅 班级留言墙 · 分享日常、发起投票、趣味猜人")
        col_search, col_sort, col_type = st.columns([3, 1, 1])
        with col_search:
            search_key = st.text_input("🔍 搜索人名/内容", placeholder="输入关键词筛选")
        with col_sort:
            sort_mode = st.selectbox("排序", ["最新发布", "点赞最多"])
        with col_type:
            filter_type = st.selectbox("帖子类型", ["全部", "普通", "投票", "猜人"])
        anon_tick = st.checkbox("匿名发布（隐藏姓名）")
        st.divider()

        post_type = st.radio("帖子类型", ["普通分享", "班级投票", "趣味猜人"], horizontal=True)
        post_text = st.text_area("正文内容", height=90, placeholder="写下你想分享的内容...")
        vote_cfg = {}
        guess_hint = ""
        if post_type == "班级投票":
            vote_title = st.text_input("投票标题", placeholder="例：毕业旅行去哪里")
            vote_opt = st.text_input("选项，英文逗号分隔", placeholder="选项1,选项2,选项3")
            vote_multi = st.checkbox("允许多选")
            vote_cfg = {"title": vote_title, "options": vote_opt.split(",") if vote_opt else [], "multi": vote_multi}
        elif post_type == "趣味猜人":
            guess_hint = st.text_input("猜人线索提示", placeholder="例：爱打篮球，数学课代表")
        else:
            guess_hint = ""

        col_up1, col_up2 = st.columns([1, 1])
        with col_up1:
            img_upload = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        with col_up2:
            vid_upload = st.file_uploader("上传视频", type=["mp4", "mov"])
        file_upload = st.file_uploader("上传附件文件", accept_multiple_files=True)

        submit_btn = st.button("发布帖子")
        if submit_btn and post_text.strip():
            with st.spinner("发布中..."):
                imgs = [compress_encode(f) for f in img_upload] if img_upload else []
                vid = video_b64(vid_upload) if vid_upload else None
                files = file_upload if file_upload else []
                ptype_map = {"普通分享": "normal", "班级投票": "vote", "趣味猜人": "guess"}
                publish_post(curr_student, post_text, imgs, vid, files, ptype_map[post_type], vote_cfg if post_type == "班级投票" else None, anon_tick)
            st.success("🎉 帖子发布完成！")
            st.rerun()
        st.divider()

        st.markdown("## 📜 全班帖子")
        raw_posts = load_forum()
        filtered = []
        for p in raw_posts:
            if search_key.strip() and search_key.lower() not in p["text_content"].lower() and search_key.lower() not in p["author"].lower():
                continue
            if filter_type != "全部":
                type_map = {"普通": "normal", "投票": "vote", "猜人": "guess"}
                if p["post_type"] != type_map[filter_type]:
                    continue
            filtered.append(p)
        if sort_mode == "点赞最多":
            filtered.sort(key=lambda x: x["like_count"], reverse=True)
        else:
            filtered.sort(key=lambda x: x["id"], reverse=True)

        total = len(filtered)
        page_size = st.session_state.forum_page_size
        total_page = (total + page_size - 1) // page_size
        pg1, pg2, pg3 = st.columns([1, 1, 3])
        with pg1:
            if st.button("上一页") and st.session_state.forum_page > 1:
                st.session_state.forum_page -= 1
                st.rerun()
        with pg2:
            if st.button("下一页") and st.session_state.forum_page < total_page:
                st.session_state.forum_page += 1
                st.rerun()
        with pg3:
            st.caption(f"共{total}条 | 第{st.session_state.forum_page}/{total_page}页")
        page_posts = filtered[(st.session_state.forum_page - 1) * page_size: st.session_state.forum_page * page_size]

        if not page_posts:
            st.info("暂无匹配帖子，换筛选条件试试")
        else:
            for post in page_posts:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                prof = get_profile(post["author"])
                st.markdown(avatar_html(prof.get("avatar"), post["author"], f"avatar_click_{post['id']}"), unsafe_allow_html=True)
                if st.session_state.get(f"avatar_click_{post['id']}") == post["author"]:
                    st.session_state.view_user_detail = post["author"]
                    st.rerun()
                display_name = "匿名用户" if post["is_anonymous"] else post["author"]
                st.write(f"**{display_name}** · {post['create_time']}")
                if post["edit_time"]:
                    st.caption(f"已编辑 {post['edit_time']}")

                create_dt = datetime.strptime(post["create_time"], "%Y-%m-%d %H:%M")
                if post["author"] == curr_student and (datetime.now() - create_dt).total_seconds() / 60 < 10:
                    edit_txt = st.text_area("编辑帖子", value=post["text_content"], key=f"edit_{post['id']}")
                    if st.button("保存修改", key=f"save_edit_{post['id']}"):
                        edit_post(post["id"], edit_txt)
                        st.success("修改已保存")
                        st.rerun()

                full_txt = post["text_content"]
                short_txt, expand = cut_text(full_txt, 100)
                t_col, btn_col = st.columns([8, 1])
                with t_col:
                    st.write(short_txt)
                with btn_col:
                    if expand and st.button("全文", key=f"expand_{post['id']}"):
                        st.info(full_txt)

                if post["post_type"] == "vote" and post["vote_data"]:
                    vote = post["vote_data"]
                    st.subheader(f"投票：{vote['title']}")
                    opt_list = vote["options"]
                    sel = st.multiselect("选择你的投票", opt_list, key=f"vote_{post['id']}") if vote["multi"] else st.radio("选择你的投票", opt_list, key=f"vote_{post['id']}")
                    if st.button("提交投票", key=f"sub_vote_{post['id']}"):
                        st.success("投票成功（后端统计可拓展）")
                if post["post_type"] == "guess":
                    st.info(f"🔍 猜人线索：{guess_hint}")

                img_list = post.get("images", [])
                if img_list:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for idx, b64 in enumerate(img_list):
                        st.image(io.BytesIO(base64.b64decode(b64)), width=180, caption=f"图片{idx+1}")
                        st.markdown(media_popup_b64(b64, "image/jpeg", f"帖子{post['id']}_图{idx+1}"), unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                vid_b64 = post.get("video")
                if vid_b64:
                    vid_bytes = io.BytesIO(base64.b64decode(vid_b64))
                    st.video(vid_bytes)
                    st.markdown(media_popup_b64(vid_b64, "video/mp4", f"帖子{post['id']}_视频.mp4"), unsafe_allow_html=True)
                files = load_post_files(post["id"])
                if files:
                    st.subheader("附件下载")
                    for f in files:
                        st.markdown(media_popup_b64(f["file_b64"], "application/octet-stream", f"{f['file_name']}"), unsafe_allow_html=True)
                        st.write(f"📎 {f['file_name']}")

                st.markdown('<div class="post-action-bar">', unsafe_allow_html=True)
                col_share, col_like, col_msg, col_collect = st.columns([1, 1, 1, 1])
                reply_list = get_post_replies(post["id"])
                reply_cnt = len(reply_list)
                like_cnt = post.get("like_count", 0)
                with col_share:
                    st.write("🔁 转发 0")
                with col_like:
                    if st.button(f"❤️ {like_cnt}", key=f"like_{post['id']}"):
                        like_post(post["id"])
                        st.rerun()
                with col_msg:
                    if st.button(f"💬 评论 {reply_cnt}", key=f"open_reply_{post['id']}"):
                        if st.session_state.open_reply_pid == post["id"]:
                            st.session_state.open_reply_pid = None
                        else:
                            st.session_state.open_reply_pid = post["id"]
                            st.session_state.reply_target_id = None
                        st.rerun()
                with col_collect:
                    collected = any(c["username"] == curr_uname and c["post_id"] == post["id"] for c in load_collect())
                    coll_text = "⭐已收藏" if collected else "☆收藏"
                    if st.button(coll_text, key=f"coll_{post['id']}"):
                        toggle_collect(curr_uname, post["id"])
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.open_reply_pid == post["id"]:
                    st.markdown('<div class="reply-panel show">', unsafe_allow_html=True)
                    if st.session_state.reply_target_id:
                        target_r = next((r for r in reply_list if r["id"] == st.session_state.reply_target_id), None)
                        if target_r:
                            st.caption(f"回复 @{target_r['writer']}：{safe_slice(target_r['content'],30)}")
                            if st.button("取消回复"):
                                st.session_state.reply_target_id = None
                                st.rerun()
                    reply_input = st.text_input("写下你的评论", key=f"reply_in_{post['id']}", placeholder="写下你的评论...")
                    if st.button("提交回复", key=f"sub_reply_{post['id']}"):
                        if not reply_input.strip():
                            st.warning("评论不能为空")
                        else:
                            add_reply(post["id"], curr_student, reply_input, st.session_state.reply_target_id)
                            st.success("评论发送成功")
                            st.session_state.open_reply_pid = None
                            st.session_state.reply_target_id = None
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                if reply_list:
                    pid_str = str(post["id"])
                    st.session_state.reply_page_map.setdefault(pid_str, 1)
                    rp = st.session_state.reply_page_map[pid_str]
                    r_size = st.session_state.reply_page_size
                    total_rp = (len(reply_list) + r_size - 1) // r_size
                    reply_page = reply_list[(rp - 1) * r_size: rp * r_size]
                    with st.expander(f"全部评论 ({reply_cnt}) 第{rp}/{total_rp}页"):
                        for r in reply_page:
                            r_prof = get_profile(r["writer"])
                            st.markdown(avatar_html(r_prof.get("avatar"), r["writer"], f"r_avatar_{r['id']}"), unsafe_allow_html=True)
                            if r.get("reply_target"):
                                target_r = next((rr for rr in reply_list if rr["id"] == r["reply_target"]), None)
                                t_name = target_r["writer"] if target_r else ""
                                st.write(f"{r['writer']} 回复 @{t_name}：{r['content']}")
                            else:
                                st.write(f"{r['writer']}：{r['content']}")
                            st.caption(r["time"])
                            if st.button(f"回复{r['writer']}", key=f"rep_t_{r['id']}"):
                                st.session_state.reply_target_id = r["id"]
                                st.session_state.open_reply_pid = post["id"]
                                st.rerun()
                        r1, r2 = st.columns([1, 1])
                        with r1:
                            if st.button("上一页评论", key=f"rp_prev_{pid_str}") and rp > 1:
                                st.session_state.reply_page_map[pid_str] -= 1
                                st.rerun()
                        with r2:
                            if st.button("下一页评论", key=f"rp_next_{pid_str}") and rp < total_rp:
                                st.session_state.reply_page_map[pid_str] += 1
                                st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 2. 给同学写评语 =====================
    elif nav == "给同学写评语":
        st.markdown("### 🏷️ 给同学写评语，自动生成性格雷达图")
        target_stu = st.selectbox("选择要评价的同学", CLASS_STUDENTS)
        comment_txt = st.text_area("写下对TA的印象、性格描述", height=110, placeholder="温柔、自律、搞笑、阳光...")
        if st.button("保存评语") and comment_txt.strip():
            add_tag(target_stu, curr_student, comment_txt)
            st.success(f"已为{target_stu}保存评语")
            st.rerun()
        st.markdown(f"## {target_stu} 收到的评语预览")
        all_tags = load_tags()
        target_tags = [t for t in all_tags if t["target_student"] == target_stu]
        if not target_tags:
            st.info("暂无评语")
        else:
            for t in target_tags[:3]:
                st.write(f"来自 {t['writer']}：{safe_slice(t['comment'],60)}")
                st.divider()

    # ===================== 3. 个人专属档案 =====================
    elif nav == "个人专属档案":
        st.markdown(f"### 💌 {curr_student} 我的毕业档案")
        prof = get_profile(curr_uname)
        st.subheader("个人头像")
        avatar_up = st.file_uploader("上传头像", type=["jpg", "png"])
        avatar_b64 = prof.get("avatar", "")
        if avatar_up:
            avatar_b64 = compress_encode(avatar_up, max_w=300)
            st.image(io.BytesIO(base64.b64decode(avatar_b64)), width=140)
        elif avatar_b64:
            st.image(io.BytesIO(base64.b64decode(avatar_b64)), width=140)

        nick = st.text_input("昵称", value=prof.get("nick", ""))
        brief = st.text_input("星光墙简短简介", value=prof.get("brief_desc", ""))
        hobby = st.text_input("爱好", value=prof.get("hobby", ""))
        dream = st.text_input("未来理想", value=prof.get("dream", ""))
        motto = st.text_area("毕业座右铭", value=prof.get("motto", ""))
        birth = st.text_input("生日", value=prof.get("birthday", ""))
        contact = st.text_input("联系方式（仅自己可见）", value=prof.get("contact", ""))
        if st.button("保存全部档案"):
            save_profile(curr_uname, {
                "avatar": avatar_b64,
                "nick": nick,
                "brief_desc": brief,
                "hobby": hobby,
                "dream": dream,
                "motto": motto,
                "birthday": birth,
                "contact": contact
            })
            st.success("档案更新完成")
            st.rerun()
        st.divider()

        st.subheader("📩 我的私信信箱")
        chats = get_my_conversations(curr_student)
        if not chats:
            st.info("信箱暂无私信，快去和同学聊天吧")
        else:
            for chat_name, msg_list in chats.items():
                with st.expander(f"和 {chat_name} 的对话（共{len(msg_list)}条）"):
                    msg_list.sort(key=lambda x: x["time"])
                    for m in msg_list:
                        if m["sender"] == curr_student:
                            st.markdown(f'<div class="msg-send">{m["content"]}<br><small>{m["time"]}</small></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="msg-receive">{m["content"]}<br><small>{m["time"]}</small></div>', unsafe_allow_html=True)
                    reply_msg = st.text_input(f"回复 {chat_name}", key=f"chat_{chat_name}")
                    if st.button("发送私信", key=f"send_chat_{chat_name}") and reply_msg.strip():
                        send_private_msg(curr_student, chat_name, reply_msg)
                        st.success("私信发送成功")
                        st.rerun()
        st.divider()

        all_tags = load_tags()
        my_tags = [t for t in all_tags if t["target_student"] == curr_student]
        if not my_tags:
            st.warning("暂时没有同学给你写评语，去留言墙让大家给你贴标签吧！")
        else:
            all_comment = ""
            total_score = {"乐观": 0, "温柔": 0, "有趣": 0, "自律": 0, "外向": 0}
            for t in my_tags:
                all_comment += t["comment"] + " "
                single = calc_score(t["comment"])
                for k in total_score:
                    total_score[k] += single[k]
            if st.session_state.wordcloud_img is None:
                wc = WordCloud(background_color="#fff7f2", width=800, height=400, colormap="Reds", contour_width=1, contour_color="#c83e3e").generate(all_comment)
                st.session_state.wordcloud_img = wc.to_image()
            st.markdown("#### 🔖 大家对你的描述词云")
            st.image(st.session_state.wordcloud_img, width=880)
            if st.session_state.radar_fig is None:
                plt.rcParams["font.sans-serif"] = ["SimHei", "WenQuanYi Zen Hei"]
                plt.rcParams["axes.unicode_minus"] = False
                labels = list(total_score.keys())
                vals = list(total_score.values())
                angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
                vals += vals[:1]
                angles += angles[:1]
                fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"projection": "polar"})
                ax.plot(angles, vals, color="#c83e3e", linewidth=3)
                ax.fill(angles, vals, color="#e87878", alpha=0.3)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(labels, color="#773333", fontsize=12)
                ax.set_facecolor("#fff7f2")
                fig.patch.set_facecolor("#fff7f2")
                ax.tick_params(colors="#994444")
                st.session_state.radar_fig = fig
            st.markdown("#### 📊 AI性格雷达图")
            st.pyplot(st.session_state.radar_fig)
            st.markdown("#### 全班写给你的全部评语")
            for t in my_tags:
                st.write(f"来自 {t['writer']}：{t['comment']}")
                st.divider()

    # ===================== 4. 班级星光墙 =====================
    elif nav == "班级星光墙":
        st.markdown("### ⭐ 班级星光墙 · 全体同学一览")
        all_users = load_users()
        all_profs = load_profile()
        stu_list = [u["student_name"] for u in all_users.values()]
        total_stu = len(stu_list)
        page_size = st.session_state.star_page_size
        total_page = (total_stu + page_size - 1) // page_size
        pg1, pg2, pg3 = st.columns([1, 1, 3])
        with pg1:
            if st.button("上一页星光墙", key="star_prev") and st.session_state.star_page > 1:
                st.session_state.star_page -= 1
                st.rerun()
        with pg2:
            if st.button("下一页星光墙", key="star_next") and st.session_state.star_page < total_page:
                st.session_state.star_page += 1
                st.rerun()
        with pg3:
            st.caption(f"共{total_stu}位同学，第{st.session_state.star_page}/{total_page}页")
        page_stus = stu_list[(st.session_state.star_page - 1) * page_size: st.session_state.star_page * page_size]
        st.markdown('<div class="star-grid">', unsafe_allow_html=True)
        for s_name in page_stus:
            stu_prof = next((p for p in all_profs if p.get("username") and all_users[p["username"]]["student_name"] == s_name), {})
            brief = safe_slice(stu_prof.get("brief_desc", "暂无简介"), 40)
            st.markdown(avatar_html(stu_prof.get("avatar"), s_name, f"star_click_{s_name}"), unsafe_allow_html=True)
            if st.button(f"查看{s_name}", key=f"star_click_{s_name}"):
                st.session_state.view_user_detail = s_name
                st.rerun()
            st.markdown(f"<div class='star-card'><h4>{s_name}</h4><p style='font-size:12px;opacity:0.7;'>{brief}</p></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.view_user_detail:
            view_name = st.session_state.view_user_detail
            st.divider()
            st.subheader(f"📖 {view_name} 个人档案")
            view_uname = next((un for un, info in all_users.items() if info["student_name"] == view_name), None)
            if view_uname:
                vp = get_profile(view_uname)
                avatar = vp.get("avatar")
                if avatar:
                    st.image(io.BytesIO(base64.b64decode(avatar)), width=160)
                st.write(f"昵称：{vp.get('nick','未填写')}")
                st.write(f"生日：{vp.get('birthday','未填写')}")
                st.write(f"爱好：{vp.get('hobby','未填写')}")
                st.write(f"理想：{vp.get('dream','未填写')}")
                st.write(f"座右铭：{vp.get('motto','未填写')}")
                st.write(f"联系方式：{vp.get('contact','隐藏')}")
                st.subheader("给TA发送私信")
                msg_input = st.text_area("私信内容", key=f"star_msg_{view_name}")
                if st.button("发送私信", key=f"send_star_{view_name}") and msg_input.strip():
                    send_private_msg(curr_student, view_name, msg_input)
                    st.success("私信发送成功")
            if st.button("关闭档案详情"):
                st.session_state.view_user_detail = None
                st.rerun()

    # ===================== 5. 班级时光大事记 =====================
    elif nav == "班级时光大事记":
        st.markdown("### 📅 班级时光大事记 · 留存集体回忆")
        st.subheader("记录新班级事件")
        event_date = st.date_input("发生日期")
        event_title = st.text_input("事件标题", placeholder="例：毕业合照、研学旅行")
        event_detail = st.text_area("事件详细描述", height=80)
        img_upload = st.file_uploader("上传现场照片", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        submit_event = st.button("保存大事记")
        if submit_event and event_title.strip():
            with st.spinner("保存中..."):
                img_list = [compress_encode(f) for f in img_upload] if img_upload else []
                add_event(event_date, event_title, event_detail, curr_student, img_list)
            st.success("班级事件记录完成！")
            st.rerun()
        st.divider()
        st.markdown("## 📖 全部班级回忆")
        event_list = load_events()
        if not event_list:
            st.info("暂无班级大事记，快来记录你们的第一次集体活动吧")
        else:
            event_list.sort(key=lambda x: x["event_date"], reverse=True)
            for ev in event_list:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                st.write(f"**{ev['event_date']}** · 记录人：{ev['recorder']}")
                st.subheader(ev["title"])
                st.write(ev["detail"])
                ev_imgs = ev.get("images", [])
                if ev_imgs:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for idx, b64 in enumerate(ev_imgs):
                        st.image(io.BytesIO(base64.b64decode(b64)), width=180, caption=f"照片{idx+1}")
                        st.markdown(media_popup_b64(b64, "image/jpeg", f"大事记_{ev['id']}_图{idx+1}"), unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        # ===================== 6. 星海漂流瓶 =====================
    elif nav == "星海漂流瓶":
        st.markdown("### 🌊 星海漂流瓶 · 匿名倾诉小角落")
        col_throw, col_pick = st.columns([1,1])
        with col_throw:
            st.subheader("投放漂流瓶")
            bottle_text = st.text_area("写下心事、祝福、悄悄话", height=100, placeholder="匿名投放，随机被同学捡到")
            if st.button("投放进星海") and bottle_text.strip():
                throw_bottle(bottle_text)
                st.success("你的漂流瓶已沉入星海！")
                st.rerun()
        with col_pick:
            st.subheader("随机打捞漂流瓶")
            if st.button("开始打捞"):
                all_bottles = load_bottle()
                if len(all_bottles) == 0:
                    st.info("星海空空如也，还没有人投放漂流瓶")
                    st.session_state.current_bottle = None
                else:
                    random_pick = random.choice(all_bottles)
                    st.session_state.current_bottle = random_pick
                    st.rerun()
        st.divider()
        # 展示打捞到的瓶子
        if st.session_state.get("current_bottle"):
            b = st.session_state.current_bottle
            st.markdown('<div class="bottle-show-box">', unsafe_allow_html=True)
            st.subheader("🌊 你打捞到一只漂流瓶")
            st.write(f"投递时间：{b['create_time']}")
            st.markdown(f"<p style='font-size:16px;line-height:1.8;'>{b['content']}</p>", unsafe_allow_html=True)
            if st.button("放回大海"):
                st.session_state.current_bottle = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ===================== 7. 我的收藏留言 =====================
    elif nav == "我的收藏留言":
        st.markdown("### ⭐ 我的收藏夹 · 保存喜欢的帖子")
        collect_posts = get_collected_posts(curr_uname)
        if not collect_posts:
            st.info("收藏夹空空，去留言墙收藏喜欢的帖子吧")
        else:
            for post in collect_posts:
                st.markdown('<div class="card-box">', unsafe_allow_html=True)
                prof = get_profile(post["author"])
                st.markdown(avatar_html(prof.get("avatar"), post["author"], f"coll_avatar_{post['id']}"), unsafe_allow_html=True)
                display_name = "匿名用户" if post["is_anonymous"] else post["author"]
                st.write(f"**{display_name}** · {post['create_time']}")
                full_txt = post["text_content"]
                short_txt, expand = cut_text(full_txt, 100)
                st.write(short_txt)
                if expand and st.button("查看全文", key=f"coll_expand_{post['id']}"):
                    st.info(full_txt)
                # 图片预览
                img_list = post.get("images", [])
                if img_list:
                    st.markdown('<div class="img-grid">', unsafe_allow_html=True)
                    for idx, b64 in enumerate(img_list):
                        st.image(io.BytesIO(base64.b64decode(b64)), width=180)
                        st.markdown(media_popup_b64(b64, "image/jpeg", f"收藏帖{post['id']}_图{idx+1}"), unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                # 附件文件
                files = load_post_files(post["id"])
                if files:
                    st.subheader("附件下载")
                    for f in files:
                        st.markdown(media_popup_b64(f["file_b64"], "application/octet-stream", f"{f['file_name']}"), unsafe_allow_html=True)
                        st.write(f"📎 {f['file_name']}")
                # 取消收藏按钮
                if st.button("取消收藏", key=f"uncollect_{post['id']}"):
                    toggle_collect(curr_uname, post["id"])
                    st.success("已取消收藏")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# ===================== 侧边个人中心抽屉（完整保留） =====================
if st.session_state.show_user_drawer:
    with st.sidebar:
        st.markdown("## 👤 个人中心快捷面板")
        prof = get_profile(curr_uname)
        avatar_b64 = prof.get("avatar")
        if avatar_b64:
            st.image(io.BytesIO(base64.b64decode(avatar_b64)), width=120)
        st.write(f"当前账号：{curr_uname}")
        st.write(f"姓名：{curr_student}")
        st.divider()
        st.markdown("快捷跳转")
        if st.button("打开我的档案"):
            nav = "个人专属档案"
            st.session_state.show_user_drawer = False
            st.rerun()
        if st.button("查看我的收藏"):
            nav = "我的收藏留言"
            st.session_state.show_user_drawer = False
            st.rerun()
        if st.button("关闭面板"):
            st.session_state.show_user_drawer = False
            st.rerun()

# 页面底部版权
st.markdown("""
<hr style="margin-top:40px;">
<div style="text-align:center;opacity:0.7;color:#994444;font-size:13px;">
🍅 石榴16班毕业纪念册 | 十六岁的我们，岁岁常相见
</div>
""", unsafe_allow_html=True)            