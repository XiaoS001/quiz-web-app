# -*- coding: utf-8 -*-
"""Flask 主应用"""
import os
import json
import random
import csv
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from sqlalchemy import inspect, text

from models import db, QuizSet, Question, Record, Favorite
from parser import parse_txt, check_answer, normalize_answer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'quiz-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'quiz.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

db.init_app(app)

# Jinja 过滤器
app.jinja_env.filters['from_json'] = lambda s: json.loads(s) if s else []

TYPE_CN = {
    'choice': '选择题',
    'judge': '判断题',
    'multi': '多选题',
    'fill': '填空题',
    'short_answer': '简答题',
}


# ========== 首页：题库列表 ==========

@app.route('/')
def index():
    # 最近访问的题库排前面（last_visited 不为空的按时间倒序），其余按创建时间倒序
    quiz_sets = QuizSet.query.order_by(
        QuizSet.last_visited.is_(None),
        QuizSet.last_visited.desc(),
        QuizSet.created_at.desc()
    ).all()
    return render_template('index.html', quiz_sets=quiz_sets, type_cn=TYPE_CN)


# ========== 下载格式规范 ==========

@app.route('/format-template')
def format_template():
    """下载题库格式规范 TXT，方便用户拿给 AI 按格式生成题库"""
    content = """# 题库名称：示例题库名称（此处替换为你的题库名）

## 章节：第一章 概述

### [选择] 这是一道单选题的题干文本？
A. 选项A的内容
B. 选项B的内容
C. 选项C的内容
D. 选项D的内容
答案：B

### [判断] 这是一道判断题的题干文本，判断对错。
答案：对

### [多选] 这是一道多选题的题干文本，以下哪些是正确的？（多选）
A. 选项A的内容
B. 选项B的内容
C. 选项C的内容
D. 选项D的内容
答案：ABC

### [填空] 这是一道填空题，空格处应填入____。
答案：正确答案

### [简答] 这是一道简答题的题干文本，请简述其原理。
答案：简答题的参考答案，支持多行和多段落。简答题采用关键词匹配判分，只要用户回答命中关键信息即为正确。

## 章节：第二章 进阶

### [选择] 另一道单选题？
A. 选项A
B. 选项B
C. 选项C
D. 选项D
答案：A

"""

    return Response(
        content,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=format-template.txt'}
    )


# ========== 上传题库 ==========

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        flash('请选择至少一个TXT文件', 'error')
        return redirect(url_for('index'))

    success_count = 0
    for f in files:
        if not f.filename.endswith('.txt'):
            flash(f'{f.filename} 不是TXT文件，已跳过', 'error')
            continue

        content = f.read().decode('utf-8')
        quiz_name, questions = parse_txt(content)

        if not questions:
            flash(f'{f.filename} 未解析到题目，请检查格式', 'error')
            continue

        # 如果题库名为空，用文件名
        if not quiz_name or quiz_name == '未命名题库':
            quiz_name = os.path.splitext(f.filename)[0]

        quiz_set = QuizSet(name=quiz_name)
        db.session.add(quiz_set)
        db.session.flush()  # 获取id

        for q in questions:
            question = Question(
                quiz_set_id=quiz_set.id,
                chapter=q['chapter'],
                type=q['type'],
                stem=q['stem'],
                options=q['options'],
                answer=q['answer'],
                explanation=q['explanation'],
            )
            db.session.add(question)

        success_count += 1

    db.session.commit()

    if success_count:
        flash(f'成功导入 {success_count} 个题库', 'success')

    return redirect(url_for('index'))


# ========== 删除题库 ==========

@app.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
def delete_quiz(quiz_id):
    quiz_set = QuizSet.query.get_or_404(quiz_id)
    db.session.delete(quiz_set)
    db.session.commit()
    flash(f'已删除题库：{quiz_set.name}', 'success')
    return redirect(url_for('index'))


# ========== 题型选择菜单 ==========

@app.route('/quiz/<int:quiz_id>')
def practice_menu(quiz_id):
    """题型选择菜单"""
    quiz_set = QuizSet.query.get_or_404(quiz_id)
    # 更新最近访问时间（用于首页置顶排序）
    quiz_set.last_visited = datetime.now()
    db.session.commit()
    return render_template('practice_menu.html', quiz_set=quiz_set, type_cn=TYPE_CN)


# ========== 刷题页 ==========

@app.route('/quiz/<int:quiz_id>/practice/<q_type>')
def practice(quiz_id, q_type):
    """刷题页：从某题库刷某题型"""
    if q_type not in TYPE_CN:
        flash('题型不存在', 'error')
        return redirect(url_for('index'))

    quiz_set = QuizSet.query.get_or_404(quiz_id)

    # 取该题型所有题目，随机排序
    questions = Question.query.filter_by(
        quiz_set_id=quiz_id, type=q_type
    ).all()
    random.shuffle(questions)

    # 序列化题目数据（打乱选项），带安全清洗防止 tojson 崩溃
    q_list = []
    for q in questions:
        try:
            item = {
                'id': q.id,
                'stem': str(q.stem) if q.stem else '',
                'type': str(q.type),
                'chapter': str(q.chapter) if q.chapter else '',
            }
            if q.type in ('choice', 'multi'):
                try:
                    options = json.loads(q.options) if q.options else []
                    if not isinstance(options, list):
                        options = []
                except (json.JSONDecodeError, TypeError, ValueError):
                    options = []
                # 打乱选项顺序
                shuffled = options[:]
                item['options'] = shuffled
            q_list.append(item)
        except Exception as e:
            # 单题序列化失败则跳过，不阻断整个页面
            app.logger.warning(f'题目 id={q.id} 序列化跳过: {e}')
            continue

    # 查询当前已收藏的题目ID集合
    fav_ids = [f.question_id for f in Favorite.query.filter_by(quiz_set_id=quiz_id).all()]

    return render_template('practice.html',
                           quiz_set=quiz_set,
                           q_type=q_type,
                           q_type_cn=TYPE_CN[q_type],
                           questions=q_list,
                           total=len(q_list),
                           favorite_ids=fav_ids)


# ========== 提交答案（AJAX） ==========

@app.route('/api/check', methods=['POST'])
def api_check():
    """提交单题答案，返回判分结果"""
    data = request.get_json()
    question_id = data.get('question_id')
    user_answer = data.get('user_answer', '')

    question = Question.query.get_or_404(question_id)

    is_correct, normalized = check_answer(
        question.type, user_answer, question.answer, question.options
    )

    # 保存记录
    record = Record(
        question_id=question.id,
        quiz_set_id=question.quiz_set_id,
        type=question.type,
        user_answer=normalized,
        is_correct=is_correct,
    )
    db.session.add(record)
    db.session.commit()

    # 返回正确答案内容
    correct_display = question.answer
    if question.type in ('choice', 'multi'):
        try:
            options = json.loads(question.options)
            if question.type == 'choice':
                for opt in options:
                    if opt['letter'] == question.answer:
                        correct_display = f"{opt['letter']}. {opt['text']}"
                        break
            else:
                # 多选
                parts = []
                for letter in question.answer:
                    for opt in options:
                        if opt['letter'] == letter:
                            parts.append(f"{opt['letter']}. {opt['text']}")
                            break
                correct_display = '\n'.join(parts)
        except Exception:
            pass

    return jsonify({
        'is_correct': is_correct,
        'correct_answer': correct_display,
        'user_answer': normalized,
    })


# ========== 错题本 ==========

@app.route('/quiz/<int:quiz_id>/wrongbook')
def wrongbook(quiz_id):
    """错题本：按题型分tab展示"""
    quiz_set = QuizSet.query.get_or_404(quiz_id)

    # 各题型错题（取最新记录为错的题目）
    wrong_by_type = {}
    for q_type, cn in TYPE_CN.items():
        # 找出该题型所有错题记录对应的question_id
        wrong_records = Record.query.filter_by(
            quiz_set_id=quiz_id, type=q_type, is_correct=False
        ).all()

        # 去重：同一个题目只取最新一条记录
        seen = {}
        for r in wrong_records:
            if r.question_id not in seen or r.created_at > seen[r.question_id].created_at:
                seen[r.question_id] = r

        # 但如果后来答对了，就不算错题了
        wrong_list = []
        for qid, latest_wrong in seen.items():
            # 检查该题目是否有更新的正确记录
            newer_correct = Record.query.filter_by(
                question_id=qid, is_correct=True
            ).filter(Record.created_at > latest_wrong.created_at).first()

            if not newer_correct:
                q = Question.query.get(qid)
                if q:
                    wrong_list.append({
                        'question': q,
                        'wrong_answer': latest_wrong.user_answer,
                        'wrong_time': latest_wrong.created_at,
                    })

        wrong_by_type[q_type] = wrong_list

    return render_template('wrongbook.html',
                           quiz_set=quiz_set,
                           wrong_by_type=wrong_by_type,
                           type_cn=TYPE_CN)


# ========== 错题练习 ==========

@app.route('/quiz/<int:quiz_id>/wrongbook/<q_type>/practice')
def wrong_practice(quiz_id, q_type):
    """错题练习：针对某题型的错题进行刷题"""
    if q_type not in TYPE_CN:
        flash('题型不存在', 'error')
        return redirect(url_for('index'))

    quiz_set = QuizSet.query.get_or_404(quiz_id)

    # 复用错题本查询逻辑：找出该题型当前仍是错题的题目
    wrong_records = Record.query.filter_by(
        quiz_set_id=quiz_id, type=q_type, is_correct=False
    ).all()

    seen = {}
    for r in wrong_records:
        if r.question_id not in seen or r.created_at > seen[r.question_id].created_at:
            seen[r.question_id] = r

    # 排除已经答对的题目
    wrong_questions = []
    for qid, latest_wrong in seen.items():
        newer_correct = Record.query.filter_by(
            question_id=qid, is_correct=True
        ).filter(Record.created_at > latest_wrong.created_at).first()
        if not newer_correct:
            q = Question.query.get(qid)
            if q:
                wrong_questions.append(q)

    if not wrong_questions:
        flash(f'没有{TYPE_CN[q_type]}错题，无需练习', 'info')
        return redirect(url_for('wrongbook', quiz_id=quiz_id))

    # 随机打乱
    random.shuffle(wrong_questions)

    # 序列化（与普通练习相同，打乱选项），带安全清洗
    q_list = []
    for q in wrong_questions:
        try:
            item = {
                'id': q.id,
                'stem': str(q.stem) if q.stem else '',
                'type': str(q.type),
                'chapter': str(q.chapter) if q.chapter else '',
            }
            if q.type in ('choice', 'multi'):
                try:
                    options = json.loads(q.options) if q.options else []
                    if not isinstance(options, list):
                        options = []
                except (json.JSONDecodeError, TypeError, ValueError):
                    options = []
                shuffled = options[:]
                item['options'] = shuffled
            q_list.append(item)
        except Exception as e:
            app.logger.warning(f'错题 id={q.id} 序列化跳过: {e}')
            continue

    favorite_ids = [f.question_id for f in Favorite.query.filter_by(quiz_set_id=quiz_id).all()]

    return render_template('practice.html',
                           quiz_set=quiz_set,
                           q_type=q_type,
                           q_type_cn=TYPE_CN[q_type],
                           questions=q_list,
                           total=len(q_list),
                           is_wrong_practice=True,
                           favorite_ids=favorite_ids)


# ========== 清空错题记录 ==========

@app.route('/quiz/<int:quiz_id>/wrongbook/<q_type>/clear', methods=['POST'])
def clear_wrong(quiz_id, q_type):
    """清空某题型的错题记录"""
    Record.query.filter_by(
        quiz_set_id=quiz_id, type=q_type, is_correct=False
    ).delete()
    db.session.commit()
    flash(f'已清空{TYPE_CN.get(q_type, "")}错题记录', 'success')
    return redirect(url_for('wrongbook', quiz_id=quiz_id))


# ========== 统计 ==========

@app.route('/quiz/<int:quiz_id>/stats')
def stats(quiz_id):
    """统计页"""
    quiz_set = QuizSet.query.get_or_404(quiz_id)
    stats = quiz_set.stats()
    accuracy = quiz_set.accuracy()
    wrong = quiz_set.wrong_counts()

    # 最近10次答题
    recent = Record.query.filter_by(quiz_set_id=quiz_id).order_by(
        Record.created_at.desc()
    ).limit(10).all()

    return render_template('stats.html',
                           quiz_set=quiz_set,
                           stats=stats,
                           accuracy=accuracy,
                           wrong=wrong,
                           recent=recent,
                           type_cn=TYPE_CN)


# ========== 收藏功能 ==========

@app.route('/api/favorite', methods=['POST'])
def api_favorite():
    """收藏/取消收藏题目（AJAX）"""
    data = request.get_json()
    question_id = data.get('question_id')
    if not question_id:
        return jsonify({'error': '缺少题目ID'}), 400

    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': '题目不存在'}), 404

    fav = Favorite.query.filter_by(question_id=question_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({'favorited': False})
    else:
        fav = Favorite(question_id=question_id, quiz_set_id=question.quiz_set_id)
        db.session.add(fav)
        db.session.commit()
        return jsonify({'favorited': True})


@app.route('/favorites')
def favorites():
    """我的收藏列表"""
    favs = Favorite.query.order_by(Favorite.created_at.desc()).all()
    # 按题库分组
    fav_by_quiz = {}
    for fav in favs:
        q = Question.query.get(fav.question_id)
        if q:
            if fav.quiz_set_id not in fav_by_quiz:
                quiz = QuizSet.query.get(fav.quiz_set_id)
                fav_by_quiz[fav.quiz_set_id] = {
                    'quiz_set': quiz,
                    'items': []
                }
            fav_by_quiz[fav.quiz_set_id]['items'].append({
                'fav': fav,
                'question': q,
            })

    return render_template('favorites.html',
                           fav_by_quiz=fav_by_quiz,
                           type_cn=TYPE_CN)


@app.route('/favorites/<int:quiz_id>/practice')
def favorite_practice(quiz_id):
    """收藏题目练习：针对某题库的收藏题目刷题"""
    quiz_set = QuizSet.query.get_or_404(quiz_id)
    favs = Favorite.query.filter_by(quiz_set_id=quiz_id).all()
    fav_ids = [f.question_id for f in favs]
    questions = [Question.query.get(f.question_id) for f in favs if Question.query.get(f.question_id)]

    if not questions:
        flash('没有收藏题目，无需练习', 'info')
        return redirect(url_for('favorites'))

    random.shuffle(questions)

    q_list = []
    for q in questions:
        try:
            item = {
                'id': q.id,
                'stem': str(q.stem) if q.stem else '',
                'type': str(q.type),
                'chapter': str(q.chapter) if q.chapter else '',
            }
            if q.type in ('choice', 'multi'):
                try:
                    options = json.loads(q.options) if q.options else []
                    if not isinstance(options, list):
                        options = []
                except (json.JSONDecodeError, TypeError, ValueError):
                    options = []
                shuffled = options[:]
                item['options'] = shuffled
            q_list.append(item)
        except Exception as e:
            app.logger.warning(f'收藏题 id={q.id} 序列化跳过: {e}')
            continue

    return render_template('practice.html',
                           quiz_set=quiz_set,
                           q_type='favorite',
                           q_type_cn='收藏题练习',
                           questions=q_list,
                           total=len(q_list),
                           is_wrong_practice=True,
                           favorite_ids=fav_ids)


# ========== 题目搜索 ==========

@app.route('/search')
def search():
    """题目搜索"""
    keyword = request.args.get('q', '').strip()
    quiz_id = request.args.get('quiz_id', '', type=str)

    results = []
    if keyword:
        query = Question.query.filter(
            Question.stem.contains(keyword)
        )
        if quiz_id:
            query = query.filter_by(quiz_set_id=quiz_id)
        results = query.limit(200).all()

    # 获取所有题库供选择范围
    quiz_sets = QuizSet.query.order_by(QuizSet.created_at.desc()).all()

    return render_template('search.html',
                           keyword=keyword,
                           results=results,
                           quiz_sets=quiz_sets,
                           selected_quiz=quiz_id,
                           type_cn=TYPE_CN)


# ========== 导出功能 ==========

@app.route('/quiz/<int:quiz_id>/wrongbook/export')
def export_wrongbook(quiz_id):
    """导出错题为TXT"""
    quiz_set = QuizSet.query.get_or_404(quiz_id)

    # 复用错题查询逻辑
    wrong_records = Record.query.filter_by(
        quiz_set_id=quiz_id, is_correct=False
    ).all()

    seen = {}
    for r in wrong_records:
        if r.question_id not in seen or r.created_at > seen[r.question_id].created_at:
            seen[r.question_id] = r

    wrong_questions = []
    for qid, latest_wrong in seen.items():
        newer_correct = Record.query.filter_by(
            question_id=qid, is_correct=True
        ).filter(Record.created_at > latest_wrong.created_at).first()
        if not newer_correct:
            q = Question.query.get(qid)
            if q:
                wrong_questions.append((q, latest_wrong))

    # 生成TXT
    lines = [f'# 错题本导出 - {quiz_set.name}']
    lines.append(f'# 导出时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append(f'# 共 {len(wrong_questions)} 道错题')
    lines.append('')

    type_map = {'choice': '选择', 'judge': '判断', 'multi': '多选', 'fill': '填空'}
    for i, (q, record) in enumerate(wrong_questions, 1):
        lines.append(f'### [{type_map.get(q.type, q.type)}] {q.stem}')
        if q.type in ('choice', 'multi'):
            try:
                opts = json.loads(q.options) if q.options else []
                for opt in opts:
                    lines.append(f"{opt['letter']}. {opt['text']}")
            except Exception:
                pass
        lines.append(f'你的答案：{record.user_answer}')
        lines.append(f'正确答案：{q.answer}')
        lines.append('')

    content = '\n'.join(lines)
    filename = f'错题本_{quiz_set.name}_{datetime.now().strftime("%Y%m%d")}.txt'

    return Response(
        content,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@app.route('/quiz/<int:quiz_id>/records/export')
def export_records(quiz_id):
    """导出答题记录为CSV"""
    quiz_set = QuizSet.query.get_or_404(quiz_id)
    records = Record.query.filter_by(quiz_set_id=quiz_id).order_by(
        Record.created_at.desc()
    ).all()

    output = io.StringIO()
    output.write('\ufeff')  # BOM，让Excel正确识别UTF-8
    writer = csv.writer(output)
    writer.writerow(['序号', '题型', '题干', '你的答案', '正确答案', '是否正确', '答题时间'])

    for i, r in enumerate(records, 1):
        q = Question.query.get(r.question_id)
        stem = q.stem[:80] + '...' if q and q.stem and len(q.stem) > 80 else (q.stem if q else '')
        writer.writerow([
            i,
            TYPE_CN.get(r.type, r.type),
            stem,
            r.user_answer,
            q.answer if q else '',
            '正确' if r.is_correct else '错误',
            r.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    content = output.getvalue()
    filename = f'答题记录_{quiz_set.name}_{datetime.now().strftime("%Y%m%d")}.csv'

    return Response(
        content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


# ========== 初始化 ==========

with app.app_context():
    db.create_all()
    # 自动迁移：为旧数据库补充 last_visited 字段
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns('quiz_set')]
    if 'last_visited' not in columns:
        db.session.execute(text('ALTER TABLE quiz_set ADD COLUMN last_visited DATETIME'))
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
