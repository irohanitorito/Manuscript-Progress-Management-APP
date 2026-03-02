import sqlite3
import hashlib
from datetime import date, datetime
import streamlit as st

# 1. 基本設定
st.set_page_config(page_title="進捗管理アプリ（マルチユーザー版）", layout="centered")

# 2. データベース初期化
conn = sqlite3.connect("progress.db", check_same_thread=False)
c = conn.cursor()

# ユーザーテーブルと作品テーブル（user_idを追加）
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    username TEXT UNIQUE, 
    password TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    user_id INTEGER,
    title TEXT, total_pages INTEGER,
    event_name TEXT, event_date TEXT, deadline TEXT,
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
    .header-bar {
        background-color: #C199E5; height: 60px;
        display: flex; align-items: center; justify-content: center;
        margin: -60px -500px 30px -500px;
    }
    .header-title { color: white; font-size: 1.1rem; font-weight: bold; }
    .big-datetime { text-align: center; font-size: clamp(1.8rem, 8vw, 2.8rem); font-weight: bold; color: #B282E6; margin-bottom: 15px; }
    div.stButton > button { border-radius: 12px !important; font-weight: bold !important; }
    div.stButton > button[kind="primary"] { background-color: #C199E5 !important; color: white !important; border: none !important; }
    div.stButton > button[kind="secondary"] { border: 2px solid #C199E5 !important; color: #C199E5 !important; background-color: white !important; }
    div.stButton > button[key="add_btn_ui"] { font-size: 24px !important; width: 45px !important; height: 45px !important; }
    div[data-testid="stNumberInput"] button { display: none !important; }
    div[data-testid="stNumberInput"] input { padding-right: 10px !important; }
    .progress-container { width: 100%; background-color: #F0F0F0; border-radius: 10px; margin: 5px 0; height: 12px; overflow: hidden; }
    .progress-bar-fill { height: 100%; background-color: #C199E5; transition: width 0.3s ease; }
    .detail-label { font-size: clamp(1.1rem, 5vw, 1.8rem); color: #B282E6; font-weight: bold; }
    .detail-value { font-size: clamp(1.4rem, 7vw, 2.8rem); color: #B282E6; text-align: right; font-weight: bold; }
    .detail-unit { font-size: 0.8rem; margin-left: 3px; opacity: 0.8; }
    .back-btn-wrapper { margin-top: -90px; margin-bottom: 40px; }
    @media (max-width: 640px) {
        .detail-label { margin-bottom: -5px; }
        .detail-value { line-height: 1.1; }
        .stDivider { margin: 10px 0 !important; }
    }
</style>
""", unsafe_allow_html=True)

# ユーティリティ関数
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
        username = st.text_input("ユーザー名", key="login_user")
        password = st.text_input("パスワード", type='password', key="login_pass")
        if st.button("ログイン", type="primary", use_container_width=True):
            c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
            data = c.fetchone()
            if data and check_hashes(password, data[1]):
                st.session_state.user_id = data[0]
                st.session_state.username = username
                st.rerun()
            else: st.error("ユーザー名かパスワードが違います")
    with tab2:
        new_user = st.text_input("希望のユーザー名", key="reg_user")
        new_pass = st.text_input("希望のパスワード", type='password', key="reg_pass")
        if st.button("アカウント作成", use_container_width=True):
            if new_user and new_pass:
                try:
                    c.execute('INSERT INTO users(username, password) VALUES (?,?)', (new_user, make_hashes(new_pass)))
                    conn.commit(); st.success("作成完了！ログインしてください")
                except: st.error("そのユーザー名は既に使用されています")
            else: st.warning("ユーザー名とパスワードを入力してください")
    st.stop()

# サイドバー（ログアウト）
with st.sidebar:
    st.write(f"ログイン中: {st.session_state.username}")
    if st.button("ログアウト"):
        st.session_state.user_id = None; st.session_state.username = None; st.rerun()

# =========================
# 【ホーム画面】
# =========================
if st.session_state.page == "list":
    st.markdown(f'<div class="header-bar"><div class="header-title">{st.session_state.username}さんの進捗</div></div>', unsafe_allow_html=True)
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    st.markdown(f'<div class="big-datetime">{now_str}</div>', unsafe_allow_html=True)
    
    c.execute("SELECT * FROM works WHERE user_id = ?", (st.session_state.user_id,))
    works = c.fetchall()
    
    _, col_center, _ = st.columns([1, 2, 1])
    if col_center.button("今日の進捗", use_container_width=True, disabled=(len(works) == 0)):
        st.session_state.selected_title_for_daily = None; st.session_state.page = "daily"; st.rerun()
    st.divider()
    col_empty, col_btn = st.columns([7, 1])
    with col_btn:
        if st.button("＋", key="add_btn_ui", type="primary"):
            st.session_state.edit_id = None; st.session_state.page = "form"; st.rerun()

    for work in works:
        try: ev_date = date.fromisoformat(work[5]); ev_str = f"{ev_date.month}/{ev_date.day}"
        except: ev_str = work[5]
        try: dl_date = date.fromisoformat(work[6]); dl_str = f"{dl_date.month}/{dl_date.day}"
        except: dl_str = work[6]
        st.markdown(f'<div style="font-size:12px; font-weight:bold; color:#B282E6; margin-top:15px;">{ev_str} {work[4]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:18px; font-weight:bold; color:#B282E6; margin-bottom:5px;">{dl_str}〆 {work[2]}</div>', unsafe_allow_html=True)
        percent = calculate_total_percent(work)
        col_bar, col_edit, col_read = st.columns([5, 1.2, 1.2])
        with col_bar:
            st.markdown(f'<div class="progress-container"><div class="progress-bar-fill" style="width:{percent}%;"></div></div><div style="text-align:right; font-size:10px; color:#B282E6;">{percent}%</div>', unsafe_allow_html=True)
        with col_edit:
            if st.button("編集", key=f"ed_{work[0]}", use_container_width=True, type="secondary"):
                st.session_state.edit_id = work[0]; st.session_state.page = "form"; st.rerun()
        with col_read:
            if st.button("閲覧", key=f"rd_{work[0]}", use_container_width=True, type="primary"):
                st.session_state.view_id = work[0]; st.session_state.page = "view"; st.rerun()

# =========================
# 【作品閲覧画面】
# =========================
elif st.session_state.page == "view":
    c.execute("SELECT * FROM works WHERE id=? AND user_id=?", (st.session_state.view_id, st.session_state.user_id))
    work = c.fetchone()
    if not work: st.session_state.page = "list"; st.rerun()
    st.markdown(f'<div class="header-bar"><div class="header-title">{work[2]}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bv"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    today = date.today()
    try:
        deadline_date = date.fromisoformat(work[6])
        days_diff = (deadline_date - today).days
        deadline_info = f"<b>〆切まであと{days_diff}日</b>"
    except: deadline_info = f"<b>締切：{work[6]}</b>"
    st.markdown(f"<div style='text-align:center; color:#B282E6; font-size:0.9rem;'>今日：{today.strftime('%Y/%m/%d')} | {deadline_info}</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    percent = calculate_total_percent(work)
    st.markdown('<div style="text-align:center; color:#B282E6; font-size:1.2rem; font-weight:bold;">現在の進捗</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-container" style="height:15px; margin-top:5px;"><div class="progress-bar-fill" style="width:{percent}%;"></div></div><div style="text-align:right; font-size:0.8rem; color:#B282E6; margin-bottom:20px;">{percent}%</div>', unsafe_allow_html=True)
    st.divider()
    def detail_item(label, current, total=None):
        col_l, col_r = st.columns([1, 1])
        with col_l: st.markdown(f'<div class="detail-label">{label}</div>', unsafe_allow_html=True)
        with col_r:
            v_html = f'{current}/{total}<span class="detail-unit">P</span>' if total else f'{current}<span class="detail-unit">%</span>'
            st.markdown(f'<div class="detail-value">{v_html}</div>', unsafe_allow_html=True)
    detail_item("プロット", work[7])
    detail_item("ネーム", work[8], work[3])
    detail_item("線画", work[10], work[3])
    detail_item("トーン・仕上げ", work[11], work[3])
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("今日の進捗を入力する", use_container_width=True, type="primary"):
        st.session_state.selected_title_for_daily = work[2]; st.session_state.page = "daily"; st.rerun()

# =========================
# 【今日の進捗入力画面】
# =========================
elif st.session_state.page == "daily":
    st.markdown('<div class="header-bar"><div class="header-title">今日の進捗</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bd"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    c.execute("SELECT id, title FROM works WHERE user_id = ?", (st.session_state.user_id,))
    works_list = c.fetchall()
    if works_list:
        titles = [w[1] for w in works_list]
        default_idx = titles.index(st.session_state.selected_title_for_daily) if st.session_state.selected_title_for_daily in titles else 0
        selected_title = st.selectbox("作品名", titles, index=default_idx, label_visibility="collapsed")
        c.execute("SELECT * FROM works WHERE title=? AND user_id=?", (selected_title, st.session_state.user_id))
        work = c.fetchone()
        st.divider()
        def progress_row(label, current_val, unit, key):
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1: st.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
            with c2: val = st.number_input(label, min_value=0, key=key, label_visibility="collapsed")
            with c3: st.markdown(f"<div style='color:#B282E6; font-size:10px;'>昨日まで:<br>{current_val}{unit}</div>", unsafe_allow_html=True)
            return val
        p = progress_row("プロット", work[7], "%", "dp")
        n = progress_row("ネーム", work[8], "P", "dn")
        l = progress_row("線画", work[10], "P", "dl")
        t = progress_row("トーン", work[11], "P", "dt")
        if st.button("保存", use_container_width=True, type="primary"):
            total_pages = work[3]
            errors = []
            if work[7] + p > 100: errors.append("プロットが100%を超えます")
            if work[8] + n > total_pages: errors.append("ネームが総ページ数を超えます")
            if work[10] + l > total_pages: errors.append("線画が総ページ数を超えます")
            if work[11] + t > total_pages: errors.append("トーンが総ページ数を超えます")
            if errors:
                for msg in errors: st.error(msg)
            else:
                c.execute("UPDATE works SET plot_percent=plot_percent+?, name_pages=name_pages+?, line_pages=line_pages+?, tone_pages=tone_pages+? WHERE id=? AND user_id=?", (p, n, l, t, work[0], st.session_state.user_id))
                conn.commit(); st.session_state.page = "list"; st.rerun()

# =========================
# 【作品登録・編集画面】
# =========================
elif st.session_state.page == "form":
    is_edit = st.session_state.edit_id is not None
    if is_edit: 
        c.execute("SELECT * FROM works WHERE id=? AND user_id=?", (st.session_state.edit_id, st.session_state.user_id))
        work_data = c.fetchone()
    else: 
        work_data = (None, st.session_state.user_id, "", 0, "", str(date.today()), str(date.today()))
    st.markdown(f'<div class="header-bar"><div class="header-title">{"作品編集" if is_edit else "新規登録"}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bf"): st.session_state.page = "list"; st.session_state.confirm_delete = False; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    title = st.text_input("作品名", value=work_data[2])
    pages = st.number_input("総ページ数", 0, 1000, int(work_data[3]))
    event = st.text_input("イベント名", value=work_data[4])
    e_date = st.date_input("イベント日", value=date.fromisoformat(work_data[5]), format="YYYY/MM/DD")
    d_date = st.date_input("締切日", value=date.fromisoformat(work_data[6]), format="YYYY/MM/DD")
    st.markdown("<br>", unsafe_allow_html=True)
    if is_edit:
        if not st.session_state.confirm_delete:
            col_del, col_save = st.columns(2)
            with col_del:
                if st.button("削除", use_container_width=True, type="secondary"): st.session_state.confirm_delete = True; st.rerun()
            with col_save:
                if st.button("保存", use_container_width=True, type="primary"):
                    c.execute("UPDATE works SET title=?, total_pages=?, event_name=?, event_date=?, deadline=? WHERE id=? AND user_id=?", (title, pages, event, str(e_date), str(d_date), st.session_state.edit_id, st.session_state.user_id))
                    conn.commit(); st.session_state.page = "list"; st.rerun()
        else:
            st.error("この作品を削除しますか？")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("いいえ", use_container_width=True): st.session_state.confirm_delete = False; st.rerun()
            with c2:
                if st.button("削除する", use_container_width=True, type="primary"):
                    c.execute("DELETE FROM works WHERE id=? AND user_id=?", (st.session_state.edit_id, st.session_state.user_id))
                    conn.commit(); st.session_state.confirm_delete = False; st.session_state.page = "list"; st.rerun()
    else:
        if st.button("登録", use_container_width=True, type="primary"):
            c.execute("INSERT INTO works (user_id, title, total_pages, event_name, event_date, deadline) VALUES (?,?,?,?,?,?)", (st.session_state.user_id, title, pages, event, str(e_date), str(d_date)))
            conn.commit(); st.session_state.page = "list"; st.rerun()
