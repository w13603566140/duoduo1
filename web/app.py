"""
Flask Web应用工厂
"""
from flask import Flask
from config import config as app_config


def create_app() -> Flask:
    """创建并配置Flask应用"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "pdd-monitor-secret-key-2024"

    # 注册路由
    from web.routes import routes_bp
    from web.api import api_bp

    app.register_blueprint(routes_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # 在模板中注入配置
    @app.context_processor
    def inject_config():
        return {
            "search_keyword": app_config.search_keyword,
            "web_port": app_config.web_port,
        }

    return app
