####################################################
# Use Simple Inkscape Scripting to embed HTML code #
# within an SVG image.                             #
####################################################

# Set the canvas size.
canvas.true_width = 600
canvas.true_height = 394
canvas.viewbox = [-10, -10, 590, 384]

# Draw a face.
eye_mouth_style = {'fill': 'black', 'stroke': 'none', 'stroke_width': 4}
circle((488, 282), 88, fill='yellow', stroke_width=4)
circle((457, 258), 16, **eye_mouth_style)
circle((519, 258), 16, **eye_mouth_style)
ellipse((488, 327), (40, 24), **eye_mouth_style)

# Draw a word balloon.
path([Move(192, 0),
      Arc(192, 128, 0, 0, 0, 0, 128),
      Arc(192, 128, 0, 0, 0, 192, 256),
      Arc(192, 128, 0, 0, 0, 287, 239),
      Line(384, 288),
      Line(334, 214),
      Arc(192, 128, 0, 0, 0, 384, 128),
      Arc(192, 128, 0, 0, 0, 192, 0),
      ZoneClose()],
     fill='ghostwhite', stroke_width=4)

# Add HTML to the word balloon.
foreign((48, 56), (332, 200), '''\
<div xmlns="http://www.w3.org/1999/xhtml"
     style="max-height:160px; overflow-y:auto">
  <h1 style="font-size:x-large; color:navy">HTML within SVG</h1>

  <p>Did you know it's possible to embed <a
  href="https://html.spec.whatwg.org/">HTML</a> code within an <a
  href="https://www.w3.org/Graphics/SVG/">SVG</a> image?  Well it is!</p>

  <p>This image was created programmatically using the <a
  href="https://inkscape.org/~pakin/%E2%98%85simple-inkscape-scripting">Simple
  Inkscape Scripting</a> extension for the <a
  href="https://inkscape.org/">Inkscape</a> vector-graphics editor.  A
  programmer writes a simple <a
  href="https://www.python.org/">Python</a> program that draws a
  picture using functions such as</p>
  <ul>
    <li><code>circle</code>,</li>
    <li><code>ellipse</code>, and</li>
    <li><code>path</code>,</li>
  </ul>
  <p>with the output being an SVG image.</p>

  <p>The new Simple Inkscape Scripting feature being demonstrated here
  is the <code>foreign</code> function.  <code>foreign</code> supports
  embedding non-SVG <a href="https://www.w3.org/XML/">XML</a> code
  (such as HTML) into an SVG file.  While Inkscape does not currently
  display foreign objects, web browsers can display foreign HTML.</p>

  <h2 style="font-size:medium; text-align:center">For more
  information</h2>

  <p>Complete documentation is available at the <a
  href="https://github.com/spakin/SimpInkScr/wiki">Simple Inkscape
  Scripting wiki</a>.</p>

</div>
''')
