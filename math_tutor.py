import streamlit as st
import google.generativeai as genai

# --- 1. アプリの初期設定 ---
st.set_page_config(page_title="数学AIチューター", page_icon="📐")

st.title("📐 高校数学 AIチューター")
st.caption("Gemini 1.5 Pro 搭載。ヒントを出して一緒に考えてくれるよ！")

# --- 2. 会話履歴の保存場所 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. サイドバー設定 ---
with st.sidebar:
    st.header("先生用管理画面")
    
    # APIキー設定（Secrets対応）
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("✅ 認証済み（サーバーキー使用中）")
    except:
        pass

    if not api_key:
        api_key = st.text_input("Gemini APIキーを入力", type="password")
    
    st.markdown("---")
    
    system_instruction = """
    あなたは日本の高校の親切で優秀な数学教師です。
    生徒からの数学の質問に答えてください。
    
    【指導のルール】
    1. **すぐに最終的な正解を教えないこと**。
    2. 生徒が自力で解けるように、段階的なヒントや、考え方の道筋を示してください。
    3. 生徒が間違えている場合は、否定せず「惜しい！」「ここを確認してみて」と励ましてください。
    4. 数式はLaTeX形式（$マークで囲む）を使って綺麗に表示してください。
    5. 解説は高校生にもわかりやすい平易な言葉を使ってください。
    """

# --- 4. モデルのセットアップ（ここを修正！） ---
if api_key:
    genai.configure(api_key=api_key)
    
    try:
        # 【修正点】モデルを自動探索せず、名指しで指定します。
        # これにより、勝手に実験版(2.5)が選ばれるエラーを防ぎます。
        # "gemini-1.5-pro" は現在無料で使える中で最も賢いモデルです。
        target_model_name = "gemini-1.5-pro"
        
        model = genai.GenerativeModel(
            model_name=target_model_name,
            system_instruction=system_instruction
        )
        
        # デバッグ用表示（必要なければ消してもOK）
        # st.sidebar.caption(f"使用モデル: {target_model_name}")

    except Exception as e:
        st.error(f"モデル設定エラー: {e}")
        st.stop()

# --- 5. 過去の会話履歴を表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 6. 新しい質問の処理 ---
if prompt := st.chat_input("質問を入力（例：ベクトルの内積って何？）"):
    if not api_key:
        st.warning("左のサイドバーにAPIキーを入れてください")
        st.stop()

    # ユーザーの質問を表示
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AIの回答を生成
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # 履歴の変換処理
            chat_history_for_ai = [
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages 
                if m["role"] != "system"
            ]
            
            # チャット開始
            chat = model.start_chat(history=chat_history_for_ai)
            response = chat.send_message(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "model", "content": full_response})

        except Exception as e:
            # エラー処理
            err_msg = str(e)
            if "429" in err_msg:
                st.error("⚠️ 使いすぎです（429エラー）。少し時間を置いてから試してください。")
            else:
                st.error(f"エラーが発生しました: {e}")
