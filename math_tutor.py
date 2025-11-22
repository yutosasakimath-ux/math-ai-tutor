import streamlit as st
import google.generativeai as genai
from PIL import Image
import time

# --- 1. アプリの基本設定 ---
st.set_page_config(page_title="数学AIチューター Pro", page_icon="🎓", layout="wide")

st.title("🎓 高校数学 AIチューター Pro")
st.caption("Gemini 1.5 Pro搭載。文脈を理解し、あなたの専属家庭教師として指導します。")

# --- 2. 記憶（セッション）の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. サイドバー（設定とツール） ---
with st.sidebar:
    st.header("🛠️ 先生用メニュー")
    
    # APIキー設定（サーバーの鍵があれば自動読み込み、なければ手動入力）
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("✅ 認証済み")
    except:
        pass

    if not api_key:
        api_key = st.text_input("Gemini APIキー", type="password")

    st.markdown("---")

    # 3-1. 会話リセットボタン
    if st.button("🗑️ 会話をリセット", type="primary"):
        st.session_state.messages = []
        st.rerun()

    # 3-2. 類題生成ボタン
    if st.button("🔄 さっきの類題を出題"):
        # AIに送る「類題作成」の特別リクエスト
        prompt_text = """
        【教師へのリクエスト】
        直前のやり取りで扱った問題と「同じ単元」「同じ難易度」の類題を1問作成してください。
        単に数字を変えるだけでなく、本質的な理解を試す問題にしてください。
        まだ解説はせず、問題のみを提示してください。
        """
        # ユーザーの発言として履歴に追加し、AIの回答を誘発する
        st.session_state.messages.append({"role": "user", "content": prompt_text})
        st.rerun()

    st.markdown("---")
    
    # 3-3. 指導プロンプト（AIの性格設定）
    with st.expander("指導方針（システムプロンプト）"):
        system_instruction = st.text_area(
            "指示内容",
            value="""
            あなたは日本の高校数学のプロフェッショナルな教師です。
            
            【行動ルール】
            1. **文脈重視**: 過去の会話の流れを常に意識して回答すること。
            2. **スキャフォルディング**: いきなり正解を教えず、ヒントを出して生徒に考えさせること。
            3. **数式表示**: 数式は必ずLaTeX形式（$マークで囲む）で記述すること。
            4. **類題作成**: 「類題」を求められたら、直前の問題の構造を分析し、適切な練習問題を作成すること。
            5. **トーン**: 生徒を励まし、数学の面白さを伝えるような温かい口調で話すこと。
            """
        )
        
    # 3-4. ログ保存
    log_text = ""
    for m in st.session_state.messages:
        role = "生徒" if m["role"] == "user" else "AI先生"
        content = m["content"] if isinstance(m["content"], str) else "[画像または複合データ]"
        log_text += f"【{role}】\n{content}\n\n"
    st.download_button("対話ログを保存 (.txt)", log_text, "math_log.txt")

# --- 4. AIモデルの設定（最高性能版） ---
model = None
if api_key:
    genai.configure(api_key=api_key)
    try:
        # ★重要：Gemini 1.5 Pro (最新安定版) を指定
        # 思考力・文脈理解力が最も高く、数学指導に最適です。
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro", 
            system_instruction=system_instruction
        )
    except Exception as e:
        st.error(f"モデル設定エラー: {e}")

# --- 5. チャット履歴の表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        content = message["content"]
        
        # テキストの場合
        if isinstance(content, str):
            st.markdown(content)
        # 画像+テキスト（辞書型）の場合
        elif isinstance(content, dict):
            if "image" in content:
                st.image(content["image"], width=300)
            if "text" in content:
                st.markdown(content["text"])

# --- 6. AI応答ロジック（文脈を保持して回答する） ---
# 履歴の最後が「user」なら、AIが答える番です
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    
    if not api_key:
        st.warning("サイドバーでAPIキーを設定してください。")
        st.stop()

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # --- 文脈データの構築 ---
            # 過去のやり取りをGeminiが理解できる形式に変換します
            history_for_ai = []
            
            # 今回の最新メッセージ以外（過去ログ）を履歴として積み上げる
            for msg in st.session_state.messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]
                
                parts = []
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, dict):
                    if "text" in content: parts.append(content["text"])
                    if "image" in content: parts.append(content["image"])
                
                history_for_ai.append({"role": role, "parts": parts})

            # --- チャット開始 ---
            # 過去の履歴を持った状態でチャットセッションを作る
            chat = model.start_chat(history=history_for_ai)
            
            # 今回のユーザー入力データを作成
            current_msg = st.session_state.messages[-1]["content"]
            current_parts = []
            if isinstance(current_msg, str):
                current_parts.append(current_msg)
            elif isinstance(current_msg, dict):
                if "text" in current_msg: current_parts.append(current_msg["text"])
                if "image" in current_msg: current_parts.append(current_msg["image"])

            # 送信
            response = chat.send_message(current_parts, stream=True)
            
            # ストリーミング表示
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response)
            
            # 回答を履歴に保存
            st.session_state.messages.append({"role": "model", "content": full_response})
            
            # 完了したらリロード（連投防止）
            st.rerun()

        except Exception as e:
            # エラー処理：特に「使いすぎ(429)」の場合のアドバイス
            error_msg = str(e)
            if "429" in error_msg:
                st.error("⚠️ アクセス集中によりAIが混雑しています（429 Quota Exceeded）。")
                st.info("Proモデルは高性能ですが利用制限が厳しいため、1分ほど待ってから再試行してください。")
            else:
                st.error(f"エラーが発生しました: {error_msg}")
                st.info("会話が長くなりすぎている場合は「リセット」ボタンを試してください。")

# --- 7. 入力エリア ---
uploaded_file = st.file_uploader("📸 画像をアップロード（任意）", type=["jpg", "png", "jpeg"], key="file_uploader")

if prompt := st.chat_input("質問を入力してください..."):
    # 画像があるかどうかで保存形式を変える
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.session_state.messages.append({"role": "user", "content": {"text": prompt, "image": img}})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
    
    st.rerun()
