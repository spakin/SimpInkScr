#################################################################
# Use Simple Inkscape Scripting to place text on a curved path. #
#################################################################

curve = path(['M', 32, 381,
              'C', 112, 141, 144, 205, 224, 381,
              304, 557, 368, 509, 416, 381,
              464, 253, 544, 141, 608, 381,
              672, 621, 736, 573, 800, 381,
              848, 253, 896, 109, 992, 381],
             stroke='none')
text('“May your dreams be larger than mountains and may '
     'you have the courage to scale their summits.”  — Harley King',
     (0, 0), path=curve, font_size='24pt',
     font_family='Abyssinica SIL, Times New Roman, serif')
