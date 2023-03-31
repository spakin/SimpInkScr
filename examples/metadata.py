#############################################################
# Add metadata to an image using Simple Inkscape Scripting. #
#############################################################

import datetime

# Draw a picture.
wd, ht = canvas.width, canvas.height
radius = min(wd, ht)/2
c1 = circle((wd/2, ht/2), radius*0.9).to_path()
c2 = circle((wd/2, ht/2), radius*0.45).to_path()
c1.append(c2.reverse())
c1.style(stroke_width='2pt', fill='#3737c8')

# Specify a variety of document metadata.
metadata.title = 'Circle with a Hole'
now = datetime.datetime.now().astimezone()  # Date+time and timezone
metadata.date = now
metadata.creator = 'Scott Pakin'
metadata.rights = f'Copyright (C) {now.year} Scott Pakin'
metadata.keywords = ['circle', 'blue', 'donut', 'hole']
metadata.description = 'Drawing of a large, blue circle with a hole' \
    ' in its center.'
metadata.license = 'CC Attribution'
