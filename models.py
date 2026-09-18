# -*- coding: utf-8 -*-
"""数据模型定义"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class QuizSet(db.Model):
    """题库集"""
    __tablename__ = 'quiz_set'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_visited = db.Column(db.DateTime)  # 最近访问时间，用于首页置顶排序

    questions = db.relationship('Question', backref='quiz_set',
                                cascade='all, delete-orphan', lazy='dynamic')
    records = db.relationship('Record', backref='quiz_set',
                              cascade='all, delete-orphan', lazy='dynamic')

    def stats(self):
        """返回各题型数量统计"""
        from collections import Counter
        counts = Counter(q.type for q in self.questions)
        return {
            'choice': counts.get('choice', 0),
            'judge': counts.get('judge', 0),
            'multi': counts.get('multi', 0),
            'fill': counts.get('fill', 0),
            'short_answer': counts.get('short_answer', 0),
            'total': self.questions.count(),
        }

    def accuracy(self):
        """总正确率"""
        total = self.records.count()
        if total == 0:
            return 0
        correct = self.records.filter_by(is_correct=True).count()
        return round(correct / total * 100)

    def wrong_counts(self):
        """各题型错题数"""
        from collections import Counter
        wrongs = self.records.filter_by(is_correct=False).all()
        counts = Counter(r.type for r in wrongs)
        return {
            'choice': counts.get('choice', 0),
            'judge': counts.get('judge', 0),
            'multi': counts.get('multi', 0),
            'fill': counts.get('fill', 0),
            'short_answer': counts.get('short_answer', 0),
        }


class Question(db.Model):
    """题目"""
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    quiz_set_id = db.Column(db.Integer, db.ForeignKey('quiz_set.id'), nullable=False)
    chapter = db.Column(db.String(200), default='')
    type = db.Column(db.String(20), nullable=False)  # choice/judge/multi/fill
    stem = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, default='[]')  # JSON数组
    answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, default='')


class Record(db.Model):
    """答题记录"""
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    quiz_set_id = db.Column(db.Integer, db.ForeignKey('quiz_set.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    user_answer = db.Column(db.Text, default='')
    is_correct = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    question = db.relationship('Question', backref='records')


class Favorite(db.Model):
    """收藏题目"""
    __tablename__ = 'favorite'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    quiz_set_id = db.Column(db.Integer, db.ForeignKey('quiz_set.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    question = db.relationship('Question', backref='favorites')
    quiz_set = db.relationship('QuizSet', backref='favorites')
