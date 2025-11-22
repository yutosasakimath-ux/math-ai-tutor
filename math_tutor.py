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
    
    # APIキー設定
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

# --- 4. モデル設定（修正済み） ---
model = None
if api_key:
    genai.configure(api_key=api_key)
    try:
        # 【修正】実験的なモデルを避け、安定版の「1.5 Flash」を指名する
        # Flashは高速で、無料枠の制限も緩いため教育アプリに最適です
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction=system_instruction
        )
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

            # エラーハンドリングを追加
            try:
                response = model.generate_content(content_to_send, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response)
                
                st.session_state.messages.append({"role": "model", "content": full_response})
                st.rerun()
            
            except Exception as api_error:
                # APIエラー（429など）が出た場合に画面に優しく表示する
                st.error(f"通信エラーが発生しました: {api_error}")
                st.info("時間を置いてもう一度試すか、会話をリセットしてみてください。")

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
