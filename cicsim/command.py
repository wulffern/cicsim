######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-24
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################

import os
import re
import ast
import logging
import math
import operator
import subprocess
from contextlib import contextmanager

@contextmanager
def suppress_console_logging(name="cicsim"):
    """Temporarily remove StreamHandlers and disable propagation so tqdm owns the terminal."""
    log = logging.getLogger(name)
    stream_handlers = [h for h in log.handlers if isinstance(h, logging.StreamHandler)]
    old_propagate = log.propagate
    for h in stream_handlers:
        log.removeHandler(h)
    log.propagate = False
    try:
        yield
    finally:
        for h in stream_handlers:
            log.addHandler(h)
        log.propagate = old_propagate

logger = logging.getLogger("cicsim")


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: '\033[36m',
        logging.INFO: '\033[32m',
        logging.WARNING: '\033[93m',
        logging.ERROR: '\033[31m',
        logging.CRITICAL: '\033[31m',
    }
    RESET = '\033[0m'

    def format(self, record):
        msg = super().format(record)
        color = self.COLORS.get(record.levelno, '')
        return f"{color}{msg}{self.RESET}"


def setup_logging(color=True, level=logging.INFO):
    """Configure the cicsim logger with optional colored output."""
    log = logging.getLogger("cicsim")
    log.setLevel(level)
    log.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(level)

    if color:
        formatter = ColoredFormatter("%(message)s")
    else:
        formatter = logging.Formatter("%(levelname)-7s | %(message)s")

    handler.setFormatter(formatter)
    log.addHandler(handler)


class Command:

    def __init__(self):
        pass

    def doCmd(self,cmd):
        subprocess.run(cmd, shell=True)



    @contextmanager
    def pushd(self,path):
        prev = os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(prev)


    def doCmdWithReturn(self,cmd):
        result = subprocess.run(cmd, shell=True, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        return result.stdout

    def sub(self,buffer,keyval):
        """Replace ${NAME} constructs in buffer with values from 'dict' or shell environment.
        When a value contains newlines, the replacement is indented to match the line where
        ${NAME} appears so that YAML parses the whole block as one scalar (fixes issue #26:
        first line of schematic description was lost because unindented following lines were
        parsed as new keys).
        """
        for (k,v) in keyval.items():
            s = str(v)
            if '\n' in s:
                # Preserve line indent so multi-line value is parsed as one scalar
                pattern = r'^( *)(.*?)\$\{%s\}(.*)$' % re.escape(k)
                def repl(m):
                    indent = m.group(1)
                    replacement = '\n'.join(indent + line for line in s.split('\n'))
                    return m.group(1) + m.group(2) + replacement + m.group(3)
                buffer = re.sub(pattern, repl, buffer, flags=re.MULTILINE)
            else:
                buffer = re.sub(r'\${%s}' % k, s, buffer)
        m = re.search(r'\${([^}]+)}',buffer)
        if(m):
            for var in m.groups():
                val = os.getenv(var)
                if(val):
                    if '\n' in val:
                        pattern = r'^( *)(.*?)\$\{%s\}(.*)$' % re.escape(var)
                        def repl(m):
                            indent = m.group(1)
                            replacement = '\n'.join(indent + line for line in val.split('\n'))
                            return m.group(1) + m.group(2) + replacement + m.group(3)
                        buffer = re.sub(pattern, repl, buffer, flags=re.MULTILINE)
                    else:
                        buffer = re.sub(r'\${%s}' % var, val, buffer)
        return buffer

    def safe_eval(self,s):
        #https://stackoverflow.com/questions/15197673/using-pythons-eval-vs-ast-literal-eval
        def checkmath(x, *args):
            if x not in [x for x in dir(math) if not "__" in x]:
                raise SyntaxError(f"Unknown func {x}()")
            fun = getattr(math, x)
            return fun(*args)

        binOps = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.Call: checkmath,
            ast.BinOp: ast.BinOp,
        }

        unOps = {
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
            ast.UnaryOp: ast.UnaryOp,
        }

        ops = tuple(binOps) + tuple(unOps)

        tree = ast.parse(s, mode='eval')

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                if isinstance(node.left, ops):
                    left = _eval(node.left)
                else:
                    left = node.left.value
                if isinstance(node.right, ops):
                    right = _eval(node.right)
                else:
                    right = node.right.value
                return binOps[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                if isinstance(node.operand, ops):
                    operand = _eval(node.operand)
                else:
                    operand = node.operand.value
                return unOps[type(node.op)](operand)
            elif isinstance(node, ast.Call):
                args = [_eval(x) for x in node.args]
                r = checkmath(node.func.id, *args)
                return r
            else:
                raise SyntaxError(f"Bad syntax, {type(node)}")

        return _eval(tree)
