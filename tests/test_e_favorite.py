# -*- coding: utf-8 -*-
"""E 组 · 收藏功能"""
from models import Favorite, Question, QuizSet, db


def test_E01_E02_收藏与取消收藏(client, sample_questions):
    """E-01 / E-02 点一次收藏，再点一次取消"""
    q = sample_questions["choice"]

    r1 = client.post("/api/favorite", json={"question_id": q["id"]})
    assert r1.status_code == 200
    assert r1.get_json()["favorited"] is True

    r2 = client.post("/api/favorite", json={"question_id": q["id"]})
    assert r2.status_code == 200
    assert r2.get_json()["favorited"] is False


def test_E03_收藏列表页正常返回(client):
    """E-03 收藏列表页应正常打开"""
    assert client.get("/favorites").status_code == 200


def test_E04_收藏后可进入收藏练习(client, sample_questions):
    """E-04 有收藏时应能进入收藏练习页"""
    q = sample_questions["choice"]
    client.post("/api/favorite", json={"question_id": q["id"]})
    r = client.get("/favorites/%d/practice" % q["quiz_set_id"])
    assert r.status_code == 200
    client.post("/api/favorite", json={"question_id": q["id"]})  # 复原


def test_E06_收藏不存在的题目返回404(client):
    """E-06 收藏不存在的题目应返回 404"""
    assert client.post("/api/favorite", json={"question_id": 999999}).status_code == 404


def test_E07_收藏缺参数返回400(client):
    """E-07 不传 question_id 应返回 400"""
    assert client.post("/api/favorite", json={}).status_code == 400


def test_E08_删除带收藏记录的题库(client, app_module):
    """E-08 【潜在缺陷探测】删除一个「有收藏记录」的题库

    背景：models.py 里 Favorite 只配了 backref，没有配 cascade='all, delete-orphan'，
    而 favorite.question_id / quiz_set_id 都是 nullable=False。
    因此删除题库时 ORM 可能尝试把外键置空 → 触发完整性错误。
    """
    with app_module.app.app_context():
        tmp = QuizSet(name="__pytest_带收藏题库__")
        db.session.add(tmp)
        db.session.flush()
        tid = tmp.id

        qq = Question(quiz_set_id=tid, chapter="测试", type="choice",
                      stem="临时题", options="[]", answer="A", explanation="")
        db.session.add(qq)
        db.session.flush()

        db.session.add(Favorite(question_id=qq.id, quiz_set_id=tid))
        db.session.commit()

    r = client.post("/quiz/%d/delete" % tid)
    assert r.status_code == 302, "删除带收藏的题库应正常完成，实际状态码 %d" % r.status_code

    with app_module.app.app_context():
        assert db.session.get(QuizSet, tid) is None, "题库应被删除"
        assert Favorite.query.filter_by(quiz_set_id=tid).count() == 0, "收藏记录应一并清理"
