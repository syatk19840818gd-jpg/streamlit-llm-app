# 0) .env から環境変数を読む（OPENAI_API_KEY 用）
# 環境変数をロードするために
# dotenvモジュールからload_dotenv関数をインポート
from dotenv import load_dotenv
load_dotenv()

# 0) 使うライブラリをまとめて読み込む
import os
import base64
import json
import re
import streamlit as st
import io                   

from gtts import gTTS       
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


# =========================
# 1) 設定
# =========================
# アプリの表示タイトル・背景画像・使うモデル名
APP_TITLE = "ワニせんせい"
BG_IMAGE_PATH = "unnamed.jpg"  # 背景にしたい画像ファイル（同じフォルダに置く）
MODEL_NAME = "gpt-4o-mini"


# =========================
# 2) 背景画像をCSSでセット
# （画像がない場合はデフォルト背景色）
# =========================
# 背景画像を base64 にして CSS の background-image に埋め込む
def _set_background(image_path: str) -> None:
    # 背景画像が無いとき：警告＋単色背景へ切り替え
    if not os.path.exists(image_path):
        st.warning(f"背景画像が見つかりませんでした: {image_path}")
        st.markdown(
            """
            <style>
              .stApp { background-color: #f5f5f5; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        return

    # 画像ファイルを読み込んで base64 文字列にする
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    # CSSをまとめて差し込む（見た目はここで決まる）
    st.markdown(
        f"""
        <style>
          /* 全体背景（画像を敷く） */
          .stApp {{
            background-image: url("data:image/jpeg;base64,{b64}");
            background-repeat: no-repeat;
            background-position: 50% 42%;
            background-size: min(800px, 92vw) auto;
            background-attachment: fixed;
            background-color: white;
          }}

          /* 画面の横幅・上の余白（全体のレイアウト） */
           /* 【自動調整1】上の余白を環境に合わせて計算する */
          .block-container {{
            /* calc(60px + env(safe-area-inset-top)) の意味：
               「基本の60px」＋「そのスマホの切り欠き（ノッチ）の高さ」を
               自動で足し算して余白にする命令。*/
            padding-top: calc(60px + env(safe-area-inset-top)) !important;
            padding-bottom: 40px;
            max-width: 980px;
          }}          

          /* タイトル（明朝） */
           /* 【自動調整2】文字サイズを画面幅に合わせて伸縮させる */
          .wani-title {{
            font-family: "Yu Mincho", "游明朝", "YuMincho", "Hiragino Mincho ProN", "MS Mincho", serif;
            font-weight: 900;
            
            /* clamp(最小サイズ, 推奨サイズ, 最大サイズ) の意味：
               ・画面が小さくても「32px」よりは小さくしない
               ・基本は画面幅の「10% (10vw)」の大きさにする
               ・画面が大きくても「64px」よりは大きくしない
               これをブラウザが自動で計算する。*/
            font-size: clamp(32px, 10vw, 64px);

            /* 行間調整 */
            line-height: 1.4;
            
            /* 文字周り調整 */
            margin-bottom: 10px;
            padding-top: 10px;
          }}

          /* 概要（ゴシック） */
           /* 概要文レスポンシブ対応 */
          .wani-desc {{
            font-family: "Yu Gothic", "游ゴシック", "YuGothic", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            /* スマホなら14px、PCなら18pxくらいになるように調整 */
            font-size: clamp(14px, 4vw, 18px);
            line-height: 1.7;
            margin-bottom: 14px;
          }}

          /* ラジオ全体の上下の余白調整 */
          div[data-testid="stRadio"] {{
            margin-top: 2px;
            margin-bottom: 0px;
          }}

          /* ラジオ1項目ごとの余白（項目どうしの間隔）調整 */
          div[data-testid="stRadio"] label[data-baseweb="radio"] {{
            align-items: flex-start;
            margin-bottom: 16px;
          }}

          /* ラジオ：最後の項目だけ下の余白を小さくする */
          div[data-testid="stRadio"] label[data-baseweb="radio"]:last-of-type {{
            margin-bottom: 6px;
          }}

          /* ラジオ：文字側の見た目（フォント・サイズ・行間・改行） */
          div[data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child {{
            font-family: "Yu Gothic", "游ゴシック", "YuGothic", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            font-size: 22px;
            font-weight: 400;
            line-height: 1.35;
            white-space: pre-wrap;
            margin-top: -2px;
          }}

          /* ラジオ：1行目だけ太字（「おしえて☆モード」などを強調） */
          div[data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child::first-line {{
            font-weight: 900;
          }}

          /* 例文のフォント（入力のヒント） */
          .wani-example {{
            font-family: "Yu Gothic", "游ゴシック", "YuGothic", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            font-size: 16px;
            margin-top: 0px;
            margin-bottom: -18px;
          }}

          /* 入力欄のフォント */
          input[type="text"] {{
            font-family: "Yu Gothic", "游ゴシック", "YuGothic", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            font-size: 18px;
          }}

          /* 入力欄の上の余白を詰める */
          div[data-testid="stTextInput"] {{
            margin-top: -14px;
          }}

          /* ボタンのフォント */
          button[kind="primary"], button[kind="secondary"] {{
            font-family: "Yu Gothic", "游ゴシック", "YuGothic", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            font-size: 18px !important;
          }}

          /* 出力BOX（枠線・行間・背景） */
          .wani-output {{
            border: 2px solid #111;
            min-height: 320px;
            padding: 18px 18px;
            font-family: "Yu Gothic", "游ゴシック", "YuGothic", "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            font-size: 18px;
            line-height: 1.5;
            white-space: pre-wrap;
            background: rgba(255,255,255,0.0);
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 3) LLMを用意（キャッシュ）
# =========================
# ChatOpenAI をキャッシュして使い回す（毎回作らない）
@st.cache_resource
def _get_llm() -> ChatOpenAI:
    # APIキーが無いときは止める（安全策）
    api_key = os.getenv("OPENAI_API_KEY", None)
    if not api_key:
        st.error("OPENAI_API_KEYが設定されていません。環境変数またはst.secretsで設定してください。")
        raise ValueError("APIキー未設定")
    # 使うモデル名と温度をここで固定
    return ChatOpenAI(model=MODEL_NAME, temperature=0.6)


# =========================
# 4) プロンプト
# =========================
# おしえて☆モード用の指示文
TEACH_SYSTEM = """
【役割】
あなたは「{topic}」について、小学生にわかりやすく正しい知識を教える先生です。

【実行プロセス】
[①] 「{topic}」に関する、図鑑や教科書に載っているような「客観的で確実な事実」をリストアップする。
[②] 調べた情報を要約し、小学生にもわかりやすい説明文を作る

【重要：出力ルール】
・出力は、説明の文章だけ（見出し（【役割】など）／手順／番号（[①]など）／箇条書き（・）を出さない）
・250文字以内

【重要：問題作成の禁止・制限事項】
・完成した説明文全体で、漢字は３割以内にし、残りはひらがな/カタカナにすること
・「画数が多くて線の密度がある漢字」は ひらがな/カタカナ にする。
・「一番」「最古」などの順位を扱う場合は、必ず「〇〇で一番」「〇〇の中で」のように**範囲や条件を明確にした上で明記**すること。
・文脈によって答えが変わるようなあいまいな文は作らないこと。
・あなたが100%の自信を持てない情報は絶対に書かないこと。
"""


# クイズ☆モード用（JSONで2問返す）
QUIZ_SYSTEM_JSON = """
【役割】
あなたは「{topic}」について、小学生に正しい知識を教えるクイズ博士です。

【実行プロセス】
[①] 「{topic}」に関する、図鑑や教科書に載っているような「客観的で確実な事実」をリストアップする。
[②] ①から問題文と解答をセットで2つ作る。

【重要：出力ルール】
・出力は JSON だけ（前後に文章をつけない／コードブロックも禁止）。
・クイズは必ず2問。
・questionは150文字以内、answerは20文字以内、explanationは100文字以内。
・explanationは、その答えの「りゆう（解説）」を書く。
・question/answer/explanationの中で " は使わない（強調は「」）

【重要：問題作成の禁止・制限事項】
・完成した説明文全体で、漢字は３割以内にし、残りはひらがな/カタカナにすること
・「画数が多くて線の密度がある漢字」は ひらがな/カタカナ にする。
・「一番」「最古」などの順位を扱う場合は、必ず「〇〇で一番」「〇〇の中で」のように**範囲や条件を明確にした上で、問題文に明記**すること。
・文脈によって答えが変わるようなあいまいな問題は作らないこと。
・あなたが100%の自信を持てない情報は絶対に出題しないこと。

出力JSONはこの形だけ：
{{"quizzes":[{{"question":"...","answer":"...","explanation":"..."}},{{"question":"...","answer":"...","explanation":"..."}}]}}
"""


# JSONが壊れたときに、同じ形式へ直させる指示文
QUIZ_REPAIR_SYSTEM = """
次のテキストを、指定のJSON形式に直して返して。

【出力】
・JSONだけ（前後の文章なし、コードブロックなし）
・quizzesは必ず2つ
・キーは必ず " で囲む（' は使わない）
・question/answer/explanationの中で " は使わない（強調は「」）

形式：
{{"quizzes":[{{"question":"...","answer":"...","explanation":"..."}},{{"question":"...","answer":"...","explanation":"..."}}]}}
"""


# =========================
# 5) LLM呼び出し
# =========================
# 入力（topic）とモードに応じて、LLMから文字列をもらう
def get_wani_answer(input_text: str, mode_value: str) -> str:
    # キャッシュ済みのLLMを取り出す
    llm = _get_llm()

    # おしえて☆モード：説明文を返す
    if mode_value == "おしえて☆モード":
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TEACH_SYSTEM),
                ("human", "しりたいこと：{topic}"),
            ]
        )
        res = llm.invoke(prompt.format_messages(topic=input_text))
        return (res.content or "").strip()

    # クイズ☆モード：JSON文字列を返す
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", QUIZ_SYSTEM_JSON),
            ("human", "しりたいこと：{topic}"),
        ]
    )
    res = llm.invoke(prompt.format_messages(topic=input_text))
    return (res.content or "").strip()


# =========================
# 6) 文字処理（見出し除去 / JSON抽出 / JSON修復 / 長さ調整）
# =========================
# 文字数オーバー時の保険（文末っぽい所で切る）
def _truncate_at_punct(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t

    head = t[:max_chars]
    # 文の終わりっぽい所で止める（途中で切れにくくする）
    cut_candidates = []
    for p in ["。", "！", "？", "!", "?"]:
        idx = head.rfind(p)
        if idx != -1:
            cut_candidates.append(idx + 1)

    if cut_candidates:
        cut = max(cut_candidates)
        return head[:cut].rstrip()

    return head.rstrip()


# おしえて☆モードの出力から、見出し/箇条書きっぽい行を削る
def _clean_teach_answer(text: str) -> str:
    t = (text or "").strip()
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    kept = []
    for ln in lines:
        if ln.startswith(("#", "・", "[", "【")):
            continue
        if any(key in ln for key in ("実行プロセス", "出力形式", "役割", "[①", "[②", "[③")):
            continue
        kept.append(ln)
    if kept:
        t = "\n".join(kept).strip()

    # ★変更点：250で「…」にせず、280以内で文末っぽい所に収める
    t = _truncate_at_punct(t, 280)
    return t


# LLMの出力から JSON だけを拾って dict に変える
def _extract_json_obj(text: str):
    t = (text or "").strip()
    t = re.sub(r"```(?:json)?\s*", "", t, flags=re.IGNORECASE).replace("```", "").strip()

    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return None

    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


# JSONが壊れてたら、LLMに「指定の形に直して」と頼む
def _repair_quiz_json(raw_text: str):
    llm = _get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", QUIZ_REPAIR_SYSTEM),
            ("human", "テキスト：\n{raw}"),
        ]
    )
    res = llm.invoke(prompt.format_messages(raw=raw_text))
    return _extract_json_obj((res.content or "").strip())


# quizzes の文字数をルール内に収める（出力の保険）
def _trim_quiz_lengths(obj: dict) -> dict:
    quizzes = obj.get("quizzes", [])
    if not isinstance(quizzes, list):
        return obj

    out = []
    for item in quizzes[:2]:
        q = str(item.get("question", "")).strip()
        a = str(item.get("answer", "")).strip()
        e = str(item.get("explanation", "")).strip()

        # ★変更点：途中で「…」になりにくいように、文末っぽい所で収める
        q = _truncate_at_punct(q, 150)
        a = _truncate_at_punct(a, 20)
        e = _truncate_at_punct(e, 100)

        out.append({"question": q, "answer": a, "explanation": e})

    obj["quizzes"] = out
    return obj

# =========================
# 音声データのHTML化
# =========================
def _make_audio_html(text: str) -> str:
    """テキストをgTTSで音声化し、base64エンコードしてHTMLタグを返す"""
    if not text:
        return ""
    try:
        # gTTSで音声生成 (lang='ja'で日本語)
        tts = gTTS(text=text, lang='ja')
        # メモリ上に書き込み
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        # Base64変換
        b64 = base64.b64encode(mp3_fp.read()).decode()
        
        # HTMLタグ生成（回答文の下に出すプレイヤー）
        # margin-topなどで位置を調整
        html = f"""
        <div style="margin-top: 20px; padding-top: 10px; border-top: 1px dashed #ccc; text-align: right;">
            <span style="font-size: 14px; margin-right: 8px; font-weight: bold; color: #555;">🔊 よみあげ</span>
            <audio controls style="vertical-align: middle; height: 32px;">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        </div>
        """
        return html
    except Exception as e:
        return ""

# =========================
# 7) 画面
# =========================
# 画面設定＋背景CSSの適用
st.set_page_config(page_title=APP_TITLE, page_icon="🐊", layout="centered")
_set_background(BG_IMAGE_PATH)

# セッション状態：表示テキスト・クイズの進行状態を保存する箱
if "output_text" not in st.session_state:
    st.session_state.output_text = ""

if "audio_html" not in st.session_state:
    st.session_state.audio_html = ""

if "quiz_stage" not in st.session_state:
    st.session_state.quiz_stage = 0

if "quiz_topic" not in st.session_state:
    st.session_state.quiz_topic = ""

for k in ("quiz_q1", "quiz_a1", "quiz_e1", "quiz_q2", "quiz_a2", "quiz_e2"):
    if k not in st.session_state:
        st.session_state[k] = ""

# タイトル・説明文（CSSクラスで見た目を当てる）
st.markdown(f'<div class="wani-title">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="wani-desc">
      この世界のことを、な〜んでもしってるワニ先生だよ！<br>
      キミが「しりたいこと」を２つのモードから選んでね！
    </div>
    """,
    unsafe_allow_html=True,
)

# モード選択（ラジオ）：表示文字は改行込みで整える
MODE_LABELS = {
    "teach": "おしえて☆モード\n   ｢しりたいこと｣を わかりやす〜くおしえるよ！",
    "quiz":  "クイズ☆モード\n   ｢しりたいこと｣のアッ！とおどろくクイズをだすよ！",
}
mode_key = st.radio("モード選択", ["teach", "quiz"], index=0, format_func=lambda k: MODE_LABELS[k], label_visibility="collapsed")
mode = "おしえて☆モード" if mode_key == "teach" else "クイズ☆モード"

# 例文（入力のヒント）
st.markdown(
    '<div class="wani-example">たとえば？「パンダ」「アメリカ」「うちゅう」「おんがく」など</div>',
    unsafe_allow_html=True,
)

# 入力欄（topic）
topic = st.text_input("知りたいこと", value="", placeholder="しりたいことを1ついれて「おしえて！」をおしてね。", label_visibility="collapsed")

# 入力チェック（空・長すぎ）
def validate_topic(x: str):
    if not x.strip():
        return "なにをしりたい？（ことばを1つだけいれてね）"
    if len(x) > 20:
        return "２０もじまでいれられるよ！"
    return None

# 実行ボタン
clicked = st.button("おしえて！")

# 出力枠（あとから書き換えるために empty を使う）
output_area = st.empty()
output_area.markdown(
    f'<div class="wani-output">{st.session_state.output_text}</div>',
    unsafe_allow_html=True,
)

# ボタンが押されたら：入力チェック→LLM呼び出し→出力更新
if clicked:
    err = validate_topic(topic)
    if err:
        st.warning(err)
    else:
        # 先に「考え中…」を表示（体感を良くする）
        output_area.markdown(
            '<div class="wani-output">考え中..すこしまってね。</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("考え中..すこしまってね。"):
            try:
                # おしえて☆モード：説明文を整形して出す
                if mode == "おしえて☆モード":
                    raw = get_wani_answer(topic, mode)
                    ans = _clean_teach_answer(raw)
                    st.session_state.output_text = ans
                    # 音声を生成
                    st.session_state.audio_html = _make_audio_html(ans)

                # クイズ☆モード：1回目=問題、2回目=答え＋せつめい
                else:
                    # 入力が変わったらクイズ状態をリセット
                    if st.session_state.quiz_topic != topic:
                        st.session_state.quiz_stage = 0
                        st.session_state.quiz_topic = topic
                        st.session_state.quiz_q1 = ""
                        st.session_state.quiz_a1 = ""
                        st.session_state.quiz_e1 = ""
                        st.session_state.quiz_q2 = ""
                        st.session_state.quiz_a2 = ""
                        st.session_state.quiz_e2 = ""

                    # 1回目：問題だけ表示
                    if st.session_state.quiz_stage == 0:
                        raw = get_wani_answer(topic, mode)
                        obj = _extract_json_obj(raw)

                        if not isinstance(obj, dict) or not isinstance(obj.get("quizzes"), list):
                            obj = _repair_quiz_json(raw)

                        if not isinstance(obj, dict) or not isinstance(obj.get("quizzes"), list):
                            st.session_state.output_text = "うまくクイズを作れなかったよ。もう1回おしてみてね！"
                        else:
                            obj = _trim_quiz_lengths(obj)
                            quizzes = obj.get("quizzes", [])

                            if len(quizzes) < 2:
                                st.session_state.output_text = "うまくクイズを作れなかったよ。もう1回おしてみてね！"
                            else:
                                q1 = quizzes[0]["question"]
                                a1 = quizzes[0]["answer"]
                                e1 = quizzes[0].get("explanation", "")
                                q2 = quizzes[1]["question"]
                                a2 = quizzes[1]["answer"]
                                e2 = quizzes[1].get("explanation", "")

                                # 2回目用に保存
                                st.session_state.quiz_q1 = q1
                                st.session_state.quiz_a1 = a1
                                st.session_state.quiz_e1 = e1
                                st.session_state.quiz_q2 = q2
                                st.session_state.quiz_a2 = a2
                                st.session_state.quiz_e2 = e2

                                st.session_state.quiz_stage = 1
                                st.session_state.output_text = (
                                    f"① {q1}\n\n"
                                    f"② {q2}\n\n"
                                    "「おしえて！」をもう１回おすと「こたえ」と「せつめい」がでるよ！"
                                )
                                # 音声を生成
                                st.session_state.audio_html = _make_audio_html(st.session_state.output_text)

                    # 2回目：答え＋せつめい表示
                    else:
                        q1 = st.session_state.quiz_q1
                        a1 = st.session_state.quiz_a1
                        e1 = st.session_state.quiz_e1
                        q2 = st.session_state.quiz_q2
                        a2 = st.session_state.quiz_a2
                        e2 = st.session_state.quiz_e2

                        st.session_state.output_text = (
                            f"① {q1}\n"
                            f"答え：{a1}\n"
                            f"せつめい：{e1}\n\n"
                            f"② {q2}\n"
                            f"答え：{a2}\n"
                            f"せつめい：{e2}"
                        )
                        st.session_state.quiz_stage = 0
                        # 音声を生成
                        st.session_state.audio_html = _make_audio_html(st.session_state.output_text)

            except Exception:
                st.session_state.output_text = "ごめんね、うまくできなかったよ。もう1回おしてみてね！"

        # テキストと音声を合体させて表示
        render_text = st.session_state.output_text.replace("\n", "<br>")
        audio_tag = st.session_state.audio_html
        
        # wani-output の枠の中に audio_tag を入れることで枠内にボタンを表示
        output_area.markdown(
            f'<div class="wani-output">{render_text}{audio_tag}</div>',
            unsafe_allow_html=True,
        )
