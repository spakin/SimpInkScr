#########################################################
# Invoke Inkscape's *Path* → *Stroke to Path* function. #
#########################################################

r = rect((100, 100), (200, 200),
         stroke_width=16, stroke='#000080', fill='#add8e6')
new_objs = apply_action('object-stroke-to-path', r)
for obj in new_objs:
    try:
        if obj.style()['fill'] == '#000080':
            obj.translate_path((50, 50))
    except KeyError:
        pass
