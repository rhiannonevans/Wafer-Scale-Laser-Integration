# Resources

Rendered .svg equations and block diagram from latex

The conversion is done by using the [standalone](https://ctan.org/pkg/standalone?lang=en) package.

Use the command `pdflatex -shell-escape <file>.tex` to generate the pdf and svg files.

The makefile in this directory will this compilation and only leaves the svg output.

Additional dependencies needed for standalone to convert are:

- [imagemagick](https://imagemagick.org/)
  - [potrace](https://potrace.sourceforge.net/) if it doesn't come with imagemagick


If new svg files are generated and need to be display on RA:
- add file name to active.qrc
- in command line, navigate to active/resources folder and use the command `pyside6-rcc active.qrc -o active_rc.py` to update active_rc.py file