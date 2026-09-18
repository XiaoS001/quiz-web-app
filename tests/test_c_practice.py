# -*- coding: utf-8 -*-
"""C 组 · 刷题与判分（核心模块）"""
import json

import pytest

from models import Question, Record


def _extract_questions(html):
    """从刷题页 HTML 里取出后端传过来的 QUESTIONS 数据

    页面里是这样注入的：const QUESTIONS = [...] ;
    用 raw_decode 解析，避免被选项数组里的 ] 打断。
    """
    key = "const QUESTIONS = "
    i = html.index(key) + len(key)
    obj, _ = json.JSONDecoder().raw_decode(html[i:])
    return obj


# ---------- 题型入口 ----------

def test_C21_无效题型重定向回首页(client):
    """C-21 访问不存在的题型应重定向，而不是报 500"""
    r = client.get("/quiz/1/practice/not_exist")
    assert r.status_code == 302


# ---------- 选择题判分 ----------

def test_C01_选择题答对判正确(client, sample_questions):
    """C-01 提交正确答案应判对"""
    q = sample_questions["choice"]
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"]})
    assert r.status_code == 200
    assert r.get_json()["is_correct"] is True


def test_C02_选择题答错判错误并返回正确答案(client, sample_questions):
    """C-02 提交错误答案应判错，并返回正确答案内容"""
    q = sample_questions["choice"]
    wrong = next(o["letter"] for o in q["options"] if o["letter"] != q["answer"])
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": wrong})
    body = r.get_json()
    assert body["is_correct"] is False
    assert body["correct_answer"], "判错时应返回正确答案"


def test_C19_提交空答案判错且不报错(client, sample_questions):
    """C-19 空答案应判错，且服务端不报错"""
    q = sample_questions["choice"]
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": ""})
    assert r.status_code == 200
    assert r.get_json()["is_correct"] is False


def test_C20_答题后写入record表(client, app_module, sample_questions):
    """C-20 每次提交答案都应写入 record 表（用数据库核对，不只信页面）"""
    q = sample_questions["choice"]
    with app_module.app.app_context():
        before = Record.query.count()
    client.post("/api/check", json={"question_id": q["id"], "user_answer": "A"})
    with app_module.app.app_context():
        assert Record.query.count() == before + 1


# ---------- 选项打乱（BUG-001）----------

def test_C03_选项应按设计打乱(client, app_module, sample_questions):
    """C-03 设计文档要求「打乱选项顺序」以防记忆字母位置（app.py 的 practice() / wrong_practice()）

    做法：把页面注入的选项顺序与数据库存储顺序逐题比对。
    因为打乱是随机的，单看一道题有约 1/24 的概率刚好又排回原序，
    所以这里统计「有多少道题顺序与数据库不同」——只要有一道不同，就说明打乱生效。
    """
    q = sample_questions["choice"]
    quiz_id = q["quiz_set_id"]

    with app_module.app.app_context():
        db_rows = {}
        for row in Question.query.filter_by(quiz_set_id=quiz_id, type="choice").all():
            try:
                db_rows[row.id] = [o["letter"] for o in json.loads(row.options or "[]")]
            except Exception:
                pass

    html = client.get("/quiz/%d/practice/choice" % quiz_id).get_data(as_text=True)
    data = _extract_questions(html)
    assert data, "刷题页应返回题目数据"

    compared = 0
    changed = 0
    for item in data:
        if item.get("type") != "choice":
            continue
        db_order = db_rows.get(item["id"])
        if not db_order:
            continue
        compared += 1
        if [o["letter"] for o in item["options"]] != db_order:
            changed += 1

    assert compared > 0, "没有可比对的选择题"
    assert changed > 0, (
        "共比对 %d 道选择题，选项顺序全部与数据库存储顺序一致 —— 说明选项没有被打乱" % compared)


# ---------- 其它题型判分 ----------

def test_C09_判断题答对(client, sample_questions):
    """C-09 判断题提交正确答案应判对"""
    q = sample_questions["judge"]
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"]})
    assert r.get_json()["is_correct"] is True


def test_C04_多选题全对判对(client, sample_questions):
    """C-04 多选题选齐全部正确项应判对"""
    q = sample_questions["multi"]
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"]})
    assert r.get_json()["is_correct"] is True


def test_C08_多选题答案乱序输入仍判对(client, sample_questions):
    """C-08 多选答案顺序打乱着输入应仍判对（判分比对字母集合）"""
    q = sample_questions["multi"]
    shuffled = "".join(reversed(list(q["answer"])))
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": shuffled})
    assert r.get_json()["is_correct"] is True


def test_C05_多选题少选判错(client, sample_questions):
    """C-05 多选题少选应判错"""
    q = sample_questions["multi"]
    if len(q["answer"]) < 2:
        pytest.skip("样本多选题只有一个正确项，无法测少选")
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"][:1]})
    assert r.get_json()["is_correct"] is False


def test_C12_填空题答案一致判对(client, sample_questions):
    """C-12 填空题答案完全一致应判对"""
    q = sample_questions["fill"]
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"]})
    assert r.get_json()["is_correct"] is True


def test_C13_填空题多余空格标点仍判对(client, sample_questions):
    """C-13 填空题答案前后加多余空格与标点，应仍判对（去标点归一化）"""
    q = sample_questions["fill"]
    r = client.post("/api/check",
                    json={"question_id": q["id"], "user_answer": "  %s，。 " % q["answer"]})
    assert r.get_json()["is_correct"] is True


def test_C16_填空题答无关内容判错(client, sample_questions):
    """C-16 填空题答完全无关内容应判错"""
    q = sample_questions["fill"]
    r = client.post("/api/check",
                    json={"question_id": q["id"], "user_answer": "zzz完全无关的内容zzz"})
    assert r.get_json()["is_correct"] is False


def test_C17_简答题命中关键词判对(client, sample_questions):
    """C-17 简答题用参考答案作答应判对"""
    q = sample_questions.get("short_answer")
    if not q:
        pytest.skip("题库里没有简答题")
    r = client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"]})
    assert r.get_json()["is_correct"] is True


# ---------- 接口健壮性（BUG-003）----------

def test_C22_提交不存在的题目返回404(client):
    """C-22 不存在的 question_id 应返回 404"""
    r = client.post("/api/check", json={"question_id": 999999, "user_answer": "A"})
    assert r.status_code == 404


def test_C23_非JSON请求体应返回4xx而非5xx(client):
    """C-23 请求体不是 JSON 时应返回 4xx，不应 500（对应 BUG-003）"""
    r = client.post("/api/check", data="not a json", content_type="text/plain")
    assert 400 <= r.status_code < 500, "实际返回 %d，属服务端异常" % r.status_code


def test_C24_空JSON请求体应返回4xx而非5xx(client):
    """C-24 请求体为空 JSON 时应返回 4xx，不应 500（对应 BUG-003）"""
    r = client.post("/api/check", json={})
    assert 400 <= r.status_code < 500, "实际返回 %d，属服务端异常" % r.status_code
