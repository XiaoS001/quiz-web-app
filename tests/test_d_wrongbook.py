# -*- coding: utf-8 -*-
"""D 组 · 错题本"""
import pytest

from models import Question, Record, QuizSet, db


def _wrong_question_ids(app_module, quiz_id, q_type):
    """复现 app.py wrongbook() 里「当前仍是错题」的判断逻辑

    逻辑：取该题型的错题记录 → 同一题只保留最新一条 → 若之后有更新的正确记录，则不算错题
    """
    with app_module.app.app_context():
        recs = Record.query.filter_by(quiz_set_id=quiz_id, type=q_type, is_correct=False).all()
        latest = {}
        for r in recs:
            if r.question_id not in latest or r.created_at > latest[r.question_id].created_at:
                latest[r.question_id] = r
        out = []
        for qid, lw in latest.items():
            newer = (Record.query.filter_by(question_id=qid, is_correct=True)
                     .filter(Record.created_at > lw.created_at).first())
            if not newer:
                out.append(qid)
        return out


def _wrong_letter(q):
    return next(o["letter"] for o in q["options"] if o["letter"] != q["answer"])


def test_D01_答错后该题进入错题集(client, app_module, sample_questions):
    """D-01 答错后应写入 is_correct=0 的记录，并出现在错题集里"""
    q = sample_questions["choice"]
    client.post("/api/check", json={"question_id": q["id"], "user_answer": _wrong_letter(q)})

    assert q["id"] in _wrong_question_ids(app_module, q["quiz_set_id"], "choice")
    assert client.get("/quiz/%d/wrongbook" % q["quiz_set_id"]).status_code == 200


def test_D02_错题按题型隔离(client, app_module, sample_questions):
    """D-02 选择题不应出现在判断题的错题集里"""
    c = sample_questions["choice"]
    with app_module.app.app_context():
        jq = Question.query.filter_by(quiz_set_id=c["quiz_set_id"], type="judge").first()
    if not jq:
        pytest.skip("该题库没有判断题，无法验证题型隔离")

    client.post("/api/check", json={"question_id": c["id"], "user_answer": _wrong_letter(c)})

    judge_wrongs = _wrong_question_ids(app_module, c["quiz_set_id"], "judge")
    assert c["id"] not in judge_wrongs, "选择题不应出现在判断题错题集里"


def test_D03_同一题多次答错只算一道错题(client, app_module, sample_questions):
    """D-03 同一题连续答错 2 次，错题集里只应有 1 条"""
    q = sample_questions["choice"]
    for _ in range(2):
        client.post("/api/check", json={"question_id": q["id"], "user_answer": _wrong_letter(q)})

    ids = _wrong_question_ids(app_module, q["quiz_set_id"], "choice")
    assert ids.count(q["id"]) == 1, "同一题重复答错应去重，只保留一条"


def test_D04_错题答对后从错题集移除(client, app_module, sample_questions):
    """D-04 【关键】错题答对一次后，应从错题集移除"""
    q = sample_questions["choice"]
    client.post("/api/check", json={"question_id": q["id"], "user_answer": _wrong_letter(q)})
    assert q["id"] in _wrong_question_ids(app_module, q["quiz_set_id"], "choice")

    client.post("/api/check", json={"question_id": q["id"], "user_answer": q["answer"]})
    assert q["id"] not in _wrong_question_ids(app_module, q["quiz_set_id"], "choice"), \
        "答对后该题应从上错题集移除"


def test_D05_有错题时可进入错题练习(client, app_module, sample_questions):
    """D-05 有错题时应能进入错题练习页"""
    q = sample_questions["choice"]
    client.post("/api/check", json={"question_id": q["id"], "user_answer": _wrong_letter(q)})
    r = client.get("/quiz/%d/wrongbook/choice/practice" % q["quiz_set_id"])
    assert r.status_code == 200


def test_D06_无错题时进入错题练习会跳转(client, app_module):
    """D-06 没有错题时应提示并跳回错题本，而不是报错"""
    with app_module.app.app_context():
        tmp = QuizSet(name="__pytest_空题库__")
        db.session.add(tmp)
        db.session.commit()
        tid = tmp.id

    r = client.get("/quiz/%d/wrongbook/choice/practice" % tid)
    assert r.status_code == 302, "没有错题时应重定向"
    assert client.get("/quiz/%d/wrongbook" % tid).status_code == 200


def test_D07_清空某题型错题(client, app_module, sample_questions):
    """D-07 清空某题型错题后，该题型错题应清空"""
    q = sample_questions["choice"]
    client.post("/api/check", json={"question_id": q["id"], "user_answer": _wrong_letter(q)})
    assert q["id"] in _wrong_question_ids(app_module, q["quiz_set_id"], "choice")

    r = client.post("/quiz/%d/wrongbook/choice/clear" % q["quiz_set_id"])
    assert r.status_code == 302
    assert _wrong_question_ids(app_module, q["quiz_set_id"], "choice") == [], \
        "清空后该题型不应再有错题"


def test_D08_清空后错题本页面仍可正常打开(client, sample_questions):
    """D-08 清空全部错题后页面不应报错"""
    q = sample_questions["choice"]
    for t in ("choice", "judge", "multi", "fill", "short_answer"):
        client.post("/quiz/%d/wrongbook/%s/clear" % (q["quiz_set_id"], t))
    assert client.get("/quiz/%d/wrongbook" % q["quiz_set_id"]).status_code == 200
