import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client
import base64
from PIL import Image
import io

# ===================== 页面基础配置 =====================
st.set_page_config(page_title="班级后台管理系统", page_icon="🛡️", layout="wide")

# 后台专用CSS
admin_css = """
<style>
.stApp {
    background: #f7f8fa;
}
.main-title {
    font-size: 36px;
    color: #233759;
    font-weight: bold;
    text-align: center;
    margin-bottom: 30px;
}
/* 危险按钮样式 */
.danger-btn button {
    background-color: #e03131 !important;
}
.danger-btn button:hover {
    background-color: #c92a2a !important;
}
.info-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 1px 5px #e0e0e0;
    margin: 10px 0;
}
</style>
"""
st.markdown(admin_css, unsafe_allow_html=True)

# ===================== Supabase 初始化（和前台共用） =====================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase()

# ===================== 全局状态 =====================
if "admin_login" not in st.session_state:
    st.session_state.admin_login = False

# 固定管理员密码
ADMIN_PWD = "xar20091005"

# ===================== 工具函数 =====================
def load_all_users():
    res = supabase.table("user_accounts").select("*").execute()
    user_dict = {}
    for row in res.data:
        user_dict[row["username"]] = row
    return user_dict

def load_all_forum():
    res = supabase.table("forum_messages").select("*").order("id", desc=True).limit(1000).execute()
    return res.data

def load_all_replies():
    res = supabase.table("forum_reply").select("*").limit(2000).execute()
    return res.data

def load_all_tags():
    res = supabase.table("tag_data").select("*").execute()
    return res.data

def load_events():
    res = supabase.table("class_events").select("*").order("event_date", desc=True).execute()
    return res.data

def load_bottles():
    res = supabase.table("bottle_list").select("*").execute()
    return res.data

# ===================== 管理员登录页面（仅固定密码登录，无账号校验） =====================
def admin_login_page():
    st.markdown('<div class="main-title">🛡️ 班级后台管理系统</div>', unsafe_allow_html=True)
    st.divider()
    st.info("本后台仅管理员可进入，输入专用管理密码登录")
    pwd_input = st.text_input("请输入管理员密码", type="password")
    login_btn = st.button("登录后台", type="primary")

    if login_btn:
        if pwd_input == ADMIN_PWD:
            st.session_state.admin_login = True
            st.success("密码正确，正在进入管理面板...")
            st.rerun()
        else:
            st.error("密码错误，无法登录后台")

# ===================== 后台管理主面板 =====================
def admin_dashboard():
    st.markdown('<div class="main-title">🛡️ 后台管理中心</div>', unsafe_allow_html=True)
    logout = st.button("退出登录", type="secondary")
    if logout:
        st.session_state.admin_login = False
        st.rerun()
    st.divider()

    # 分标签管理
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "留言管理", "评论管理", "学生账号管理", "评语管理", "大事记&漂流瓶", "系统工具"
    ])

    # 1. 留言管理
    with tab1:
        st.subheader("全部留言管理（可删除违规内容）")
        forum_list = load_all_forum()
        st.caption(f"总留言数量：{len(forum_list)}")
        del_msg_id = st.number_input("输入待删除留言ID", min_value=1)
        if st.button("删除该留言 + 关联全部评论", type="primary"):
            confirm = st.checkbox("确认永久删除，无法恢复")
            if confirm:
                with st.spinner("删除中..."):
                    supabase.table("forum_reply").delete().eq("post_id", del_msg_id).execute()
                    supabase.table("forum_messages").delete().eq("id", del_msg_id).execute()
                st.success("删除完成！")
                st.rerun()
        st.divider()
        st.subheader("留言预览列表（仅展示前30条）")
        for item in forum_list[:30]:
            with st.container():
                st.write(f"ID:{item['id']} | 发布人：{item['author']} | {item['create_time']}")
                content_show = item["text_content"][:150] + "..." if len(item["text_content"]) > 150 else item["text_content"]
                st.write(content_show)
                st.divider()

    # 2. 评论管理
    with tab2:
        st.subheader("全部评论管理")
        reply_list = load_all_replies()
        st.caption(f"总评论数量：{len(reply_list)}")
        del_reply_id = st.number_input("输入待删除评论ID", min_value=1)
        if st.button("删除单条评论", type="primary"):
            confirm = st.checkbox("确认删除")
            if confirm:
                supabase.table("forum_reply").delete().eq("id", del_reply_id).execute()
                st.success("删除完成")
                st.rerun()
        st.divider()
        for r in reply_list[:30]:
            st.write(f"评论ID:{r['id']} | 帖子ID:{r['post_id']} | 作者:{r['writer']}")
            st.write(r["content"])
            st.divider()

    # 3. 账号管理
    with tab3:
        st.subheader("学生账号管理")
        user_data = load_all_users()
        st.caption(f"注册总人数：{len(user_data)}")
        username_del = st.text_input("输入要删除的账号用户名")
        # 外层套div实现红色危险按钮
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("删除账号", type="secondary"):
            confirm = st.checkbox("确认删除该学生账号")
            if confirm:
                supabase.table("user_accounts").delete().eq("username", username_del).execute()
                st.success("账号已删除")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        # 展示所有账号 【修复：info["student_name"] 替换原来 info["name"]】
        for uname, info in user_data.items():
            st.write(f"用户名：{uname} | 姓名：{info['student_name']}")

    # 4. 评语管理
    with tab4:
        st.subheader("互评评语管理")
        tag_list = load_all_tags()
        del_tag_id = st.number_input("删除评语ID", min_value=1)
        if st.button("删除该条评语", type="primary"):
            supabase.table("tag_data").delete().eq("id", del_tag_id).execute()
            st.success("已删除")
            st.rerun()
        for t in tag_list[:30]:
            st.write(f"评价对象：{t['target_student']} | 评价人：{t['writer']}")
            st.write(t["comment"])
            st.divider()

    # 5. 大事记 & 漂流瓶
    with tab5:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("班级大事记")
            event_list = load_events()
            del_eid = st.number_input("删除大事记ID", min_value=1)
            if st.button("删除大事记", type="primary"):
                supabase.table("class_events").delete().eq("id", del_eid).execute()
                st.rerun()
            for e in event_list:
                st.write(f"{e['event_date']} | {e['title']}")
        with col2:
            st.subheader("漂流瓶管理")
            bottle_list = load_bottles()
            del_bid = st.number_input("删除漂流瓶ID", min_value=1)
            if st.button("删除漂流瓶", type="primary"):
                supabase.table("bottle_list").delete().eq("id", del_bid).execute()
                st.rerun()
            for b in bottle_list[:20]:
                st.write(f"发布人：{b['nickname']} | {b['content'][:100]}")

    # 6. 系统工具（清空数据，只删记录，保留数据表）
    with tab6:
        st.markdown("## ⚠️ 高危操作区，谨慎使用")
        st.warning("以下操作仅删除数据记录，数据表、字段、索引全部保留，删除后无法恢复！")
        clear_opt = st.selectbox("选择要清空的数据表", [
            "forum_messages 全部留言（同步清空所有评论）",
            "forum_reply 全部评论",
            "tag_data 全部互评评语",
            "bottle_list 全部漂流瓶",
            "class_events 全部班级大事记",
            "一键清空所有业务数据（留言/评论/评语/漂流瓶/大事记）"
        ])
        clear_confirm = st.checkbox("我已确认风险，同意永久删除数据")
        st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
        if st.button("执行清空", type="secondary") and clear_confirm:
            with st.spinner("正在清空数据..."):
                if clear_opt == "forum_messages 全部留言（同步清空所有评论）":
                    supabase.table("forum_reply").delete().gt("id", 0).execute()
                    supabase.table("forum_messages").delete().gt("id", 0).execute()
                elif clear_opt == "forum_reply 全部评论":
                    supabase.table("forum_reply").delete().gt("id", 0).execute()
                elif clear_opt == "tag_data 全部互评评语":
                    supabase.table("tag_data").delete().gt("id", 0).execute()
                elif clear_opt == "bottle_list 全部漂流瓶":
                    supabase.table("bottle_list").delete().gt("id", 0).execute()
                elif clear_opt == "class_events 全部班级大事记":
                    supabase.table("class_events").delete().gt("id", 0).execute()
                else:
                    supabase.table("forum_reply").delete().gt("id", 0).execute()
                    supabase.table("forum_messages").delete().gt("id", 0).execute()
                    supabase.table("tag_data").delete().gt("id", 0).execute()
                    supabase.table("bottle_list").delete().gt("id", 0).execute()
                    supabase.table("class_events").delete().gt("id", 0).execute()
            st.success("对应数据表数据已全部清空，表结构完整保留！")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ===================== 程序入口 =====================
if __name__ == "__main__":
    if not st.session_state.admin_login:
        admin_login_page()
    else:
        admin_dashboard()