class HttpResponse(object):

    def __init__(self):
        self.body = ''
        self.headers = {}
        self.status_code = 200
        self.status_string = 'OK'
        self.version = 'HTTP/1.1'

    def to_string(self):
        h = '%s %d %s\r\n' % (
                self.version, self.status_code, self.status_string)
        for k,v in self.headers.iteritems():
            h = '%s%s: %s\r\n' % (h, k, v)
        if len(self.body):
            h = '%sContent-Length: %d\r\n\r\n' % (h, len(self.body))
            h = '%s%s' % (h, self.body)
        return h
