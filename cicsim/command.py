

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
        print(self.getIndent() + self.getColor(color) + ss + "\n"  + colors.reset)

    def error(self,ss):
        self.comment(ss,"red")
