import streamlit as st
import google.generativeai as genai

# --- 1. アプリの初期設定 ---
st.set_page_config(page_title="数学AIチューター", page_icon="📐")

st.title("📐 高校数学 AIチューター")
st.caption("Gemini 2.5 Flash 搭載。最新AIがあなたの学習をサポートします！")

# --- 2. 会話履歴の保存場所 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. サイドバー設定 ---
with st.sidebar:
    st.header("先生用管理画面")
    
    # APIキー設定
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("✅ 認証済み（サーバーキー使用中）")
    except:
        pass

    if not api_key:
        input_key = st.text_input("Gemini APIキーを入力", type="password")
        if input_key:
            api_key = input_key.strip()
    
    st.markdown("---")

    # ★機能1：会話リセットボタン（赤色）★
    if st.button("🗑️ 会話をリセットする", type="primary"):
        st.session_state.messages = []
        st.rerun()

    # ★機能2：類題出題ボタン（通常色）★
    # 押すと、裏側で「類題を作って」という指示をAIに送ります
    if st.button("🔄 さっきの類題を出題"):
        # AIへの指示内容
        prompt_text = """
        【教師へのリクエスト】
        直前のやり取りで扱った問題と「同じ単元」「同じ難易度」の類題を1問作成してください。
        数値を変えるだけでなく、本質的な理解を試す問題にしてください。
        まだ解説はせず、問題のみを提示してください。
        """
        # ユーザーの発言として履歴に追加
        st.session_state.messages.append({"role": "user", "content": prompt_text})
        st.rerun()  # 画面を更新してAIに答えさせる
    
    st.markdown("---")
    
    # システムプロンプト（指導方針）
    system_instruction = """
    あなたは日本の高校の親切で優秀な数学教師です。
    生徒からの数学の質問に答えてください。
    
    【指導のルール】
    1. **すぐに最終的な正解を教えないこと**。
    2. 生徒が自力で解けるように、段階的なヒントや、考え方の道筋を示してください。
    3. 生徒が間違えている場合は、否定せず「惜しい！」「ここを確認してみて」と励ましてください。
    4. 数式はLaTeX形式（$マークで囲む）を使って綺麗に表示してください。
    5. 解説は高校生にもわかりやすい平易な言葉を使ってください。
    6. 「類題」を求められたら、直前の問題の構造を分析し、適切な練習問題を作成してください。
    """

# --- 4. モデルのセットアップ ---
if api_key:
    genai.configure(api_key=api_key)
    
    try:
        # 最新モデル指定
        target_model_name = "gemini-2.5-flash"
        
        model = genai.GenerativeModel(
            model_name=target_model_name,
            system_instruction=system_instruction
        )

        # 開発者用モデル表示
        st.sidebar.divider()
        st.sidebar.caption("🛠️ Developer Info")
        st.sidebar.info(f"🤖 Active Model:\n`{target_model_name}`")

    except Exception as e:
        st.error(f"モデル設定エラー: {e}")
        st.stop()

# --- 5. 過去の会話履歴を表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. AI応答ロジック（ボタンからも入力欄からも共通で動く） ---
# 履歴の最後が「user」なら、AIが答える番です
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    if not api_key:
        st.warning("左のサイドバーにAPIキーを入れてください")
        st.stop()

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # 過去の会話履歴をAIに渡す
            chat_history_for_ai = [
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages 
                if m["role"] != "system"
            ]
            
            # チャット開始
            chat = model.start_chat(history=chat_history_for_ai)
            
            # 最新のメッセージ（ユーザー入力またはボタンの指示）を取得して送信
            last_msg = st.session_state.messages[-1]["content"]
            response = chat.send_message(last_msg, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response)
            
            # AIの回答を保存
            st.session_state.messages.append({"role": "model", "content": full_response})
            
            # 完了後にリロード（連打防止）
            st.rerun()

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                 st.error("⚠️ 利用制限（429エラー）。少し時間を置いてください。")
            elif "404" in err_msg:
                 st.error(f"⚠️ モデルが見つかりません: {target_model_name}")
            else:
                st.error(f"エラーが発生しました: {e}")

# --- 7. 入力エリア ---
# ※AIが回答中の時は入力欄を出さない（エラー防止）
if not (st.session_state.messages and st.session_state.messages[-1]["role"] == "user"):
    if prompt := st.chat_input("質問を入力（例：ベクトルの内積って何？）"):
        # ユーザーの質問を表示
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
