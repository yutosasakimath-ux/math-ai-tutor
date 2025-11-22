import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. アプリの初期設定 ---
st.set_page_config(page_title="数学AIチューター Pro", page_icon="🎓", layout="wide")

st.title("🎓 高校数学 AIチューター Pro")
st.caption("わからない問題を質問してみよう。サイドバーのボタンで「類題」も出せるよ！")

# --- 2. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. サイドバー設定 ---
with st.sidebar:
    st.header("🛠️ 先生用・ツール")
    
    # APIキー設定（エラー回避ロジック）
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("✅ 認証済み（サーバーキー）")
    except:
        pass

    if not api_key:
        api_key = st.text_input("Gemini APIキーを入力", type="password")

    st.markdown("---")

    # 会話リセットボタン
    if st.button("🗑️ 会話をリセットする", type="primary"):
        st.session_state.messages = [] 
        st.rerun() 

    # 類題生成ボタン
    if st.button("🔄 さっきの類題を出題"):
        st.session_state.messages.append({
            "role": "user", 
            "content": "さっきの解説を踏まえて、数値や設定を変えた【類題】を1問作成してください。まだ答えは言わないでください。"
        })
        st.rerun() 

    st.markdown("---")
    
    # ログダウンロード
    log_text = ""
    for m in st.session_state.messages:
        role_name = "自分" if m["role"] == "user" else "AI先生"
        content_text = m["content"] if isinstance(m["content"], str) else "[画像]"
        log_text += f"【{role_name}】\n{content_text}\n\n"
    st.download_button("ログをダウンロード (.txt)", log_text, "math_log.txt")

    # システムプロンプト
    with st.expander("先生用：指導方針"):
        system_instruction = st.text_area(
            "プロンプト内容",
            value="""
            あなたは日本の高校の親切で優秀な数学教師です。
            生徒からの数学の質問（テキストまたは画像）に答えてください。
            
            【指導のルール】
            1. **すぐに正解を教えない**。ヒントを出して考えさせる。
            2. 画像が送られた場合、その問題の内容を読み取って解説する。
            3. 数式はLaTeX形式（$マーク）を使って綺麗に表示する。
            4. 生徒を励まし、ポジティブなフィードバックを行う。
            5. 「類題」を求められたら、直前の問題と似た難易度の問題を1問作成する。
            """
        )

# --- 4. モデル設定（安全策：実験モデルを除外して自動選択） ---
model = None
if api_key:
    genai.configure(api_key=api_key)
    try:
        # 利用可能なモデルを全取得
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 【ここが重要】無料枠のない実験モデル(exp)や最新すぎるモデル(2.5)を除外する
        stable_models = [m for m in all_models if "exp" not in m and "2.5" not in m]
        
        target_model = "gemini-1.5-flash" # 第一希望
        
        if stable_models:
            # 1. "flash" がつく安定モデルを探す
            flash_model = next((m for m in stable_models if "flash" in m), None)
            # 2. なければ "pro" がつく安定モデルを探す
            pro_model = next((m for m in stable_models if "pro" in m), None)
            
            # 優先順位：Flash > Pro > リストの最初
            if flash_model:
                target_model = flash_model
            elif pro_model:
                target_model = pro_model
            else:
                target_model = stable_models[0]
        
        # モデル決定
        model = genai.GenerativeModel(
            model_name=target_model, 
            system_instruction=system_instruction
        )
        # デバッグ用に少しだけ情報を出す（必要なければ消してOK）
        # st.sidebar.caption(f"使用モデル: {target_model}")
        
    except Exception as e:
        st.error(f"モデル設定エラー: {e}")

# --- 5. チャット履歴の表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        content = message["content"]
        if isinstance(content, str):
            st.markdown(content)
        elif isinstance(content, dict) and "image" in content:
            st.image(content["image"], width=300)
            if "text" in content:
                st.markdown(content["text"])

# --- 6. AI応答ロジック ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    if not api_key:
        with st.chat_message("assistant"):
            st.warning("APIキーが設定されていません。")
        st.stop()

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        try:
            last_msg = st.session_state.messages[-1]["content"]
            content_to_send = [last_msg["text"], last_msg["image"]] if isinstance(last_msg, dict) else last_msg

            try:
                response = model.generate_content(content_to_send, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response)
                
                st.session_state.messages.append({"role": "model", "content": full_response})
                st.rerun()
            
            except Exception as api_error:
                st.error(f"通信エラー: {api_error}")
                st.info("時間を置くか、リセットボタンを押してみてください。")

        except Exception as e:
            st.error(f"予期せぬエラー: {e}")

# --- 7. 入力エリア ---
uploaded_file = st.file_uploader("📸 画像をアップロード（任意）", type=["jpg", "png", "jpeg"], key="img_uploader")

if prompt := st.chat_input("質問を入力..."):
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.session_state.messages.append({"role": "user", "content": {"text": prompt, "image": img}})
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()
