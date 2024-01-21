###########################################################
# Show how to use the Python Imaging Library to convert   #
# each pixel of a bitmapped image to a colored rectangle. #
###########################################################

import base64
from PIL import Image
import io


def render_with_rectangles(obj):
    'Render an image with SVG rectangles.'
    # Convert the SVG image to an RGBA PIL image by parsing the raw data.
    img_data_b64 = obj.svg_get('xlink:href', True).partition(',')[2]
    img_data = base64.b64decode(img_data_b64)
    img = Image.open(io.BytesIO(img_data)).convert(mode='RGBA')

    # Acquire image properties.
    pix_x0, pix_y0 = obj.svg_get('x'), obj.svg_get('y')
    pix_wd = inkex.units.convert_unit(obj.svg_get('width'), 'px')
    pix_ht = inkex.units.convert_unit(obj.svg_get('height'), 'px')
    iwd, iht = img.width, img.height
    xedge, yedge = pix_wd/iwd, pix_ht/iht
    xform = obj.transform

    # Convert each pixel to an SVG rectangle.
    rectangles = []
    for y in range(iht):
        for x in range(iwd):
            red, grn, blu, alp = img.getpixel((x, y))
            x0, y0 = x*xedge + pix_x0, y*yedge + pix_y0
            r = rect((x0, y0), (x0 + xedge, y0 + yedge),
                     fill='#%02x%02x%02x' % (red, grn, blu),
                     stroke='none',
                     opacity=alp/255,
                     transform=xform)
            rectangles.append(r)
    return rectangles


# Download a bitmapped image from the web.
img_src = 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c0/' + \
          'Gnome-emblem-web.svg/48px-Gnome-emblem-web.svg.png'
img = image(img_src, (20, 20), embed=True, transform='scale(2)')

# Convert each pixel of the image to an SVG rectangle.
group(render_with_rectangles(img))
img.remove()
