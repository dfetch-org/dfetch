% dfetch LaTeX preamble
%
% Included by conf.py via latex_elements['preamble'].
% Prerequisites: XeLaTeX, fontspec (declared in latex_elements['fontpkg']).

% ---- Unicode glyphs ---------------------------------------------------------
\usepackage{newunicodechar}
\usepackage{pifont}
\newunicodechar{✔}{\ding{51}}
\newunicodechar{✘}{\ding{55}}

% ---- Design tokens ----------------------------------------------------------
\usepackage{xcolor}
\definecolor{dfprimary}{HTML}{c2620a}
\definecolor{dfaccent}{HTML}{4e7fa0}
\definecolor{dftextmuted}{HTML}{78716c}
\definecolor{dfnearblack}{HTML}{1c1917}
\definecolor{dfbgtint}{HTML}{fef8f0}
\definecolor{dfbgmint}{HTML}{eff6fa}
\definecolor{dfborder}{HTML}{e7e0d8}
\definecolor{dfgreen}{HTML}{7aad6b}
\definecolor{dfbggreen}{HTML}{f3faf2}
\definecolor{dferror}{HTML}{c0544a}
\definecolor{dfbgerror}{HTML}{fff5f4}
% Cover page palette
\definecolor{dfetchCoverTop}{HTML}{3a6682}
\definecolor{dfetchCoverDark}{HTML}{1c1917}
\definecolor{dfetchCoverBottom}{HTML}{c2620a}
\definecolor{dfetchCoverAccent}{HTML}{4e7fa0}
\definecolor{dfetchCoverLight}{HTML}{fef8f0}

% ---- Cover page -------------------------------------------------------------
\usepackage{tikz}

% ---- Chapter & section titles -----------------------------------------------
% titlesec overrides fncychap so we get full control of colours and spacing.
\usepackage{titlesec}
% Chapter: small muted "CHAPTER N" eyebrow + large near-black title + amber rule
\titleformat{\chapter}[display]
  {\normalfont\sffamily}
  {\color{dftextmuted}\fontsize{9}{11}\selectfont\bfseries
   \MakeUppercase{\chaptertitlename}~\thechapter}
  {4pt}
  {\color{dfnearblack}\fontsize{22}{26}\selectfont\bfseries}
  [\vspace{6pt}{\color{dfprimary}\rule{\linewidth}{1.5pt}}]
\titlespacing*{\chapter}{0pt}{-6pt}{18pt}
% Section: amber number pip + near-black title text
\titleformat{\section}
  {\normalfont\sffamily\Large\bfseries\color{dfnearblack}}
  {\textcolor{dfprimary}{\thesection}}
  {0.75em}{}
% Subsection: muted number + near-black title text
\titleformat{\subsection}
  {\normalfont\sffamily\large\bfseries\color{dfnearblack}}
  {\textcolor{dftextmuted}{\thesubsection}}
  {0.75em}{}
\titleformat{\subsubsection}
  {\normalfont\sffamily\normalsize\bfseries\color{dfnearblack}}
  {\textcolor{dftextmuted}{\thesubsubsection}}
  {0.75em}{}

% ---- Admonitions: left-stripe card style matching the website ---------------
% Sphinx 5+ emits \begin{sphinxadmonition}{type}{Title:} for every admonition.
% We override that single two-arg environment and dispatch to per-type opener
% commands defined here.  tcolorbox skins supplies borderline west (left stripe
% only) and frame hidden (no outer box border).
\usepackage{tcolorbox}
\tcbuselibrary{skins}
\usepackage{etoolbox}
\tcbset{
  dfnote/.style={enhanced, frame hidden,
    borderline west={3.5pt}{0pt}{dfaccent}, colback=dfbgmint,
    left=10pt, right=10pt, top=8pt, bottom=8pt,
    before skip=\baselineskip, after skip=0.5\baselineskip},
  dfwarn/.style={enhanced, frame hidden,
    borderline west={3.5pt}{0pt}{dfprimary}, colback=dfbgtint,
    left=10pt, right=10pt, top=8pt, bottom=8pt,
    before skip=\baselineskip, after skip=0.5\baselineskip},
  dftip/.style={enhanced, frame hidden,
    borderline west={3.5pt}{0pt}{dfgreen}, colback=dfbggreen,
    left=10pt, right=10pt, top=8pt, bottom=8pt,
    before skip=\baselineskip, after skip=0.5\baselineskip},
  dferrstyle/.style={enhanced, frame hidden,
    borderline west={3.5pt}{0pt}{dferror}, colback=dfbgerror,
    left=10pt, right=10pt, top=8pt, bottom=8pt,
    before skip=\baselineskip, after skip=0.5\baselineskip},
}
% Per-type opener commands
\newcommand{\dfadmonnote}[1]{\begin{tcolorbox}[dfnote]{\color{dfaccent}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmonimportant}[1]{\begin{tcolorbox}[dfnote]{\color{dfaccent}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmontip}[1]{\begin{tcolorbox}[dftip]{\color{dfgreen}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmonhint}[1]{\begin{tcolorbox}[dftip]{\color{dfgreen}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmonwarning}[1]{\begin{tcolorbox}[dfwarn]{\color{dfprimary}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmoncaution}[1]{\begin{tcolorbox}[dfwarn]{\color{dfprimary}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmondanger}[1]{\begin{tcolorbox}[dferrstyle]{\color{dferror}\sffamily\bfseries#1}\par\smallskip}
\newcommand{\dfadmonerror}[1]{\begin{tcolorbox}[dferrstyle]{\color{dferror}\sffamily\bfseries#1}\par\smallskip}
% Dispatcher: look up \dfadmon<type>; fall back to note style for unknown types
\newcommand{\dfadmonbegin}[2]{%
  \ifcsdef{dfadmon#1}{\csuse{dfadmon#1}{#2}}{\dfadmonnote{#2}}%
}
% sphinx.sty is loaded by \documentclass before the user preamble runs, so
% sphinxadmonition is already defined here and \renewenvironment works directly.
\renewenvironment{sphinxadmonition}[2]{%
  \dfadmonbegin{#1}{#2}%
}{%
  \end{tcolorbox}%
}
