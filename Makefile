.PHONY: install test run deploy

PYTHON := ./venv/Scripts/python.exe

install:
	@if [ ! -f ./venv/Scripts/python.exe ]; then \
		python -m venv venv; \
	fi
	$(PYTHON) -m pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

test:
	$(PYTHON) -m pytest tests -p no:warnings

run:
	$(PYTHON) app.py

# 服务器上用 gunicorn 起（入口是 wsgi.py）：
#   gunicorn -w 4 -b 0.0.0.0:8080 wsgi:app

deploy:
	bash deploy.sh
