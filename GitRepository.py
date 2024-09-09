import os
import configparser

class GitRepository():

    workTree=None
    gitDir=None
    conf=None

    def __init__(self,path,force=False):

        workTree=path
        gitDir=os.path.join(self.workTree,".git")
        
        if force==False or not os.path.isdir(self.gitDir):
            raise Exception(f"Not a git repository {self.workTree}")
        
        self.conf=configparser.ConfigParser()
        cf=repo_file(self,"config")
        
        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif force==False:
            raise Exception("Configaration file is missing")
        
        if force==False:
            vers=int(self.conf.get("core","repositoryformatversion"))
            
            if(vers!=0):
                raise Exception(f"Unsupported repositoryformatversion {vers}")



def repo_path(repo,*path):
    return os.path.join(repo.gitDir,*path)


def repo_dir(repo,*path,mkdir=False):
    path=repo_path(repo,*path)
    
    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception(f"Not a directory {path}")
    
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_file(repo,*path,mkdir=False):
    if repo_dir(repo,*path[:-1],mkdir=mkdir):
        return repo_path(repo,*path)


def repo_default_config():
    ret=configparser.ConfigParser()
    
    ret.add_section("core")
    ret.set("core","repositoryformatversion","0")
    ret.set("core","filemode","false")
    ret.set("core","bare","false")

    return ret


def repo_create(path):
    repo = GitRepository(path,True)

    if os.path.exists(repo.workTree):
        if not os.path.isdir(repo.workTree):
            raise Exception(f"{repo.workTree} is not a directory")
        if os.path.exists(repo.gitDir) and os.listdir(repo.gitDir):
            raise Exception(f"{repo.gitDir} is not empty")
    else:
        os.makedirs(repo.workTree)
    
    assert repo_dir(repo,"branches",mkdir=True)
    assert repo_dir(repo,"objects",mkdir=True)
    assert repo_dir(repo,"refs","tags",mkdir=True)
    assert repo_dir(repo,"refs","head",mkdir=True)

    with open(repo_file(repo,"description"),"w")as f:
        f.write("Unammed repository.\nEdit this file 'description' to name the repository")
    
    with open(repo_file(repo,"HEAD"),"w")as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo,"config"),"w")as f:
        config=repo_default_config()
        config.write(f)
    
    return repo


    
    