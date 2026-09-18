#!/bin/bash
# 刷题网站一键部署脚本
# 用法：上传 quiz-deploy.tar.gz 到 /opt/ 后执行 bash deploy.sh

set -e

APP_DIR="/opt/quiz-app"
TAR_FILE="${APP_DIR}/../quiz-deploy.tar.gz"
VENV_DIR="${APP_DIR}/venv"

echo "=== 刷题网站部署脚本 ==="

# 1. 创建目录
echo "[1/6] 创建应用目录..."
mkdir -p ${APP_DIR}
mkdir -p ${APP_DIR}/logs

# 2. 解压
echo "[2/6] 解压部署包..."
if [ -f "${TAR_FILE}" ]; then
    tar -xzf "${TAR_FILE}" -C ${APP_DIR} --strip-components=1
    echo "     解压完成"
else
    echo "     未找到 ${TAR_FILE}，请先上传部署包"
    exit 1
fi

# 3. Python 虚拟环境
echo "[3/6] 配置 Python 环境..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv ${VENV_DIR}
fi
source ${VENV_DIR}/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r ${APP_DIR}/requirements.txt
echo "     依赖安装完成"

# 4. 文件权限
echo "[4/6] 设置文件权限..."
chown -R root:root ${APP_DIR}
chmod 644 ${APP_DIR}/*.py ${APP_DIR}/*.txt ${APP_DIR}/*.sh ${APP_DIR}/*.conf.py 2>/dev/null || true
chmod -R 755 ${APP_DIR}/static ${APP_DIR}/templates
chmod 666 ${APP_DIR}/quiz.db 2>/dev/null || true

# 5. 安装/重启 systemd 服务
echo "[5/6] 配置系统服务..."
cat > /etc/systemd/system/quiz-app.service << 'EOF'
[Unit]
Description=Quiz App (Flask + Gunicorn)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/quiz-app
Environment="PATH=/opt/quiz-app/venv/bin"
ExecStart=/opt/quiz-app/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable quiz-app
systemctl restart quiz-app

# 6. 防火墙
echo "[6/6] 配置防火墙..."
firewall-cmd --add-port=5000/tcp --permanent 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "常用命令:"
echo "  查看状态: systemctl status quiz-app"
echo "  查看日志: journalctl -u quiz-app -f"
echo "  重启服务: systemctl restart quiz-app"
echo "  停止服务: systemctl stop quiz-app"
