import collections
import os
import configparser
import zlib
import hashlib

class GitRepository():

    workTree=None
    gitDir=None
    conf=None

    def __init__(self,path,force=False):

        self.workTree=path
        self.gitDir=os.path.join(self.workTree,".git")
        
        if not (force or os.path.isdir(self.gitDir)):
            raise Exception("Not a git repository ",{self.workTree})
        
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


class GitObject(object):

    def __init__(self,data=None):
        if data!=None:
            self.deserialize(data)
        else:
            self.init()    

    def serialize(self,repo):
        raise Exception("Must be implemented")

    def deserialize(self,data):
        raise Exception("Must be implemented")
    
    def init(self):
        pass


class GitBlob(GitObject):
    fmt=b'blob'

    def serialize(self):
        return self.blobdata
    
    def deserialize(self, data):
        self.blobdata=data


class GitCommit(GitObject):
    fmt=b'commit'
    
    def init(self):
        self.kvlm=dict()

    def deserialize(self, data):
        self.kvlm=kvlm_parser(data)
        
    def serialize(self):
        return kvlm_serialize(self.kvlm)
    

class GitTreeLeaf(object):
    def __init__(self,mode,path,sha):
        self.mode=mode
        self.path=path
        self.sha=sha


class GitTree(GitObject):
    fmt=b'tree'

    def deserialize(self, data):
        self.items=tree_parse(data)

    def serialize(self):
        return tree_serialize(self)

    def init(self):
        self.items=list()


def repo_path(repo,*path):
    return os.path.join(repo.gitDir,*path)


def repo_file(repo,*path,mkdir=False):
    if repo_dir(repo,*path[:-1],mkdir=mkdir):
        return repo_path(repo,*path)


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


def repo_find(path=".",required=True):
    path=os.path.realpath(path)

    if os.path.isdir(os.path.join(path,".git")):
        return GitRepository(path)
    
    parent = os.path.realpath(os.path.join(path,".."))
    
    if parent == path:
        if required:
            raise Exception("No git directory")
        else :
            return None
    
    return repo_find(parent,required)


def object_read(repo,sha):
    path=repo_file(repo,"objects",sha[:2],sha[2:])
    if not os.path.isfile(path):
        return None
    
    with open(path,"rb") as f:
        raw=zlib.decompress(f.read())
        
        x=raw.find(b' ')
        fmt=raw[:x]

        y=raw.find(b'\x00',x)
        size=int(raw[x:y].decode('ascii'))

        if size!=len(raw)-y-1:
            raise Exception("Malformed object {0}:bad length".format(sha))
        
        match fmt:
            case b'commit' : c=GitCommit
            case b'tree' : c=GitTree
            case b'tag' : c=GitTag
            case b'blob' : c=GitBlob
            case _:
                raise Exception("Unkown type {0} for object {1}".format(fmt.decode("ascii"),sha))
            
        return c(raw[y+1:])


def object_write(obj,repo=None):
    data=obj.serialize()
    result=obj.fmt+b' '+str(len(data)).encode()+b'\x00'+data
    sha=hashlib.sha1(result).hexdigest()

    if repo:
        path=repo_file(repo,"objects",sha[:2],sha[2:],mkdir=True)
        if not os.path.exists(path):
            with open(path,'rb')as f:
                f.write(zlib.compress(result))
        
    return sha


def kvlm_parser(raw,start=0,dct=None):
    if not dct:
        dct=collections.OrderedDict()
    
    spc=raw.find(b' ',start)
    nl=raw.find(b'\n',start)

    if(spc<0)or nl<spc:
        assert nl==start
        dct[None]=raw[start+1:]
        return dct
    
    key=raw[start:spc]
    end=spc
    
    while True:
        end=raw.find(b'\n',end+1)
        if(raw[end+1]!=ord(' ')):break
    
    value=raw[spc+1:end].replace(b'\n ',b'\n')
    
    if key in dct:
        if type(dct[key])==list:
            dct[key].append(value)
        else:
            dct[key]=[dct[key],value]
    else:
        dct[key]=value

    return kvlm_parser(raw,start=end+1,dct=dct)


def kvlm_serialize(kvlm):
    ret=b''
    
    for k in kvlm.keys():
        if k==None:
            continue
        val=kvlm[k]

        if type(val)!=list:
            val=[val]
        
        for v in val:
            ret+=k+b' '+(v.replace(b'\n',b'\n '))+b'\n'
    
    ret+=b'\n'+kvlm[None]+b'\n'

    return ret


def tree_parse_one(raw,start=0):
    x=raw.find(b' ',start)
    assert x-start==5 or x-start==6
    mode=raw[start:x]
    if len(mode)==5:
        mode = b" "+mode
    y=raw.find(b'\x00',x)
    path=raw[x+1:y]
    sha=format(int.from_bytes(raw[y+1:y+21],"big"),"040x")
    return y+21,GitTreeLeaf(mode,path.decode("utf8"),sha)


def tree_parse(raw):
    pos=0
    max=len(raw)
    ret=list()
    while pos<max:
        pos,data=tree_parse_one(raw,pos)
        ret.append(data)
    return ret


def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"10"):
        return leaf.path
    return leaf.path+"/"


def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    ret = b''
    for i in obj.items():
        ret+=i.mode+b' '+i.path.encode("utf8")+b'\x00'
        sha=int(i.sha,16)
        ret+=sha.to_bytes(20,byteorder="big")

    return ret