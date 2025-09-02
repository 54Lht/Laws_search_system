from flask import Flask, render_template, jsonify, request, send_from_directory
import os
from find_law import FindLawProcessor

# 初始化Flask app
app = Flask(__name__)
# 初始化法律处理器（指定DOCX目录和索引文件）
law_processor = FindLawProcessor(
    pdf_dir="laws_doc",
    index_file="instance/laws_index.json"
)

# ------------------- 路由配置 -------------------
@app.route("/")
def index():
    """前端搜索页面"""
    return render_template("index.html")

@app.route("/api/law-types")
def get_law_types():
    """API：获取所有指定法律类型（用于前端下拉框）"""
    try:
        law_types = law_processor.get_law_types()
        return jsonify({
            "success": True,
            "types": law_types
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/search")
def search_law():
    """API：搜索法律内容（接收关键词和法律类型参数）"""
    try:
        keyword = request.args.get("q", "").strip()
        law_type = request.args.get("type", "all").strip()
        results = law_processor.search(keyword, law_type)
        return jsonify({
            "success": True,
            "keyword": keyword,
            "law_type": law_type,
            "total": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/laws_doc/<path:filename>')
def serve_pdf(filename):
    """提供文件访问"""
    return send_from_directory('laws_doc', filename)

# ------------------- 启动配置 -------------------
if __name__ == "__main__":
    # 确保laws_doc目录存在（存放指定DOCX文件）
    os.makedirs("laws_doc", exist_ok=True)
    # 手动构建索引
    law_processor.build_index()
    # 启动Flask（debug模式仅用于开发）
    app.run(debug=True, host="0.0.0.0", port=5000)