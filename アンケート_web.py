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

# --- 重要視する要因の選択肢マスタ（ステークホルダー別） ---
FACTORS_4 = {
    "patient": ["説明が分かりやすいこと", "予定・処置の見通しが立つこと", "医療者の接遇が丁寧であること", "希望・不安を伝えやすいこと", "必要時にすぐ対応してもらえること", "患者に合わせた対応を受けられること", "医療・ケアが安全に行われること", "身体的な負担が少ないこと", "病室・病棟環境が快適であること", "プライバシーに配慮されること", "周囲とのつながりを保てること"],
    "nurse": ["患者と向き合う時間が確保されていること", "患者の状態・希望を把握できていること", "患者に合わせたケアが行えること", "患者への接遇が適切であること", "患者の尊厳・プライバシーに配慮できていること", "医療安全が確保されていること", "記録・情報共有が円滑であること", "多職種との連携が円滑であること", "業務量・時間的負担が過度でないこと", "物品・設備が利用しやすいこと", "病室・病棟環境を維持できること"],
    "manager": ["説明が適切に行われること", "接遇・声かけが丁寧であること", "必要時の対応が確実であること", "医療安全を確保できること", "病室・病棟環境を維持できること", "情報共有・記録が正確であること", "多職種が連携しやすいこと", "手順・判断基準が明確であること", "医療従事者の負担が軽減されること", "物品・設備を管理しやすいこと", "費用対効果が高いこと"]
}

FACTORS_3 = {
    "patient": ["安心できること", "理解・納得できること", "医療者を信頼できること", "不安が少ないこと", "尊厳が保たれること", "自分らしく過ごせること", "身体的に楽であること"],
    "nurse": ["医療の質・安全を維持できること", "業務を効率的に進められること", "専門性を発揮できること", "心身の余裕を保てること", "チームで協力できること", "誠実なケアを提供できること", "患者との信頼関係を築けること"],
    "manager": ["運営が安定していること", "医療の質・安全を維持できること", "患者との信頼関係を築けること", "働きやすい職場をつくれること", "資源を妥当に活用できること", "収益性・持続可能性を確保できること", "組織改善・成長につながること"]
}

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
        progress = 0.20 + (st.session_state.current_tp_idx / len(tps)) * 0.70
    elif st.session_state.step == "factors_page": progress = 0.95
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

# 全体タイトル（「01」のステップである同意画面とプロファイル画面でのみ表示）
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
    
    # 戻ってきた時用に前回の選択を復元
    c_index = ["未選択", "同意する", "同意しない"].index(st.session_state.answers.get("consent", "未選択"))
    consent = st.radio("回答への同意：", ["未選択", "同意する", "同意しない"], index=c_index, horizontal=True)
    
    sh_options = ["patient", "nurse", "manager"]
    sh_index = sh_options.index(st.session_state.answers.get("stakeholder", "patient"))
    stakeholder = st.selectbox("あなたの立場を選択してください（※システム制約上の追加項目）", sh_options, index=sh_index, format_func=lambda x: {"patient":"患者", "nurse":"看護師", "manager":"経営・運営者"}[x])
    
    if st.button("次へ", type="primary"):
        if consent == "同意する":
            st.session_state.answers['consent'] = consent
            st.session_state.answers['stakeholder'] = stakeholder
            next_step("profile")
        elif consent == "同意しない":
            next_step("end_denied")
        else:
            st.error("「同意する」または「同意しない」を選択してください。")

# =========================================================
# 2. 属性入力ページ
# =========================================================
elif st.session_state.step == "profile":
    st.header("基本情報の入力")
    sh = st.session_state.answers['stakeholder']

    with st.form("profile_form"):
        # keyを設定することで、戻ってきたときに自動で入力内容が復元されます
        st.radio("性別：", ["男性", "女性", "その他"], key="prof_gender", horizontal=True)
        st.text_input("年齢（代）：（半角数字 例：20、30など）", key="prof_age")
        
        if sh == "patient":
            st.text_input("入院日数（日）：（半角数字）", key="prof_days")
            st.text_input("診療科：", key="prof_dept")
            st.radio("入院回数：", ["初めて", "2回目以上"], key="prof_exp", horizontal=True)

        elif sh == "nurse":
            st.text_input("看護師経験年数（通算 年）：（半角数字）", key="prof_exp_total")
            st.text_input("看護師経験年数（現在の病棟 年）：（半角数字）", key="prof_exp_current")
            st.text_input("診療科：", key="prof_dept")
            st.radio("勤務体制：", ["日勤", "夜勤", "その他"], key="prof_shift", horizontal=True)
            st.text_input("勤務体制（その他の場合）：", key="prof_shift_other")
            st.radio("役職：", ["一般看護師", "リーダー・主任", "看護師長", "その他"], key="prof_role", horizontal=True)
            st.text_input("役職（その他の場合）：", key="prof_role_other")

        elif sh == "manager":
            st.text_input("経営・運営に関わる経験年数（通算 年）：（半角数字）", key="prof_exp_total")
            st.text_input("現在の施設での役職経験（年）：（半角数字）", key="prof_exp_current")
            st.text_input("役職：", key="prof_role")
            st.radio("運営施設の種別：", ["一般病院", "特定機能病院", "地域医療支援病院", "精神病院", "その他"], key="prof_fac", horizontal=True)
            st.text_input("運営施設の種別（その他の場合）：", key="prof_fac_other")
            st.radio("病床数：", ["20〜99床", "100〜199床", "200〜499床", "500床以上"], key="prof_beds", horizontal=True)
            
        col1, col2 = st.columns([1, 1])
        with col1:
            back_btn = st.form_submit_button("前のページへ戻る")
        with col2:
            submit_btn = st.form_submit_button("次へ（記入方法の確認）", type="primary")
            
    # 戻る処理
    if back_btn:
        next_step("consent")
        
    # 次へ進む処理（バリデーション）
    if submit_btn:
        is_valid = True
        errors = []
        p_ans = {}
        
        # 共通項目：年齢
        val_age = st.session_state.prof_age
        if not val_age:
            is_valid = False; errors.append("年齢が未入力です。")
        else:
            norm_age = unicodedata.normalize('NFKC', val_age) # 全角を半角に変換
            if not norm_age.isdigit(): is_valid = False; errors.append("年齢は半角数字で入力してください。")
            else: p_ans["age"] = norm_age + "代"
            
        p_ans["gender"] = st.session_state.prof_gender

        # 患者のバリデーション
        if sh == "patient":
            val_days = st.session_state.prof_days
            if not val_days: is_valid = False; errors.append("入院日数が未入力です。")
            else:
                norm_days = unicodedata.normalize('NFKC', val_days)
                if not norm_days.isdigit(): is_valid = False; errors.append("入院日数は半角数字で入力してください。")
                else: p_ans["days"] = norm_days
                
            p_ans["dept"] = st.session_state.prof_dept
            if not p_ans["dept"]: is_valid = False; errors.append("診療科が未入力です。")
            p_ans["experience"] = st.session_state.prof_exp
            
        # 看護師のバリデーション
        elif sh == "nurse":
            for k, label in [("prof_exp_total", "看護師経験年数（通算）"), ("prof_exp_current", "看護師経験年数（現在の病棟）")]:
                v = st.session_state[k]
                if not v: is_valid = False; errors.append(f"{label}が未入力です。")
                else:
                    nv = unicodedata.normalize('NFKC', v)
                    if not nv.isdigit(): is_valid = False; errors.append(f"{label}は半角数字で入力してください。")
                    else: p_ans[k] = nv
            
            p_ans["dept"] = st.session_state.prof_dept
            if not p_ans["dept"]: is_valid = False; errors.append("診療科が未入力です。")
            
            p_ans["shift"] = st.session_state.prof_shift_other if st.session_state.prof_shift == "その他" else st.session_state.prof_shift
            if st.session_state.prof_shift == "その他" and not st.session_state.prof_shift_other:
                is_valid = False; errors.append("勤務体制（その他）の詳細を入力してください。")
                
            p_ans["role"] = st.session_state.prof_role_other if st.session_state.prof_role == "その他" else st.session_state.prof_role
            if st.session_state.prof_role == "その他" and not st.session_state.prof_role_other:
                is_valid = False; errors.append("役職（その他）の詳細を入力してください。")
                
        # 経営者のバリデーション
        elif sh == "manager":
            for k, label in [("prof_exp_total", "経験年数（通算）"), ("prof_exp_current", "現在の施設での役職経験")]:
                v = st.session_state[k]
                if not v: is_valid = False; errors.append(f"{label}が未入力です。")
                else:
                    nv = unicodedata.normalize('NFKC', v)
                    if not nv.isdigit(): is_valid = False; errors.append(f"{label}は半角数字で入力してください。")
                    else: p_ans[k] = nv
                    
            p_ans["role"] = st.session_state.prof_role
            if not p_ans["role"]: is_valid = False; errors.append("役職が未入力です。")
            
            p_ans["facility_type"] = st.session_state.prof_fac_other if st.session_state.prof_fac == "その他" else st.session_state.prof_fac
            if st.session_state.prof_fac == "その他" and not st.session_state.prof_fac_other:
                is_valid = False; errors.append("運営施設の種別（その他）の詳細を入力してください。")
                
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
    
    # HTMLタグとCSSを用いて文字装飾と改行、太字の追加を実現
    st.markdown("""
    <div style='background-color: #f0f2f6; padding: 20px; border-radius: 5px; margin-bottom: 20px;'>
        <p>❖ <strong>「理想としてどの程度求めるか」</strong>を、スライダーを動かして評価してください。</p>
        <p>❖ 左端(0)は<span style='color: #d32f2f; font-weight: bold;'>「標準的な対応でよい（普通）」</span>、右端(100)は<span style='color: #d32f2f; font-weight: bold;'>「強く求める」</span>を表します。</p>
        <p>❖ <span style='color: #1976d2; font-weight: bold;'>すべての選択肢について</span>、空欄にせず印をつけてください。あまり重視しないものは、左端に近い位置に印をつけてください。</p>
        <p>❖ その他、加えたい内容がある場合は、任意でご記入ください。</p>
        <p>❖ 実際の現場では患者の状態や病棟の状況によって対応が異なると思いますが、本調査では、細かな条件を厳密に想定しすぎず、<strong>直感的にお答えください。</strong></p>
        <p>❖ 正解はありませんので、一般的に望ましいと思われる回答ではなく、ご自身の率直なお考えをご回答ください。ご回答の内容が、<strong>他の職員の方などに見られることはありません。</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 【記入例】")
    if os.path.exists(IMAGE_EXAMPLE):
        st.image(IMAGE_EXAMPLE, caption="スライダーの操作イメージ")
    else:
        st.info(f"※ここに記入例の画像（{IMAGE_EXAMPLE}）が表示されます。プログラムと同じフォルダに画像を配置してください。")
        
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
# 4. アンケート本編
# =========================================================
elif st.session_state.step == "survey_page":
    sh = st.session_state.answers['stakeholder']
    tps = df_master[df_master['stakeholder_id'] == sh]['touchpoint_text'].unique()
    current_tp = tps[st.session_state.current_tp_idx]
    
    st.header(f"Q{st.session_state.current_tp_idx + 1}. {current_tp}")
    st.write("") # 少し余白
    
    q_df = df_master[(df_master['stakeholder_id'] == sh) & (df_master['touchpoint_text'] == current_tp)]
    
    for q_id in q_df['question_text'].unique():
        options = q_df[q_df['question_text'] == q_id]
        
        # 1. 既存の選択肢のVAS (初期値を0に設定)
        for _, row in options.iterrows():
            key = f"val_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}_opt{row['option_id']}_item{row['item_id']}"
            st.session_state.answers[key] = st.slider(row['option_text'], 0, 100, 0, key=key)
            
        # 2. その他の入力欄と動的VAS (初期値を0に設定)
        other_key_text = f"other_text_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}"
        other_text = st.text_input("その他（上記以外）：", key=other_key_text)
        
        if other_text:
            other_key_val = f"other_val_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}"
            st.session_state.answers[other_key_val] = st.slider(f"「{other_text}」の評価", 0, 100, 0, key=other_key_val)
            st.session_state.answers[f"other_label_{sh}_tp{st.session_state.current_tp_idx}_q{q_id}"] = other_text

    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("前のテーマへ戻る", type="secondary"):
            if st.session_state.current_tp_idx > 0:
                st.session_state.current_tp_idx -= 1
                st.rerun()
            else:
                next_step("instructions")
                
    with col2:
        button_label = "次のテーマへ進む" if st.session_state.current_tp_idx < len(tps) - 1 else "重要視する要因の調査へ進む"
        if st.button(button_label, type="primary"):
            st.session_state.current_tp_idx += 1
            if st.session_state.current_tp_idx >= len(tps):
                next_step("factors_page")
            else:
                st.rerun()

# =========================================================
# 5. 重要視する要因に関する調査（チェックボックス版）
# =========================================================
elif st.session_state.step == "factors_page":
    st.header("03　重要視する要因に関する調査")
    sh = st.session_state.answers['stakeholder']
    
    label_context = {"patient": "入院生活", "nurse": "業務", "manager": "病院運営"}[sh]
    st.write(f"{label_context}において特に重視する要因をお答えください。")
    
    st.markdown("---")
    
    # 【1】4つ選択
    st.subheader("【1】以下の中から、特に重視するものを 4つ 選択してください。")
    selected_4 = []
    # 前回の選択状態を取得（戻ってきたとき用）
    prev_selected_4 = st.session_state.answers.get('factors_4_list', [])
    
    for factor in FACTORS_4[sh]:
        # チェックボックスを作成し、チェックされたらリストに追加
        is_checked = st.checkbox(factor, value=(factor in prev_selected_4), key=f"chk4_{factor}")
        if is_checked:
            selected_4.append(factor)
            
    st.write("") # 余白
    
    # 【2】3つ選択
    st.subheader("【2】以下の中から、特に重視するものを 3つ 選択してください。")
    selected_3 = []
    prev_selected_3 = st.session_state.answers.get('factors_3_list', [])
    
    for factor in FACTORS_3[sh]:
        is_checked = st.checkbox(factor, value=(factor in prev_selected_3), key=f"chk3_{factor}")
        if is_checked:
            selected_3.append(factor)

    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("アンケート（前ページ）へ戻る", type="secondary"):
            tps = df_master[df_master['stakeholder_id'] == sh]['touchpoint_text'].unique()
            st.session_state.current_tp_idx = len(tps) - 1
            next_step("survey_page")
            
    with col2:
        if st.button("最終確認へ進む", type="primary"):
            # バリデーション（指定の個数をきちんと選んでいるかチェック）
            if len(selected_4) != 4:
                st.error(f"【1】の設問は必ず「4つ」選択してください。（現在 {len(selected_4)}個 選択中）")
            elif len(selected_3) != 3:
                st.error(f"【2】の設問は必ず「3つ」選択してください。（現在 {len(selected_3)}個 選択中）")
            else:
                # データをカンマ区切りの文字列として保存
                st.session_state.answers['factors_4_list'] = selected_4
                st.session_state.answers['factors_3_list'] = selected_3
                st.session_state.answers['factors_4_text'] = ", ".join(selected_4)
                st.session_state.answers['factors_3_text'] = ", ".join(selected_3)
                next_step("final_submit")

# =========================================================
# 6. 最終送信ページ
# =========================================================
elif st.session_state.step == "final_submit":
    st.header("アンケートの完了")
    st.write("すべての回答が終了しました。以下のボタンを押してデータを送信してください。")
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("要因の調査へ戻る", type="secondary"):
            next_step("factors_page")
            
    with col2:
        if st.button("アンケートを送信する", type="primary"):
            st.session_state.answers['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 不要なリスト型データをスプレッドシート送信前に除外する処理
            answers_to_save = st.session_state.answers.copy()
            answers_to_save.pop('factors_4_list', None)
            answers_to_save.pop('factors_3_list', None)
            
            try:
                # 金庫から鍵を取り出してGoogleにログイン
                credentials_dict = json.loads(st.secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(credentials_dict)
                
                # 指定された新しいスプレッドシートを開く
                SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1kkZiyhLeOJnM0ypLpzytZZiVYhJBcRsc7bVnCXdhICk/edit"
                sh_doc = gc.open_by_url(SPREADSHEET_URL)
                worksheet = sh_doc.sheet1
                
                # データをリスト形式に変換
                headers = list(answers_to_save.keys())
                values = list(answers_to_save.values())
                
                # シートが空なら1行目に項目名（ヘッダー）を書き込む
                if not worksheet.get_all_values():
                    worksheet.append_row(headers)
                
                # 回答データを一番下の行に追加する
                worksheet.append_row(values)
                
                # 成功したらサンクスページへ
                next_step("thanks")
                
            except Exception as e:
                st.error(f"データ保存中にエラーが発生しました。設定を確認してください: {e}")

# =========================================================
# 7. 終了画面
# =========================================================
elif st.session_state.step == "thanks":
    st.success("多くの質問へのご回答そしてご協力、誠にありがとうございました。")
    st.write("データが正常に記録されました。このウィンドウを閉じて終了してください。")
    st.balloons()

elif st.session_state.step == "end_denied":
    st.warning("調査への同意が得られなかったため、アンケートを終了します。ご協力ありがとうございました。")
