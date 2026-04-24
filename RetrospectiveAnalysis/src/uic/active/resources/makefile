# Makefile to compile all .tex files in subfolders to .svg

# Set the LaTeX compiler
LATEX = pdflatex

# Find all .tex files in subfolders
TEX_FILES := $(shell find . -type f -name '*.tex')

# Generate corresponding .svg filenames
SVG_FILES := $(addsuffix .svg, $(basename $(TEX_FILES)))

# Rule to compile .tex files to .pdf
%.svg: %.tex
	cd $(dir $@); \
	$(LATEX) -shell-escape $(notdir $<)

# Default target, compiles all .tex files and cleans up auxiliary
all: $(SVG_FILES)
	find . -type f -name '*.aux' -delete
	find . -type f -name '*.log' -delete
	find . -type f -name '*.out' -delete
	find . -type f -name '*.toc' -delete
	find . -type f -name '*.pdf' -delete
	find . -type f -name '*.fdb_latexmk' -delete
	find . -type f -name '*.fls' -delete
	find . -type f -name '*.synctex.gz' -delete
	find . -type f -name '*.dvi' -delete
	find . -type f -name '*.ps' -delete

# Clean up auxiliary files
clean:
	find . -type f -name '*.aux' -delete
	find . -type f -name '*.log' -delete
	find . -type f -name '*.out' -delete
	find . -type f -name '*.toc' -delete
	find . -type f -name '*.pdf' -delete
	find . -type f -name '*.svg' -delete
	find . -type f -name '*.fdb_latexmk' -delete
	find . -type f -name '*.fls' -delete
	find . -type f -name '*.synctex.gz' -delete
	find . -type f -name '*.dvi' -delete
	find . -type f -name '*.ps' -delete

.PHONY: all clean
