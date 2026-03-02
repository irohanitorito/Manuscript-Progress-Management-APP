import sqlite3
import hashlib
from datetime import date, datetime
import streamlit as st

# 1. 基本設定
st.set_page_config(page_title="進捗管理アプリ", layout="centered")

# 2. データベース初期化
conn = sqlite3.connect("progress.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)")
c.execute("""
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
    title TEXT, total_pages INTEGER, event_name TEXT, event_date TEXT, deadline TEXT,
    plot_percent INTEGER DEFAULT 0, name_pages INTEGER DEFAULT 0,
    draft_pages INTEGER DEFAULT 0, line_pages INTEGER DEFAULT 0, tone_pages INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# セッション管理
if "user_id" not in st.session_state: st.session_state.user_id = None
if "username" not in st.session_state: st.session_state.username = None
if "page" not in st.session_state: st.session_state.page = "list"
if "edit_id" not in st.session_state: st.session_state.edit_id = None
if "view_id" not in st.session_state: st.session_state.view_id = None
if "selected_title_for_daily" not in st.session_state: st.session_state.selected_title_for_daily = None
if "confirm_delete" not in st.session_state: st.session_state.confirm_delete = False

# 3. カスタムCSS
st.markdown("""
<style>
    .stApp { background-color: white; color: #B282E6; }
    header { visibility: hidden; }
    .header-bar { background-color: #C199E5; height: 60px; display: flex; align-items: center; justify-content: center; margin: -60px -500px 30px -500px; }
    .header-title { color: white; font-size: 1.1rem; font-weight: bold; }
    .big-datetime { text-align: center; font-size: clamp(1.8rem, 8vw, 2.8rem); font-weight: bold; color: #B282E6; margin-bottom: 15px; }
    div.stButton > button { border-radius: 12px !important; font-weight: bold !important; }
    div.stButton > button[kind="primary"] { background-color: #C199E5 !important; color: white !important; border: none !important; }
    div.stButton > button[kind="secondary"] { border: 2px solid #C199E5 !important; color: #C199E5 !important; background-color: white !important; }
    .progress-container { width: 100%; background-color: #F0F0F0; border-radius: 10px; margin: 5px 0; height: 12px; overflow: hidden; }
    .progress-bar-fill { height: 100%; background-color: #C199E5; transition: width 0.3s ease; }
    .back-btn-wrapper { margin-top: -90px; margin-bottom: 40px; }
</style>
""", unsafe_allow_html=True)

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text
def calculate_total_percent(work_data):
    total = work_data[3] if work_data[3] and work_data[3] > 0 else 1
    p = (work_data[7] + (work_data[8]/total*100) + (work_data[10]/total*100) + (work_data[11]/total*100)) / 4
    return round(max(0.0, min(float(p), 100.0)), 1)

# --- ログイン・会員登録 ---
if st.session_state.user_id is None:
    st.markdown('<div class="header-bar"><div class="header-title">進捗管理ログイン</div></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["ログイン", "新規登録"])
    with tab1:
        u = st.text_input("ユーザー名", key="l_u")
        p = st.text_input("パスワード", type='password', key="l_p")
        if st.button("ログイン", type="primary", use_container_width=True):
            c.execute('SELECT id, password FROM users WHERE username = ?', (u,))
            data = c.fetchone()
            if data and check_hashes(p, data[1]):
                st.session_state.user_id, st.session_state.username = data[0], u
                st.rerun()
            else: st.error("ユーザー名かパスワードが違います")
    with tab2:
        nu = st.text_input("希望のユーザー名", key="r_u")
        np = st.text_input("希望のパスワード", type='password', key="r_p")
        if st.button("アカウント作成", use_container_width=True):
            if nu and np:
                try:
                    c.execute('INSERT INTO users(username, password) VALUES (?,?)', (nu, make_hashes(np)))
                    conn.commit(); st.success("作成完了！ログインしてください")
                except: st.error("そのユーザー名は既に使用されています")
    st.stop()

# --- サイドバーメニュー ---
with st.sidebar:
    st.write(f"👤 {st.session_state.username}")
    if st.button("🏠 ホーム"): st.session_state.page = "list"; st.rerun()
    if st.button("⚙️ パスワード変更"): st.session_state.page = "settings"; st.rerun()
    st.divider()
    if st.button("🚪 ログアウト"):
        st.session_state.user_id = None; st.session_state.username = None; st.rerun()

# --- 画面表示 ---
if st.session_state.page == "list":
    st.markdown(f'<div class="header-bar"><div class="header-title">{st.session_state.username}さんの進捗</div></div>', unsafe_allow_html=True)
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    st.markdown(f'<div class="big-datetime">{now_str}</div>', unsafe_allow_html=True)
    c.execute("SELECT * FROM works WHERE user_id = ?", (st.session_state.user_id,))
    works = c.fetchall()
    _, col_c, _ = st.columns([1, 2, 1])
    if col_c.button("今日の進捗", use_container_width=True, disabled=(len(works) == 0)):
        st.session_state.selected_title_for_daily = None; st.session_state.page = "daily"; st.rerun()
    st.divider()
    col_e, col_b = st.columns([7, 1])
    with col_b:
        if st.button("＋", key="add_btn_ui", type="primary"):
            st.session_state.edit_id = None; st.session_state.page = "form"; st.rerun()
    for work in works:
        try: ev_d = date.fromisoformat(work[5]); ev_s = f"{ev_d.month}/{ev_d.day}"
        except: ev_s = work[5]
        try: dl_d = date.fromisoformat(work[6]); dl_s = f"{dl_d.month}/{dl_d.day}"
        except: dl_s = work[6]
        st.markdown(f'<div style="font-size:12px; font-weight:bold; color:#B282E6; margin-top:15px;">{ev_s} {work[4]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:18px; font-weight:bold; color:#B282E6; margin-bottom:5px;">{dl_s}〆 {work[2]}</div>', unsafe_allow_html=True)
        percent = calculate_total_percent(work)
        col_bar, col_edit, col_read = st.columns([5, 1.2, 1.2])
        with col_bar: st.markdown(f'<div class="progress-container"><div class="progress-bar-fill" style="width:{percent}%;"></div></div><div style="text-align:right; font-size:10px; color:#B282E6;">{percent}%</div>', unsafe_allow_html=True)
        with col_edit:
            if st.button("編集", key=f"ed_{work[0]}", use_container_width=True, type="secondary"): st.session_state.edit_id = work[0]; st.session_state.page = "form"; st.rerun()
        with col_read:
            if st.button("閲覧", key=f"rd_{work[0]}", use_container_width=True, type="primary"): st.session_state.view_id = work[0]; st.session_state.page = "view"; st.rerun()

elif st.session_state.page == "settings":
    st.markdown('<div class="header-bar"><div class="header-title">パスワード変更</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bs"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    current_p = st.text_input("現在のパスワード", type="password")
    new_p = st.text_input("新しいパスワード", type="password")
    conf_p = st.text_input("新しいパスワード（確認）", type="password")
    
    if st.button("パスワードを更新する", type="primary", use_container_width=True):
        c.execute('SELECT password FROM users WHERE id = ?', (st.session_state.user_id,))
        hashed_p = c.fetchone()[0]
        if not check_hashes(current_p, hashed_p):
            st.error("現在のパスワードが正しくありません")
        elif new_p != conf_p:
            st.error("新しいパスワードが一致しません")
        elif len(new_p) < 4:
            st.error("パスワードは4文字以上にしてください")
        else:
            c.execute('UPDATE users SET password = ? WHERE id = ?', (make_hashes(new_p), st.session_state.user_id))
            conn.commit()
            st.success("パスワードを更新しました！")

# --- 他の画面 (view, daily, form) は前回と同じため維持 ---
elif st.session_state.page == "view":
    c.execute("SELECT * FROM works WHERE id=? AND user_id=?", (st.session_state.view_id, st.session_state.user_id))
    work = c.fetchone()
    if not work: st.session_state.page = "list"; st.rerun()
    st.markdown(f'<div class="header-bar"><div class="header-title">{work[2]}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bv"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    percent = calculate_total_percent(work)
    st.markdown(f'<div class="progress-container" style="height:15px;"><div class="progress-bar-fill" style="width:{percent}%;"></div></div><div style="text-align:right; font-size:0.8rem; color:#B282E6; margin-bottom:20px;">{percent}%</div>', unsafe_allow_html=True)
    st.divider()
    def detail_item(label, current, total=None):
        col_l, col_r = st.columns([1, 1])
        with col_l: st.markdown(f'<div style="font-weight:bold; color:#B282E6;">{label}</div>', unsafe_allow_html=True)
        with col_r: st.markdown(f'<div style="text-align:right; font-weight:bold; color:#B282E6;">{current}{"/"+str(total)+"P" if total else "%"}</div>', unsafe_allow_html=True)
    detail_item("プロット", work[7])
    detail_item("ネーム", work[8], work[3])
    detail_item("線画", work[10], work[3])
    detail_item("トーン・仕上げ", work[11], work[3])
    if st.button("今日の進捗を入力する", use_container_width=True, type="primary"): st.session_state.selected_title_for_daily = work[2]; st.session_state.page = "daily"; st.rerun()

elif st.session_state.page == "daily":
    st.markdown('<div class="header-bar"><div class="header-title">今日の進捗</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bd"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    c.execute("SELECT id, title FROM works WHERE user_id = ?", (st.session_state.user_id,))
    works_list = c.fetchall()
    if works_list:
        titles = [w[1] for w in works_list]
        selected_title = st.selectbox("作品名", titles, label_visibility="collapsed")
        c.execute("SELECT * FROM works WHERE title=? AND user_id=?", (selected_title, st.session_state.user_id))
        work = c.fetchone()
        st.divider()
        def p_row(label, current_val, unit, key):
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1: st.write(label)
            with c2: val = st.number_input(label, min_value=0, key=key, label_visibility="collapsed")
            with c3: st.write(f"前:{current_val}{unit}")
            return val
        p, n, l, t = p_row("プロット", work[7], "%", "dp"), p_row("ネーム", work[8], "P", "dn"), p_row("線画", work[10], "P", "dl"), p_row("トーン", work[11], "P", "dt")
        if st.button("保存", use_container_width=True, type="primary"):
            c.execute("UPDATE works SET plot_percent=plot_percent+?, name_pages=name_pages+?, line_pages=line_pages+?, tone_pages=tone_pages+? WHERE id=? AND user_id=?", (p, n, l, t, work[0], st.session_state.user_id))
            conn.commit(); st.session_state.page = "list"; st.rerun()

elif st.session_state.page == "form":
    is_edit = st.session_state.edit_id is not None
    if is_edit: 
        c.execute("SELECT * FROM works WHERE id=? AND user_id=?", (st.session_state.edit_id, st.session_state.user_id))
        work_data = c.fetchone()
    else: work_data = (None, st.session_state.user_id, "", 0, "", str(date.today()), str(date.today()))
    st.markdown(f'<div class="header-bar"><div class="header-title">作品設定</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bf"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    t, pg, ev, ed, dd = st.text_input("作品名", value=work_data[2]), st.number_input("総ページ", 0, 1000, int(work_data[3])), st.text_input("イベント", value=work_data[4]), st.date_input("イベント日", value=date.fromisoformat(work_data[5]), format="YYYY/MM/DD"), st.date_input("締切日", value=date.fromisoformat(work_data[6]), format="YYYY/MM/DD")
    if is_edit:
        if st.button("保存", use_container_width=True, type="primary"):
            c.execute("UPDATE works SET title=?, total_pages=?, event_name=?, event_date=?, deadline=? WHERE id=? AND user_id=?", (t, pg, ev, str(ed), str(dd), st.session_state.edit_id, st.session_state.user_id))
            conn.commit(); st.session_state.page = "list"; st.rerun()
        if st.button("削除", use_container_width=True, type="secondary"):
            c.execute("DELETE FROM works WHERE id=? AND user_id=?", (st.session_state.edit_id, st.session_state.user_id))
            conn.commit(); st.session_state.page = "list"; st.rerun()
    else:
        if st.button("登録", use_container_width=True, type="primary"):
            c.execute("INSERT INTO works (user_id, title, total_pages, event_name, event_date, deadline) VALUES (?,?,?,?,?,?)", (st.session_state.user_id, t, pg, ev, str(ed), str(dd)))
            conn.commit(); st.session_state.page = "list"; st.rerun()
