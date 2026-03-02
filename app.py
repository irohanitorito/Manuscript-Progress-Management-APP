import sqlite3
from datetime import date, datetime
import streamlit as st

# 1. 基本設定
st.set_page_config(page_title="進捗管理アプリ", layout="centered")

# 2. データベース接続
conn = sqlite3.connect("progress.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, total_pages INTEGER,
    event_name TEXT, event_date TEXT, deadline TEXT,
    plot_percent INTEGER DEFAULT 0, name_pages INTEGER DEFAULT 0,
    draft_pages INTEGER DEFAULT 0, line_pages INTEGER DEFAULT 0, tone_pages INTEGER DEFAULT 0
)
""")
conn.commit()

# セッション管理
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
    .header-title { color: white; font-size: 20px; font-weight: bold; }

    .big-datetime {
        text-align: center; font-size: 42px; font-weight: bold;
        color: #B282E6; margin-bottom: 15px;
    }

    div.stButton > button[kind="primary"] {
        background-color: #C199E5 !important; color: white !important;
        border: none !important; border-radius: 12px !important; font-weight: bold !important;
    }
    div.stButton > button[kind="secondary"] {
        border: 2px solid #C199E5 !important; color: #C199E5 !important;
        background-color: white !important; border-radius: 12px !important;
    }
    
    div.stButton > button[key="add_btn_ui"] {
        font-size: 28px !important; font-weight: 900 !important;
        width: 45px !important; height: 45px !important; padding: 0 !important;
        display: flex !important; align-items: center !important; justify-content: center !important;
    }

    div[data-testid="stNumberInput"] button { display: none !important; }
    div[data-testid="stNumberInput"] input { padding-right: 10px !important; }

    .left-title { color: #B282E6; font-size: 24px; font-weight: bold; text-align: left; margin: 10px 0; }

    .progress-container {
        width: 100%; background-color: #F0F0F0; border-radius: 10px;
        margin: 5px 0 10px 0; height: 12px; overflow: hidden;
    }
    .progress-bar-fill { height: 100%; background-color: #C199E5; transition: width 0.3s ease; }
    
    .detail-label { font-size: 32px; color: #B282E6; margin-bottom: 10px; }
    .detail-value { font-size: 48px; color: #B282E6; text-align: right; }
    .detail-unit { font-size: 20px; margin-left: 5px; }
    
    .back-btn-wrapper { margin-top: -90px; margin-bottom: 40px; }
</style>
""", unsafe_allow_html=True)

def calculate_total_percent(work_data):
    total = work_data[2] if work_data[2] and work_data[2] > 0 else 1
    p = (work_data[6] + (work_data[7]/total*100) + (work_data[9]/total*100) + (work_data[10]/total*100)) / 4
    return round(max(0.0, min(float(p), 100.0)), 1)

# =========================
# 【ホーム画面】
# =========================
if st.session_state.page == "list":
    st.markdown('<div class="header-bar"><div class="header-title">進捗管理アプリ</div></div>', unsafe_allow_html=True)
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
    st.markdown(f'<div class="big-datetime">{now_str}</div>', unsafe_allow_html=True)
    
    c.execute("SELECT COUNT(*) FROM works")
    works_count = c.fetchone()[0]
    
    _, col_center, _ = st.columns([1, 2, 1])
    if col_center.button("今日の進捗", use_container_width=True, disabled=(works_count == 0)):
        st.session_state.selected_title_for_daily = None # リセット
        st.session_state.page = "daily"; st.rerun()

    st.divider()

    col_empty, col_btn = st.columns([7, 1])
    with col_btn:
        if st.button("＋", key="add_btn_ui", type="primary"):
            st.session_state.edit_id = None; st.session_state.page = "form"; st.rerun()

    st.markdown('<div class="left-title">進行中の原稿</div>', unsafe_allow_html=True)
    c.execute("SELECT * FROM works")
    works = c.fetchall()
    for work in works:
        try: ev_date = date.fromisoformat(work[4]); ev_str = f"{ev_date.month}/{ev_date.day}"
        except: ev_str = work[4]
        try: dl_date = date.fromisoformat(work[5]); dl_str = f"{dl_date.month}/{dl_date.day}"
        except: dl_str = work[5]
        st.markdown(f'<div style="font-size:12px; font-weight:bold; color:#B282E6; margin-top:15px;">{ev_str} {work[3]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:18px; font-weight:bold; color:#B282E6; margin-bottom:5px;">{dl_str}〆 {work[1]}</div>', unsafe_allow_html=True)
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
    c.execute("SELECT * FROM works WHERE id=?", (st.session_state.view_id,))
    work = c.fetchone()
    if not work: st.session_state.page = "list"; st.rerun()
    st.markdown(f'<div class="header-bar"><div class="header-title">{work[1]}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bv"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    today = date.today()
    try:
        deadline_date = date.fromisoformat(work[5])
        days_diff = (deadline_date - today).days
        deadline_info = f"<b>〆切まであと{days_diff}日（締切日：{deadline_date.strftime('%Y/%m/%d')}）</b>"
    except: deadline_info = f"<b>締切日：{work[5]}</b>"
    st.markdown(f"<div style='text-align:center; color:#B282E6; font-weight:bold;'>今日の日付：{today.strftime('%Y/%m/%d')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center; color:#B282E6; margin-bottom:15px;'>{deadline_info}</div>", unsafe_allow_html=True)
    try: ev_date_str = date.fromisoformat(work[4]).strftime('%Y/%m/%d')
    except: ev_date_str = work[4]
    st.markdown(f"<div style='text-align:center; color:#B282E6; font-size:16px;'>{ev_date_str} {work[3]}</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    percent = calculate_total_percent(work)
    st.markdown('<div style="text-align:center; color:#B282E6; font-size:24px; font-weight:bold;">現在の進捗</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-container" style="height:15px; margin-top:5px;"><div class="progress-bar-fill" style="width:{percent}%;"></div></div><div style="text-align:right; font-size:14px; color:#B282E6; margin-bottom:20px;">{percent}%</div>', unsafe_allow_html=True)
    st.divider()
    def detail_item(label, current, total=None):
        col_l, col_r = st.columns([1, 1])
        with col_l: st.markdown(f'<div class="detail-label">{label}</div>', unsafe_allow_html=True)
        with col_r:
            v_html = f'{current}/{total}<span class="detail-unit">ページ</span>' if total else f'{current}<span class="detail-unit">%</span>'
            st.markdown(f'<div class="detail-value">{v_html}</div>', unsafe_allow_html=True)
    detail_item("プロット", work[6]); detail_item("ネーム", work[7], work[2]); detail_item("線画", work[9], work[2]); detail_item("トーン・ベタ仕上げ", work[10], work[2])
    
    st.markdown("<br>", unsafe_allow_html=True)
    # 今日の進捗へのショートカットボタン
    if st.button("今日の進捗を入力する", use_container_width=True, type="primary"):
        st.session_state.selected_title_for_daily = work[1] # 現在の作品名をセット
        st.session_state.page = "daily"
        st.rerun()

# =========================
# 【今日の進捗入力画面】
# =========================
elif st.session_state.page == "daily":
    st.markdown('<div class="header-bar"><div class="header-title">今日の進捗</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bd"): st.session_state.page = "list"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    c.execute("SELECT id, title FROM works")
    works_list = c.fetchall()
    
    if works_list:
        titles = [w[1] for w in works_list]
        
        # 閲覧画面から来た場合はその作品を初期選択にする
        default_index = 0
        if st.session_state.selected_title_for_daily in titles:
            default_index = titles.index(st.session_state.selected_title_for_daily)
            
        selected_title = st.selectbox("作品名", titles, index=default_index, label_visibility="collapsed")
        c.execute("SELECT * FROM works WHERE title=?", (selected_title,))
        work = c.fetchone()
        st.divider()
        
        def progress_row(label, current_val, unit, key):
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1: st.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
            with c2: val = st.number_input(label, min_value=0, key=key, label_visibility="collapsed")
            with c3: st.markdown(f"<div style='color:#B282E6; font-size:12px;'>{unit}<br>昨日まで:{current_val}{unit}</div>", unsafe_allow_html=True)
            return val
            
        p = progress_row("プロット", work[6], "%", "dp")
        n = progress_row("ネーム", work[7], "ページ", "dn")
        l = progress_row("線画", work[9], "ページ", "dl")
        t = progress_row("トーン", work[10], "ページ", "dt")
        
        if st.button("保存", use_container_width=True, type="primary"):
            total_pages = work[2]
            errors = []
            if work[6] + p > 100: errors.append(f"プロットが100%を超えています（あと {100 - work[6]}% 入力可能です）")
            if work[7] + n > total_pages: errors.append(f"ネームが総ページ数を超えています（あと {total_pages - work[7]}ページ 入力可能です）")
            if work[9] + l > total_pages: errors.append(f"線画が総ページ数を超えています（あと {total_pages - work[9]}ページ 入力可能です）")
            if work[10] + t > total_pages: errors.append(f"トーンが総ページ数を超えています（あと {total_pages - work[10]}ページ 入力可能です）")
            
            if errors:
                for msg in errors: st.error(msg)
            else:
                c.execute("UPDATE works SET plot_percent=plot_percent+?, name_pages=name_pages+?, line_pages=line_pages+?, tone_pages=tone_pages+? WHERE id=?", (p, n, l, t, work[0]))
                conn.commit(); st.session_state.page = "list"; st.rerun()

# =========================
# 【作品登録・編集画面】
# =========================
elif st.session_state.page == "form":
    is_edit = st.session_state.edit_id is not None
    if is_edit: c.execute("SELECT * FROM works WHERE id=?", (st.session_state.edit_id,)); work_data = c.fetchone()
    else: work_data = (None, "", 0, "", str(date.today()), str(date.today()))
    st.markdown(f'<div class="header-bar"><div class="header-title">{"作品編集" if is_edit else "新規登録"}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="back-btn-wrapper">', unsafe_allow_html=True)
    if st.button("◀", key="bf"): 
        st.session_state.page = "list"
        st.session_state.confirm_delete = False; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    title = st.text_input("作品名", value=work_data[1]); pages = st.number_input("総ページ数", 0, 1000, int(work_data[2])); event = st.text_input("イベント名", value=work_data[3]); e_date = st.date_input("イベント開催日", value=date.fromisoformat(work_data[4])); d_date = st.date_input("原稿締切日", value=date.fromisoformat(work_data[5]))
    st.markdown("<br>", unsafe_allow_html=True)
    if is_edit:
        if not st.session_state.confirm_delete:
            col_del, col_save = st.columns(2)
            with col_del:
                if st.button("削除", use_container_width=True, type="secondary"): st.session_state.confirm_delete = True; st.rerun()
            with col_save:
                if st.button("保存", use_container_width=True, type="primary"):
                    c.execute("UPDATE works SET title=?, total_pages=?, event_name=?, event_date=?, deadline=? WHERE id=?", (title, pages, event, str(e_date), str(d_date), st.session_state.edit_id))
                    conn.commit(); st.session_state.page = "list"; st.rerun()
        else:
            st.error("この作品を完全に削除しますか？")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("いいえ", use_container_width=True): st.session_state.confirm_delete = False; st.rerun()
            with c2:
                if st.button("はい、削除します", use_container_width=True, type="primary"):
                    c.execute("DELETE FROM works WHERE id=?", (st.session_state.edit_id,)); conn.commit(); st.session_state.confirm_delete = False; st.session_state.page = "list"; st.rerun()
    else:
        if st.button("保存", use_container_width=True, type="primary"):
            c.execute("INSERT INTO works (title, total_pages, event_name, event_date, deadline) VALUES (?,?,?,?,?)", (title, pages, event, str(e_date), str(d_date)))
            conn.commit(); st.session_state.page = "list"; st.rerun()