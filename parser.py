# -*- coding: utf-8 -*-
"""TXT 题库解析器
格式规范：
  # 题库名称：xxx
  ## 章节：xxx
  ### [选择] 题干
  A. 选项A
  B. 选项B
  答案：B
"""
import re
import json

# 题型映射
TYPE_MAP = {
    '选择': 'choice',
    '判断': 'judge',
    '多选': 'multi',
    '填空': 'fill',
    '简答': 'short_answer',
}


def parse_txt(content):
    """
    解析TXT题库内容，返回 (题库名, [题目列表])
    每个题目: {chapter, type, stem, options, answer, explanation}
    """
    lines = content.split('\n')

    quiz_name = '未命名题库'
    current_chapter = ''
    questions = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 跳过空行
        if not line:
            i += 1
            continue

        # 题库名称 # 题库名称：xxx
        if line.startswith('#') and '题库名称' in line:
            m = re.match(r'#\s*题库名称[：:]\s*(.+)', line)
            if m:
                quiz_name = m.group(1).strip()
            i += 1
            continue

        # 章节 ## 章节：xxx
        if line.startswith('##') and not line.startswith('###'):
            m = re.match(r'##\s*章节[：:]\s*(.+)', line)
            if m:
                current_chapter = m.group(1).strip()
            i += 1
            continue

        # 题目开始 ### [题型] 题干
        if line.startswith('###'):
            m = re.match(r'###\s*\[(.+?)\]\s*(.*)', line)
            if not m:
                i += 1
                continue

            type_cn = m.group(1).strip()
            stem = m.group(2).strip()
            q_type = TYPE_MAP.get(type_cn)

            if not q_type:
                i += 1
                continue

            # 读取后续行：选项和答案
            options = []
            answer = ''
            i += 1

            while i < len(lines):
                sub = lines[i].strip()

                if not sub:
                    i += 1
                    # 空行后如果遇到新的 ### 或 ## 或 #，说明本题结束
                    if i < len(lines):
                        nxt = lines[i].strip()
                        if nxt.startswith('###') or nxt.startswith('##') or (nxt.startswith('#') and '题库名称' in nxt):
                            break
                    continue

                # 答案行
                if sub.startswith('答案'):
                    am = re.match(r'答案[：:]\s*(.+)', sub)
                    if am:
                        answer = am.group(1).strip()
                    i += 1
                    continue

                # 选项行 A. xxx 或 A、xxx
                opt_match = re.match(r'^([A-Da-d])[.、）)]\s*(.+)', sub)
                if opt_match:
                    letter = opt_match.group(1).upper()
                    text = opt_match.group(2).strip()
                    options.append({'letter': letter, 'text': text})
                    i += 1
                    continue

                # 非选项非答案的内容，可能是题干续行
                # 判断题/填空题可能没有选项，直接到答案
                # 如果这一行不像新题开头，就当作题干的一部分
                if not sub.startswith('###') and not sub.startswith('##'):
                    stem += '\n' + sub
                    i += 1
                    continue

                break

            # 标准化答案
            answer = normalize_answer(q_type, answer)

            questions.append({
                'chapter': current_chapter,
                'type': q_type,
                'stem': stem,
                'options': json.dumps(options, ensure_ascii=False),
                'answer': answer,
                'explanation': '',
            })
            continue

        i += 1

    return quiz_name, questions


def normalize_answer(q_type, answer):
    """标准化答案"""
    answer = answer.strip()

    if q_type == 'choice':
        # 单选：单个大写字母
        answer = answer.upper()
        m = re.match(r'^([A-D])', answer)
        if m:
            return m.group(1)

    elif q_type == 'judge':
        # 判断：对/错
        if answer in ('对', '正确', 'true', 'True', 'T', '√', '是'):
            return '对'
        if answer in ('错', '错误', 'false', 'False', 'F', '×', '否'):
            return '错'

    elif q_type == 'multi':
        # 多选：大写字母连写 ABCD
        answer = answer.upper()
        letters = re.findall(r'[A-D]', answer)
        if letters:
            return ''.join(sorted(set(letters)))

    elif q_type == 'fill':
        # 填空：保持原文，去掉首尾引号
        answer = answer.strip('\'"""')

    elif q_type == 'short_answer':
        # 简答：保持原文，去掉首尾引号
        answer = answer.strip('\'"""')

    return answer


def check_answer(q_type, user_answer, correct_answer, options_json='[]'):
    """
    判分函数
    返回 (是否正确, 标准化后的用户答案)
    """
    user_answer = user_answer.strip()

    if q_type == 'choice':
        # 选择题：比对选项内容（支持打乱后判分）
        try:
            options = json.loads(options_json)
        except Exception:
            options = []

        # 找到用户选择的字母对应的选项内容
        user_letter = user_answer.upper().strip()
        user_text = ''
        for opt in options:
            if opt['letter'] == user_letter:
                user_text = opt['text']
                break

        # 找到正确字母对应的选项内容
        correct_text = ''
        for opt in options:
            if opt['letter'] == correct_answer.upper():
                correct_text = opt['text']
                break

        # 如果能匹配到内容，比对内容；否则比对字母
        if user_text and correct_text:
            return user_text == correct_text, user_letter
        return user_letter == correct_answer.upper(), user_letter

    elif q_type == 'judge':
        user = user_answer.strip()
        if user in ('对', '正确', 'true', 'True', 'T', '√', '是'):
            user = '对'
        elif user in ('错', '错误', 'false', 'False', 'F', '×', '否'):
            user = '错'
        return user == correct_answer, user

    elif q_type == 'multi':
        # 多选题：比对字母集合
        user_letters = ''.join(sorted(set(re.findall(r'[A-D]', user_answer.upper()))))
        correct_letters = ''.join(sorted(set(re.findall(r'[A-D]', correct_answer.upper()))))
        return user_letters == correct_letters, user_letters

    elif q_type == 'fill':
        # 填空题：关键词包含匹配
        return _fill_match(user_answer, correct_answer), user_answer

    elif q_type == 'short_answer':
        # 简答题：宽松关键词包含匹配（同上填空题，更宽松）
        return _fill_match(user_answer, correct_answer), user_answer

    return False, user_answer


def _fill_match(user_input, correct_answer):
    """
    填空题判分：智能关键词匹配
    支持多种答案格式，连字符归一化，允许部分匹配
    """
    import re as _re

    def normalize(s):
        """统一清理：去空白、标点、连字符，转小写"""
        s = _re.sub(r'[\s\-，。、；：\u201c\u201d\u2018\u2019「」（）()【】\[\].,;:!?！？_]', '', s)
        return s.lower()

    def clean_ans(s):
        """去首尾空白和括号编号"""
        s = s.strip()
        return _re.sub(r'^\(\d+\)\s*', '', s).strip()

    # ===== 拆分空位 =====
    slots = []
    numbered = _re.findall(r'\((\d+)\)\s*(.+?)(?=\s*\(\d+\)|$)', correct_answer)
    if numbered and len(numbered) > 1:
        for _, text in numbered:
            text = text.strip()
            if text:
                slots.append(text)
    elif '|' in correct_answer:
        for part in correct_answer.split('|'):
            part = part.strip()
            if part:
                slots.append(part)
    else:
        slots = [correct_answer.strip()]

    if not slots:
        return False

    # ===== 提取关键词（已normalize）=====
    required = []
    for slot in slots:
        slot_clean = clean_ans(slot)
        if not slot_clean:
            continue
        or_parts = _re.split(r'/', slot_clean)
        or_group = []
        for part in or_parts:
            part = part.strip()
            if not part:
                continue
            and_kws = [_re.sub(r'[\s\-，。、；：\u201c\u201d\u2018\u2019「」（）()【】\[\].,;:!?！？_]', '', k).lower()
                      for k in _re.split(r'[\s、]+', part)]
            and_kws = [k for k in and_kws if k]
            if and_kws:
                or_group.append(and_kws)
        if or_group:
            required.append(or_group)

    if not required:
        return True

    # ===== 匹配 =====
    # 先按空格/标点拆分用户输入为词元（保留原始分隔），再逐一归一化
    raw_tokens = _re.split(r'[\s，。、；：\u201c\u201d\u2018\u2019「」（）()【】\[\].,;:!?！？]+', user_input)
    raw_tokens = [t.strip() for t in raw_tokens if t.strip()]
    if not raw_tokens:
        return False

    # 对每个词元做normalize，得到匹配用词元列表
    user_norm = normalize(user_input)  # 整串用于兜底匹配
    norm_tokens = [normalize(t) for t in raw_tokens if normalize(t)]

    def kw_match(kw, u):
        """单关键词匹配"""
        if not kw or not u:
            return False
        if kw in u:
            return True
        # 用户输入是关键词前缀（答"非侵入"对"非侵入式"）
        if len(u) >= 2 and kw.startswith(u):
            return True
        # 关键词在用户输入中作为前缀出现
        if len(kw) >= 2 and u.startswith(kw):
            return True
        # 足够长的子串包含
        if len(u) >= max(3, len(kw) * 0.5) and u in kw:
            return True
        return False

    for or_group in required:
        passed = False
        for and_grp in or_group:
            if not and_grp:
                continue
            # 每个答案关键词需在用户词元中找到匹配
            all_ok = True
            for kw in and_grp:
                found = any(kw_match(kw, ut) for ut in norm_tokens)
                if not found:
                    found = kw_match(kw, user_norm)  # 兜底：对整串匹配
                if not found:
                    all_ok = False
                    break
            if all_ok:
                passed = True
                break
        if not passed:
            return False
    return True
