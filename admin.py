import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client
import base64
from PIL import Image
import io
import pandas as pd
import uuid

# ===================== 页面基础配置 =====================
st.set_page_config(page_title="石榴16班·后台管理系统", page_icon="🛡️", layout="wide")

# 全局后台CSS（分层卡片、危险按钮、预览大图、数据看板）
admin_css = """
<style>
.stApp {
    background: #f7f8fa;
}
.main-title {
    font-size: 36px;
    color: #c83e3e;
    font-weight: bold;
    text-align: center;
    margin-bottom: 10px;
}
.sub-title {
    text-align:center;
    color:#994444;
    margin-bottom:30px;
}
/* 危险红色按钮 */
.danger-btn button {
    background-color: #e03131 !important;
    color:white !important;
}
.danger-btn button:hover {
    background-color: #c92a2a !important;
}
/* 操作按钮 */
.edit-btn button {
    background:#228be6 !important;
    color:white !important;
}
/* 统计看板卡片 */
.stat-card {
    background: linear-gradient(135deg,#fff3f0,#ffe9e3);
    padding:20px;
    border-radius:16px;
    border:1px solid #e8a8a8;
    text-align:center;
}
.stat-num {
    font-size:32px;
    font-weight:bold;
    color:#c83e3e;
}
.stat-label {
    color:#773333;
    font-size:14px;
}
/* 内容卡片 */
.info-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 1px 5px #e0e0e0;
    margin: 10px 0;
}
/* 大图预览容器 */
.img-preview-box {
    background:#f0f0f0;
    padding:10px;
    border-radius:10px;
}
/* 日志区域 */
.log-box {
    background:#1e1e1e;
    color:#ccc;
    padding:15px;
    border-radius:8px;
    font-family:monospace;
    font-size:13px;
}
</style>
"""
st.markdown(admin_css, unsafe_allow_html=True)

# ===================== Supabase 全局单例 =====================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase()

# ===================== 全局会话状态初始化 =====================
if "admin_login" not in st.session_state:
    st.session_state.admin_login = False
if "admin_operate_log" not in st.session_state:
    st.session_state.admin_operate_log = []
# 模拟在线登录用户池（前台登录缓存模拟在线状态）
if "online_user_list" not in st.session_state:
    st.session_state.online_user_list = []
# 当前查看详情ID缓存
if "current_view_id" not in st.session_state:
    st.session_state.current_view_id = None

# 管理员固定密码
ADMIN_PWD = "xar20091005"

# ===================== 全局工具函数 =====================
## 1. 操作日志写入
def write_operate_log(content: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = f"[{now}] {content}"
    st.session_state.admin_operate_log.append(log_text)
    # 仅保留最新50条日志
    if len(st.session_state.admin_operate_log) > 50:
        st.session_state.admin_operate_log = st.session_state.admin_operate_log[-50:]

## 2. 全表数据加载函数
def load_all_users():
    res = supabase.table("user_accounts").select("*").execute()
    user_dict = {}
    for row in res.data:
        user_dict[row["username"]] = row
    return user_dict, res.data

def load_all_forum():
    res = supabase.table("forum_messages").select("*").order("id", desc=True).execute()
    return res.data

def load_all_replies():
    res = supabase.table("forum_reply").select("*").order("id", desc=True).execute()
    return res.data

def load_all_tags():
    res = supabase.table("tag_data").select("*").order("id", desc=True).execute()
    return res.data

def load_all_profile():
    res = supabase.table("user_profile").select("*").execute()
    return res.data

def load_all_private_msg():
    res = supabase.table("private_msg").select("*").order("time", desc=True).execute()
    return res.data

def load_events():
    res = supabase.table("class_events").select("*").order("event_date", desc=True).execute()
    return res.data

def load_bottles():
    res = supabase.table("bottle_list").select("*").order("id", desc=True).execute()
    return res.data

def load_starwall():
    res = supabase.table("star_wall").select("*").execute()
    return res.data

## 3. Base64图片解码预览
def decode_img_preview(b64_str, width=300):
    try:
        img_bin = base64.b64decode(b64_str)
        img = Image.open(io.BytesIO(img_bin))
        return img
    except Exception as e:
        return None

## 4. 导出CSV工具
def export_df_csv(df: pd.DataFrame, filename: str):
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
    csv_bytes = csv_buf.getvalue().encode("utf-8-sig")
    st.download_button(
        label=f"下载 {filename}.csv",
        data=csv_bytes,
        file_name=f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

## 5. 全局数据统计看板
def render_stat_dashboard():
    users_dict, users_raw = load_all_users()
    forum = load_all_forum()
    replies = load_all_replies()
    starwall = load_starwall()
    msg = load_all_private_msg()
    events = load_events()
    bottles = load_bottles()
    tags = load_all_tags()
    profile = load_all_profile()
    online_count = len(st.session_state.online_user_list)

    col1,col2,col3,col4,col5,col6 = st.columns(6)
    with col1:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(users_raw)}</div>
            <div class="stat-label">注册学生账号</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{online_count}</div>
            <div class="stat-label">当前在线用户</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(forum)}</div>
            <div class="stat-label">班级留言总数</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(replies)}</div>
            <div class="stat-label">评论总数</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(starwall)}</div>
            <div class="stat-label">星光武将卡数量</div>
        </div>""", unsafe_allow_html=True)
    with col6:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(msg)}</div>
            <div class="stat-label">私信总数</div>
        </div>""", unsafe_allow_html=True)
    st.divider()
    col_a,col_b,col_c,col_d = st.columns(4)
    with col_a:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(tags)}</div>
            <div class="stat-label">同学互评评语</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(profile)}</div>
            <div class="stat-label">完善个人档案人数</div>
        </div>""", unsafe_allow_html=True)
    with col_c:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(events)}</div>
            <div class="stat-label">班级大事记</div>
        </div>""", unsafe_allow_html=True)
    with col_d:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-num">{len(bottles)}</div>
            <div class="stat-label">漂流瓶总数</div>
        </div>""", unsafe_allow_html=True)
    st.divider()

# ===================== 登录页面 =====================
def admin_login_page():
    st.markdown('<div class="main-title">🛡️ 石榴16班 后台管理系统</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">全功能数据管理 · 在线监测 · 批量操作</div>', unsafe_allow_html=True)
    st.divider()
    st.info("仅管理员可登录，输入专用管理密码进入后台控制面板")
    pwd_input = st.text_input("管理员密码", type="password")
    login_btn = st.button("登录后台", type="primary")

    if login_btn:
        if pwd_input == ADMIN_PWD:
            st.session_state.admin_login = True
            write_operate_log("管理员登录后台系统")
            st.success("密码校验通过，正在进入管理面板...")
            st.rerun()
        else:
            st.error("密码错误，拒绝访问后台")
            write_operate_log("管理员密码输入错误，登录失败")

# ===================== 后台主面板入口 =====================
def admin_dashboard():
    # 顶部头部
    st.markdown('<div class="main-title">🛡️ 班级后台管理中心</div>', unsafe_allow_html=True)
    col_head1, col_head2, col_head3 = st.columns([6,1,1])
    with col_head2:
        if st.button("刷新全部数据"):
            write_operate_log("手动刷新全量业务数据")
            st.rerun()
    with col_head3:
        logout = st.button("退出登录", type="secondary")
        if logout:
            write_operate_log("管理员退出后台")
            st.session_state.admin_login = False
            st.session_state.online_user_list = []
            st.rerun()
    st.divider()

    # 全局数据统计看板
    render_stat_dashboard()

    # 顶级导航Tab（10大功能模块）
    tab_overview, tab_online, tab_user, tab_forum, tab_reply, tab_star, tab_msg, tab_tag_event, tab_bottle, tab_system = st.tabs([
        "总览&数据导出", "在线用户监测", "学生账号&档案管理", "班级留言管理",
        "评论楼中楼管理", "星光武将卡管理", "私信信箱管理", "评语&大事记",
        "漂流瓶管理", "系统工具&操作日志"
    ])

    # ========== Tab1：总览&批量导出 ==========
    with tab_overview:
        st.subheader("📤 全业务数据表批量导出CSV")
        all_users_dict, users_raw = load_all_users()
        forum_data = load_all_forum()
        reply_data = load_all_replies()
        star_data = load_starwall()
        msg_data = load_all_private_msg()
        tag_data = load_all_tags()
        profile_data = load_all_profile()
        event_data = load_events()
        bottle_data = load_bottles()

        exp1,exp2,exp3,exp4 = st.columns(4)
        with exp1:
            export_df_csv(pd.DataFrame(users_raw), "学生账号表")
            export_df_csv(pd.DataFrame(profile_data), "个人档案表")
        with exp2:
            export_df_csv(pd.DataFrame(forum_data), "留言墙数据表")
            export_df_csv(pd.DataFrame(reply_data), "评论数据表")
        with exp3:
            export_df_csv(pd.DataFrame(star_data), "星光武将卡表")
            export_df_csv(pd.DataFrame(msg_data), "私信数据表")
        with exp4:
            export_df_csv(pd.DataFrame(tag_data), "互评评语表")
            export_df_csv(pd.DataFrame(event_data), "班级大事记表")
        export_df_csv(pd.DataFrame(bottle_data), "漂流瓶数据表")

        st.divider()
        st.subheader("数据总览预览（各表前10条）")
        st.caption("如需完整数据请使用上方导出按钮")
        st.dataframe(pd.DataFrame(users_raw[:10]), use_container_width=True)

    # ========== Tab2：在线用户监测模块 ==========
    with tab_online:
        st.subheader("🟢 当前在线学生监测面板")
        users_dict, users_raw = load_all_users()
        all_student_names = [row["student_name"] for row in users_raw]

        col_on1, col_on2 = st.columns([2,1])
        with col_on1:
            st.info("模拟前台登录在线池（用于展示实时在线状态）")
            select_online = st.multiselect("添加在线学生", all_student_names)
            if st.button("更新在线列表"):
                st.session_state.online_user_list = select_online
                write_operate_log(f"更新在线用户池，当前在线{len(select_online)}人")
                st.rerun()
        with col_on2:
            st.metric("实时在线人数", value=len(st.session_state.online_user_list))
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("清空全部在线用户"):
                st.session_state.online_user_list = []
                write_operate_log("清空在线用户列表")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("在线学生名单")
        if len(st.session_state.online_user_list) == 0:
            st.warning("暂无学生登录在线")
        else:
            for name in st.session_state.online_user_list:
                st.success(f"🟢 {name} 在线中")

    # ========== Tab3：学生账号+个人档案一体化管理 ==========
    with tab_user:
        users_dict, users_raw = load_all_users()
        profile_all = load_all_profile()
        st.subheader("学生账号完整管理（注册/删除/档案编辑）")
        st.caption(f"总注册账号：{len(users_raw)}")

        # 新增学生账号
        st.markdown("### 新增学生注册账号")
        new_uname = st.text_input("新建账号用户名")
        new_pwd = st.text_input("账号密码", type="password")
        new_stu_name = st.selectbox("绑定学生姓名", CLASS_STUDENTS)
        if st.button("创建账号", type="primary"):
            if new_uname.strip() and new_pwd.strip():
                if new_uname in users_dict:
                    st.error("用户名已存在，无法创建")
                else:
                    supabase.table("user_accounts").insert({
                        "username": new_uname,
                        "password": new_pwd,
                        "student_name": new_stu_name
                    }).execute()
                    write_operate_log(f"新建账号：{new_uname} 学生：{new_stu_name}")
                    st.success("账号创建完成")
                    st.rerun()

        st.divider()
        # 删除账号
        st.markdown("### 删除学生账号（同步清空该学生星光卡/档案/私信）")
        del_username = st.text_input("待删除用户名")
        confirm_del_user = st.checkbox("确认永久删除该账号全部关联数据")
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("执行删除账号") and confirm_del_user and del_username:
            # 级联删除关联数据
            supabase.table("user_accounts").delete().eq("username", del_username).execute()
            supabase.table("user_profile").delete().eq("username", del_username).execute()
            supabase.table("star_wall").delete().eq("username", del_username).execute()
            supabase.table("private_msg").delete().eq("sender", del_username).execute()
            write_operate_log(f"彻底删除账号：{del_username} 及全部关联数据")
            st.success("账号及关联数据已全部清除")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        # 编辑个人档案
        st.markdown("### 后台直接编辑学生毕业档案")
        edit_user_select = st.selectbox("选择要编辑档案的学生账号", list(users_dict.keys()))
        target_stu_name = users_dict[edit_user_select]["student_name"]
        # 读取现有档案
        curr_profile = None
        for p in profile_all:
            if p["username"] == edit_user_select:
                curr_profile = p
                break
        nick = st.text_input("昵称", value=curr_profile.get("nick","") if curr_profile else "")
        hobby = st.text_input("爱好", value=curr_profile.get("hobby","") if curr_profile else "")
        dream = st.text_input("未来理想", value=curr_profile.get("dream","") if curr_profile else "")
        motto = st.text_area("座右铭", value=curr_profile.get("motto","") if curr_profile else "")
        contact = st.text_input("联系方式", value=curr_profile.get("contact","") if curr_profile else "")
        st.markdown('<div class="edit-btn">', unsafe_allow_html=True)
        if st.button("保存档案修改"):
            data_update = {
                "nick":nick,"hobby":hobby,"dream":dream,"motto":motto,"contact":contact
            }
            if curr_profile:
                supabase.table("user_profile").update(data_update).eq("username", edit_user_select).execute()
            else:
                data_update["username"] = edit_user_select
                supabase.table("user_profile").insert(data_update).execute()
            write_operate_log(f"后台修改学生{target_stu_name}档案信息")
            st.success("档案修改保存成功")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("全部账号列表")
        st.dataframe(pd.DataFrame(users_raw), use_container_width=True)

    # ========== Tab4：班级留言墙管理（编辑/删除/大图预览） ==========
    with tab_forum:
        forum_list = load_all_forum()
        st.subheader("班级留言完整管理（删除、预览配图、批量清空）")
        st.caption(f"总留言条数：{len(forum_list)}")
        del_fid = st.number_input("输入待删除留言ID", min_value=1)
        del_confirm_forum = st.checkbox("同步删除该留言下所有评论")
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("删除留言+全部关联评论") and del_confirm_forum:
            supabase.table("forum_reply").delete().eq("post_id", del_fid).execute()
            supabase.table("forum_messages").delete().eq("id", del_fid).execute()
            write_operate_log(f"删除留言ID：{del_fid} 及其全部评论")
            st.success("删除完成")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("留言预览（带图片大图查看）")
        for item in forum_list[:30]:
            with st.container(border=True):
                st.write(f"ID:{item['id']} | 发布人：{item['author']} | {item['create_time']} | 点赞数：{item['like_count']}")
                st.write("正文：", item["text_content"])
                # 展示图片
                img_list = item.get("images", [])
                if len(img_list) > 0:
                    st.markdown('<div class="img-preview-box">', unsafe_allow_html=True)
                    img_cols = st.columns(len(img_list))
                    for idx, b64 in enumerate(img_list):
                        img = decode_img_preview(b64)
                        if img:
                            with img_cols[idx]:
                                st.image(img, width=180)
                    st.markdown('</div>', unsafe_allow_html=True)
                # 视频暂不预览
                if item.get("video"):
                    st.info("本条留言附带短视频，后台暂不预览")
                st.divider()

    # ========== Tab5：评论楼中楼管理 ==========
    with tab_reply:
        reply_list = load_all_replies()
        st.subheader("全部评论管理（单条删除，关联帖子ID）")
        st.caption(f"评论总条数：{len(reply_list)}")
        del_rid = st.number_input("删除评论ID", min_value=1)
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("删除单条评论"):
            supabase.table("forum_reply").delete().eq("id", del_rid).execute()
            write_operate_log(f"删除评论ID：{del_rid}")
            st.success("删除成功")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        st.dataframe(pd.DataFrame(reply_list[:50]), use_container_width=True)

    # ========== Tab6：星光武将卡完整管理（适配前台三国杀卡片） ==========
    with tab_star:
        star_list = load_starwall()
        users_dict, users_raw = load_all_users()
        st.subheader("✨ 班级星光墙武将卡后台管理（编辑/删除/大图头像预览）")
        st.caption(f"已创建星光卡总数：{len(star_list)}")

        # 删除星光卡
        del_star_id = st.number_input("删除星光卡ID", min_value=1)
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("删除该学生星光卡"):
            supabase.table("star_wall").delete().eq("id", del_star_id).execute()
            write_operate_log(f"删除星光卡ID：{del_star_id}")
            st.success("删除完成")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        # 后台编辑星光卡
        st.markdown("### 后台直接修改学生星光武将卡")
        star_edit_select = st.selectbox("选择要编辑的星光卡", [f"{s['id']} | {s['student_name']}" for s in star_list])
        edit_star_id = int(star_edit_select.split("|")[0].strip())
        target_card = None
        for s in star_list:
            if s["id"] == edit_star_id:
                target_card = s
                break
        if target_card:
            title_edit = st.text_input("武将称号", value=target_card.get("title",""))
            s1n = st.text_input("一技能名称", value=target_card.get("skill1_name",""))
            s1d = st.text_area("一技能描述", value=target_card.get("skill1_desc",""))
            s2n = st.text_input("二技能名称", value=target_card.get("skill2_name",""))
            s2d = st.text_area("二技能描述", value=target_card.get("skill2_desc",""))
            bio_edit = st.text_area("人物背景简介", value=target_card.get("bio",""))
            # 头像预览
            if target_card.get("avatar_b64"):
                st.markdown('<div class="img-preview-box">', unsafe_allow_html=True)
                img = decode_img_preview(target_card["avatar_b64"])
                if img:
                    st.image(img, width=260)
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="edit-btn">', unsafe_allow_html=True)
            if st.button("保存星光卡修改"):
                update_data = {
                    "title":title_edit,"skill1_name":s1n,"skill1_desc":s1d,
                    "skill2_name":s2n,"skill2_desc":s2d,"bio":bio_edit
                }
                supabase.table("star_wall").update(update_data).eq("id", edit_star_id).execute()
                write_operate_log(f"后台修改{target_card['student_name']}星光武将卡")
                st.success("星光卡修改保存成功")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("全部星光卡列表预览")
        for card in star_list:
            with st.container(border=True):
                st.write(f"ID:{card['id']} | 学生：{card['student_name']} | 账号：{card['username']}")
                st.write(f"称号：{card.get('title','无')}")
                st.write(f"一技能【{card.get('skill1_name','无')}】：{card.get('skill1_desc','无描述')}")
                st.write(f"二技能【{card.get('skill2_name','无')}】：{card.get('skill2_desc','无描述')}")
                st.divider()

    # ========== Tab7：私信信箱管理（后台查看全部私信） ==========
    with tab_msg:
        msg_list = load_all_private_msg()
        st.subheader("全班私信完整后台查看（保护隐私，仅管理员可见）")
        st.caption(f"私信总条数：{len(msg_list)}")
        st.dataframe(pd.DataFrame(msg_list), use_container_width=True)
        st.divider()
        del_msg_id = st.number_input("删除违规私信ID", min_value=1)
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("删除单条私信"):
            supabase.table("private_msg").delete().eq("id", del_msg_id).execute()
            write_operate_log(f"删除私信ID：{del_msg_id}")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ========== Tab8：互评评语 + 班级大事记 ==========
    with tab_tag_event:
        col_t1, col_t2 = st.columns(2)
        # 互评评语
        with col_t1:
            tag_list = load_all_tags()
            st.subheader("学生互评评语管理")
            del_tid = st.number_input("删除评语ID", min_value=1)
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("删除评语"):
                supabase.table("tag_data").delete().eq("id", del_tid).execute()
                write_operate_log(f"删除互评评语ID：{del_tid}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(tag_list[:30]), use_container_width=True)
        # 大事记
        with col_t2:
            event_list = load_events()
            st.subheader("班级大事记管理")
            del_eid = st.number_input("删除大事记ID", min_value=1)
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("删除大事记"):
                supabase.table("class_events").delete().eq("id", del_eid).execute()
                write_operate_log(f"删除大事记ID：{del_eid}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            for ev in event_list[:15]:
                st.write(f"{ev['event_date']} | {ev['title']}")
                st.write(ev["detail"][:120]+"..." if len(ev["detail"])>120 else ev["detail"])
                st.divider()

    # ========== Tab9：漂流瓶管理 ==========
    with tab_bottle:
        bottle_list = load_bottles()
        st.subheader("匿名漂流瓶后台管理")
        st.caption(f"漂流瓶总数：{len(bottle_list)}")
        del_bid = st.number_input("删除漂流瓶ID", min_value=1)
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("删除漂流瓶"):
            supabase.table("bottle_list").delete().eq("id", del_bid).execute()
            write_operate_log(f"删除漂流瓶ID：{del_bid}")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(bottle_list[:40]), use_container_width=True)

    # ========== Tab10：系统工具 + 操作日志 ==========
    with tab_system:
        st.subheader("⚠️ 系统高危批量清空工具（不可逆）")
        st.warning("所有清空操作永久删除数据，数据表结构保留，删除后无法恢复！")
        clear_opt = st.selectbox("选择批量清空数据表", [
            "forum_messages 全部留言（同步清空评论）",
            "forum_reply 全部评论",
            "tag_data 全部互评评语",
            "bottle_list 全部漂流瓶",
            "class_events 全部大事记",
            "star_wall 全部星光武将卡",
            "private_msg 全部私信",
            "一键清空所有业务数据（留言/评论/星光卡/私信/评语/大事记/漂流瓶）"
        ])
        clear_confirm = st.checkbox("我已完全知晓风险，确认永久清空数据")
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("执行批量清空") and clear_confirm:
            with st.spinner("批量删除数据中..."):
                if clear_opt == "forum_messages 全部留言（同步清空评论）":
                    supabase.table("forum_reply").delete().gt("id",0).execute()
                    supabase.table("forum_messages").delete().gt("id",0).execute()
                elif clear_opt == "forum_reply 全部评论":
                    supabase.table("forum_reply").delete().gt("id",0).execute()
                elif clear_opt == "tag_data 全部互评评语":
                    supabase.table("tag_data").delete().gt("id",0).execute()
                elif clear_opt == "bottle_list 全部漂流瓶":
                    supabase.table("bottle_list").delete().gt("id",0).execute()
                elif clear_opt == "class_events 全部大事记":
                    supabase.table("class_events").delete().gt("id",0).execute()
                elif clear_opt == "star_wall 全部星光武将卡":
                    supabase.table("star_wall").delete().gt("id",0).execute()
                elif clear_opt == "private_msg 全部私信":
                    supabase.table("private_msg").delete().gt("id",0).execute()
                else:
                    supabase.table("forum_reply").delete().gt("id",0).execute()
                    supabase.table("forum_messages").delete().gt("id",0).execute()
                    supabase.table("tag_data").delete().gt("id",0).execute()
                    supabase.table("bottle_list").delete().gt("id",0).execute()
                    supabase.table("class_events").delete().gt("id",0).execute()
                    supabase.table("star_wall").delete().gt("id",0).execute()
                    supabase.table("private_msg").delete().gt("id",0).execute()
            write_operate_log(f"执行批量清空操作：{clear_opt}")
            st.success("指定数据表数据已全部清空！")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("📋 管理员操作日志（最近50条）")
        log_text = "\n".join(st.session_state.admin_operate_log)
        st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)
        if st.button("清空操作日志"):
            st.session_state.admin_operate_log = []
            st.rerun()

# ===================== 班级学生名单常量（和前台完全统一） =====================
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

# ===================== 程序入口 =====================
if __name__ == "__main__":
    if not st.session_state.admin_login:
        admin_login_page()
    else:
        admin_dashboard()