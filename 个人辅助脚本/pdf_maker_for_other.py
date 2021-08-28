
from types import FunctionType


for name in ("world", "python"):
    func = FunctionType(compile(
        ("def hello():\n"
        "    return '{}'".format(name)),
    "<string>",
    "exec").co_consts[0], globals())

    print(func())