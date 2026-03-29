PDF=whispertunnel-report.pdf
SRC=main.tex

all: $(PDF)

$(PDF): $(SRC) chapters/*.tex appendices/*.tex
	pdflatex -interaction=nonstopmode -halt-on-error $(SRC)
	pdflatex -interaction=nonstopmode -halt-on-error $(SRC)
	mv main.pdf $(PDF)

clean:
	rm -f *.aux *.bbl *.bcf *.blg *.fdb_latexmk *.fls *.lof *.log *.lot *.out *.run.xml *.toc *.pdf

.PHONY: all clean
