import re
import hashlib
import logging

class Register(object):
    
    POST    = 0
    GET     = 1

    def __init__(self):
        self.post_callables = {}
        self.get_callables = {}
        self.post_expressions = []
        self.get_expressions = []
        self.path_regex = re.compile('(?P<sub>\<\w+\>)')

    def set_callable(self, regex, function, verb):
        # search for the <name> pattern and create 
        # a compatible regex
        logging.debug('Register.set_callable - regex is %s' % regex)
        parts = self.path_regex.findall(regex)
        re_regex = regex
        re_regex = '^%s$' % re_regex
        keyword_args = []
        for p in parts :
            keyword_args.append(p.strip('<>'))
            re_regex = re_regex.replace(p, '(?P%s\w+)' % p)            
        logging.debug('Register.set_callable - re module regex is %s' % re_regex)
        logging.debug('Register.set_callable - callable keyword args are %s' % keyword_args)
        if verb == Register.POST:
            self.post_callables[re_regex] = (function, keyword_args)
            self.post_expressions.append(re.compile(re_regex))
        else :
            self.get_callables[re_regex] = (function, keyword_args)
            self.get_expressions.append(re.compile(re_regex))
        

    def get_callable(self, uri, verb):
        callables = None
        expressions = None
        if verb == Register.POST :
            callables = self.post_callables
            expressions = self.post_expressions
        else :
            callables = self.get_callables
            expressions = self.get_expressions
        logging.debug('Register.get_callable - match uri %s' % uri)
        for ex in expressions :
            try :
                logging.debug('Register.get_callable - evaluating %s' % ex.pattern)
                result = ex.match(uri)
                if result :
                    logging.debug('Register.get_callable - matched %s' % ex.pattern)
                    call, args = callables[ex.pattern]
                    keyword_args = dict(zip(args, result.groups()))
                    return call, keyword_args
            except :
                continue
        return None, None
                
register = Register()

def post(uri_regex):
    def wrap(func):
        register.set_callable(uri_regex, func, Register.POST)
        def wrapped(*args, **kargs):
            func(*args, **kargs)
        return wrapped
    return wrap

def get(uri_regex):
    def wrap(func):
        register.set_callable(uri_regex, func, Register.GET)
        def wrapped(*args, **kargs):
            func(*args, **kargs)
        return wrapped
    return wrap


if __name__ == '__main__' :
    
    logging.basicConfig(
            level=logging.DEBUG, 
            format='%(asctime)-15s %(levelname)s %(message)s')

    @post('/path/<name>/test')
    def my_handler(name):
        logging.debug('my_handler : %s' % name)
    
    @post('/path/<name>/test/<qualifier>')
    def my_great_handler(name, qualifier):
        logging.debug('my_great_handler : %s %s' % (name, qualifier))

    call, keyword_args = register.get_callable('/path/nemi/test', Register.POST)
    call(*[], **keyword_args)

    call, keyword_args = register.get_callable('/path/nemi/test/salame', Register.POST)
    call(*[], **keyword_args)

    call, keyword_args = register.get_callable('/path/nemi/test/salame/', Register.POST)
    assert(call is None)
        

