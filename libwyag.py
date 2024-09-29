import argparse
import sys
from GitRepository import *
import collections



argparser = argparse.ArgumentParser(description="Hi Mom!!")

argsubparsers = argparser.add_subparsers(title="Commands",dest="command")
argsubparsers.required=True

argsp=argsubparsers.add_parser("init",help="Initialize a new, empty repository")
argsp.add_argument("path",metavar="directory",nargs="?",default=".",help="Where to create the repository.")

argsp=argsubparsers.add_parser("cat-file",help="Provide content of repository objects")
argsp.add_argument("type",metavar="type",choices=['blob','commit','tag','tree'],help="Specify the type.")
argsp.add_argument("object",metavar="object",help="The object to display.")

argsp=argsubparsers.add_parser("hash-object",help="Compute object ID and optionally creates a blob from a file")
argsp.add_argument("-t",metavar="type",dest="type",choices=['blob','commit','tag','tree'],default="blob",help="Specify the type.")
argsp.add_argument("-w",dest="write",action="store_true",help="Write the object to the database.")
argsp.add_argument("path",help="Read object from file.")

argsp=argsubparsers.add_parser("log",help="Display history of a given commit")
argsp.add_argument("commit",default="HEAD",nargs="?",help="Commit to start at.")

argsp=argsubparsers.add_parser("ls-tree",help="Pretty print a tree object")
argsp.add_argument("-r",dest="recursive",action="store_true",help="recurse into sub trees")
argsp.add_argument("tree",help="A tree-ish object")

argsp=argsubparsers.add_parser("checkout",help="Checkout a commit inside a directory")
argsp.add_argument("commit",help="The commit or tree to checkout")
argsp.add_argument("path",help="The EMPTY directory to checkout on.")

def main(argv=sys.argv[1:]):
    args=argparser.parse_args(argv)
    match args.command:
        case "add"          : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Bad command.")


def cmd_init(args):
    repo_create(args.path)


def cmd_cat_file(args):
    repo=repo_find()
    cat_file(repo,args.object,fmt=args.type.encode())


def cat_file(repo,obj,fmt=None):
    obj=object_read(repo,object_find(repo,obj,fmt=fmt))
    sys.stdout.buffer.write(obj.serialize)


def object_find(repo,name,fmt=None,follow=True):
    return name


def cmd_hash_object(args):
    if (args.write):
        repo=repo_find()
    else:
        repo=None
    with open(args.path,"rb") as fd:
        sha=object_hash(fd,args.type.encode(),repo)
        print(sha)


def object_hash(fd,fmt,repo=None):
    data=fd.read()

    match fmt:
        case b'commit' : obj=GitCommit(data)
        case b'tree' : obj=GitTree(data)
        case b'tag' : obj=GitTag(data)
        case b'blob' : obj=GitBlob(data)
        case _ : raise Exception(f"Unkown type {fmt}!")
    
    return object_write(obj,repo)


def cmd_log(args):
    repo=repo_find()
    print("digraph wyaglog{")
    print("node[shape=rect]")
    # print(repo)
    # return
    log_graphviz(repo,object_find(repo,args.commit),set())
    print("}")


def log_graphviz(repo,sha,seen):
    
    if sha in seen:
        return 
    seen.add(sha)
    commit=object_read(repo,sha)
    # print(commit)
    short_hash=sha[0:8]
    message=commit.kvlm[None].decode('utf-8').strip()
    message=message.replace("\\","\\\\")
    message=message.replace("\"","\\\"")

    if "\n" in message:
        message=message[:message.index('\n')]

    print(" c_{0} [label=\"{1}:{2}\"]".format(sha,sha[0:7],message))
    assert commit.fmt==b'commit'

    if not b'parent' in commit.kvlm.keys():
        return
    
    parents=commit.kvlm[b'parent']

    if type(parents)!=list:
        parents=[parents]
    
    for p in parents:
        p=p.decode("ascii")
        print(" c_{0} -> c_{1};".format(sha,p))
        log_graphviz(repo,p,seen)


def cmd_ls_tree(args):
    repo=repo_find()
    ls_tree(repo,args.tree,args.recursive)


def ls_tree(repo,ref,recursive=None,prefix=""):
    sha=object_find(repo,ref,fmt=b"tree")
    obj=object_read(repo,sha)

    for item in obj.items():
        if len(item.mode)==5:
            type=item.mode[0:1]
        else:
            type=item.mode[0:2]
        match type:
            case b'04':type="tree"
            case b'10':type="blob"
            case b'12':type="blob"
            case b'16':type="commit"
            case _:raise Exception(f"Weird tree leaf mode {item.mode}")

        if not(recursive and type=="tree"):
            print("{0} {1} {2}\t {3}".format("0"*(6-len(item.mode))+item.mode.decode("ascii"),type,item.sha,os.path.join(prefix,item.path)))
        else:
            ls_tree(repo,item.sha,recursive,os.path.join(prefix,item.path))

        
def cmd_checkout(args):
    repo=repo_find()
    obj=object_read(repo,object_find(repo,args.commit))

    if obj.fmt==b'commit':
        obj=object_read(repo,obj.kvlm[b'tree'].decode("ascii"))

    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not a directory {0}!".format(args.path))
        if os.listdir(args.path):
            raise Exception(f"Not an empty directory {args.path}")
    else:
        os.makedirs(args.path)

    tree_checkout(repo,obj,os.path.realpath(args.path))


def tree_checkout(repo,tree,path):
    for item in tree.items:
        obj=object_read(repo,item.sha)
        dest=os.path.join(path,item.path)

        if obj.fmt==b'tree':
            os.mkdir(dest)
            tree_checkout(repo,obj,dest)
        elif obj.fmt==b'blob':
            with open(dest,"wb") as f:
                f.write(obj.blobdata)


