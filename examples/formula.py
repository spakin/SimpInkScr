###################################################################
# Demonstrate the formula function for rendering LaTeX equations #
# in Simple Inkscape Scripting using pdflatex.                   #
###################################################################

# Set up the canvas
canvas.true_width = 600
canvas.true_height = 400

# Draw a title
text('LaTeX Formula Examples', (50, 40), font_size='24pt', font_weight='bold')

# Simple inline formula
formula(r'\alpha + \beta = \gamma', (50, 100), fontsize=14)

# Fraction example
formula(r'\frac{a^2 + b^2}{c^3}', (50, 150), fontsize=16)

# Display math mode for larger equations (integral without sqrt)
formula(r'\int_0^\infty e^{-x^2} dx = \frac{\pi^{1/2}}{2}',
        (50, 220), fontsize=14, display_math=True)

# Matrix example with scaling
formula(r'\begin{pmatrix} a & b \\ c & d \end{pmatrix}',
        (350, 100), fontsize=12, scale=1.5)

# Custom preamble for additional packages
formula(r'\mathbb{R}^n \rightarrow \mathcal{H}',
        (350, 200), preamble=r'\usepackage{mathrsfs}')

# Styled formula with fill color
formula(r'E = mc^2', (350, 280), fontsize=20, scale=1.2, fill='navy')
