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
import operator


class colors:
    '''Colors class:
    reset all colors with colors.reset
    
    '''
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    fg = {
        "red" : '\033[31m',
        "green" : '\033[32m',
        "blue" : '\033[34m',
        "cyan" :'\033[36m',
        "yellow" :'\033[93m',
        "default": '',
    }

class Command:

    def __init__(self):
        self.indentstr = "|-"
        self.indent = 0

    def getColor(self,color):
        if(color in colors.fg):
            return colors.fg[color]
        else:
            return colors.fg["default"]

    def getIndent(self,nextindent=None):

        if(nextindent is None):
            nextindent = self.indent
        
        if(nextindent == 0):
            return ""
        else:
            return self.indentstr + self.getIndent(nextindent-1)

    def comment(self,ss,color="green"):
        print(self.getIndent() + self.getColor(color) + ss  + colors.reset)

    def warning(self,ss):
        self.comment(ss,"yellow")

    def error(self,ss):
        ss_h = "Error: "
        self.comment(ss_h + ss,"red")

    def doCmd(self,cmd):
        os.system(cmd)

    def doCmdWithReturn(self,cmd):
        result = os.popen(cmd + " 2>&1").read()
        return result

    def sub(self,buffer,keyval):
        """Replace ${NAME} constructs in buffer with values from 'dict' or shell environment"""
        for (k,v) in keyval.items():
            buffer = re.sub('\${%s}'%k,v,buffer)
        m = re.search('\${([^}]+)}',buffer)
        if(m):
            for var in m.groups():
                val = os.getenv(var)
                if(val):
                    buffer = re.sub('\${%s}' %var,val,buffer)
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
            elif isinstance(node, ast.Str):
                return node.s
            elif isinstance(node, ast.Num):
                return node.value
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
