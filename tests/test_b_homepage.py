# -*- coding: utf-8 -*-
"""B 组 · 首页与题库管理"""
from models import QuizSet, db


def test_B01_首页正常返回并列出题库(client):
    """B-01 首页应返回 200，并渲染题库列表"""
    r = client.get("/")
    assert r.status_code == 200
    assert "我的题库" in r.get_data(as_text=True)


def test_B02_首页题库卡片数与数据库一致(client, app_module):
    """B-01 首页展示的题库数量应与数据库一致"""
    with app_module.app.app_context():
        expect = QuizSet.query.count()
    html = client.get("/").get_data(as_text=True)
    assert expect > 0, "数据库里应该至少有一个题库"
    assert html.count("开始刷题") == expect, "首页题库卡片数(%d)与数据库(%d)不一致" % (
        html.count("开始刷题"), expect)


def test_B03_访问题库后写入last_visited(client, app_module):
    """B-03 访问题库详情后应更新 last_visited（用于首页置顶排序）"""
    with app_module.app.app_context():
        qs = QuizSet.query.order_by(QuizSet.id).first()
        qid = qs.id
        qs.last_visited = None
        db.session.commit()

    assert client.get("/quiz/%d" % qid).status_code == 200

    with app_module.app.app_context():
        qs = db.session.get(QuizSet, qid)
        assert qs.last_visited is not None, "访问题库后 last_visited 应被写入"


def test_B06_访问不存在的题库返回404(client):
    """B-06 不存在的题库 id 应返回 404"""
    assert client.get("/quiz/999999").status_code == 404


def test_B05_删除不存在的题库返回404(client):
    """B-05 删除不存在的题库应返回 404"""
    assert client.post("/quiz/999999/delete").status_code == 404


def test_B04_删除题库级联删除题目(client, app_module):
    """B-04 / B-07 删除题库后，其题目应一并删除（此处用新建的临时题库验证，不动真实数据）"""
    from models import Question

    with app_module.app.app_context():
        tmp = QuizSet(name="__pytest_临时题库__")
        db.session.add(tmp)
        db.session.flush()
        tmp_id = tmp.id
        db.session.add(Question(quiz_set_id=tmp_id, chapter="测试", type="choice",
                                stem="临时题目", options="[]", answer="A", explanation=""))
        db.session.commit()
        assert Question.query.filter_by(quiz_set_id=tmp_id).count() == 1

    r = client.post("/quiz/%d/delete" % tmp_id)
    assert r.status_code == 302, "删除后应重定向回首页"

    with app_module.app.app_context():
        assert db.session.get(QuizSet, tmp_id) is None, "题库应被删除"
        assert Question.query.filter_by(quiz_set_id=tmp_id).count() == 0, "题目应被级联删除"
