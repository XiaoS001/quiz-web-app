"""
速记版题库优化脚本：
1. 修复答案格式（去掉多选变体、清理乱码）
2. 添加记忆辅助（口诀、关键词加粗、简化表述）
3. 输出到 D:\XIAZAI\速记\改\
"""

import re, os
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

SRC_DIR = r'D:\WorkXM\6a17\刷题\标准题库'
OUT_DIR = r'D:\XIAZAI\速记\改'

FILES = [
    # (源文件名, 输出文件名, 科目简称)
    ('Java期末选择判断多选.txt',  'Java期末选择判断多选.docx', 'Java'),
    ('Java期末填空.txt',          'Java期末填空.docx', 'Java'),
    ('Python期末选择判断多选.txt', 'Python期末选择判断多选.docx', 'Python'),
    ('Python期末填空.txt',         'Python期末填空.docx', 'Python'),
    ('Python期末简答题.txt',       'Python期末简答题.docx', 'Python'),
    ('软件设计期末选择判断多选.txt','软件设计期末选择判断多选.docx', '软件设计'),
    ('软件设计期末填空.txt',        '软件设计期末填空.docx', '软件设计'),
    ('软件设计期末简答题.txt',      '软件设计期末简答题.docx', '软件设计'),
]

# ===== 记忆口诀库 =====
MNEMONICS = {
    'Python': {
        '特点': '♬ 简开可移扩类富，通多中文 — 缺：低效不兼加密差',
        '数据类型': '口：整形浮点布尔复，None字列元字集',
        '命名规范': '口：模块小写全、类名首大写、常量全大写、函数蛇形名',
        'lambda': '口：lambda 参数: 表达式 — 一行搞定小函数',
        '列表vs元组': '口：列可改元不可改 → 列方括号元圆括号',
        '异常处理': '口：try试-except抓-else没异常-finally都要干',
        '面向对象': '口：封装隐藏继承复用多态灵活',
        '字典': '口：花括号键值对，键不可变值任意',
        '递归': '口：自己调用自己，大问题变小问题',
        'match_vs_search': '口：match从头搜，search到处找',
        '静态vs实例vs类': '口：实例(self)绑对象，类(cls)绑类体，静态(无self/cls)是普通函数',
        '文本vs二进制': '口：文本存字符能读，二进制存啥都不行(直接)',
        '位置vs关键字vs默认': '口：位置按序传，关键字指名传，默认给初值',
    },
    'Java': {
        'Spring模块': '口：Beans装对象，Core是基础，Context上下文，SpEL表达式',
        'IoC/DI': '口：IoC控制反转(给容器管)，DI依赖注入(容器来送)',
        '作用域': '口：singleton(单)全共用一个，prototype(原)次次新，request(请求)一次请求，session(会话)一个用户，globalsession全局会话',
        'AOP术语': '口：切面(做什么)=通知+切点，切点(在哪切)=匹配规则，通知(何时做)=before/after/around，织入=插入过程',
        'JDK vs CGLIB': '口：JDK代理要接口(is-a)，CGLIB代理继承类(extends)',
        '事务': '口：编程式(自己写try)，声明式(@Transactional注解)',
        'MVC': '口：Model存数据，View画界面，Controller当调度',
        'Bean生命周期': '口：实例化→属性赋值→初始化(init)→使用→销毁(destroy)',
    },
    '软件设计': {
        '生命周期': '口：定开运维 (定义→开发→运行→维护)',
        'OOA vs OOD': '口：OOA分析(建模型)，OOD设计(定方案)',
        'MVC': '口：M存数据，V画界面，C当管家',
        'UML图分类': '口：静态(结构)：类图对象图组件图部署图包图；动态(行为)：用例图活动图状态图序列图通信图',
        '设计原则': '口：单一职责(一事)，开闭原则(扩不改)，里氏替换(子替父)，依赖倒置(依抽象)，接口隔离(接口小)，迪米特(少知道)',
        '4+1视图': '口：逻辑(类图)，开发(包图)，过程(时序)，物理(部署)+用例(胶水)',
        'ACID': '口：A原子性(全或无)，C一致性(约束保持)，I隔离性(互不干扰)，D持久性(永久保存)',
        '管道过滤器': '口：管道传数据，过滤器加工数据',
        'B/S vs C/S': '口：B/S免装跨平台但慢，C/S快安全但要装客户端',
        '云计算': '口：IaaS(基础设施)，PaaS(平台即服务)，SaaS(软件即服务) — 从底到顶',
        '继承类型': '口：单继承(一个爹)，多重继承(多个爹)，多级继承(爷爷-爹-子)',
        '黄金规则': '口：一致快捷反馈完，防错撤销用户控，少记',
    }
}

def clean_answer(answer_text, qtype):
    """清理答案文本，只保留主要答案"""
    answer_text = answer_text.strip()
    
    if qtype == '填空':
        # 分号分隔多答案，取第一个不含空格的
        parts = re.split(r'[;；]', answer_text)
        # 过滤空串
        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            return answer_text
        # 优先选择不带小写变体的（即首字母大写或首字符是符号的）
        # 如 "help();help" → 取 "help()"
        best = parts[0]
        for p in parts:
            if p.startswith('('):
                return answer_text  # 多空题保留原样
        # 如果第一个答案已经包含()则优先
        return best if best else answer_text
    
    return answer_text


def add_memory_hint(question, answer, qtype, subject, idx):
    """为特定题目添加记忆提示"""
    q = question.strip()
    a = answer.strip()
    
    hints = {
        # Python 基础
        'Python特点': '♬ 简开可移扩类富，通多中文；缺：低效不兼加密差',
        '数据类型8种': '口：整浮布复None，字列元字集 — 前4数字+None，后4复合',
        '命名规范': '口：模块全小、类驼峰、常量全大、函数蛇形、变量蛇形',
        '变量名规范': '口：不数字开头、不用关键字、不用特殊符号(只_允许)',
        'input/print': '口：input()返回字符串，print()支持换行(\\n)和分隔(sep)',
        '静态vs脚本': '口：编译=静态(C/Java)，解释=脚本(Python/JS)',
        'Python数字类型': '口：整浮复布 — 整数浮点复数布尔',
        '复数组成': '口：实部+虚部j — 如 3+4j',
        '布尔是整型': '口：True=1, False=0 → 布尔是特殊的整型',
        '布尔型判断': '口：3<4<5链式比较返回True',
        'lambda': '口：lambda 参数: 表达式 — 匿名函数一行搞定',
        'match vs search': '口：match(从开头) search(任意位置)',
        
        # Java Spring
        'IoC/DI': '口：IoC=控制反转(容器管对象)，DI=依赖注入(容器送依赖)',
        'Spring模块': '口：Core基础+Beans对象+Context环境+AOP切面+Data数据+Web网络',
        '作用域': '口：单全一(singleton)，原次新(prototype)，请一次(request)',
        '自动装配': '口：@Autowired自动注入，@Qualifier指定Bean名',
        '声明式事务': '口：@Transactional一行搞定事务',
        'JDK vs CGLIB': '口：JDK需要接口(implements)，CGLIB继承类(extends)',
        'MVC': '口：M数据 V界面 C调度器',
        'Bean生命周期': '口：创建→装属性→初始化→使用→销毁',
        
        # 软件设计
        '生命周期阶段': '口：定开运维 — 定义→开发→运行→维护',
        'UML': '口：统一建模语言，9种图：静5(类对组部包) 动4(用例活动状态序列/通信)',
        '分层目的': '口：分层降耦合，增加复用性',
        '设计模式分类': '口：创建型(怎么new)，结构型(怎么组)，行为型(怎么干)',
        '4+1视图': '口：逻辑(类图)+开发(包图)+过程(时序)+物理(部署)+1用例(串联)',
        'ACID': '口：A-原子(全或无)，C-一致(约束保)，I-隔离(互不扰)，D-持久(永保存)',
        'OOA vs OOD': '口：A分析(What是什么)，D设计(How怎么做)',
        '黄金规则': '口：一致性 快捷 反馈 完成 防错 撤销 用户控 少记',
        '设计原则SOLID': '口：S单一 O开关 L替换 I隔离 D倒置 — SOLID五字诀',
    }
    
    # 尝试匹配
    for key, hint in hints.items():
        if key in q or key in question.strip():
            return hint
    
    # 通用匹配
    if qtype == '简答' and len(a) > 100:
        # 长答案给简化提示
        if '特点' in q or '优点' in q or '缺点' in q:
            # 提取关键短语
            keywords = re.findall(r'[①②③④⑤⑥⑦⑧⑨⑩]', a)
            if keywords:
                return f'💡 {len(keywords)}个要点，记住编号'
            words = re.findall(r'[（(]\d[）)]', a)
            if words:
                return f'💡 {len(words)}个要点'
        if '区别' in q or '不同' in q or '差异' in q:
            return '💡 对比记忆：先记关键不同点'
        if '定义' in q or '是什么' in q:
            return '💡 一句话定义，抓住核心关键词'
    
    return None


def create_improved_docx(questions, subject, out_path):
    """创建优化版速记docx"""
    doc = Document()
    
    # 页面设置
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    
    # 默认字体
    style = doc.styles['Normal']
    style.font.name = '微软雅黑'
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    style.paragraph_format.space_after = Pt(4)
    style.paragraph_format.line_spacing = 1.35
    
    # 标题
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(f'{subject}期末 · 考前速记')
    title_run.bold = True
    title_run.font.size = Pt(18)
    title_run.font.name = '微软雅黑'
    title_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    title_run.font.color.rgb = RGBColor(139, 115, 85)  # #8B7355 warm brown
    
    # 副标题
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_run = sub.add_run('观看法 · 快速记忆版 — 只看题目和答案，反复过目')
    sub_run.font.size = Pt(9)
    sub_run.font.color.rgb = RGBColor(160, 160, 160)
    sub_run.font.name = '微软雅黑'
    sub_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    # 分隔线
    sep = doc.add_paragraph()
    sep.paragraph_format.space_before = Pt(4)
    sep.paragraph_format.space_after = Pt(8)
    sep_run = sep.add_run('━' * 50)
    sep_run.font.size = Pt(6)
    sep_run.font.color.rgb = RGBColor(200, 200, 200)
    
    # 按题型分组
    grouped = {}
    for q in questions:
        t = q['type']
        if t not in grouped:
            grouped[t] = []
        grouped[t].append(q)
    
    TYPE_CN = {'选择': '选择题', '判断': '判断题', '多选': '多选题', '填空': '填空题', '简答': '简答题'}
    TYPE_COLOR = {'选择': RGBColor(0, 82, 163), '判断': RGBColor(0, 135, 90), '多选': RGBColor(163, 73, 0), '填空': RGBColor(130, 57, 171), '简答': RGBColor(180, 40, 40)}
    TYPE_TAG = {'选择': '选', '判断': '判', '多选': '多', '填空': '空', '简答': '简'}
    
    global_idx = 0
    
    for tkey in ['选择', '判断', '多选', '填空', '简答']:
        if tkey not in grouped:
            continue
        
        qs = grouped[tkey]
        
        # 章节标题
        sec = doc.add_paragraph()
        sec.paragraph_format.space_before = Pt(14)
        sec.paragraph_format.space_after = Pt(6)
        
        # 彩色竖线装饰
        bar = sec.add_run('▌ ')
        bar.bold = True
        bar.font.size = Pt(14)
        bar.font.color.rgb = TYPE_COLOR[tkey]
        bar.font.name = '微软雅黑'
        bar.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        
        sec_title = sec.add_run(f'{TYPE_CN[tkey]} × {len(qs)}题')
        sec_title.bold = True
        sec_title.font.size = Pt(14)
        sec_title.font.name = '微软雅黑'
        sec_title.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        sec_title.font.color.rgb = TYPE_COLOR[tkey]
        
        # 添加该题型总口诀（如果有）
        topic_mnemonics = MNEMONICS.get(subject, {})
        if tkey == '选择' or tkey == '多选':
            pass  # 选择/多选不需要总口诀
        elif tkey == '填空':
            pass
        elif tkey == '简答' and subject == 'Python':
            hint_para = doc.add_paragraph()
            hint_para.paragraph_format.space_after = Pt(6)
            hint_run = hint_para.add_run('💡 简答题记忆策略：先记关键词，再展开 → 老师按关键词给分')
            hint_run.font.size = Pt(9)
            hint_run.font.italic = True
            hint_run.font.color.rgb = RGBColor(100, 100, 100)
            hint_run.font.name = '微软雅黑'
            hint_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        
        for idx, q in enumerate(qs, 1):
            global_idx += 1
            
            # === 题目行 ===
            q_para = doc.add_paragraph()
            q_para.paragraph_format.space_before = Pt(6)
            q_para.paragraph_format.space_after = Pt(2)
            
            # 序号
            num = q_para.add_run(f'{idx}.')
            num.bold = True
            num.font.size = Pt(10.5)
            num.font.name = '微软雅黑'
            num.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 题型标签
            tag = q_para.add_run(f' [{TYPE_TAG[tkey]}] ')
            tag.font.size = Pt(8)
            tag.font.color.rgb = TYPE_COLOR[tkey]
            tag.font.name = '微软雅黑'
            tag.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 题目文本（加粗）
            qt = q_para.add_run(q['question'])
            qt.bold = True
            qt.font.size = Pt(10.5)
            qt.font.name = '微软雅黑'
            qt.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # === 答案行 ===
            ans_para = doc.add_paragraph()
            ans_para.paragraph_format.space_after = Pt(3)
            ans_para.paragraph_format.left_indent = Cm(0.5)
            
            ans_label = ans_para.add_run('→ ')
            ans_label.font.size = Pt(10.5)
            ans_label.font.color.rgb = RGBColor(210, 40, 40)  # 红色
            ans_label.font.name = '微软雅黑'
            ans_label.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            ans_run = ans_para.add_run(q['answer'])
            ans_run.bold = True
            ans_run.font.size = Pt(10.5)
            ans_run.font.color.rgb = RGBColor(210, 40, 40)
            ans_run.font.name = '微软雅黑'
            ans_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
            
            # 特殊标注：判断为"错"的用橙色
            if tkey == '判断' and '错' in q['answer']:
                ans_run.font.color.rgb = RGBColor(230, 130, 0)
            
            # === 记忆提示（如果有） ===
            hint = add_memory_hint(q['question'], q['answer'], tkey, subject, idx)
            if hint:
                hint_para = doc.add_paragraph()
                hint_para.paragraph_format.space_after = Pt(4)
                hint_para.paragraph_format.left_indent = Cm(0.8)
                hint_run = hint_para.add_run(hint)
                hint_run.font.size = Pt(8.5)
                hint_run.font.italic = True
                hint_run.font.color.rgb = RGBColor(100, 140, 100)
                hint_run.font.name = '微软雅黑'
                hint_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    # 结尾统计
    doc.add_paragraph()
    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer_run = footer.add_run(f'共计 {global_idx} 题 · 反复观看加深印象')
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(180, 180, 180)
    footer_run.font.italic = True
    footer_run.font.name = '微软雅黑'
    footer_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
    
    doc.save(out_path)
    return global_idx


def parse_questions(txt_path):
    """解析TXT题库文件"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = []
    blocks = re.split(r'###\s*\[(选择|判断|多选|填空|简答)\]', content)
    
    i = 1
    while i < len(blocks) - 1:
        qtype = blocks[i].strip()
        block = blocks[i+1]
        i += 2
        
        # 提取答案
        ans_match = re.search(r'答案[：:]\s*(.+?)(?:\n|$)', block)
        if not ans_match:
            continue
        
        raw_answer = ans_match.group(1).strip()
        question_part = block[:ans_match.start()].strip()
        
        # 清理题目文本
        if qtype in ('选择', '多选'):
            lines = []
            for line in question_part.split('\n'):
                line = line.strip()
                if re.match(r'^[A-D]\s*[\.、．]\s*', line):
                    continue
                lines.append(line)
            question_text = '\n'.join(lines).strip()
        elif qtype == '判断':
            question_text = question_part.strip()
            question_text = re.sub(r'（\s*）\s*$|(\(\s*\)\s*$)', '', question_text).strip()
        else:
            question_text = question_part.strip()
        
        # 去题号前缀
        question_text = re.sub(r'^\d+[、\.]\s*', '', question_text, count=1).strip()
        
        # 清理答案
        clean_ans = clean_answer(raw_answer, qtype)
        
        questions.append({
            'type': qtype,
            'question': question_text,
            'answer': clean_ans,
        })
    
    return questions


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    grand_total = 0
    
    for src_name, out_name, subject in FILES:
        src_path = os.path.join(SRC_DIR, src_name)
        out_path = os.path.join(OUT_DIR, out_name)
        
        if not os.path.exists(src_path):
            print(f'[SKIP] {src_name} 不存在')
            continue
        
        questions = parse_questions(src_path)
        count = create_improved_docx(questions, subject, out_path)
        grand_total += count
        
        # 统计
        stats = {}
        for q in questions:
            stats[q['type']] = stats.get(q['type'], 0) + 1
        stat_str = ' | '.join(f"{t}={c}" for t, c in stats.items())
        print(f'[OK] {out_name}: {count}题 ({stat_str})')
    
    print(f'\n===== 总计 {grand_total} 题，已输出到 {OUT_DIR} =====')


if __name__ == '__main__':
    main()
