import streamlit as st
import google.generativeai as genai

# --- 1. アプリの初期設定 ---
st.set_page_config(page_title="数学AIチューター", page_icon="📐")

st.title("📐 高校数学 AIチューター")
st.caption("わからない問題を質問してみよう。ヒントを出して一緒に考えてくれるよ！")

# --- 2. 会話履歴の保存場所を作る ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. サイドバー設定 ---
with st.sidebar:
    st.header("先生用管理画面")
    
    # 【変更点】APIキーをSecretsから自動読み込みするロジック
    # サーバーにキーが保存されていればそれを使い、なければ手動入力欄を出す
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ 認証済み（サーバーのキーを使用）")
    else:
        api_key = st.text_input("Gemini APIキーを入力", type="password")
    
    st.markdown("---")
    # システムプロンプト（AIへの指示書）
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

# --- 4. モデルのセットアップ ---
if api_key:
    genai.configure(api_key=api_key)
    
    # エラー回避のためのモデル自動選択ロジック
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        if available_models:
            # 優先順位：Flash -> Pro -> その他
            priority_keywords = ["flash", "pro", "gemini-1.5", "gemini-1.0"]
            selected_model_name = available_models[0]
            
            for keyword in priority_keywords:
                found = next((m for m in available_models if keyword in m), None)
                if found:
                    selected_model_name = found
                    break
            
            # モデルのインスタンス化
            model = genai.GenerativeModel(
                model_name=selected_model_name,
                system_instruction=system_instruction
            )
        else:
            st.error("利用可能なモデルが見つかりませんでした。")
            st.stop()

    except Exception as e:
        st.error(f"モデル設定エラー: {e}")
        st.stop()

# --- 5. 過去の会話履歴を表示する ---
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
    # 履歴に追加（保存）
    st.session_state.messages.append({"role": "user", "content": prompt})

    # AIの回答を生成
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # 過去の会話履歴をAIに渡す形に変換
            chat_history_for_ai = [
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages 
                if m["role"] != "system" # システムメッセージは除外
            ]
            
            # チャットセッションを開始
            chat = model.start_chat(history=chat_history_for_ai)
            response = chat.send_message(prompt, stream=True)
            
            # ストリーミング表示
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response)
            
            # AIの回答も履歴に追加（保存）
            st.session_state.messages.append({"role": "model", "content": full_response})

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")