DOC = pdsc
CLEAN = *.log *.aux *.out *.bbl *.blg *.acr *.acn *.glg *.gls *.glo *.ist *.alg
CLEANER = *.pdf

all:
	pdflatex $(DOC)
	if grep -c -q '\\citation' $(DOC).aux; then bibtex $(DOC); fi
	pdflatex $(DOC)
	pdflatex $(DOC)

clean:
	rm -f $(CLEAN)

cleaner: clean
	rm -f $(CLEANER)
