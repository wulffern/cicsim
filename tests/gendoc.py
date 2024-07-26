#!/usr/bin/env python3
import click
import os
import yaml
import re
import cicsim as cs

class GenDoc(cs.Command):


    def run_image(self,buff,odir):
        obj = yaml.safe_load(buff)
        ss = "```bash\n" + obj["run"] + "\n```\n\n"
        iurl = obj["output_image"]
        ourl = odir + os.path.sep + "assets"+ os.path.sep + iurl

        if(not os.path.exists(ourl)):
            os.system(obj["run"])
            os.system("cp " + iurl + " " + ourl)

        ss += f"![](/cicsim/assets/{iurl})"
        return ss

    def cat(self,buff,odir):
        obj = yaml.safe_load(buff)
        finame = obj["file"]
        if("lines" in obj):
            lines = obj["lines"]
        else:
            lines = None

        if("linenumbers" in obj):
            linenumbers = True
        else:
            linenumbers = False


        linenr= 0
        ss = ""
        with open(finame) as fi:
            for line in fi:
                if(lines is not None and lines < linenr):
                    continue
                if(linenumbers):
                    ss += str(linenr) + " " + line
                else:
                    ss += line
                linenr +=1


        if("language" in obj):
            language = obj["language"]
        else:
            language = ""

        if(language == "markdown"):
            return  ss +"\n\n"
        else:
            return finame + ":\n" + f"```{language}\n" + ss + "\n```\n\n"

    def run_output(self,buff,odir):
        obj = yaml.safe_load(buff)

        ss = "```bash\n" + obj["run"] + "\n```\n\n"

        ss += "```bash\n" + self.doCmdWithReturn(obj["run"]) + "\n```\n\n"
        return ss


    def cli(self,finame,foname):
        odir = os.path.dirname(foname)
        isCmd = False
        cmd = ""
        buff = ""
        with open(finame) as fi:
            with open(foname,"w") as fo:
                for line in fi:
                    if(re.search("^-->",line)):
                        isCmd = False
                        try:
                            o = getattr(self,cmd)
                        except Exception as e:
                            print(e)
                            self.error("Don't know how to support command '%s'" %cmd)
                            o = None
                        if(o):
                            fo.write(o(buff,odir))
                        cmd = ""
                        buff = ""


                        continue

                    if(isCmd):
                        buff += line
                        continue

                    m = re.search("^<!--([^:]+):",line)
                    if(m):
                        buff = ""
                        isCmd = True
                        cmd  = m.group(1)
                        continue

                    fo.write(line)




@click.command()
@click.argument("finame")
@click.argument("foname")
def cli(finame,foname):
    g = GenDoc()
    g.cli(finame,foname)


        




if __name__ == "__main__":
    cli()
