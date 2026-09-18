# -*- coding: utf-8 -*-
"""从提取的Python题库原始文本中，解析并格式化为标准题库文件"""
import re

def clean_html_entities(text):
    """清理HTML实体和特殊字符"""
    text = text.replace('&gt;', '>')
    text = text.replace('&lt;', '<')
    text = text.replace('&amp;', '&')
    text = text.replace('&nbsp;', ' ')
    text = text.replace('\xa0', ' ')
    return text.strip()

def parse_choice_questions(lines, start, end):
    """解析单选题"""
    questions = []
    i = start
    while i < end:
        line = clean_html_entities(lines[i])
        # 找题号开头的行
        if re.match(r'^\d+、', line) or re.match(r'^\d+\.', line):
            stem = line
            options = []
            answer = ''
            explanation = ''
            i += 1
            # 收集选项和答案
            while i < end:
                l = clean_html_entities(lines[i])
                if re.match(r'^[A-D]、', l):
                    # 选项开头行
                    opt_label = l[0]
                    opt_text = l[2:].strip()
                    # 选项内容可能跨多行
                    i += 1
                    while i < end:
                        next_l = clean_html_entities(lines[i])
                        if re.match(r'^[A-D]、', next_l) or next_l.startswith('正确答案') or re.match(r'^\d+、', next_l) or next_l.startswith('解析'):
                            break
                        opt_text += ' ' + next_l
                        i += 1
                    options.append(f"{opt_label}、{opt_text}")
                    continue
                elif l.startswith('正确答案'):
                    i += 1
                    if i < end:
                        answer = clean_html_entities(lines[i]).strip()
                        # 答案可能只有字母
                        answer = re.sub(r'[、，。]', '', answer)
                        i += 1
                    continue
                elif l.startswith('解析'):
                    explanation = l[2:].strip() if len(l) > 2 else ''
                    i += 1
                    while i < end:
                        next_l = clean_html_entities(lines[i])
                        if re.match(r'^\d+、', next_l) or next_l.startswith('正确答案') or next_l.startswith('解析') or re.match(r'^[A-D]、', next_l):
                            break
                        explanation += ' ' + next_l
                        i += 1
                    continue
                elif re.match(r'^\d+、', l):
                    break
                else:
                    # 可能是stem的续行
                    if l and not l.startswith('正确答案'):
                        stem += ' ' + l
                    i += 1
                    continue
            
            if stem and answer:
                questions.append({
                    'type': 'choice',
                    'stem': stem,
                    'options': options,
                    'answer': answer,
                    'explanation': explanation
                })
        else:
            i += 1
    return questions

def parse_judge_questions(lines, start, end):
    """解析判断题"""
    questions = []
    i = start
    while i < end:
        line = clean_html_entities(lines[i])
        if re.match(r'^\d+、', line):
            stem = line
            answer = ''
            explanation = ''
            i += 1
            while i < end:
                l = clean_html_entities(lines[i])
                if l.startswith('正确答案'):
                    i += 1
                    if i < end:
                        answer = clean_html_entities(lines[i]).strip()
                        if answer in ['正确', '对', 'True', 'true']:
                            answer = '正确'
                        elif answer in ['错误', '错', 'False', 'false']:
                            answer = '错误'
                        i += 1
                    continue
                elif l.startswith('解析'):
                    explanation = l[2:].strip() if len(l) > 2 else ''
                    i += 1
                    while i < end:
                        next_l = clean_html_entities(lines[i])
                        if re.match(r'^\d+、', next_l) or next_l.startswith('正确答案') or next_l.startswith('解析'):
                            break
                        explanation += ' ' + next_l
                        i += 1
                    continue
                elif re.match(r'^\d+、', l):
                    break
                else:
                    if l and not l.startswith('正确答案') and not l.startswith('解析'):
                        stem += ' ' + l
                    i += 1
                    continue
            
            if stem and answer:
                # 清理stem中的空格碎片
                stem = re.sub(r'\s+', ' ', stem).strip()
                questions.append({
                    'type': 'judge',
                    'stem': stem,
                    'options': [],
                    'answer': answer,
                    'explanation': explanation
                })
        else:
            i += 1
    return questions

def parse_fill_questions(lines, start, end):
    """解析填空题"""
    questions = []
    i = start
    while i < end:
        line = clean_html_entities(lines[i])
        if re.match(r'^\d+、', line):
            stem = line
            blanks = []
            explanation = ''
            i += 1
            while i < end:
                l = clean_html_entities(lines[i])
                if l.startswith('正确答案'):
                    i += 1
                    # 读取所有空
                    while i < end:
                        next_l = clean_html_entities(lines[i])
                        if next_l.startswith('第') and '空' in next_l:
                            i += 1
                            if i < end:
                                blank_answer = clean_html_entities(lines[i]).strip()
                                blanks.append(blank_answer)
                                i += 1
                        elif next_l.startswith('解析'):
                            break
                        elif re.match(r'^\d+、', next_l):
                            break
                        else:
                            i += 1
                    continue
                elif l.startswith('解析'):
                    explanation = l[2:].strip() if len(l) > 2 else ''
                    i += 1
                    while i < end:
                        next_l = clean_html_entities(lines[i])
                        if re.match(r'^\d+、', next_l) or next_l.startswith('正确答案') or next_l.startswith('解析'):
                            break
                        explanation += ' ' + next_l
                        i += 1
                    continue
                elif re.match(r'^\d+、', l):
                    break
                else:
                    if l and not l.startswith('正确答案') and not l.startswith('解析') and not l.startswith('第'):
                        stem += ' ' + l
                    i += 1
                    continue
            
            if stem and blanks:
                stem = re.sub(r'\s+', ' ', stem).strip()
                # 用____替换空位标记, 并在stem末尾标注答案
                answer_str = '; '.join(blanks)
                questions.append({
                    'type': 'fill',
                    'stem': stem,
                    'options': [],
                    'answer': answer_str,
                    'explanation': explanation
                })
        else:
            i += 1
    return questions

def parse_short_answer_questions(lines, start, end):
    """解析简答题"""
    questions = []
    i = start
    while i < end:
        line = clean_html_entities(lines[i])
        if re.match(r'^\d+、', line):
            stem = line
            answer = ''
            i += 1
            while i < end:
                l = clean_html_entities(lines[i])
                if l.startswith('正确答案'):
                    i += 1
                    # 收集答案（可能多行）
                    answer_lines = []
                    while i < end:
                        next_l = clean_html_entities(lines[i])
                        if re.match(r'^\d+、', next_l) or next_l.startswith('二、') or next_l.startswith('三、'):
                            break
                        answer_lines.append(next_l)
                        i += 1
                    answer = ' '.join(answer_lines).strip()
                    break
                elif re.match(r'^\d+、', l):
                    break
                else:
                    if l and not l.startswith('正确答案'):
                        stem += ' ' + l
                    i += 1
                    continue
            
            if stem and answer:
                stem = re.sub(r'\s+', ' ', stem).strip()
                answer = re.sub(r'\s+', ' ', answer).strip()
                questions.append({
                    'type': 'short_answer',
                    'stem': stem,
                    'options': [],
                    'answer': answer,
                    'explanation': ''
                })
        else:
            i += 1
    return questions

def write_standard_file(filename, quiz_name, questions):
    """写入标准题库格式文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# 题库名称: {quiz_name}\n\n")
        for q in questions:
            type_cn = {'choice': '选择', 'judge': '判断', 'multi': '多选', 'fill': '填空', 'short_answer': '简答'}
            f.write(f"### [{type_cn[q['type']]}]\n")
            f.write(f"{q['stem']}\n")
            if q['options']:
                for opt in q['options']:
                    f.write(f"{opt}\n")
            f.write(f"答案: {q['answer']}\n")
            if q['explanation']:
                f.write(f"解析: {q['explanation']}\n")
            f.write("\n")
    return len(questions)

# Main processing
print("读取提取的文本文件...")

with open(r'C:/Users/Administrator/.workbuddy/binaries/python/workspace/python_rev1_utf8.txt', 'r', encoding='utf-8') as f:
    rev1_lines = f.read().split('\n')

with open(r'C:/Users/Administrator/.workbuddy/binaries/python/workspace/python_rev2_utf8.txt', 'r', encoding='utf-8') as f:
    rev2_lines = f.read().split('\n')

# 期末复习1 结构:
# 一、单选题 (line 2 to 2129)
# 二、填空题 (line 2130 to 2708)
# 三、判断题 (line 2709 to ~3213)
# 五、程序填空题 (line 3214 to 3234) - 只有1题

# 期末复习2 结构:
# 一、简答题 (line 2 to 78)
# 二、程序设计题 (line 79 to 938) - 排除，相当于论述题/编程题
# 三、程序填空题 (line 939 to 1605) - 17题

print("解析单选题...")
choice_qs = parse_choice_questions(rev1_lines, 2, 2129)
print(f"  单选题: {len(choice_qs)} 题")

print("解析判断题...")
judge_qs = parse_judge_questions(rev1_lines, 2709, 3213)
print(f"  判断题: {len(judge_qs)} 题")

print("解析填空题 (复习1)...")
fill1_qs = parse_fill_questions(rev1_lines, 2130, 2708)
print(f"  填空题1: {len(fill1_qs)} 题")

# 程序填空题(复习1只有1题, 复习2有17题)
print("解析程序填空题...")
prog_fill1_qs = parse_fill_questions(rev1_lines, 3214, 3234)
prog_fill2_qs = parse_fill_questions(rev2_lines, 939, 1605)
print(f"  程序填空题1: {len(prog_fill1_qs)} 题")
print(f"  程序填空题2: {len(prog_fill2_qs)} 题")

print("解析简答题...")
short_qs = parse_short_answer_questions(rev2_lines, 2, 78)
print(f"  简答题: {len(short_qs)} 题")

# 合并题型
# 1. 选择判断多选.txt: choice + judge (no multi in this dataset)
choice_judge_qs = choice_qs + judge_qs

# 2. 填空.txt: fill + 程序填空
fill_all_qs = fill1_qs + prog_fill1_qs + prog_fill2_qs

# 3. 简答题.txt: short_answer
short_all_qs = short_qs

print(f"\n总计统计:")
print(f"  选择判断多选: {len(choice_judge_qs)} 题 (选择{len(choice_qs)} + 判断{len(judge_qs)})")
print(f"  填空: {len(fill_all_qs)} 题 (填空{len(fill1_qs)} + 程序填空{len(prog_fill1_qs)+len(prog_fill2_qs)})")
print(f"  简答: {len(short_all_qs)} 题")

# 写入标准题库文件
base_dir = r'D:/WorkXM/6a17/刷题/标准题库'

n1 = write_standard_file(
    f'{base_dir}/Python期末选择判断多选.txt',
    'Python期末（选择判断多选）',
    choice_judge_qs
)
print(f"✓ Python期末选择判断多选.txt: {n1} 题")

n2 = write_standard_file(
    f'{base_dir}/Python期末填空.txt',
    'Python期末（填空）',
    fill_all_qs
)
print(f"✓ Python期末填空.txt: {n2} 题")

n3 = write_standard_file(
    f'{base_dir}/Python期末简答题.txt',
    'Python期末简答题',
    short_all_qs
)
print(f"✓ Python期末简答题.txt: {n3} 题")

print("\n完成!")
