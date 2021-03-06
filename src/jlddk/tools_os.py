"""
    Created on 2012-01-19
    @author: jldupont
"""
import os, errno, tempfile, types, shutil
import subprocess, logging

from pyfnc import patterned, pattern, partial

def handle_path(path):
    logging.info("Resolving path: %s" % path)
    code, path=resolve_path(path)
    if not code.startswith("ok"):
        raise Exception("Can't resolve path '%s'" % path)
    
    logging.info("Creating (if necessary) path: %s" % path)
    code, _=mkdir_p(path)
    if not code.startswith("ok"):
        raise Exception("Can't create path '%s'" % path)
    
    return path


def getsubdirs(path, max_entries=None):
    """
    >>> print getsubdirs("/tmp")
    ...
    """
    try:
        paths=os.listdir(path)
        if max_entries is not None:
            paths=paths[0:max_entries]
            
        paths=map(partial(os.path.join, path), paths)
        dirs=filter(os.path.isdir, paths)
        return ("ok", dirs)
    except Exception,e:
        return ("error", e)


def move(src_path, dst_path):
    try:
        os.rename(src_path, dst_path)
        return ("ok", None)
    except:
        return ('error', None)


def file_contents(path):
    """
    Simple "get file contents"
    """
    try:
        fh=open(path, "r")
        return ('ok', fh.read())
    except:
        return ("error", None)
    finally:
        try:
            fh.close()
        except:
            pass

def atomic_write(path, contents, tmppath=None):
    """
    Atomic write to file
    
    Create temporary file and then move/rename to specified path.
    Rename operation in the same filesystem are atomic (at least in Linux).
    
    >>> atomic_write("/tmp/_jlddk_atomic_write", "test!") ## doctest: +ELLIPSIS
    ('ok', ...
    """
    
    dn=tmppath or os.path.dirname(path)
    fd, tfn=tempfile.mkstemp(dir=dn)
    
    try:
        ### part 1: write to temp file
        f=os.fdopen(fd, "w")
        f.write(contents)
        f.close()
    except Exception, e:
        try:    os.close(fd)
        except: pass
        return ("error", "write to temp file: %s" % str(e))        
        
    try:
        ### part 2: rename to specified path
        os.rename(tfn, path)
    except Exception,e:
        return ("error", "rename to path '%s': %s" % (path, e))
        
    return ("ok", tfn)
        
    

def quick_write(path, contents):
    """
    Best effort "write contents to file" 
    
    >>> quick_write("/tmp/QuickWriteTest", "{'param': 'value'}") # doctest:+ELLIPSIS
    ('ok', ...)
    >>> file_contents("/tmp/QuickWriteTest")
    ('ok', "{'param': 'value'}")
    >>> rm('/tmp/QuickWriteTest') # doctest:+ELLIPSIS
    ('ok', ...)
    """
    try:
        code, maybe_rpath=resolve_path(path)
        if not code.startswith("ok"):
            return (code, maybe_rpath) 
        fh=open(maybe_rpath, "w")
        fh.write(contents)
        fh.close()
        return ('ok', path)
    except Exception, e:
        return ("error", str(e))
    finally:
        try:
            fh.close()
        except:
            pass


@pattern(str, None, list)
def filter_files_by_ext_NL(criteria, extlist, files):
    return files

@pattern(str, None, types.TupleType)
def filter_files_by_ext_NA(criteria, extlist, (code, maybe_list)):
    if not code.startswith("ok"):
        return []
    return maybe_list


@pattern(str, list, types.TupleType)
def filter_files_by_ext_tup(criteria, extlist, (code, maybe_list)):
    if not code.startswith("ok"):
        return []
    
    return filter_files_by_ext(criteria, extlist, maybe_list)


@pattern("include", list, list)
def filter_files_by_ext_inc(criteria, extlist, files):
    
    def inf(path):
        _root, ext=os.path.splitext(path)
        return ext in extlist
    
    return filter(inf, files)

@pattern("exclude", list, list)
def filter_files_by_ext_exc(criteria, extlist, files):

    def exf(path):
        _root, ext=os.path.splitext(path)
        return not ext in extlist
    
    return filter(exf, files)

@patterned
def filter_files_by_ext(criteria, extlist, files):
    """
    >>> filter_files_by_ext("include", [".json"], ["a.json", "b.json", "c.py"])
    ['a.json', 'b.json']
    >>> filter_files_by_ext("exclude", [".json"], ["a.json", "b.json", "c.py"])
    ['c.py']
    >>> filter_files_by_ext("include", [".json"], ("ok", ["a.json", "b.json", "c.py"]))
    ['a.json', 'b.json']
    >>> filter_files_by_ext("exclude", [".json"], ("error", None))
    []
    """

def get_root_files(src_path, strip_dirname=False, max_entries=None):
    """
    Retrieve files from the root of src_path
    
    @return absolute paths
    
    >> get_root_files("/tmp")
    
    >> get_root_files("/tmp", strip_dirname=True)
    
    """
    def add_src_path(p):
        return os.path.join(src_path, p)
    
    try:
        liste=os.listdir(src_path)
        if max_entries is not None:
            liste=liste[0:max_entries]
        liste=map(add_src_path, liste)        
        liste=filter(os.path.isfile, liste)
        
        if strip_dirname:
            liste=map(os.path.basename, liste)
     
        return ("ok", liste)
    except:
        return ("error", None)

def touch(path):
    """
    >>> touch("/tmp/JustTouching")
    ('ok', '/tmp/JustTouching')
    >>> rm('/tmp/JustTouching')
    ('ok', '/tmp/JustTouching')
    """
    fhandle = file(path, 'a')
    try:
        os.utime(path, None)
        return ('ok', path)
    except OSError, exc:
        return ("error", (exc.errno, errno.errorcode[exc.errno]))
    finally:
        fhandle.close()        

def rm(path):
    """
    Silently (i.e. no exception thrown) removes a path if possible
    
    >>> rm("/tmp/NotAFile") ## no need to complain if there is no file
    ('ok', '/tmp/NotAFile')
    """
    try:
        os.remove(path)
        return ('ok', path)
    except OSError, exc:
        if exc.errno==errno.ENOENT:
            return ('ok', path)
        return ("error", (exc.errno, errno.errorcode[exc.errno]))


def rmdir(path):
    try:
        shutil.rmtree(path)
        return ("ok", None)
    except Exception,e:
        return ("error", e)


def can_write(path):
    """
    Checks if the current user (i.e. the script) can delete the given path
    Must check both user & group level permissions
    
    FOR THIS TEST, NEED TO CREATE A DIRECTORY /tmp/_test_root_sipi THROUGH ROOT
    
    >>> p="/tmp/_test_sipi"
    >>> rm(p)
    ('ok', '/tmp/_test_sipi')
    >>> touch(p)
    ('ok', '/tmp/_test_sipi')
    >>> can_write(p)
    ('ok', True)
    >>> rm(p)
    ('ok', '/tmp/_test_sipi')
    >>> can_write("/tmp/_test_root_sipi/")
    ('ok', False)
    """
    try:
        return ("ok", os.access(path, os.W_OK))
    except:
        return ("error", None)



def remove_common_prefix(common_prefix, path):
    """
    >>> remove_common_prefix("/tmp", "/tmp/some_dir/some_file.ext")
    ('ok', '/some_dir/some_file.ext')
    """
    try:
        _head, _sep, tail=path.partition(common_prefix)
        return ("ok", tail)
    except:
        return ("error", path)


def gen_walk(path, max_files=None):
    count=0
    done=False
    for root, _dirs, files in os.walk(path):
        
        for f in files:
            yield os.path.join(root, f)
        
            count=count+1
            if max_files is not None:
                if count==max_files:
                    done=True
                    break
            
        if done: break
        



def safe_listdir(path):
    try:
        return ("ok", os.listdir(path))
    except Exception, e:
        return ("error", e)

def get_path_extension(path):
    """
    >>> get_path_extension("/some/path/config.yaml")
    ('/some/path/config', '.yaml')
    >>> get_path_extension(".bashrc")
    ('.bashrc', '')
    >>> get_path_extension("/some/path/file")
    ('/some/path/file', '')
    """
    return os.path.splitext(path)

def mkdir_p(path):
    """
    Silently (i.e. no exception thrown) makes a directory structure if possible
    
    This function can be found in the 'sipi' package.
    """
    try:
        os.makedirs(path)
        return ('ok', path)
    except OSError, exc:
        if exc.errno == errno.EEXIST:
            return ('ok', path)

        return ('error', (exc.errno, errno.errorcode[exc.errno]))


def resolve_path(path):
    try:
        path=os.path.expandvars(path)
        path=os.path.expanduser(path)
        return ("ok", path)
    except:
        return ("error", None)


def safe_isfile(path):
    try:
        return os.path.isfile(path)
    except:
        return False
    
    
def simple_popen(path_script, env={}):
    new_env=os.environ.copy()
    new_env.update(env)
    return subprocess.Popen(path_script, env=new_env)


def split_all_ext(path):
    return path.split(".")[0]


def gen_dir_walk(start_path, target_level=1, dobelow=False):
    """
    Walks the directories 'target_level' down the 'start_path'
    
    >>> g=gen_dir_walk("/tmp/test", target_level=2, dobelow=True)
    >>> for d in g:
    ...    print d
    """
    start_level=len(start_path.split(os.path.sep))
    abs_target_level=start_level+target_level
    
    for root, _dirs, _files in os.walk(start_path):
        
        for _dir in _dirs:
            abs_dir=os.path.join(root, _dir)
            current_level=len(abs_dir.split(os.path.sep))
            if current_level==abs_target_level or (dobelow and current_level>abs_target_level):
                    yield abs_dir

if __name__=="__main__":
    import doctest
    doctest.testmod()
    