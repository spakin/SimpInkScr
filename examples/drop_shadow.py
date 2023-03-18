######################################################################
# Use Simple Inkscape Scripting to draw a circle with a drop shadow. #
######################################################################

# Define a drop shadow as an offset, blurred, black copy of the input
# shape placed underneath a copy of the original object.
shadow = filter_effect('Drop Shadow')
flood = shadow.add('Flood', floodOpacity=1, floodColor='black')
comp1 = shadow.add('Composite', src1=flood, src2='SourceGraphic',
                   operator='in')
blur = shadow.add('GaussianBlur', src1=comp1, stdDeviation=3)
ofs = shadow.add('Offset', dx=5, dy=5)
comp2 = shadow.add('Composite', src1='SourceGraphic', src2=ofs,
                   operator='over')

# Draw a bright-green circle and add a drop shadow to it.
circle((canvas.width/2, canvas.height/2), 100, fill='#99ff55', stroke='black',
       stroke_width=2, filter=shadow)
