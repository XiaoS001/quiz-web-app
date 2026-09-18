# -*- coding: utf-8 -*-
"""重建软件设计题库：从所有原始源文件合并、查重、输出标准格式文件"""

import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '标准题库')

def normalize_stem(stem):
    """标准化题干用于比较：去序号、去⚠️标记、统一空白、统一标点"""
    s = stem.strip()
    # 去掉序号前缀如 "1." "2、" "30." 等
    s = re.sub(r'^[\d]+[.、]\s*', '', s)
    # 去掉⚠️标记
    s = re.sub(r'⚠️|【易错题】', '', s)
    # 统一中文逗号和英文逗号
    s = s.replace(',', '，').replace(',', '，')
    # 统一括号
    s = s.replace('(', '（').replace(')', '）')
    # 统一空白
    s = re.sub(r'\s+', ' ', s).strip()
    # 统一填空占位符
    s = re.sub(r'_{2,}', '____', s)
    s = re.sub(r'____{2,}', '____', s)
    return s

def parse_choice_question(lines):
    """解析一道选择题，返回 (stem, options_dict, answer, explanation)"""
    stem = lines[0].strip()
    # 去序号
    stem = re.sub(r'^[\d]+[.、)\s]+', '', stem)
    stem = re.sub(r'⚠️|【易错题】', '', stem).strip()
    
    options = {}
    answer = ''
    explanation = ''
    for line in lines[1:]:
        line = line.strip()
        # 选项行
        m = re.match(r'^([A-D])[.、]\s*(.+)', line)
        if m:
            options[m.group(1)] = m.group(2).strip()
        # 答案行
        elif line.startswith('答案') or line.startswith('正确答案'):
            ans_match = re.search(r'[A-D]+', line)
            if ans_match:
                answer = ans_match.group(0)
            # 可能带解析
            paren = re.search(r'[（(].+', line)
            if paren:
                explanation = paren.group(0).strip()
        elif line.startswith('解析'):
            explanation = line
    return stem, options, answer, explanation

def parse_judge_question(lines):
    """解析判断题"""
    stem = lines[0].strip()
    stem = re.sub(r'^[\d]+[.、)\s]+', '', stem)
    stem = re.sub(r'⚠️|【易错题】', '', stem).strip()
    
    answer = ''
    explanation = ''
    for line in lines[1:]:
        line = line.strip()
        if '正确' in line or '对' in line and line.startswith('答案'):
            answer = '对'
        elif '错误' in line or '错' in line and line.startswith('答案'):
            answer = '错'
        elif line.startswith('解析'):
            explanation = line
    return stem, answer, explanation

def parse_fill_question(lines):
    """解析填空题"""
    stem = lines[0].strip()
    stem = re.sub(r'^[\d]+[.、)\s]+', '', stem)
    stem = re.sub(r'⚠️|【易错题】', '', stem).strip()
    
    answer = ''
    explanation = ''
    for line in lines[1:]:
        line = line.strip()
        if line.startswith('答案'):
            # 去掉"答案："前缀
            ans = re.sub(r'^答案[：:]\s*', '', line)
            answer = ans.strip()
        elif line.startswith('解析') or line.startswith('（注意'):
            explanation = line
    return stem, answer, explanation

def parse_source_txt(filepath):
    """解析原始源TXT文件，返回题目列表"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = []
    # 按题号分割
    blocks = re.split(r'\n(?=\d+[.、]\s)', content)
    
    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if not lines:
            continue
        
        first_line = lines[0]
        # 判断题型
        if '答案' not in block and '正确答案' not in block:
            continue
        
        # 检查是否有多选特征（答案为ABC等多字母）
        has_multi_answer = False
        for line in lines:
            if re.match(r'^答案[：:]\s*[A-D]{2,}', line) or re.match(r'^正确答案[：:]\s*[A-D]{2,}', line):
                has_multi_answer = True
                break
        
        # 检查选项数量（4个选项且答案多字母=多选）
        option_count = sum(1 for l in lines if re.match(r'^[A-D][.、]\s', l))
        
        if has_multi_answer and option_count >= 2:
            q_type = 'multi'
            stem, options, answer, explanation = parse_choice_question(lines)
            questions.append({
                'type': q_type,
                'stem': stem,
                'options': options,
                'answer': answer,
                'explanation': explanation
            })
        elif option_count >= 2:
            # 选择题（单选，答案为单字母）
            q_type = 'choice'
            stem, options, answer, explanation = parse_choice_question(lines)
            questions.append({
                'type': q_type,
                'stem': stem,
                'options': options,
                'answer': answer,
                'explanation': explanation
            })
        else:
            # 判断题或填空题
            # 检查是否有判断题特征
            for line in lines:
                if re.match(r'^答案[：:]\s*(正确|错误|对|错)', line):
                    q_type = 'judge'
                    stem, answer, explanation = parse_judge_question(lines)
                    questions.append({
                        'type': q_type,
                        'stem': stem,
                        'answer': answer,
                        'explanation': explanation
                    })
                    break
            else:
                q_type = 'fill'
                stem, answer, explanation = parse_fill_question(lines)
                questions.append({
                    'type': q_type,
                    'stem': stem,
                    'answer': answer,
                    'explanation': explanation
                })
    
    return questions

def parse_standard_file(filepath):
    """解析标准格式题库文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = []
    # 按 ### 分割题目
    blocks = re.split(r'\n###\s+', content)
    
    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if not lines:
            continue
        
        # 第一行：[类型] 题干
        header = lines[0]
        type_match = re.match(r'\[(选择|判断|多选|填空|简答)\]\s*(.+)', header)
        if not type_match:
            continue
        
        type_cn = type_match.group(1)
        stem = type_match.group(2).strip()
        
        type_map = {'选择': 'choice', '判断': 'judge', '多选': 'multi', '填空': 'fill', '简答': 'short_answer'}
        q_type = type_map.get(type_cn, type_cn)
        
        options = {}
        answer = ''
        explanation = ''
        
        for line in lines[1:]:
            line = line.strip()
            m = re.match(r'^([A-D])[.、]\s*(.+)', line)
            if m:
                options[m.group(1)] = m.group(2).strip()
            elif line.startswith('答案') or line.startswith('正确答案'):
                ans = re.sub(r'^答案[：:]\s*', '', line)
                ans = re.sub(r'^正确答案[：:]\s*', '', ans)
                # 提取括号中的解析
                paren_match = re.search(r'[（(](.+)[）)]', ans)
                if paren_match:
                    explanation = paren_match.group(1)
                    ans = re.sub(r'[（(].+[）)]', '', ans).strip()
                answer = ans.strip()
            elif line.startswith('解析') or line.startswith('（注意'):
                explanation = line
        
        questions.append({
            'type': q_type,
            'stem': stem,
            'options': options,
            'answer': answer,
            'explanation': explanation
        })
    
    return questions

# ========== 合并所有源 ==========

all_questions = {}

# 1. 从标准题库文件读取（这些是最完整的）
std_files = {
    '软件设计期末选择判断多选.txt': os.path.join(OUTPUT_DIR, '软件设计期末选择判断多选.txt'),
    '软件设计期末填空.txt': os.path.join(OUTPUT_DIR, '软件设计期末填空.txt'),
    '软件设计期末简答题.txt': os.path.join(OUTPUT_DIR, '软件设计期末简答题.txt'),
}

for fname, fpath in std_files.items():
    if os.path.exists(fpath):
        qs = parse_standard_file(fpath)
        for q in qs:
            key = (q['type'], normalize_stem(q['stem']))
            if key not in all_questions:
                all_questions[key] = q
            else:
                # 保留更完整的版本（有解析的优先）
                existing = all_questions[key]
                if not existing.get('explanation') and q.get('explanation'):
                    all_questions[key] = q
                elif not existing.get('options') and q.get('options'):
                    all_questions[key] = q

# 2. 从原始源文件读取并合并
source_files = [
    os.path.join(BASE_DIR, '题库', '软件设计', '作业1-4（记）', '选择题.txt'),
    os.path.join(BASE_DIR, '题库', '软件设计', '作业1-4（记）', '填空题.txt'),
    os.path.join(BASE_DIR, '题库', '软件设计', '期中测试（记）', '选择题.txt'),
    os.path.join(BASE_DIR, '题库', '软件设计', '期中测试（记）', '填空题.txt'),
]

for fpath in source_files:
    if os.path.exists(fpath):
        qs = parse_source_txt(fpath)
        for q in qs:
            key = (q['type'], normalize_stem(q['stem']))
            if key not in all_questions:
                all_questions[key] = q
            else:
                # 保留更完整的版本
                existing = all_questions[key]
                if not existing.get('explanation') and q.get('explanation'):
                    all_questions[key] = q
                elif not existing.get('options') and q.get('options'):
                    all_questions[key] = q

# 3. 从DOCX提取的题目手动添加（DOCX中有一些标准文件里可能缺失的题）
# 这里手动列出DOCX中提取的题目（因为DOCX解析太碎）
docx_questions = [
    # 选择题 - 确保DOCX中的所有题都覆盖
    {'type': 'choice', 'stem': '在软件架构风格中，管道/过滤器架构风格的核心特点是（ ）',
     'options': {'A': '组件之间通过共享内存进行数据交换', 'B': '组件之间通过显示式调用进行交互',
                 'C': '数据流在过滤器之间流动，每个过滤器独立处理数据', 'D': '所有组件共享一个全局数据结构'},
     'answer': 'C'},
    {'type': 'choice', 'stem': '软件概要设计将软件需求转化为软件设计的（ ）和软件的（ ）',
     'options': {'A': '数据结构、算法流程', 'B': '数据结构、系统结构',
                 'C': '交互原型、操作接口', 'D': '操作接口、程序流程'},
     'answer': 'B'},
    {'type': 'choice', 'stem': '下列措施中，不利于提高软件可维护性的是（ ）',
     'options': {'A': '建立明确的软件质量目标', 'B': '使用瀑布模型',
                 'C': '使用面向对象的开发方法', 'D': '使用历史文档'},
     'answer': 'B'},
    {'type': 'choice', 'stem': '下列哪项属于事件驱动架构的核心特征？',
     'options': {'A': '基于进程通信', 'B': '同步方法调用', 'C': '异步消息传递', 'D': '事务处理'},
     'answer': 'C'},
    {'type': 'choice', 'stem': '以下有关MVC模式的特点说法错误的是（ ）',
     'options': {'A': '控制器处理业务逻辑', 'B': '模型存储数据', 'C': '视图负责渲染界面', 'D': '服务层和界面耦合'},
     'answer': 'D'},
    {'type': 'choice', 'stem': '在分层架构中，通常将数据库访问放在哪一层？',
     'options': {'A': '应用层', 'B': '控制层', 'C': '表示层', 'D': '数据访问层'},
     'answer': 'D'},
    {'type': 'choice', 'stem': '以下不属于UML行为建模图的有？',
     'options': {'A': '用例图', 'B': '时序图', 'C': '状态图', 'D': '类图'},
     'answer': 'D', 'explanation': 'UML行为建模图用于描述系统动态行为，包括用例图（功能需求）、时序图（交互过程）、状态图（对象状态变化）；类图属于结构建模图，描述静态结构。'},
    {'type': 'choice', 'stem': '不属于软件设计模式分类包括？',
     'options': {'A': '创建型模式', 'B': '结构型模式', 'C': '行为型模式', 'D': '逻辑型模式'},
     'answer': 'D'},
    {'type': 'choice', 'stem': 'B/S架构的核心优势不包括以下哪项？',
     'options': {'A': '客户端零安装维护', 'B': '跨平台兼容性强', 'C': '服务器负载低', 'D': '部署更新便捷'},
     'answer': 'C', 'explanation': 'B/S架构中大部分业务逻辑在服务器端处理，会增加服务器负载，而非降低。'},
    {'type': 'choice', 'stem': '关于软件体系结构架构语言(ADL)，下列说法错误的是（ ）',
     'options': {'A': '用于描述体系体系结构的架构和作用', 'B': '不支持体系结构的分析和验证',
                 'C': '可定义构件和连接件的接口', 'D': '是理解和交流体系结构的工具'},
     'answer': 'B'},
    {'type': 'choice', 'stem': '用户通过浏览器直接使用在线办公软件，这种服务属于云计算的哪种类型？',
     'options': {'A': 'IaaS', 'B': 'PaaS', 'C': 'SaaS', 'D': 'CaaS'},
     'answer': 'C', 'explanation': 'SaaS（软件即服务）通过互联网提供完整的软件应用，用户无需安装即可通过浏览器使用。'},
    {'type': 'choice', 'stem': '软件设计的主要任务是（ ）',
     'options': {'A': '编写程序代码', 'B': '确定软件的功能', 'C': '给出软件的结构、数据和过程', 'D': '测试软件'},
     'answer': 'C'},
    {'type': 'choice', 'stem': '云计算按服务类型可分为IaaS、PaaS、SaaS，以下关于这三类服务的描述不正确的有？',
     'options': {'A': 'IaaS提供基础计算、存储资源，用户需自行部署操作系统',
                 'B': 'PaaS提供开发平台，用户无需关注底层硬件维护',
                 'C': 'SaaS通过浏览器提供软件应用，用户无需安装客户端',
                 'D': 'PaaS需要用户自行管理数据库系统'},
     'answer': 'D',
     'explanation': 'PaaS通常包含数据库管理服务，用户无需自行管理。'},
    {'type': 'choice', 'stem': '以下哪项不属于面向对象的七大基本原则？',
     'options': {'A': '单一职责原则', 'B': '开放-封闭原则', 'C': '依赖倒置原则', 'D': '数据耦合原则'},
     'answer': 'D',
     'explanation': '面向对象七大原则包括：单一职责、开放-封闭、里氏替换、依赖倒置、接口隔离、迪米特法则、合成复用原则，数据耦合属于耦合性分类。'},
    {'type': 'choice', 'stem': '以下不属于高可信软件核心性质的有哪些？',
     'options': {'A': '可靠性', 'B': '安全性', 'C': '可维护性', 'D': '可用性'},
     'answer': 'C',
     'explanation': '高可信软件的核心性质包括可靠性、安全性、可用性，可维护性属于软件质量属性但非高可信核心特征。'},
    {'type': 'choice', 'stem': 'ISO/IEC 25010软件质量模型中，不属于功能性子特征的有？',
     'options': {'A': '适用性', 'B': '准确性', 'C': '互操作性', 'D': '容错性'},
     'answer': 'D',
     'explanation': 'ISO/IEC 25010中，功能性子特征包括适用性、准确性、互操作性、安全性、功能性合规性；容错性属于可靠性子特征。'},
    {'type': 'choice', 'stem': '软件体系结构的核心作用不包括以下哪一项？',
     'options': {'A': '指导开发团队进行模块化设计', 'B': '降低系统维护成本和复杂度',
                 'C': '直接实现具体业务逻辑功能', 'D': '为系统演化提供清晰的框架'},
     'answer': 'C',
     'explanation': '软件体系结构主要关注系统的整体结构和组件间关系，不直接负责具体业务逻辑的实现。'},
    {'type': 'choice', 'stem': '保证一个类仅有一个实例，并提供一个访问它的全局访问点。这句话是对（ ）设计模式的描述',
     'options': {'A': '外观模式', 'B': '策略模式', 'C': '适配器模式', 'D': '单例模式'},
     'answer': 'D'},
    {'type': 'choice', 'stem': '以下关于B/S架构的描述，正确的是？',
     'options': {'A': 'B/S架构需要在客户端安装专用软件', 'B': 'B/S架构的维护成本主要在客户端',
                 'C': 'B/S架构通过浏览器即可访问，客户端兼容性好', 'D': 'B/S架构的响应速度通常比C/S架构快'},
     'answer': 'C',
     'explanation': 'B/S架构基于浏览器访问，无需安装专用客户端软件，维护成本集中在服务器端，兼容性好，但受网络影响响应速度可能不如C/S架构。'},
    {'type': 'choice', 'stem': "MVC模式中的'V'代表什么？其主要功能是？",
     'options': {'A': 'View，处理业务逻辑', 'B': 'View，负责数据展示与用户交互',
                 'C': 'ViewModel，管理数据模型', 'D': 'View，处理数据存储'},
     'answer': 'B',
     'explanation': 'MVC模式中，M(Model)是数据模型，V(View)是视图，C(Controller)是控制器。'},
    {'type': 'choice', 'stem': 'MVC模式中负责处理用户交互请求的是哪个部分？',
     'options': {'A': 'Model', 'B': 'View', 'C': 'Controller', 'D': 'Service'},
     'answer': 'C',
     'explanation': 'MVC中Controller负责接收用户请求，调用Model处理数据，并将结果传递给View展示。'},
    {'type': 'choice', 'stem': '在分层DFD图中，1层图是对0层图中的哪个元素的分解？',
     'options': {'A': '外部实体', 'B': '数据存储', 'C': '加工', 'D': '数据流'},
     'answer': 'C'},
    # 判断题
    {'type': 'judge', 'stem': '软件体系结构仅关注系统的功能模块划分，不涉及模块间的交互关系。', 'answer': '错',
     'explanation': '软件体系结构不仅包括功能模块划分，还需明确模块间的交互方式、拓扑结构等关系。'},
    {'type': 'judge', 'stem': 'MVC模式中的视图组件负责处理业务逻辑计算。', 'answer': '错',
     'explanation': 'MVC模式中，视图仅负责数据展示，业务逻辑计算由模型组件处理。'},
    # 多选题
    {'type': 'multi', 'stem': 'MVC模式的组成部分包括以下哪些？',
     'options': {'A': 'Model', 'B': 'View', 'C': 'Controller', 'D': 'Service'},
     'answer': 'ABC',
     'explanation': 'MVC模式由Model、View、Controller三部分组成，Service不属于MVC的核心组成。'},
    {'type': 'multi', 'stem': '常用的软件设计模式分类包括？',
     'options': {'A': '创建型模式', 'B': '结构型模式', 'C': '行为型模式', 'D': '逻辑型模式'},
     'answer': 'ABC'},
    {'type': 'multi', 'stem': '高可信软件通常具备的性质有？',
     'options': {'A': '可靠性', 'B': '安全性', 'C': '可预测性', 'D': '高效性'},
     'answer': 'ABC',
     'explanation': '高可信软件的核心性质包括可靠性、安全性、可预测性；高效性属于性能属性。'},
    {'type': 'multi', 'stem': '以下属于软件质量模型（如ISO/IEC 25010）中功能性子特征的有哪些？',
     'options': {'A': '适合性', 'B': '准确性', 'C': '互操作性', 'D': '可靠性'},
     'answer': 'ABC',
     'explanation': '可靠性属于独立的质量特性，不属于功能性子特征。'},
    {'type': 'multi', 'stem': 'B/S架构相比C/S架构的优势在于？',
     'options': {'A': '客户端无需安装专用软件', 'B': '部署维护成本低', 'C': '网络传输数据量小', 'D': '跨平台兼容性好'},
     'answer': 'ABD',
     'explanation': 'B/S架构依赖网络传输页面数据，数据量通常大于C/S架构。'},
    {'type': 'multi', 'stem': '面向对象方法用于系统开发的优势包括哪些？',
     'options': {'A': '良好的可复用性', 'B': '增强系统可维护性', 'C': '支持增量式开发', 'D': '降低开发成本'},
     'answer': 'ABC',
     'explanation': '面向对象方法初期设计成本可能较高，不一定直接降低总成本。'},
    # 填空题（DOCX新增）
    {'type': 'fill', 'stem': '数据库事务的ACID特性中，_______保证事务执行前后数据的完整性约束不被破坏。', 'answer': '一致性'},
    {'type': 'fill', 'stem': '一个子类同时继承多个父类的特性，这种继承方式称为_______。', 'answer': '多重继承'},
    {'type': 'fill', 'stem': 'OOA的核心是_______，OOD的核心是_______。', 'answer': '建立系统的对象模型；设计系统的实现架构'},
    {'type': 'fill', 'stem': 'MVC模式中，_______负责封装数据与业务逻辑，_______负责展示数据界面。', 'answer': 'Model；View'},
    {'type': 'fill', 'stem': '在_______软件体系结构中，组件通过_______传递数据，每个组件对输入数据进行处理后产生输出。', 'answer': '管道-过滤器；数据流'},
]

for q in docx_questions:
    key = (q['type'], normalize_stem(q['stem']))
    if key not in all_questions:
        all_questions[key] = q
    else:
        existing = all_questions[key]
        if not existing.get('explanation') and q.get('explanation'):
            all_questions[key] = q

# ========== 输出标准格式文件 ==========

def write_choice_judge_multi_file(filepath, questions):
    """写入选择+判断+多选标准格式文件"""
    choice_qs = [q for q in questions if q['type'] == 'choice']
    judge_qs = [q for q in questions if q['type'] == 'judge']
    multi_qs = [q for q in questions if q['type'] == 'multi']
    
    lines = ['# 题库名称：软件设计期末（选择判断多选）']
    
    if choice_qs:
        lines.append('\n## 章节：选择题')
        for q in choice_qs:
            lines.append(f'\n### [选择] {q["stem"]}')
            if q.get('options'):
                for letter in ['A', 'B', 'C', 'D']:
                    if letter in q['options']:
                        lines.append(f'{letter}. {q["options"][letter]}')
            lines.append(f'答案：{q["answer"]}')
            if q.get('explanation'):
                lines.append(f'解析：{q["explanation"]}')
    
    if judge_qs:
        lines.append('\n## 章节：判断题')
        for q in judge_qs:
            lines.append(f'\n### [判断] {q["stem"]}')
            lines.append(f'答案：{q["answer"]}')
            if q.get('explanation'):
                lines.append(f'解析：{q["explanation"]}')
    
    if multi_qs:
        lines.append('\n## 章节：多选题')
        for q in multi_qs:
            lines.append(f'\n### [多选] {q["stem"]}')
            if q.get('options'):
                for letter in ['A', 'B', 'C', 'D']:
                    if letter in q['options']:
                        lines.append(f'{letter}. {q["options"][letter]}')
            lines.append(f'答案：{q["answer"]}')
            if q.get('explanation'):
                lines.append(f'解析：{q["explanation"]}')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    return len(choice_qs), len(judge_qs), len(multi_qs)

def write_fill_file(filepath, questions):
    """写入填空题标准格式文件"""
    fill_qs = [q for q in questions if q['type'] == 'fill']
    
    lines = ['# 题库名称：软件设计期末（填空）']
    lines.append('\n## 章节：填空题')
    for q in fill_qs:
        lines.append(f'\n### [填空] {q["stem"]}')
        lines.append(f'答案：{q["answer"]}')
        if q.get('explanation'):
            lines.append(f'解析：{q["explanation"]}')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    return len(fill_qs)

def write_short_answer_file(filepath, questions):
    """写入简答题标准格式文件"""
    sa_qs = [q for q in questions if q['type'] == 'short_answer']
    
    lines = ['# 题库名称：软件设计期末简答题']
    lines.append('\n## 章节：软件设计与体系结构')
    for q in sa_qs:
        lines.append(f'\n### [简答] {q["stem"]}')
        lines.append(f'答案：{q["answer"]}')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    return len(sa_qs)

# 排序题目（按题干排序便于查找）
sorted_questions = sorted(all_questions.values(), key=lambda q: normalize_stem(q['stem']))

# 写入文件
cjm_path = os.path.join(OUTPUT_DIR, '软件设计期末选择判断多选.txt')
fill_path = os.path.join(OUTPUT_DIR, '软件设计期末填空.txt')
sa_path = os.path.join(OUTPUT_DIR, '软件设计期末简答题.txt')

cjm_count = write_choice_judge_multi_file(cjm_path, sorted_questions)
fill_count = write_fill_file(fill_path, sorted_questions)
sa_count = write_short_answer_file(sa_path, sorted_questions)

print(f'软件设计期末选择判断多选.txt: {cjm_count[0]}选择 + {cjm_count[1]}判断 + {cjm_count[2]}多选 = {sum(cjm_count)}题')
print(f'软件设计期末填空.txt: {fill_count}题')
print(f'软件设计期末简答题.txt: {sa_count}题')
print(f'总计: {sum(cjm_count) + fill_count + sa_count}题')
print()
print('查重结果:')
print(f'  合并前总题目数（含重复）: 需手动统计')
print(f'  合并后去重题目数: {len(all_questions)}题')

# 打印被去重的题目（如果有）
# 找出哪些题干被合并了（相同normalized stem出现多次）
stem_counts = {}
for q in sorted_questions:
    key = (q['type'], normalize_stem(q['stem']))
    stem_counts[key] = stem_counts.get(key, 0) + 1

duplicates = {k: v for k, v in stem_counts.items() if v > 1}
if duplicates:
    print(f'\n发现重复题干（已合并）:')
    for (qtype, stem), count in duplicates.items():
        print(f'  [{qtype}] {stem[:60]}... (出现{count}次)')
