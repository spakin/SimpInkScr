#############################################################
# Use Simple Inkscape Scripting to add a layer to an image. #
#############################################################

c1 = circle((canvas.width/2, canvas.height*3/4), 100, fill='red')
l2 = layer('My new layer')
c2 = circle((canvas.width/2, canvas.height/4), 100, fill='blue')
l2.append(c2)
