
CLI Cheatsheet
==============

.. raw:: html

   <div class="cheatsheet">

     <!-- masthead -->
     <div class="cs-masthead">
       <div class="cs-masthead-brand">
         <span class="cs-logo">df</span>
         <div>
           <div class="cs-masthead-title">Dfetch CLI Cheatsheet</div>
           <div class="cs-masthead-tagline">Vendor dependencies without the pain &nbsp;&middot;&nbsp; <code>dfetch.yaml</code> found automatically</div>
         </div>
       </div>
       <div class="cs-masthead-legend">
         <span class="cs-tok cs-tok-sc">subcommand</span>
         <span class="cs-tok cs-tok-fl">--flag</span>
         <span class="cs-tok cs-tok-ag">&lt;arg&gt;</span>
       </div>
       <button class="cs-fullscreen-btn" onclick="window.print()" title="Print" aria-label="Print cheatsheet">
         <svg width="13" height="13" viewBox="0 0 13 13" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
           <path d="M3 4V1h7v3M3 9H1V5h11v4h-2M3 7h7v5H3V7z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
         </svg>
       </button>
       <button class="cs-fullscreen-btn" id="cs-fs-btn" title="Fullscreen" aria-label="Toggle fullscreen">
         <svg width="13" height="13" viewBox="0 0 13 13" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
           <path d="M1 4.5V1h3.5M8.5 1H12v3.5M12 8.5V12H8.5M4.5 12H1V8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
         </svg>
       </button>
     </div>

     <!-- two-column body -->
     <div class="cs-body">

       <!-- column 1: Foundational + Utilities -->
       <div class="cs-col">

         <div class="cs-section">
           <div class="cs-label cs-l-primary">
             <span class="cs-label-pip"></span>Foundational
             <span class="cs-label-sub">core workflow &middot; daily use</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">init</span></div>
             <div class="cs-dsc">Create a new <code>dfetch.yaml</code> manifest</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">add</span> <span class="cs-ag">&lt;url&gt;</span></div>
             <div class="cs-dsc">Add a dependency, auto-fill defaults</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">add</span> <span class="cs-fl">-i</span> <span class="cs-ag">&lt;url&gt;</span></div>
             <div class="cs-dsc">Add interactively, step-by-step wizard</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">import</span></div>
             <div class="cs-dsc">Migrate from git submodules / SVN externals</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Show dependencies with newer versions available</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">update</span> <span class="cs-ag">[-f] [project]</span></div>
             <div class="cs-dsc">Fetch / update one or all dependencies</div>
           </div>
         </div>

         <div class="cs-section">
           <div class="cs-label cs-l-utility">
             <span class="cs-label-pip"></span>Utilities
             <span class="cs-label-sub">maintenance &middot; setup &middot; validation</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">freeze</span></div>
             <div class="cs-dsc">Pin all dependencies to currently fetched version</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">environment</span></div>
             <div class="cs-dsc">Verify VCS tools and environment setup</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">validate</span></div>
             <div class="cs-dsc">Validate the manifest without fetching</div>
           </div>
         </div>

       </div><!-- /col 1 -->

       <!-- column 2: Patching + CI/CD -->
       <div class="cs-col">

         <div class="cs-section">
           <div class="cs-label cs-l-accent">
             <span class="cs-label-pip"></span>Patching
             <span class="cs-label-sub">local changes &middot; upstream sync</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">diff</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Capture local changes as a patch file</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">update-patch</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Re-apply patches after upstream version bump</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">format-patch</span> <span class="cs-ag">[project]</span></div>
             <div class="cs-dsc">Export contributor-ready unified diff</div>
           </div>
         </div>

         <div class="cs-section">
           <div class="cs-label cs-l-ci">
             <span class="cs-label-pip"></span>CI / CD Integration
             <span class="cs-label-sub">reports &middot; sbom &middot; security</span>
           </div>

           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-fl">--jenkins-json</span></div>
             <div class="cs-dsc">Jenkins-compatible JSON report</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-fl">--sarif</span></div>
             <div class="cs-dsc">SARIF (GitHub Advanced Security etc.)</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">check</span> <span class="cs-fl">--code-climate</span></div>
             <div class="cs-dsc">Code Climate / GitLab report</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">report</span></div>
             <div class="cs-dsc">Print a dependency inventory list</div>
           </div>
           <div class="cs-row">
             <div class="cs-syn"><span class="cs-kw">dfetch</span> <span class="cs-sc">report</span> <span class="cs-fl">-t</span> <span class="cs-ag">sbom</span></div>
             <div class="cs-dsc">Generate a Software Bill of Materials</div>
           </div>
         </div>

       </div><!-- /col 2 -->

     </div><!-- /cs-body -->

     <div class="cs-footer">
       dfetch.readthedocs.io &nbsp;&middot;&nbsp; github.com/dfetch-org/dfetch
     </div>

   </div>

   <script>
   (function () {
     var btn = document.getElementById('cs-fs-btn');
     if (!btn) return;
     var cs = document.querySelector('.cheatsheet');

     function isFull() {
       return !!(document.fullscreenElement || document.webkitFullscreenElement);
     }

     function updateBtn() {
       var full = isFull();
       btn.querySelector('path').setAttribute('d', full
         ? 'M4.5 1v3.5H1M12 4.5H8.5V1M8.5 12V8.5H12M1 8.5h3.5V12'
         : 'M1 4.5V1h3.5M8.5 1H12v3.5M12 8.5V12H8.5M4.5 12H1V8.5');
       btn.title = full ? 'Exit fullscreen' : 'Fullscreen';
     }

     document.addEventListener('fullscreenchange', updateBtn);
     document.addEventListener('webkitfullscreenchange', updateBtn);

     btn.addEventListener('click', function () {
       if (isFull()) {
         (document.exitFullscreen || document.webkitExitFullscreen).call(document);
       } else {
         (cs.requestFullscreen || cs.webkitRequestFullscreen).call(cs);
       }
     });
   })();
   </script>

.. raw:: latex

   \begin{tcolorbox}[
     enhanced, arc=4pt,
     boxrule=0.5pt, colframe=black!25, colback=white,
     left=10pt, right=10pt, top=8pt, bottom=8pt,
     before skip=\baselineskip, after skip=\baselineskip,
   ]
   % masthead
   {\sffamily\bfseries\normalsize Dfetch CLI Cheatsheet}\hfill
   {\ttfamily\tiny\color{black!50}dfetch.yaml~found~automatically}\par\vspace{3pt}
   {\setlength{\fboxsep}{2pt}\tiny\sffamily
     \colorbox{dfprimary!15}{\strut\,\textcolor{dfprimary}{\ttfamily\bfseries subcommand}\,}\,
     \colorbox{dfaccent!15}{\strut\,\textcolor{dfaccent}{\ttfamily --flag}\,}\,
     \colorbox{black!8}{\strut\,\textcolor{black!50}{\ttfamily\itshape <arg>}\,}%
   }\par\nointerlineskip\vspace{5pt}%
   \noindent\textcolor{black!20}{\rule{\linewidth}{0.5pt}}\par\vspace{5pt}%
   % body: two columns
   \noindent\begin{minipage}[t]{0.482\linewidth}
   \cslabel{dfprimary}{Foundational}{core workflow · daily use}
   \begin{tabular}{@{}p{0.57\linewidth}p{0.39\linewidth}@{}}
   \cskw{dfetch} \cssc{init} & \csdsc{Create a new \texttt{dfetch.yaml}} \\[1pt]
   \cskw{dfetch} \cssc{add} \csag{<url>} & \csdsc{Add a dependency} \\[1pt]
   \cskw{dfetch} \cssc{add} \csfl{-i} \csag{<url>} & \csdsc{Add interactively} \\[1pt]
   \cskw{dfetch} \cssc{import} & \csdsc{Migrate from submodules / externals} \\[1pt]
   \cskw{dfetch} \cssc{check} \csag{[project]} & \csdsc{Show outdated dependencies} \\[1pt]
   \cskw{dfetch} \cssc{update} \csag{[-f] [project]} & \csdsc{Fetch / update dependencies} \\
   \end{tabular}
   \cslabel{dfsage}{Utilities}{maintenance · setup · validation}
   \begin{tabular}{@{}p{0.57\linewidth}p{0.39\linewidth}@{}}
   \cskw{dfetch} \cssc{freeze} & \csdsc{Pin to currently fetched version} \\[1pt]
   \cskw{dfetch} \cssc{environment} & \csdsc{Verify VCS tools} \\[1pt]
   \cskw{dfetch} \cssc{validate} & \csdsc{Validate manifest} \\
   \end{tabular}
   \end{minipage}\hfill%
   \begin{minipage}[t]{0.482\linewidth}
   \cslabel{dfaccent}{Patching}{local changes · upstream sync}
   \begin{tabular}{@{}p{0.60\linewidth}p{0.36\linewidth}@{}}
   \cskw{dfetch} \cssc{diff} \csag{[project]} & \csdsc{Capture changes as patch} \\[1pt]
   \cskw{dfetch} \cssc{update-patch} \csag{[project]} & \csdsc{Re-apply after version bump} \\[1pt]
   \cskw{dfetch} \cssc{format-patch} \csag{[project]} & \csdsc{Export unified diff} \\
   \end{tabular}
   \cslabel{dfpurple}{CI / CD Integration}{reports · sbom · security}
   \begin{tabular}{@{}p{0.60\linewidth}p{0.36\linewidth}@{}}
   \cskw{dfetch} \cssc{check} \csfl{--jenkins-json} & \csdsc{Jenkins JSON report} \\[1pt]
   \cskw{dfetch} \cssc{check} \csfl{--sarif} & \csdsc{SARIF / GitHub Security} \\[1pt]
   \cskw{dfetch} \cssc{check} \csfl{--code-climate} & \csdsc{Code Climate / GitLab} \\[1pt]
   \cskw{dfetch} \cssc{report} & \csdsc{Dependency inventory} \\[1pt]
   \cskw{dfetch} \cssc{report} \csfl{-t} \csag{sbom} & \csdsc{Software Bill of Materials} \\
   \end{tabular}
   \end{minipage}%
   % footer
   \par\nointerlineskip\vspace{5pt}%
   \noindent\textcolor{black!20}{\rule{\linewidth}{0.5pt}}\par\vspace{3pt}%
   {\centering\tiny\sffamily\color{black!50}%
     dfetch.readthedocs.io · github.com/dfetch-org/dfetch\par}%
   \end{tcolorbox}
