# -*- coding: utf-8 -*-
"""重建 quiz.db 数据库：从标准题库 TXT 文件重新导入所有题目"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import app, db
from models import QuizSet, Question
from parser import parse_txt

QUIZ_DIR = os.path.join(BASE_DIR, '标准题库')

def rebuild():
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        total_questions = 0
        for filename in sorted(os.listdir(QUIZ_DIR)):
            if not filename.endswith('.txt'):
                continue
            
            filepath = os.path.join(QUIZ_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            quiz_name, questions = parse_txt(content)
            if not questions:
                print(f"  ⚠ {filename}: 无题目")
                continue
            
            qs = QuizSet(name=quiz_name)
            db.session.add(qs)
            db.session.flush()
            
            for q in questions:
                question = Question(
                    quiz_set_id=qs.id,
                    chapter=q.get('chapter', ''),
                    type=q['type'],
                    stem=q['stem'],
                    options=q['options'],
                    answer=q['answer'],
                    explanation=q.get('explanation', '')
                )
                db.session.add(question)
                total_questions += 1
            
            print(f"  ✓ {filename} ({quiz_name}): {len(questions)} 题")
        
        db.session.commit()
        print(f"\n重建完成！总题目数: {total_questions}")

if __name__ == '__main__':
    rebuild()
