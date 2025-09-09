from __future__ import annotations
from flask import Flask, request, jsonify, send_from_directory
import ast
import operator as op
import math

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Allowed operators and nodes
ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
}
ALLOWED_UNARYOPS = {ast.UAdd: op.pos, ast.USub: op.neg}
ALLOWED_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,     # natural log
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
}
ALLOWED_NAMES = {
    "pi": math.pi,
    "e": math.e,
}

class SafeEval(ast.NodeVisitor):
    def visit(self, node):
        return super().visit(node)

    def visit_Expr(self, node: ast.Expr):
        return self.visit(node.value)

    def visit_Module(self, node: ast.Module):
        if len(node.body) != 1:
            raise ValueError("Only one expression allowed")
        return self.visit(node.body[0])

    def visit_BinOp(self, node: ast.BinOp):
        if type(node.op) not in ALLOWED_BINOPS:
            raise ValueError("Operator not allowed")
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            return ALLOWED_BINOPS[type(node.op)](left, right)
        except ZeroDivisionError:
            raise ValueError("Division by zero")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        if type(node.op) not in ALLOWED_UNARYOPS:
            raise ValueError("Unary operator not allowed")
        operand = self.visit(node.operand)
        return ALLOWED_UNARYOPS[type(node.op)](operand)

    def visit_Num(self, node: ast.Num):  # Py<3.8 compatibility
        return node.n

    def visit_Constant(self, node: ast.Constant):  # Py>=3.8
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numbers allowed as constants")

    def visit_Name(self, node: ast.Name):
        if node.id in ALLOWED_NAMES:
            return ALLOWED_NAMES[node.id]
        raise ValueError(f"Unknown symbol: {node.id}")

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only function names allowed")
        fname = node.func.id
        if fname not in ALLOWED_FUNCS:
            raise ValueError(f"Function not allowed: {fname}")
        args = [self.visit(a) for a in node.args]
        if node.keywords:
            raise ValueError("Keyword arguments not supported")
        return ALLOWED_FUNCS[fname](*args)

    def generic_visit(self, node):
        raise ValueError("Syntax not allowed")


def safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="exec")
    return SafeEval().visit(tree)


@app.route("/")
def index():
    # Serve static index.html
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/calculate")
def calculate():
    data = request.get_json(silent=True) or {}
    expr = str(data.get("expression", "")).strip()
    if not expr:
        return jsonify({"ok": False, "error": "Empty expression"}), 400
    try:
        result = safe_eval(expr)
        if result == 0:
            result = 0.0
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
