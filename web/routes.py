"""
页面路由 - Jinja2 模板渲染
"""
from flask import Blueprint, render_template

routes_bp = Blueprint("routes", __name__)


@routes_bp.route("/")
def dashboard():
    """主看板页面"""
    return render_template("dashboard.html")


@routes_bp.route("/products")
def products_list():
    """商品列表页面"""
    return render_template("products.html")


@routes_bp.route("/products/<int:product_id>")
def product_detail(product_id: int):
    """单个商品详情页面"""
    return render_template("product_detail.html", product_id=product_id)


@routes_bp.route("/logs")
def logs():
    """采集日志页面"""
    return render_template("logs.html")


@routes_bp.route("/settings")
def settings():
    """系统设置页面"""
    return render_template("settings.html")
