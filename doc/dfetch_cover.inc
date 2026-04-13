% dfetch cover page
%
% \input{dfetch_cover.inc} is called from latex_elements['maketitle'] in conf.py.
%
% Prerequisites (declared in the preamble via latex_elements):
%   packages : tikz, xcolor, fontspec, graphicx
%   colours  : dfetchCoverTop, dfetchCoverDark, dfetchCoverBottom,
%              dfetchCoverAccent, dfetchCoverLight
%   fontface : \PoiretOne  (\newfontface from fontspec)
%
\begin{titlepage}
\thispagestyle{empty}
\begin{tikzpicture}[remember picture, overlay]

  % ------------------------------------------------------------------ %
  %  BACKGROUND SECTIONS                                                %
  % ------------------------------------------------------------------ %

  % Top 60 % — Slate Dark (#3a6682, --accent-dark)
  \fill[dfetchCoverTop]
    (current page.north west) rectangle
    ([yshift=0.4\paperheight]current page.south east);

  % Middle 20 % — Near Black (#1c1917, --text)
  \fill[dfetchCoverDark]
    ([yshift=0.2\paperheight]current page.south west) rectangle
    ([yshift=0.4\paperheight]current page.south east);

  % Bottom 20 % — Amber Orange (#c2620a, --primary)
  \fill[dfetchCoverBottom]
    (current page.south west) rectangle
    ([yshift=0.2\paperheight]current page.south east);

  % ------------------------------------------------------------------ %
  %  TOP SECTION: GRID PATTERN                                          %
  % ------------------------------------------------------------------ %
  \begin{scope}
    \clip (current page.north west) rectangle
      ([yshift=0.4\paperheight]current page.south east);

    % Vertical lines
    \foreach \i in {1,2,...,14}{
      \pgfmathsetmacro{\xfrac}{\i/15}
      \draw[dfetchCoverAccent!60!dfetchCoverTop, line width=0.3pt, opacity=0.30]
        ([xshift=\xfrac\paperwidth]current page.south west) --
        ([xshift=\xfrac\paperwidth]current page.north west);
    }

    % Horizontal lines
    \foreach \i in {1,2,...,8}{
      \pgfmathsetmacro{\yfrac}{0.4 + \i * 0.075}
      \draw[dfetchCoverAccent!60!dfetchCoverTop, line width=0.3pt, opacity=0.30]
        ([yshift=\yfrac\paperheight]current page.south west) --
        ([yshift=\yfrac\paperheight]current page.south east);
    }

    % Sparse node dots at grid intersections
    \foreach \xi in {1,3,5,7,9,11,13}{
      \foreach \yi in {1,3,5,7}{
        \pgfmathsetmacro{\xdot}{\xi/15}
        \pgfmathsetmacro{\ydot}{0.4 + \yi * 0.075}
        \fill[dfetchCoverLight, opacity=0.22]
          ([xshift=\xdot\paperwidth, yshift=\ydot\paperheight]current page.south west)
          circle (1.5pt);
      }
    }
  \end{scope}

  % ------------------------------------------------------------------ %
  %  TOP SECTION: LOGO  (off-centre, right side of blue area)          %
  % ------------------------------------------------------------------ %
  \node[anchor=center, opacity=0.90]
    at ([xshift=0.70\paperwidth, yshift=0.65\paperheight]current page.south west)
    {\includegraphics[width=0.35\paperwidth]{dfetch_logo.png}};

  % ------------------------------------------------------------------ %
  %  ACCENT RULE  (Amber Orange, top edge of middle band)              %
  % ------------------------------------------------------------------ %
  \draw[dfetchCoverBottom, line width=2.5pt]
    ([yshift=0.4\paperheight]current page.south west) --
    ([yshift=0.4\paperheight]current page.south east);

  % ------------------------------------------------------------------ %
  %  MIDDLE BAND: TITLE BLOCK                                          %
  % ------------------------------------------------------------------ %

  % "User Manual" eyebrow
  \node[anchor=base west, text=dfetchCoverAccent,
        font={\sffamily\itshape\fontsize{10}{12}\selectfont},
        inner sep=0pt]
    at ([xshift=1.4cm, yshift=0.375\paperheight]current page.south west)
    {User Manual};

  % Main title — Poiret One
  \node[anchor=base west, text=dfetchCoverLight,
        font={\PoiretOne\fontsize{30}{34}\selectfont},
        inner sep=0pt]
    at ([xshift=1.4cm, yshift=0.318\paperheight]current page.south west)
    {DFetch};

  % Subtitle
  \node[anchor=base west, text=dfetchCoverAccent,
        font={\sffamily\fontsize{13}{16}\selectfont},
        inner sep=0pt]
    at ([xshift=1.4cm, yshift=0.263\paperheight]current page.south west)
    {Vendor dependencies without the pain.};

  % Thin amber accent rule under subtitle
  \draw[dfetchCoverBottom, line width=1.5pt]
    ([xshift=1.4cm,           yshift=0.238\paperheight]current page.south west) --
    ([xshift=0.60\paperwidth, yshift=0.238\paperheight]current page.south west);

  % ------------------------------------------------------------------ %
  %  BOTTOM SECTION: DOTTED PATTERN                                    %
  % ------------------------------------------------------------------ %
  \begin{scope}
    \clip (current page.south west) rectangle
      ([yshift=0.2\paperheight]current page.south east);
    \foreach \xi in {1,2,...,19}{
      \foreach \yi in {1,2,3,4}{
        \pgfmathsetmacro{\xdot}{\xi/20}
        \pgfmathsetmacro{\ydot}{\yi * 0.038}
        \fill[dfetchCoverLight, opacity=0.15]
          ([xshift=\xdot\paperwidth, yshift=\ydot\paperheight]current page.south west)
          circle (1.2pt);
      }
    }
  \end{scope}

  % ------------------------------------------------------------------ %
  %  BOTTOM SECTION: FOOTER                                            %
  % ------------------------------------------------------------------ %
  \node[anchor=south west, text=dfetchCoverLight,
        font={\sffamily\fontsize{10}{12}\selectfont},
        inner sep=0pt]
    at ([xshift=1.4cm, yshift=0.9cm]current page.south west)
    {dfetch-org $\cdot$ \py@release};

  \node[anchor=south east, text=dfetchCoverLight,
        font={\sffamily\fontsize{10}{12}\selectfont},
        inner sep=0pt]
    at ([xshift=-1.4cm, yshift=0.9cm]current page.south east)
    {User Manual};

\end{tikzpicture}
\null
\end{titlepage}
