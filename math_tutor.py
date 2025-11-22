import streamlit as st
import google.generativeai as genai
from io import BytesIO
import os

# --- PDF生成用ライブラリ ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

# --- 1. アプリの初期設定 ---
st.set_page_config(page_title="数学AIチューター", page_icon="📐")

st.title("📐 高校数学 AIチューター")
st.caption("Gemini 2.5 Flash 搭載。類題のPDF作成機能付き！")

# --- 2. 会話履歴の保存 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. フォントの登録（PDF用） ---
# フォントファイルがあるか確認し、あれば登録する
FONT_FILE = "ipaexg.ttf"  # ※必ず同じフォルダに置いてください
font_registered = False

if os.path.exists(FONT_FILE):
    try:
        pdfmetrics.registerFont(TTFont('IPAexGothic', FONT_FILE))
        font_registered = True
    except Exception as e:
        st.error(f"フォント登録エラー: {e}")
else:
    # フォントがない場合は警告（アプリ自体は止めない）
    st.warning(f"⚠️ PDF作成用のフォントファイル({FONT_FILE})が見つかりません。PDFは文字化けする可能性があります。")


# --- 4. PDF作成関数 ---
def create_pdf(problem_text, answer_text):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # フォント設定（登録できていればIPAexGothic、なければHelvetica）
    use_font = 'IPAexGothic' if font_registered else 'Helvetica'
    
    # --- 1ページ目：問題 ---
    c.setFont(use_font, 16)
    c.drawString(20 * mm, height - 20 * mm, "【類題演習】")
    
    c.setFont(use_font, 10)
    text_object = c.beginText(20 * mm, height - 35 * mm)
    text_object.setFont(use_font, 11)
    text_object.setLeading(16) # 行間
    
    # 改行で分割して1行ずつ書き込み
    for line in problem_text.split('\n'):
        # ページの端まで来たら簡易的に折り返す処理は省略（長文注意）
        text_object.textLine(line)
    c.drawText(text_object)
    
    c.showPage() # 改ページ
    
    # --- 2ページ目：解答 ---
    c.setFont(use_font, 16)
    c.drawString(20 * mm, height - 20 * mm, "【解答・解説】")
    
    c.setFont(use_font, 10)
    text_object = c.beginText(20 * mm, height - 35 * mm)
    text_object.setFont(use_font, 11)
    text_object.setLeading(16)
    
    for line in answer_text.split('\n'):
        text_object.textLine(line)
    c.drawText(text_object)
    
    c.save()
    buffer.seek(0)
    return buffer


# --- 5. サイドバー設定 ---
with st.sidebar:
    st.header("先生用管理画面")
    
    # APIキー設定
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
    st.write("### 🔄 類題作成＆PDF")
    num_questions = st.number_input("作成数", 1, 5, 1)
    
    if st.button("類題を作成する"):
        # 区切り文字 |||SPLIT||| を入れて出力させるプロンプト
        prompt_text = f"""
        【教師へのリクエスト】
        直前のやり取りで扱った問題と「同じ単元」「同じ難易度」の類題を【{num_questions}問】作成してください。
        
        【出力形式の絶対ルール】
        1. まず「問題」だけを書いてください。
        2. 次に、区切り文字として「|||SPLIT|||」とだけの行を入れてください。
        3. 最後に「解答と解説」を書いてください。
        
        ※この形式を守らないとプリント作成機能が動きません。
        """
        st.session_state.messages.append({"role": "user", "content": prompt_text})
        st.rerun()
    
    st.markdown("---")
    
    system_instruction = """
    あなたは日本の高校数学教師です。
    指導ルール：
    1. ヒントを出して導くこと。
    2. 数式はLaTeX形式（$マーク）を使うこと。
    3. 「類題」を求められたら、指示された出力形式（|||SPLIT|||で区切る）を厳守すること。
    """

# --- 6. モデル設定 ---
if api_key:
    genai.configure(api_key=api_key)
    try:
        target_model_name = "gemini-2.5-flash"
        model = genai.GenerativeModel(target_model_name, system_instruction=system_instruction)
        st.sidebar.caption(f"Model: `{target_model_name}`")
    except Exception as e:
        st.error(f"設定エラー: {e}")
        st.stop()

# --- 7. チャット表示 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 8. AI応答 & PDFボタン生成ロジック ---
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
            
            # --- PDFボタンの表示判定 ---
            # AIの回答の中に区切り文字が含まれていたら、それは「類題」なのでPDFボタンを出す
            if "|||SPLIT|||" in full_response:
                st.rerun() # ボタンを表示するためにリロード
                
        except Exception as e:
            st.error(f"エラー: {e}")

# --- 9. PDFダウンロードボタンの設置 ---
# 最新のメッセージがAIで、かつ区切り文字が含まれている場合
if st.session_state.messages and st.session_state.messages[-1]["role"] == "model":
    last_content = st.session_state.messages[-1]["content"]
    
    if "|||SPLIT|||" in last_content:
        # 区切り文字で分割
        parts = last_content.split("|||SPLIT|||")
        if len(parts) == 2:
            problem_part = parts[0].strip()
            answer_part = parts[1].strip()
            
            st.success("🎉 類題プリントが作成されました！")
            
            # PDF生成
            pdf_data = create_pdf(problem_part, answer_part)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.download_button(
                    label="📄 PDFをダウンロード",
                    data=pdf_data,
                    file_name="math_practice.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            with col2:
                st.info("※1ページ目に問題、2ページ目に解答があります。")

# --- 10. 入力エリア ---
if not (st.session_state.messages and st.session_state.messages[-1]["role"] == "user"):
    if prompt := st.chat_input("質問を入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
