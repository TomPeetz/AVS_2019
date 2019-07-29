Alle Kapitel werden als Markdown-Dateien geschrieben. Für die Abgabe werden die Daten in [Overleaf](https://www.overleaf.com/3393357433vbfrjztgwkhf) exportiert und dort finalisiert.

Umwandlung von Markdown in LaTeX mittels [pandoc](https://pandoc.org/):

```
pandoc "1-Einleitung.md" --standalone --bibliography Literatur.bib -o "1-Einleitung.tex"
```

### Referenzen
Referenzen werden einfach mit vorangestellten @-Zeichen angegeben:
> Lorem Ipsum dolor sit amet (@SampleReference).
