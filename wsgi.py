# -*- coding: utf-8 -*-
"""Gunicorn WSGI 入口"""
from app import app

if __name__ == '__main__':
    app.run()
