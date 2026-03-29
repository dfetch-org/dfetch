
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
