from Cython import Utils
import re

def cached_method(f):
    cache_name = '__%s_cache' % f.__name__
    def wrapper(self, *args):
        cache = getattr(self, cache_name, None)
        if cache is None:
            cache = {}
            setattr(self, cache_name, cache)
        if args in cache:
            return cache[args]
        res = cache[args] = f(self, *args)
        return res
    return wrapper

def strip_string_literals(code, prefix='__Pyx_L'):
    """
    Normalizes every string literal to be of the form '__Pyx_Lxxx', 
    returning the normalized code and a mapping of labels to
    string literals. 
    """
    new_code = []
    literals = {}
    counter = 0
    start = q = 0
    in_quote = False
    raw = False
    while True:
        single_q = code.find("'", q)
        double_q = code.find('"', q)
        q = min(single_q, double_q)
        if q == -1: q = max(single_q, double_q)
        if q == -1:
            if in_quote:
                counter += 1
                label = "'%s%s" % (prefix, counter)
                literals[label] = code[start:]
                new_code.append(label)
            else:
                new_code.append(code[start:])
            break
        elif in_quote:
            if code[q-1] == '\\':
                k = 2
                while q >= k and code[q-k] == '\\':
                    k += 1
                if k % 2 == 0:
                    q += 1
                    continue
            if code[q:q+len(in_quote)] == in_quote:
                counter += 1
                label = "%s%s" % (prefix, counter)
                literals[label] = code[start+len(in_quote):q]
                new_code.append("'%s'" % label)
                q += len(in_quote)
                start = q
                in_quote = False
            else:
                q += 1
        else:
            raw = False
            if len(code) >= q+3 and (code[q+1] == code[q] == code[q+2]):
                in_quote = code[q]*3
            else:
                in_quote = code[q]
            end = q
            while end>0 and code[end-1] in 'rRbBuU':
                if code[end-1] in 'rR':
                    raw = True
                end -= 1
            new_code.append(code[start:end])
            start = q
            q += len(in_quote)
    
    return "".join(new_code), literals

def parse_dependencies(source_filename):
    # Actual parsing is way to slow, so we use regular expressions.
    # The only catch is that we must strip comments and string
    # literals ahead of time.
    source = Utils.open_source_file(source_filename, "rU").read()
    source = re.sub('#.*', '', source)
    source, literals = strip_string_literals(source)
    source = source.replace('\\\n', ' ')
    if '\t' in source:
        source = source.replace('\t', ' ')
    # TODO: pure mode
    dependancy = re.compile(r"(cimport +([0-9a-zA-Z_.]+)\b)|(from +([0-9a-zA-Z_.]+) +cimport)|(include +'([^']+)')|(cdef +extern +from +'([^']+)')")
    cimports = []
    includes = []
    externs  = []
    for m in dependancy.finditer(source):
        groups = m.groups()
        if groups[0]:
            cimports.append(groups[1])
        elif groups[2]:
            cimports.append(groups[3])
        elif groups[4]:
            includes.append(literals[groups[5]])
        else:
            externs.append(literals[groups[7]])
    return cimports, includes, externs


class DependencyTree(object):
    
    def __init__(self, context):
        self.context = context
        self._transitive_cache = {}
    
    @cached_method
    def parse_dependencies(self, source_filename):
        return parse_dependencies(source_filename)
    
    @cached_method
    def immediate_dependencies(self, filename):
        cimports, includes, externs = self.parse_dependencies(filename)
        cimports = set(cimports)
        externs = set(externs)
        for include in includes:
            a, b = self.immediate_dependencies(os.path.join(os.path.dirname(filename), include))
            cimports.update(a)
            externs.update(b)
        return cimports, externs
    
    @cached_method
    def package(self, filename):
        dir = os.path.dirname(filename)
        if os.path.exists(os.path.join(dir, '__init__.py')):
            return self.package(dir) + [os.path.basename(dir)]
        else:
            return []
    
    def find_pxd(self, module, filename=None):
        if module[0] == '.':
            raise NotImplementedError, "New relative imports."
        if filename is not None:
            relative = '.'.join(self.package(filename) + module.split('.'))
            pxd = self.context.find_pxd_file(relative, None)
            if pxd:
                return pxd
        return self.context.find_pxd_file(module, None)
        
    @cached_method
    def cimported_files(self, filename):
        if filename[-4:] == '.pyx' and os.path.exists(filename[:-4] + '.pxd'):
            self_pxd = [filename[:-4] + '.pxd']
        else:
            self_pxd = []
        a = self.immediate_dependencies(filename)[0]
        b = filter(None, [self.find_pxd(m, filename) for m in self.immediate_dependencies(filename)[0]])
        if len(a) != len(b):
            print (filename)
            print ("\n\t".join(a))
            print ("\n\t".join(b))
        return self_pxd + filter(None, [self.find_pxd(m, filename) for m in self.immediate_dependencies(filename)[0]])
    
    @cached_method
    def timestamp(self, filename):
        return os.path.getmtime(filename)
    
    def extract_timestamp(self, filename):
        return self.timestamp(filename), filename
    
    def newest_dependency(self, filename):
        return self.transitive_merge(filename, self.extract_timestamp, max)
    
    def transitive_merge(self, node, extract, merge):
        try:
            seen = self._transitive_cache[extract, merge]
        except KeyError:
            seen = self._transitive_cache[extract, merge] = {}
        return self.transitive_merge_helper(
            node, extract, merge, seen, {}, self.cimported_files)[0]
    
    def transitive_merge_helper(self, node, extract, merge, seen, stack, outgoing):
        if node in seen:
            return seen[node], None
        deps = extract(node)
        if node in stack:
            return deps, node
        try:
            stack[node] = len(stack)
            loop = None
            for next in outgoing(node):
                sub_deps, sub_loop = self.transitive_merge_helper(next, extract, merge, seen, stack, outgoing)
                if sub_loop is not None:
                    if loop is not None and stack[loop] < stack[sub_loop]:
                        pass
                    else:
                        loop = sub_loop
                deps = merge(deps, sub_deps)
            if loop == node:
                loop = None
            if loop is None:
                seen[node] = deps
            return deps, loop
        finally:
            del stack[node]