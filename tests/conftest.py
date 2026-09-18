# -*- coding: utf-8 -*-
"""
pytest 公共装置（fixture）

设计要点：
1. 【数据保护】整个测试会话开始前备份 quiz.db，结束后自动还原 —— 测试绝不污染真实数据
2. 【不启服务】用 Flask 自带的 test_client() 走进程内请求，不需要另外开着 app.py
3. 【题目样本】从真实数据库里取各题型各一道，测试用真数据而不是造假的假数据
"""
import json
import os
import shutil
import sys

import pytest

# tests/ 的上一级 = 项目根目录
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJ not in sys.path:
    sys.path.insert(0, PROJ)

DB_PATH = os.path.join(PROJ, "quiz.db")
DB_BAK = os.path.join(PROJ, "quiz.db.pytest-bak")


@pytest.fixture(scope="session", autouse=True)
def protect_database():
    """测试前备份、测试后还原。这是测试的基本纪律：不污染生产数据。"""
    if not os.path.exists(DB_PATH):
        pytest.exit("找不到 quiz.db，请确认项目目录结构是否正确")
    shutil.copy2(DB_PATH, DB_BAK)
    try:
        yield
    finally:
        if os.path.exists(DB_BAK):
            shutil.copy2(DB_BAK, DB_PATH)
            os.remove(DB_BAK)


@pytest.fixture(scope="session")
def app_module():
    """导入 Flask 应用（整个会话只导入一次）"""
    import app as m
    m.app.config["TESTING"] = True
    return m


@pytest.fixture()
def client(app_module):
    """Flask 测试客户端"""
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture(scope="session")
def sample_questions(app_module):
    """从真实数据库取各题型各一道题做样本"""
    from models import Question
    out = {}
    with app_module.app.app_context():
        for t in ("choice", "judge", "multi", "fill", "short_answer"):
            q = Question.query.filter_by(type=t).first()
            if q:
                out[t] = {
                    "id": q.id,
                    "answer": q.answer,
                    "options": json.loads(q.options) if q.options else [],
                    "quiz_set_id": q.quiz_set_id,
                }
    return out
