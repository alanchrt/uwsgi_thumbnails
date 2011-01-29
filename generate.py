"""
uwsgi_thumbnails
================

Efficiently generate thumbnails from url on the fly.

Example:
http://images.mysite.com/4238_bpM4oOcw_150x200_s.jpg?ed0eee0cfa25309e40cc0d71

Components:
- Source filename id and hash (4238_bpM4oOcw[.jpg])
- Dimensions (150x200)
- Transform (s[cale])
- Extension (jpg)
- Signature (ed0eee0cfa25309e40cc0d71)

"""

import hmac
from PIL import Image
from settings import DEBUG, SECRET_KEY, IMAGE_ROOT, THUMB_ROOT

def application(environ, start_response):
    try:
        # Grab the request path
        request_uri = environ['REQUEST_URI']

        # Check for root url
        if request_uri == '/':
            start_response('403 Forbidden', [('Content-Type', 'text/plain')])
            yield "Forbidden"
            return

        # Break apart uri for parsing
        path = request_uri.split('?')
        file_data = path[0].split('.')
        filename = file_data[0][1:]
        parameters = filename.split('_')
        dimensions = parameters[2].split('x')

        # Store image metadata
        image = {
            'id': parameters[0],
            'hash': parameters[1],
            'width': dimensions[0],
            'height': dimensions[1],
            'transform': parameters[3],
            'extension': file_data[1],
            'signature': path[1],
        }

        # Validate transform type (only scaling for now)
        if not image['transform'] in ('s',):
            raise Exception, "Invalid image transform"

        # Determine the required signature
        h = hmac.new(SECRET_KEY)
        h.update(image['id'])
        h.update(image['hash'])
        h.update(image['width'])
        h.update(image['height'])
        h.update(image['transform'])
        h.update(image['extension'])
        signature = h.hexdigest()[:24]

        # Validate image signature
        if not image['signature'] == signature:
            raise Exception, "Invalid signature '%s'" % signature

        # Create the thumbnail
        im = Image.open('%s%s_%s.%s' % (IMAGE_ROOT, image['id'],
                                        image['hash'], image['extension'])) 
        size = (int(image['width']), int(image['height']))
        im.thumbnail(size, Image.ANTIALIAS)
        im.save('%s%s.%s' % (THUMB_ROOT, filename, image['extension']))

        # Redirect to the newly created file
        start_response('302 Found', [('Location', request_uri)])

    except Exception, error:
        # Display "File not found" error
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        if DEBUG:
            # Output extra 512 bytes to override Chrome friendly 404
            yield "File not found: %s%s" % (error, " " * 512)
        else:
            yield "File not found"
