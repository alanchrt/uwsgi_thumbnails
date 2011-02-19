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

class ThumbnailGenerator(object):
    def __init__(self, secret_key=None, image_root=None, thumb_root=None,
                 dummy=None, debug=False):
        # Save attributes
        self.secret_key = secret_key
        self.image_root = image_root
        self.thumb_root = thumb_root
        self.dummy = dummy
        self.debug = debug

    def pre_hook(self, image):
        """This hook is excuted before the thumnbnail is generated."""
        pass

    def post_hook(self, image, im):
        """This hook is excuted after the thumnbnail is generated."""
        pass

    def application(self, environ, start_response):
        """Parses the URI and performs the desired transform."""
        try:
            # Grab the request path
            request_uri = environ['REQUEST_URI']

            # Check for root url
            if request_uri == '/':
                start_response('403 Forbidden',
                               [('Content-Type','text/plain')])
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
            h = hmac.new(self.secret_key)
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

            # Run the pre-hook
            self.pre_hook(image)

            # Open the image or display dummy
            try:
                im = Image.open('%s%s_%s.%s' % (self.image_root, image['id'],
                                            image['hash'], image['extension']))
            except IOError, e:
                if self.dummy:
                    im = Image.open(self.dummy)
                else:
                    raise IOError, e

            # Create the thumbnail
            size = (int(image['width']), int(image['height']))
            im.thumbnail(size, Image.ANTIALIAS)
            im.save('%s%s.%s' % (self.thumb_root, filename,
                                 image['extension']))

            # Run the post-hook
            self.post_hook(image, im)

            # Redirect to the newly created file
            start_response('302 Found', [('Location', request_uri)])

        except Exception, error:
            # Display "File not found" error
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            if self.debug:
                # Output extra 512 bytes to override Chrome friendly 404
                yield "File not found: %s%s" % (error, ("\n" + " "*32)*16)
            else:
                yield "File not found"
