import streamlit as st
import pandas as pd
import datetime
import os
import unicodedata # 半角変換用
import gspread
import json

# --- 設定 ---
FILE_MASTER = "options_master.xlsx"
IMAGE_EXAMPLE = "example.png" # 記入例の画像ファイル名

st.set_page_config(page_title="TXアンケートシステム", layout="centered")

# セッション状態の初期化
if 'step' not in st.session_state:
    st.session_state.step = "consent"
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'current_tp_idx' not in st.session_state:
    st.session_state.current_tp_idx = 0

# --- データ読み込み ---
@st.cache_data
def load_master():
    if not os.path.exists(FILE_MASTER):
        st.error(f"エラー: {FILE_MASTER} が見つかりません。")
        return None
    return pd.read_excel(FILE_MASTER)

df_master = load_master()

# --- 進捗バー ---
def display_progress():
    if st.session_state.step == "consent": progress = 0.05
    elif st.session_state.step == "profile": progress = 0.15
    elif st.session_state.step == "instructions": progress = 0.20
    elif st.session_state.step == "survey_page":
        sh = st.session_state.answers.get('stakeholder', 'patient')
        tps = df_master[df_master['stakeholder_id'] == sh]['touchpoint_text'].unique()
        progress = 0.20 + (st.session_state.current_tp_idx / len(tps)) * 0.80
    else: progress = 1.0
    st.progress(progress, text="アンケート進捗状況")

# --- ページ遷移関数 ---
def next_step(target_step):
    st.session_state.step = target_step
    st.rerun()

# ==========================================
# 画面描画ロジック
# ==========================================

display_progress()

# 全体タイトル
if st.session_state.step in ["consent", "profile"]:
    st.markdown("### 医療現場における複数のステークホルダーを考慮したエクスペリエンスに関するアンケート")
    st.markdown("---")

# =========================================================
# 1. 同意・目的ページ
# =========================================================
if st.session_state.step == "consent":
    st.header("01　調査目的と基本情報")
    st.write("""
    本調査は、慶應義塾大学理工学研究科中西研究室で行う「医療現場における複数のステークホルダーを考慮したエクスペリエンスのモデル化」に関する研究の一環として実施するものです。入院中のさまざまな場面について、立場から見た理想的な対応方針を把握することを目的としています。回答は研究目的のみに使用し、個人が特定される形で公表することはありません。
    
    なお、本研究は、慶應義塾大学理工学部・理工学研究科研究倫理審査委員会の審査を受け、承認を得た上で実施しています。
    """)
    st.markdown("---")
    
    consent = st.radio("回答への同意：", ["同意する", "同意しない"], index=None, horizontal=True)
    
    sh_options = ["patient", "nurse", "manager"]
    stakeholder = st.selectbox(
        "あなたの立場を選択してください", 
        sh_options, 
        index=None, 
        format_func=lambda x: {"patient":"患者", "nurse":"看護師", "manager":"経営者"}[x] if x else "選択してください"
    )
    
    if st.button("次へ", type="primary"):
        if consent is None:
            st.error("「回答への同意」を選択してください。")
        elif stakeholder is None:
            st.error("「あなたの立場」を選択してください。")
        elif consent == "同意する":
            st.session_state.answers['consent'] = consent
            st.session_state.answers['stakeholder'] = stakeholder
            next_step("profile")
        elif consent == "同意しない":
            next_step("end_denied")

# =========================================================
# 2. 属性入力ページ
# =========================================================
elif st.session_state.step == "profile":
    st.header("基本情報の入力")
    sh = st.session_state.answers['stakeholder']

    st.radio("性別：", ["男性", "女性", "その他"], index=None, key="prof_gender", horizontal=True)
    st.text_input("年齢（代）：（半角数字 例：20、30など）", key="prof_age")
    
    if sh == "patient":
        st.text_input("入院日数（日）：（半角数字）", key="prof_days")
        st.text_input("診療科：", key="prof_dept")
        st.radio("入院回数：", ["初めて", "2回目以上"], index=None, key="prof_exp", horizontal=True)

    elif sh == "nurse":
        st.text_input("看護師経験年数（通算 年）：（半角数字）", key="prof_exp_total")
        st.text_input("診療科：", key="prof_dept")
        
        st.radio("勤務体制：", ["日勤", "夜勤", "その他"], index=None, key="prof_shift", horizontal=True)
        if st.session_state.get("prof_shift") == "その他":
            st.text_input("勤務体制（その他の場合）：", key="prof_shift_other")
            
        st.radio("役職：", ["一般看護師", "リーダー・主任", "看護師長", "その他"], index=None, key="prof_role", horizontal=True)
        if st.session_state.get("prof_role") == "その他":
            st.text_input("役職（その他の場合）：", key="prof_role_other")

    elif sh == "manager":
        st.text_input("経営に関わる経験年数（通算 年）：（半角数字）", key="prof_exp_total")
        st.text_input("役職：", key="prof_role")
        
        st.write("運営施設の種別（複数選択可）：")
        fac_options = ["一般病院", "特定機能病院", "地域医療支援病院", "精神病院", "その他"]
        selected_facs = []
        prev_facs = st.session_state.get("prof_fac_list", [])
        
        for fac in fac_options:
            if st.checkbox(fac, value=(fac in prev_facs), key=f"chk_fac_{fac}"):
                selected_facs.append(fac)
                
        st.session_state.prof_fac_list = selected_facs
        
        if "その他" in selected_facs:
            st.text_input("運営施設の種別（その他の場合）：", key="prof_fac_other")
            
        st.radio("総病床数（運営しているすべての施設の合計ベッド数）：", ["20〜99床", "100〜199床", "200〜499床", "500床以上"], index=None, key="prof_beds", horizontal=True)
        
    col1, col2 = st.columns([1, 1])
    with col1:
        back_btn = st.button("前のページへ戻る")
    with col2:
        submit_btn = st.button("次へ（記入方法の確認）", type="primary")
        
    if back_btn:
        next_step("consent")
        
    if submit_btn:
        is_valid = True
        errors = []
        p_ans = {}
        
        if not st.session_state.get("prof_gender"):
            is_valid = False; errors.append("性別が未選択です。")
        else:
            p_ans["gender"] = st.session_state.prof_gender

        val_age = st.session_state.get("prof_age")
        if not val_age:
            is_valid = False; errors.append("年齢が未入力です。")
        else:
            norm_age = unicodedata.normalize('NFKC', val_age)
            if not norm_age.isdigit(): is_valid = False; errors.append("年齢は半角数字で入力してください。")
            else: p_ans["age"] = norm_age + "代"

        if sh == "patient":
            val_days = st.session_state.get("prof_days")
            if not val_days: is_valid = False; errors.append("入院日数が未入力です。")
            else:
                norm_days = unicodedata.normalize('NFKC', val_days)
                if not norm_days.isdigit(): is_valid = False; errors.append("入院日数は半角数字で入力してください。")
                else: p_ans["days"] = norm_days
            p_ans["dept"] = st.session_state.get("prof_dept")
            if not p_ans["dept"]: is_valid = False; errors.append("診療科が未入力です。")
            
            if not st.session_state.get("prof_exp"):
                is_valid = False; errors.append("入院回数が未選択です。")
            else:
                p_ans["experience"] = st.session_state.prof_exp
            
        elif sh == "nurse":
            for k, label in [("prof_exp_total", "看護師経験年数（通算）")]:
                v = st.session_state.get(k)
                if not v: is_valid = False; errors.append(f"{label}が未入力です。")
                else:
                    nv = unicodedata.normalize('NFKC', v)
                    if not nv.isdigit(): is_valid = False; errors.append(f"{label}は半角数字で入力してください。")
                    else: p_ans[k] = nv
            p_ans["dept"] = st.session_state.get("prof_dept")
            if not p_ans["dept"]: is_valid = False; errors.append("診療科が未入力です。")
            
            if not st.session_state.get("prof_shift"):
                is_valid = False; errors.append("勤務体制が未選択です。")
            else:
                shift_val = st.session_state.get("prof_shift_other", "") if st.session_state.prof_shift == "その他" else st.session_state.prof_shift
                if st.session_state.prof_shift == "その他" and not shift_val:
                    is_valid = False; errors.append("勤務体制（その他）の詳細を入力してください。")
                p_ans["shift"] = shift_val
                
            if not st.session_state.get("prof_role"):
                is_valid = False; errors.append("役職が未選択です。")
            else:
                role_val = st.session_state.get("prof_role_other", "") if st.session_state.prof_role == "その他" else st.session_state.prof_role
                if st.session_state.prof_role == "その他" and not role_val:
                    is_valid = False; errors.append("役職（その他）の詳細を入力してください。")
                p_ans["role"] = role_val
                
        elif sh == "manager":
            for k, label in [("prof_exp_total", "経験年数（通算）")]:
                v = st.session_state.get(k)
                if not v: is_valid = False; errors.append(f"{label}が未入力です。")
                else:
                    nv = unicodedata.normalize('NFKC', v)
                    if not nv.isdigit(): is_valid = False; errors.append(f"{label}は半角数字で入力してください。")
                    else: p_ans[k] = nv
            p_ans["role"] = st.session_state.get("prof_role")
            if not p_ans["role"]: is_valid = False; errors.append("役職が未入力です。")
            
            prof_fac = st.session_state.get("prof_fac_list", [])
            if not prof_fac:
                is_valid = False; errors.append("運営施設の種別が未選択です。")
            else:
                fac_vals = []
                for f in prof_fac:
                    if f == "その他":
                        other_val = st.session_state.get("prof_fac_other", "")
                        if not other_val:
                            is_valid = False; errors.append("運営施設の種別（その他）の詳細を入力してください。")
                        fac_vals.append(f"その他({other_val})")
                    else:
                        fac_vals.append(f)
                p_ans["facility_type"] = "、".join(fac_vals)
                
            if not st.session_state.get("prof_beds"):
                is_valid = False; errors.append("総病床数が未選択です。")
            else:
                p_ans["beds"] = st.session_state.prof_beds

        if is_valid:
            st.session_state.answers.update(p_ans)
            next_step("instructions")
        else:
            for err in errors:
                st.error(err)

# =========================================================
# 3. 注意書き・記入例ページ
# =========================================================
elif st.session_state.step == "instructions":
    sh = st.session_state.answers['stakeholder']
    title_text = {"patient": "02　入院生活における理想に関する調査", 
                  "nurse": "02　業務場面における理想に関する調査", 
                  "manager": "02　病院運営における理想に関する調査"}[sh]
    
    st.header(title_text)
    st.write("以下では、様々な場面について、あなたにとっての理想をお答えいただきます。設問は35題あり、所要時間は20分～30分程度です。")

    st.markdown(f"""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 5px; margin-bottom: 20px;'>
        <p>❖ 各設問において、<strong>選択肢の重要度の合計が「100」になるように</strong>スライダーや「＋」「－」ボタンを使って配分してください。</p>
        <p>❖ 最も重視する項目に高い数値を、重視しない項目には 0 に近い数値を割り当てます。バーの長さを目安に直感的に配分してください。</p>
        <p>❖ 画面上部に合計値のバーが表示されます。<strong>合計がぴったり 100（緑色）にならないと、次の画面に進むことができません。</strong></p>
        <p>❖ その他、加えたい内容がある場合は、任意でご記入ください。（※「その他」に入力した場合、その項目も合計 100 の配分に含めてください）</p>
        <p><span style='color: #d32f2f; font-weight: bold; font-size: 1.1em;'>❖ 実際の現場では患者の状態や病棟の状況によって対応が異なると思いますが、本調査では細かな条件を厳密に想定しすぎず、直感的にお答えください。</span></p>
        <p>❖ 正解はありませんので、一般的に望ましいと思われる回答ではなく、ご自身の率直なお考えをご回答ください。ご回答の内容が他の職員の方などに見られることはありません。</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 【操作方法】")
    st.write("スライダーを左右に動かすか、両端の **「＋」「－」ボタン** を押して数値を 1 ずつ微調整してください。（※合計が100を超過するようには設定できません。増やすためには他の項目の数値を減らす必要があります。）")
    st.write("例：4つの選択肢がある場合、「40」「30」「20」「10」のように、足して 100 になるように調整します。")
        
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("基本情報の入力へ戻る", type="secondary"):
            next_step("profile")
    with col2:
        if st.button("アンケートを開始する", type="primary"):
            st.session_state.current_tp_idx = 0
            next_step("survey_page")

# =========================================================
# 4. アンケート本編（コンスタントサム・100スケール版）
# =========================================================
elif st.session_state.step == "survey_page":
    st.markdown("""
        <style>
            div[data-testid="stTickBar"] { display: none !important; }
            div[data-testid="column"] button { width: 100% !important; padding: 5px !important; }
        </style>
    """, unsafe_allow_html=True)

    sh = st.session_state.answers['stakeholder']
    tps = df_master[df_master['stakeholder_id'] == sh]['touchpoint_text'].unique()
    current_tp = tps[st.session_state.current_tp_idx]
    
    st.header(f"Q{st.session_state.current_tp_idx + 1}. {current_tp}")
    
    q_df = df_master[(df_master['stakeholder_id'] == sh) & (df_master['touchpoint_text'] == current_tp)]
    
    all_valid = True
    
    def get_val(k):
        return int(float(st.session_state.get(k, 0)))

    def slider_changed(k, all_keys):
        val = get_val(k)
        sum_others = sum(get_val(key) for key in all_keys if key != k)
        max_allowable = max(0, 100 - sum_others)
        if val > max_allowable:
            st.session_state[k] = max_allowable

    def adjust_val(k, delta, all_keys):
        val = get_val(k)
        sum_others = sum(get_val(key) for key in all_keys if key != k)
        max_allowable = max(0, 100 - sum_others)
        
        if delta > 0:
            addable = max(0, min(delta, max_allowable - val))
            st.session_state[k] = val + addable
        else:
            st.session_state[k] = max(0, val + delta)

    for q_id in q_df['question_text'].unique():
        options = q_df[q_df['question_text'] == q_id]
        
        slider_keys = [f"val_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}_opt{row['option_id']}_item{row['item_id']}" for _, row in options.iterrows()]
        other_key_text = f"other_text_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}"
        other_key_val = f"other_val_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}"
        
        other_label_key = f"other_label_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}"
        if other_key_text not in st.session_state:
            st.session_state[other_key_text] = st.session_state.answers.get(other_label_key, "")
            
        if st.session_state.get(other_key_text): 
            slider_keys.append(other_key_val)
        
        current_sum = sum(get_val(k) for k in slider_keys)
        
        bar_color = "#4CAF50" if current_sum == 100 else ("#F44336" if current_sum > 100 else "#FFC107")
        status_text = f"✅ 合計: 100" if current_sum == 100 else (f"⚠️ 合計: {current_sum} (超過)" if current_sum > 100 else f"⏳ 合計: {current_sum} (不足)")
        if current_sum != 100: 
            all_valid = False
        
        st.markdown(f"""
            <div style='background-color:#e0e0e0; border-radius:5px; width:100%; height:15px;'>
                <div style='background-color:{bar_color}; width:{min(current_sum, 100)}%; height:100%; border-radius:5px; transition:0.3s;'></div>
            </div>
            <div style='text-align:right; font-weight:bold; color:{bar_color}; font-size:14px; margin-bottom:10px;'>{status_text}</div>
        """, unsafe_allow_html=True)
        
        def draw_adjustable_slider(label, key, all_keys):
            if key not in st.session_state:
                st.session_state[key] = st.session_state.answers.get(key, 0)
                
            st.write(f"**{label}**")
            c_m, c_s, c_p = st.columns([1, 8, 1])
            with c_m:
                st.button("－", key=f"min_btn_{key}", on_click=adjust_val, args=(key, -1, all_keys))
            with c_s:
                st.slider(
                    label, 
                    min_value=0, 
                    max_value=100, 
                    step=1, 
                    format="%d", 
                    key=key, 
                    label_visibility="collapsed",
                    on_change=slider_changed, 
                    args=(key, all_keys)
                )
            with c_p:
                st.button("＋", key=f"pls_btn_{key}", on_click=adjust_val, args=(key, 1, all_keys))

        for _, row in options.iterrows():
            k = f"val_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}_opt{row['option_id']}_item{row['item_id']}"
            draw_adjustable_slider(row['option_text'], k, slider_keys)
            
        other_text = st.text_input("その他（上記以外）：", key=other_key_text)
        if other_text:
            if other_key_val not in slider_keys:
                slider_keys.append(other_key_val)
            draw_adjustable_slider(f"「{other_text}」の評価", other_key_val, slider_keys)
            st.session_state.answers[other_label_key] = other_text
        else:
            if other_key_val in st.session_state:
                st.session_state[other_key_val] = 0
            if other_label_key in st.session_state.answers:
                st.session_state.answers[other_label_key] = ""
                
        st.markdown("---")
        
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("前のテーマへ戻る", type="secondary"):
            for k in st.session_state:
                if k.startswith("val_") or k.startswith("other_val_") or k.startswith("other_label_"): 
                    st.session_state.answers[k] = st.session_state[k]
                    
            if st.session_state.current_tp_idx > 0:
                st.session_state.current_tp_idx -= 1
                st.rerun()
            else:
                next_step("instructions")
    with col2:
        button_label = "最終確認へ進む" if st.session_state.current_tp_idx >= len(tps) - 1 else "次のテーマへ進む"
        
        if not all_valid:
            st.warning("⚠️ すべての設問の合計を 100 にしてください")
            
        if st.button(button_label, type="primary", disabled=not all_valid):
            for k in st.session_state:
                if k.startswith("val_") or k.startswith("other_val_") or k.startswith("other_label_"): 
                    st.session_state.answers[k] = st.session_state[k]
                    
            st.session_state.current_tp_idx += 1
            if st.session_state.current_tp_idx >= len(tps):
                next_step("final_submit")
            else:
                st.rerun()

# =========================================================
# 5. 最終送信ページ
# =========================================================
elif st.session_state.step == "final_submit":
    st.header("アンケートの完了")
    st.write("すべての回答が終了しました。以下のボタンを押してデータを送信してください。")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("アンケートへ戻る", type="secondary"):
            sh = st.session_state.answers['stakeholder']
            tps = df_master[df_master['stakeholder_id'] == sh]['touchpoint_text'].unique()
            st.session_state.current_tp_idx = len(tps) - 1
            next_step("survey_page")
            
    with col2:
        if st.button("アンケートを送信する", type="primary"):
            sh = st.session_state.answers['stakeholder']
            st.session_state.answers['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            answers_to_save = st.session_state.answers.copy()
            
            try:
                credentials_dict = json.loads(st.secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(credentials_dict)
                SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1kkZiyhLeOJnM0ypLpzytZZiVYhJBcRsc7bVnCXdhICk/edit"
                sh_doc = gc.open_by_url(SPREADSHEET_URL)
                
                sheet_name_map = {"patient": "Sheet1", "nurse": "Sheet2", "manager": "Sheet3"}
                worksheet = sh_doc.worksheet(sheet_name_map.get(sh, "Sheet1"))
                
                def get_fixed_headers_and_labels(sh_val, df):
                    keys = ['timestamp', 'consent', 'stakeholder', 'gender', 'age']
                    labels = ['回答日時', '同意', '回答者の立場', '性別', '年齢']
                    if sh_val == 'patient':
                        keys.extend(['days', 'dept', 'experience']); labels.extend(['入院日数', '診療科', '入院回数'])
                    elif sh_val == 'nurse':
                        keys.extend(['prof_exp_total', 'dept', 'shift', 'role']); labels.extend(['看護師経験年数（通算）', '診療科', '勤務体制', '役職'])
                    elif sh_val == 'manager':
                        keys.extend(['prof_exp_total', 'role', 'facility_type', 'beds']); labels.extend(['経験年数（通算）', '役職', '運営施設の種別', '総病床数'])

                    sh_df = df[df['stakeholder_id'] == sh_val]
                    tps = sh_df['touchpoint_text'].unique()
                    for tp_idx, tp in enumerate(tps):
                        q_df = sh_df[sh_df['touchpoint_text'] == tp]
                        for q_id in q_df['question_text'].unique():
                            opts = q_df[q_df['question_text'] == q_id]
                            for _, row in opts.iterrows():
                                keys.append(f"val_{sh_val}_tp{tp_idx}_q{q_id}_opt{row['option_id']}_item{row['item_id']}")
                                labels.append(f"【{tp}】 {q_id}：{row['option_text']}")
                            keys.append(f"other_label_{sh_val}_tp{tp_idx}_q{q_id}"); labels.append(f"【{tp}】 {q_id}：その他（自由記述）")
                            keys.append(f"other_val_{sh_val}_tp{tp_idx}_q{q_id}"); labels.append(f"【{tp}】 {q_id}：その他（評価値）")
                    return keys, labels
                
                keys, readable_labels = get_fixed_headers_and_labels(sh, df_master)
                values = [answers_to_save.get(k, "") for k in keys]
                
                all_vals = worksheet.get_all_values()
                if not any(any(str(c).strip() != "" for c in r) for r in all_vals):
                    worksheet.clear(); worksheet.append_row(readable_labels)
                worksheet.append_row(values)
                next_step("thanks")
            except Exception as e:
                st.error(f"データ保存中にエラーが発生しました: {e}")

# =========================================================
# 6. 終了画面
# =========================================================
elif st.session_state.step == "thanks":
    st.success("多くの質問へのご回答そしてご協力、誠にありがとうございました。")
    st.write("データが正常に記録されました。このウィンドウを閉じて終了してください。")
    st.balloons()
elif st.session_state.step == "end_denied":
    st.warning("アンケートを終了します。ご協力ありがとうございました。")
