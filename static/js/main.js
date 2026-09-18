/* ===== 刷题主交互逻辑 ===== */

let curIndex = 0;
let correctCount = 0;
let wrongCount = 0;
let answered = false;

document.addEventListener('DOMContentLoaded', function() {
    if (typeof QUESTIONS === 'undefined' || QUESTIONS.length === 0) {
        document.getElementById('question-area').innerHTML =
            '<div class="empty-state"><p>没有题目</p></div>';
        return;
    }
    renderQuestion();
});

function renderQuestion() {
    const q = QUESTIONS[curIndex];
    answered = false;

    // 更新进度
    const total = QUESTIONS.length;
    document.getElementById('cur-num').textContent = curIndex + 1;
    document.getElementById('progress-fill').style.width = ((curIndex) / total * 100) + '%';
    document.getElementById('score-correct').textContent = correctCount;
    document.getElementById('score-wrong').textContent = wrongCount;

    let html = '<div class="question-card">';

    if (q.chapter) {
        html += '<div class="question-chapter">' + escapeHtml(q.chapter) + '</div>';
    }

    // 收藏按钮
    var isFav = (typeof FAVORITE_IDS !== 'undefined' && FAVORITE_IDS && FAVORITE_IDS.indexOf(q.id) !== -1);
    html += '<div class="fav-btn-wrap"><button class="fav-btn' + (isFav ? ' favorited' : '') + '" id="fav-btn" onclick="toggleFavorite(' + q.id + ')">' + (isFav ? '★ 已收藏' : '☆ 收藏') + '</button></div>';

    html += '<div class="question-stem">' + escapeHtml(q.stem) + '</div>';

    if (q.type === 'choice') {
        html += '<div class="option-list" id="option-list">';
        q.options.forEach(function(opt) {
            html += '<div class="option-item" data-letter="' + opt.letter + '" data-text="' + escapeAttr(opt.text) + '" onclick="selectOption(this, false)">' +
                '<div class="option-letter">' + opt.letter + '</div>' +
                '<div class="option-text">' + escapeHtml(opt.text) + '</div>' +
                '</div>';
        });
        html += '</div>';
    } else if (q.type === 'multi') {
        html += '<div class="option-list" id="option-list">';
        q.options.forEach(function(opt) {
            html += '<div class="option-item" data-letter="' + opt.letter + '" data-text="' + escapeAttr(opt.text) + '" onclick="selectOption(this, true)">' +
                '<div class="option-letter">' + opt.letter + '</div>' +
                '<div class="option-text">' + escapeHtml(opt.text) + '</div>' +
                '</div>';
        });
        html += '</div>';
        html += '<p style="font-size:13px;color:var(--text-light);margin-top:12px;">提示：可多选，选完点击提交</p>';
    } else if (q.type === 'judge') {
        html += '<div class="judge-buttons">';
        html += '<button class="judge-btn" data-val="对" onclick="selectJudge(this)">对</button>';
        html += '<button class="judge-btn" data-val="错" onclick="selectJudge(this)">错</button>';
        html += '</div>';
    } else if (q.type === 'fill') {
        html += '<input type="text" class="fill-input" id="fill-input" placeholder="输入答案，按回车提交">';
    } else if (q.type === 'short_answer') {
        html += '<textarea class="fill-input" id="fill-input" rows="4" placeholder="输入答案，按回车提交（可将输入框右下角拖大）"></textarea>';
    }

    html += '<div class="submit-area">';
    html += '<button class="btn-submit" id="submit-btn" onclick="submitAnswer()" disabled>提交</button>';
    html += '</div>';

    html += '<div class="feedback" id="feedback"></div>';

    html += '</div>';

    document.getElementById('question-area').innerHTML = html;

    // 填空题/简答题：回车提交
    if (q.type === 'fill' || q.type === 'short_answer') {
        var inputEl = document.getElementById('fill-input');
        inputEl.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey && !answered) {
                e.preventDefault();
                submitAnswer();
            }
        });
        inputEl.addEventListener('input', function() {
            document.getElementById('submit-btn').disabled = (this.value.trim() === '');
        });
    }
}

// 选择题/多选题选项点击
function selectOption(el, isMulti) {
    if (answered) return;
    if (isMulti) {
        el.classList.toggle('selected');
        // 多选题：有选中就启用提交
        const anySelected = document.querySelectorAll('.option-item.selected').length > 0;
        document.getElementById('submit-btn').disabled = !anySelected;
    } else {
        document.querySelectorAll('.option-item').forEach(function(item) {
            item.classList.remove('selected');
        });
        el.classList.add('selected');
        document.getElementById('submit-btn').disabled = false;
    }
}

// 判断题按钮
function selectJudge(el) {
    if (answered) return;
    document.querySelectorAll('.judge-btn').forEach(function(btn) {
        btn.classList.remove('selected');
    });
    el.classList.add('selected');
    document.getElementById('submit-btn').disabled = false;
}

// 提交答案
function submitAnswer() {
    if (answered) {
        nextQuestion();
        return;
    }

    const q = QUESTIONS[curIndex];
    let userAnswer = '';

    if (q.type === 'choice') {
        const selected = document.querySelector('.option-item.selected');
        if (!selected) return;
        userAnswer = selected.dataset.letter;
    } else if (q.type === 'multi') {
        const selected = document.querySelectorAll('.option-item.selected');
        if (selected.length === 0) return;
        userAnswer = Array.from(selected).map(function(el) {
            return el.dataset.letter;
        }).join('');
    } else if (q.type === 'judge') {
        const selected = document.querySelector('.judge-btn.selected');
        if (!selected) return;
        userAnswer = selected.dataset.val;
    } else if (q.type === 'fill' || q.type === 'short_answer') {
        const input = document.getElementById('fill-input');
        userAnswer = input.value.trim();
        if (!userAnswer) return;
    }

    // 发送判分请求
    fetch(CHECK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            question_id: q.id,
            user_answer: userAnswer
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        answered = true;
        showResult(q, userAnswer, data);
    })
    .catch(function(err) {
        alert('提交失败，请重试');
    });
}

// 显示判分结果
function showResult(q, userAnswer, data) {
    const feedback = document.getElementById('feedback');
    const submitBtn = document.getElementById('submit-btn');

    if (data.is_correct) {
        correctCount++;
        feedback.className = 'feedback show correct';
        feedback.innerHTML = '✓ 回答正确！';
    } else {
        wrongCount++;
        feedback.className = 'feedback show wrong';
        feedback.innerHTML = '✗ 回答错误<br>正确答案：' + escapeHtml(data.correct_answer);
    }

    // 高亮选项
    if (q.type === 'choice') {
        document.querySelectorAll('.option-item').forEach(function(item) {
            item.style.pointerEvents = 'none';
            // 标记正确选项（通过比对正确答案内容）
            // 由于选项已打乱，我们用 correct_answer 字段判断
        });
        // 标记用户选择的对错
        const userSel = document.querySelector('.option-item.selected');
        if (data.is_correct) {
            userSel.classList.add('correct');
        } else {
            userSel.classList.add('wrong');
        }
    } else if (q.type === 'multi') {
        document.querySelectorAll('.option-item').forEach(function(item) {
            item.style.pointerEvents = 'none';
            if (data.is_correct) {
                item.classList.add('correct');
            } else {
                if (item.classList.contains('selected')) {
                    item.classList.add('wrong');
                }
            }
        });
    } else if (q.type === 'judge') {
        document.querySelectorAll('.judge-btn').forEach(function(btn) {
            btn.style.pointerEvents = 'none';
        });
        const userSel = document.querySelector('.judge-btn.selected');
        if (data.is_correct) {
            userSel.classList.add('correct');
        } else {
            userSel.classList.add('wrong');
            // 标记正确那个
            document.querySelectorAll('.judge-btn').forEach(function(btn) {
                if (btn.dataset.val !== userSel.dataset.val) {
                    btn.classList.add('correct');
                }
            });
        }
    } else if (q.type === 'fill' || q.type === 'short_answer') {
        const input = document.getElementById('fill-input');
        input.disabled = true;
        if (data.is_correct) {
            input.classList.add('correct');
        } else {
            input.classList.add('wrong');
        }
    }

    // 更新分数
    document.getElementById('score-correct').textContent = correctCount;
    document.getElementById('score-wrong').textContent = wrongCount;
    document.getElementById('progress-fill').style.width = ((curIndex + 1) / QUESTIONS.length * 100) + '%';

    // 改变按钮文字
    if (curIndex < QUESTIONS.length - 1) {
        submitBtn.textContent = '下一题 →';
    } else {
        submitBtn.textContent = '查看结果 →';
    }
    submitBtn.disabled = false;
}

// 下一题
function nextQuestion() {
    curIndex++;
    if (curIndex >= QUESTIONS.length) {
        showFinish();
        return;
    }
    renderQuestion();
}

// 完成页
function showFinish() {
    const total = QUESTIONS.length;
    const rate = Math.round(correctCount / total * 100);

    const quizId = document.getElementById('quiz-id').value;
    const qType = document.getElementById('q-type').value;
    const isWrong = document.getElementById('is-wrong-practice') !== null;
    const isFav = (qType === 'favorite');

    let html = '<div class="finish-card">';
    html += '<div style="font-size:16px;color:var(--text-light);">' + (isFav ? '收藏练习完成' : (isWrong ? '错题练习完成' : '练习完成')) + '</div>';
    html += '<div class="finish-score">' + rate + '%</div>';
    html += '<div class="finish-stats">共 ' + total + ' 题 · 正确 ' + correctCount + ' · 错误 ' + wrongCount + '</div>';
    html += '<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">';
    if (isFav) {
        html += '<a href="/favorites/' + quizId + '/practice" class="btn btn-primary">再来一轮</a>';
        html += '<a href="/favorites" class="btn btn-outline">返回收藏</a>';
    } else if (isWrong) {
        html += '<a href="/quiz/' + quizId + '/wrongbook/' + qType + '/practice" class="btn btn-primary">再来一轮</a>';
        html += '<a href="/quiz/' + quizId + '/wrongbook" class="btn btn-outline">返回错题本</a>';
    } else {
        html += '<a href="/quiz/' + quizId + '/practice/' + qType + '" class="btn btn-primary">再来一轮</a>';
        html += '<a href="/quiz/' + quizId + '/wrongbook" class="btn btn-outline">查看错题</a>';
    }
    html += '<a href="/quiz/' + quizId + '" class="btn btn-outline">返回菜单</a>';
    html += '</div>';
    html += '</div>';

    document.getElementById('practice-area').innerHTML = html;
}

// HTML转义
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function escapeAttr(text) {
    if (text === null || text === undefined) return '';
    return String(text).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// 收藏/取消收藏
function toggleFavorite(questionId) {
    fetch(FAVORITE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        var btn = document.getElementById('fav-btn');
        if (data.favorited) {
            btn.classList.add('favorited');
            btn.textContent = '★ 已收藏';
            if (typeof FAVORITE_IDS !== 'undefined') {
                FAVORITE_IDS.push(questionId);
            }
        } else {
            btn.classList.remove('favorited');
            btn.textContent = '☆ 收藏';
            if (typeof FAVORITE_IDS !== 'undefined') {
                var idx = FAVORITE_IDS.indexOf(questionId);
                if (idx !== -1) FAVORITE_IDS.splice(idx, 1);
            }
        }
    })
    .catch(function(err) {
        alert('操作失败，请重试');
    });
}
