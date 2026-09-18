"""从8个标准题库TXT文件生成速记版Word文档，只保留题目和答案，去掉选项和解析"""

import re, os
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

SRC_DIR = r'D:\WorkXM\6a17\刷题\标准题库'
OUT_DIR = r'D:\XIAZAI'

TYPE_CN = {'选择': '选择题', '判断': '判断题', '多选': '多选题', '填空': '填空题', '简答': '简答题'}
TYPE_TAG = {'选择': '【选】', '判断': '【判】', '多选': '【多】', '填空': '【空】', '简答': '【简】'}

# 8个文件及其速记版命名
FILES = [
    ('Java期末选择判断多选.txt',  'Java期末选择判断多选速记版.docx'),
    ('Java期末填空.txt',          'Java期末填空速记版.docx'),
    ('Python期末选择判断多选.txt', 'Python期末选择判断多选速记版.docx'),
    ('Python期末填空.txt',         'Python期末填空速记版.docx'),
    ('Python期末简答题.txt',       'Python期末简答速记版.docx'),
    ('软件设计期末选择判断多选.txt','软件设计期末选择判断多选速记版.docx'),
    ('软件设计期末填空.txt',        '软件设计期末填空速记版.docx'),
    ('软件设计期末简答题.txt',      '软件设计期末简答速记版.docx'),
]

def parse_questions(txt_path):
    """解析TXT文件，提取所有题目，返回列表[dict]"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = []
    # 匹配 ### [类型] 开头的题块
    blocks = re.split(r'###\s*\[(选择|判断|多选|填空|简答)\]', content)
    
    # blocks[0] 是标题部分，之后交替为: type, content, type, content...
    i = 1
    while i < len(blocks) - 1:
        qtype = blocks[i].strip()
        block = blocks[i+1]
        i += 2
        
        # 提取题目文本（在答案之前的部分）
        # 答案行格式: 答案：XXX 或 答案: XXX
        ans_match = re.search(r'答案[：:]\s*(.+?)(?:\n|$)', block)
        if not ans_match:
            continue
        
        answer_text = ans_match.group(1).strip()
        
        # 题目文本 = 答案之前的所有内容
        question_part = block[:ans_match.start()].strip()
        
        # 对于选择/多选题，去掉选项行(A/B/C/D或A、B、C、D)
        if qtype in ('选择', '多选'):
            # 去掉选项行: 以 A. / A、 / A、开头
            question_lines = []
            for line in question_part.split('\n'):
                line = line.strip()
                if re.match(r'^[A-D]\s*[\.、．]\s*', line):
                    continue  # 跳过选项行
                question_lines.append(line)
            question_text = '\n'.join(question_lines).strip()
        elif qtype == '判断':
            # 判断题，去掉末尾的（  ）或（）括号
            question_text = question_part.strip()
            question_text = re.sub(r'（\s*）\s*$|(\(\s*\)\s*$)', '', question_text).strip()
        elif qtype == '填空':
            question_text = question_part.strip()
        elif qtype == '简答':
            question_text = question_part.strip()
        
        # 清理：去掉题号前缀如 "1、" "2、"
        question_text = re.sub(r'^\d+[、\.]\s*', '', question_text, count=1).strip()
        
        # 简答题答案可能很长，保持原样
        # 填空题答案可能有多个用分号分隔的变体，取第一个主要答案
        if qtype == '填空':
            # 分号分隔多个可接受答案，只取第一个
            answer_display = answer_text.split(';')[0].split('；')[0].strip()
            # 如果第一个答案以"("开头（如"(1) 管道-过滤器  (2) 数据流"），保留完整
            if answer_text.startswith('('):
                answer_display = answer_text
        else:
            answer_display = answer_text
        
        questions.append({
            'type': qtype,
            'question': question_text,
            'answer': answer_display,
            'full_answer': answer_text,
        })
    
    return questions


def create_docx(questions, title, out_path):
    """创建速记版Word文档"""
    doc = Document()
    
    # 设置默认字体
    style = doc.styles['Normal']
    font = style.font
    font.name = '微软雅黑'
    font.size = Pt(11)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    # 标题
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(title + '速记版')
    title_run.bold = True
    title_run.font.size = Pt(16)
    title_run.font.name = '微软雅黑'
    title_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    # 说明
    note_para = doc.add_paragraph()
    note_run = note_para.add_run('（仅题目+答案，去掉选项和解析，方便快速记忆）')
    note_run.font.size = Pt(10)
    note_run.font.color.rgb = RGBColor(128, 128, 128)
    note_run.font.name = '微软雅黑'
    note_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    # 按题型分组
    type_order = {'选择': '选择题', '判断': '判断题', '多选': '多选题', '填空': '填空题', '简答': '简答题'}
    type_cn = TYPE_TAG
    
    grouped = {}
    for q in questions:
        t = q['type']
        if t not in grouped:
            grouped[t] = []
        grouped[t].append(q)
    
    for tkey in TYPE_CN:
        if tkey not in grouped:
            continue
        
        # 章节标题
        section_para = doc.add_paragraph()
        section_run = section_para.add_run(TYPE_CN[tkey])
        section_run.bold = True
        section_run.font.size = Pt(14)
        section_run.font.name = '微软雅黑'
        section_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        section_run.font.color.rgb = RGBColor(0, 102, 204)
        
        for idx, q in enumerate(grouped[tkey], 1):
            # 题目行: 序号 + 类型标记 + 题目
            q_para = doc.add_paragraph()
            
            # 序号
            num_run = q_para.add_run(f'{idx}. ')
            num_run.bold = True
            num_run.font.size = Pt(12)
            num_run.font.name = '微软雅黑'
            num_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 类型小标记
            tag_run = q_para.add_run(type_cn[tkey] + ' ')
            tag_run.bold = True
            tag_run.font.size = Pt(9)
            tag_run.font.color.rgb = RGBColor(0, 153, 136) if tkey in ('判断', '填空', '简答') else RGBColor(0, 102, 204)
            tag_run.font.name = '微软雅黑'
            tag_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 题目文本
            q_run = q_para.add_run(q['question'])
            q_run.bold = True
            q_run.font.size = Pt(12)
            q_run.font.name = '微软雅黑'
            q_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 答案行
            ans_para = doc.add_paragraph()
            ans_label = ans_para.add_run('答案：')
            ans_label.bold = True
            ans_label.font.size = Pt(11)
            ans_label.font.color.rgb = RGBColor(220, 50, 50)  # 红色醒目
            ans_label.font.name = '微软雅黑'
            ans_label.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            ans_run = ans_para.add_run(q['answer'])
            ans_run.bold = True
            ans_run.font.size = Pt(11)
            ans_run.font.color.rgb = RGBColor(220, 50, 50)
            ans_run.font.name = '微软雅黑'
            ans_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 简答题答案可能很长，增加额外行距
            if tkey == '简答' and len(q['answer']) > 50:
                ans_para.paragraph_format.space_after = Pt(8)
    
    doc.save(out_path)
    return len(questions)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    
    for src_name, out_name in FILES:
        src_path = os.path.join(SRC_DIR, src_name)
        out_path = os.path.join(OUT_DIR, out_name)
        
        if not os.path.exists(src_path):
            print(f'SKIP: {src_name} not found')
            continue
        
        questions = parse_questions(src_path)
        
        # 提取标题（去掉"期末"和题型后缀）
        title = src_name.replace('.txt', '').replace('期末', '期末')
        
        count = create_docx(questions, title, out_path)
        total += count
        
        # 按题型统计
        stats = {}
        for q in questions:
            stats[q['type']] = stats.get(q['type'], 0) + 1
        
        stat_str = ' + '.join(f"{TYPE_CN.get(k,k)}{v}" for k,v in stats.items())
        print(f'{out_name}: {count}题 ({stat_str})')
    
    print(f'\n总计: {total}题, 8个速记版Word文档已生成到 {OUT_DIR}')


if __name__ == '__main__':
    main()
