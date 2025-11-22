import streamlit as st
import google.generativeai as genai
import os

# --- 1. アプリの初期設定 ---
st.set_page_config(page_title="数学AIチューター", page_icon="📐")

st.title("📐 高校数学 AIチューター")
st.caption("Gemini 2.5 Flash 搭載。数式が綺麗なプリント作成機能付き！")

# --- 2. 会話履歴の保存 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. HTML作成関数（数式対応版） ---
def create_html(problem_text, answer_text):
    # 改行コードをHTMLの<br>タグに変換
    p_text = problem_text.replace("\n", "<br>")
    a_text = answer_text.replace("\n", "<br>")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>数学類題プリント</title>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif; padding: 40px; line-height: 1.8; color: #333; }}
            h2 {{ border-bottom: 2px solid #555; padding-bottom: 10px; margin-top: 30px; }}
            .box {{ background: #f9f9f9; padding: 20px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 40px; }}
            .footer {{ font-size: 0.8em; color: #888; text-align: center; margin-top: 50px; }}
            @media print {{
                .page-break {{ page-break-before: always; }} /* 印刷時に改ページ */
                body {{ padding: 0; }}
                .box {{ border: none; }}
            }}
        </style>
    </head>
    <body>
        <h2>【類題演習】</h2>
        <div class="box">
            {p_text}
        </div>

        <div class="page-break"></div> <h2>【解答・解説】</h2>
        <div class="box">
            {a_text}
        </div>
        
        <div class="footer">Created by AI Math Tutor</div>
    </body>
    </html>
    """
    return html_content.encode('utf-8')

# --- 4. サイドバー設定 ---
with st.sidebar:
    st.header("先生用管理画面")
    
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("✅ 認証済み")
    except:
        pass

    if not api_key:
        input_key = st.text_input("Gemini APIキー", type="password")
        if input_key: api_key = input_key.strip()
    
    st.markdown("---")

    if st.button("🗑️ 会話をリセット", type="primary"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    
    # ★類題設定★
    st.write("### 🔄 類題プリント作成")
    num_questions = st.number_input("作成数", 1, 5, 1)
    
    if st.button("類題を作成する"):
        # 【修正点】書き言葉（だ・である調）を指定する強力なプロンプト
        prompt_text = f"""
        【教師へのリクエスト】
        直前のやり取りで扱った問題と「同じ単元」「同じ難易度」の類題を【{num_questions}問】作成してください。
        
        【重要：出力形式と文体】
        1. **文体**: 解答解説は、話し言葉（～ですね）ではなく、**数学の教科書や入試解答のような「だ・である調」の厳密な書き言葉**で記述してください。
        2. **形式**: 
           - まず「問題」だけを書いてください。
           - 次に区切り文字「|||SPLIT|||」だけの行を入れてください。
           - 最後に「解答と解説」を書いてください。
        """
        st.session_state.messages.append({"role": "user", "content": prompt_text})
        st.rerun()
    
    st.markdown("---")
    
    system_instruction = """
    あなたは日本の高校数学教師です。
    普段のチャットでは親しみやすい丁寧語（〜です、〜ます）で話してください。
    ただし、「類題作成」を求められた時の解答解説パートだけは、数学的に厳密な「だ・である調」で記述してください。
    数式はLaTeX形式（$マーク）を使用してください。
    """

# --- 5. モデル設定 ---
if api_key:
    genai.configure(api_key=api_key)
    try:
        target_model_name = "gemini-2.5-flash"
        model = genai.GenerativeModel(target_model_name, system_instruction=system_instruction)
        st.sidebar.divider()
        st.sidebar.caption("🛠️ Developer Info")
        st.sidebar.info(f"🤖 Active Model:\n`{target_model_name}`")
    except Exception as e:
        st.error(f"設定エラー: {e}")
        st.stop()

# --- 6. チャット表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. AI応答 & ファイル生成ロジック ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    if not api_key: st.stop()

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            chat_history = [{"role": m["role"], "parts": [str(m["content"])]} for m in st.session_state.messages if m["role"] != "system"]
            
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(st.session_state.messages[-1]["content"], stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "model", "content": full_response})
            
            # 区切り文字があればリロードしてボタンを表示
            if "|||SPLIT|||" in full_response:
                st.rerun()
                
        except Exception as e:
            st.error(f"エラー: {e}")

# --- 8. ダウンロードボタン（HTML版） ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "model":
    last_content = st.session_state.messages[-1]["content"]
    
    if "|||SPLIT|||" in last_content:
        parts = last_content.split("|||SPLIT|||")
        if len(parts) == 2:
            problem_part = parts[0].strip()
            answer_part = parts[1].strip()
            
            st.success("🎉 類題プリントが作成されました！")
            
            # HTML生成
            html_data = create_html(problem_part, answer_part)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.download_button(
                    label="📄 プリントをダウンロード",
                    data=html_data,
                    file_name="math_print.html",
                    mime="text/html",
                    type="primary"
                )
            with col2:
                st.info("💡 ダウンロードしたファイルを開き、ブラウザの印刷機能(Ctrl+P)から「PDFに保存」を選ぶと、数式が綺麗なPDFになります。")

# --- 9. 入力エリア ---
if not (st.session_state.messages and st.session_state.messages[-1]["role"] == "user"):
    if prompt := st.chat_input("質問を入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
