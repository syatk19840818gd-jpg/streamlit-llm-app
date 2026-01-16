import os
import tempfile
import base64
import pytest
from unittest import mock
import streamlit as st
from app import _set_background
from app import get_wani_answer
from app import _extract_json_obj

@pytest.fixture(autouse=True)
def reset_streamlit_state():
    # Reset Streamlit state before each test
    st.session_state.clear()

def test_set_background_image_exists(monkeypatch):
    # Create a temporary image file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"dummyimagecontent")
        tmp_path = tmp.name

    # Patch os.path.exists to return True
    monkeypatch.setattr(os.path, "exists", lambda path: path == tmp_path)

    # Patch st.markdown to capture calls
    called = {}
    def fake_markdown(html, unsafe_allow_html=False):
        called['html'] = html
        called['unsafe'] = unsafe_allow_html
    monkeypatch.setattr(st, "markdown", fake_markdown)

    _set_background(tmp_path)

    assert called['unsafe'] is True
    assert "background-image" in called['html']
    assert "base64," in called['html']

    os.remove(tmp_path)

def test_set_background_image_not_exists(monkeypatch):
    # Patch os.path.exists to return False
    monkeypatch.setattr(os.path, "exists", lambda path: False)

    # Patch st.warning and st.markdown to capture calls
    warnings = []
    markdowns = []
    monkeypatch.setattr(st, "warning", lambda msg: warnings.append(msg))
    monkeypatch.setattr(st, "markdown", lambda html, unsafe_allow_html=False: markdowns.append(html))

    _set_background("nonexistent.jpg")

    assert any("背景画像が見つかりませんでした" in w for w in warnings)
    assert any("background-color" in m for m in markdowns)
    @pytest.fixture(autouse=True)
    def reset_streamlit_state():
        st.session_state.clear()

    def test_get_wani_answer_oshiete_mode(monkeypatch):
        # Mock _get_llm to return a fake LLM object
        class FakeLLM:
            def invoke(self, msgs):
                class Res:
                    content = "これは小学生向けの説明です。"
                return Res()
        monkeypatch.setattr("app._get_llm", lambda: FakeLLM())

        # Test おしえて☆モード
        result = get_wani_answer("パンダ", "おしえて☆モード")
        assert "小学生向け" in result

    def test_get_wani_answer_quiz_mode(monkeypatch):
        # Mock _get_llm to return a fake LLM object
        class FakeLLM:
            def invoke(self, msgs):
                class Res:
                    content = '{"quizzes":[{"question":"パンダの好きな食べ物は？","answer":"たけ"},{"question":"パンダの色は？","answer":"しろとくろ"}]}'
                return Res()
        monkeypatch.setattr("app._get_llm", lambda: FakeLLM())

        # Test クイズ☆モード
        result = get_wani_answer("パンダ", "クイズ☆モード")
        assert "quizzes" in result

    def test_get_wani_answer_llm_init_fail(monkeypatch):
        # Mock _get_llm to raise Exception
        monkeypatch.setattr("app._get_llm", lambda: (_ for _ in ()).throw(Exception("APIキー未設定")))

        result = get_wani_answer("パンダ", "おしえて☆モード")
        assert "LLMの初期化に失敗しました" in result

    def test_get_wani_answer_llm_invoke_fail(monkeypatch):
        # Mock _get_llm to return a fake LLM object that raises Exception on invoke
        class FakeLLM:
            def invoke(self, msgs):
                raise Exception("invoke error")
        monkeypatch.setattr("app._get_llm", lambda: FakeLLM())

        # Patch st.error to avoid actual Streamlit error
        monkeypatch.setattr(st, "error", lambda msg: None)

        result = get_wani_answer("パンダ", "おしえて☆モード")
        assert "AIの応答取得に失敗しました" in result
        @pytest.mark.parametrize("input_text,expected", [
            # Valid JSON dict
            ('{"quizzes":[{"question":"Q1","answer":"A1"}]}', {"quizzes":[{"question":"Q1","answer":"A1"}]}),
            # Valid JSON dict with extra whitespace
            ('  { "quizzes": [ { "question": "Q1", "answer": "A1" } ] }  ', {"quizzes":[{"question":"Q1","answer":"A1"}]}),
            # Valid JSON dict embedded in text
            ('ここにJSONがあります: {"quizzes":[{"question":"Q1","answer":"A1"}]} ありがとう', {"quizzes":[{"question":"Q1","answer":"A1"}]}),
            # Invalid JSON, no dict
            ('["not","a","dict"]', None),
            # No JSON at all
            ('これはJSONではありません。', None),
            # Broken JSON
            ('{"quizzes":[{"question":"Q1","answer":"A1"}', None),
            # Multiple JSON objects, should pick the first
            ('{"quizzes":[{"question":"Q1","answer":"A1"}]} {"other":1}', {"quizzes":[{"question":"Q1","answer":"A1"}]}),
            # JSON object with extra text before and after
            ('abc {"quizzes":[{"question":"Q1","answer":"A1"}]} xyz', {"quizzes":[{"question":"Q1","answer":"A1"}]}),
        ])
        def test_extract_json_obj(input_text, expected):
            result = _extract_json_obj(input_text)
            assert result == expected

