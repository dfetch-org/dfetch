dfetch Runtime Usage
====================

.. ============================================================
.. Auto-generated file — do not edit manually.
.. Regenerate with (see security/README.md for exact commands):
..
..   python -m security.tm_<supply_chain|usage> \
..       --report security/report_template.rst \
..       > doc/explanation/threat_model_<name>.rst
..
.. ============================================================

Risk Context
------------

This report follows the risk-based approach of `BSI TR-03183-1
<https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03183/BSI-TR-03183-1.pdf>`_
Chapter 5.

Threat model for dfetch.  Covers the post-install lifecycle: reading the manifest, fetching dependencies from VCS and archive sources, applying patches, writing vendored files, and generating reports (SBOM, SARIF, check output).  The installed dfetch package - produced by the supply chain in tm_supply_chain.py - is the entry point.

Assumptions
-----------

.. list-table::
   :header-rows: 1
   :widths: 30 70
   :width: 100%

   * - Name
     - Description

   * - Trusted workstation
     - Developer workstations are trusted at dfetch invocation time.  A compromised workstation is outside the scope of this threat model.

   * - TLS delegated to client
     - TLS certificate validation is delegated to the OS trust store and the git / svn / urllib clients.  dfetch does not independently validate certificates.

   * - No persisted secrets
     - No runtime secrets are persisted to disk by dfetch itself.  VCS credentials are managed by the OS keychain, SSH agent, or CI secret store.

   * - Optional integrity hash
     - The ``integrity.hash`` field in the manifest is optional.  Archive dependencies without it have no content-authenticity guarantee beyond TLS transport, which is itself absent for plain ``http://`` URLs.

   * - Mutable VCS references
     - Branch- and tag-pinned Git dependencies are mutable references.  Upstream force-pushes silently change what is fetched without triggering a manifest diff.

   * - Manifest under code review
     - The manifest (``dfetch.yaml``) is under version control and subject to code review.  An adversary with write access to the manifest can redirect fetches to attacker-controlled sources; this threat is addressed at the code-review boundary, not within dfetch itself.

   * - dfetch scope boundary
     - dfetch is responsible only for its own security posture.  The security of fetched third-party source code is the responsibility of the manifest author who selects and pins each dependency.

   * - No HTTPS enforcement
     - HTTPS enforcement is the responsibility of the manifest author.  dfetch accepts ``http://``, ``svn://``, and other non-TLS scheme URLs as written - it does not upgrade or reject them.


Actors
------

.. list-table::
   :header-rows: 1
   :widths: 25 75
   :width: 100%

   * - Name
     - Description

   * - Developer
     - Writes and reviews ``dfetch.yaml``; selects upstream sources, pins revisions, and optionally enables ``integrity.hash`` for archive dependencies.  Trusted at workstation invocation time.  Responsible for choosing trustworthy upstream sources and keeping pins current.


Boundaries
----------

.. list-table::
   :header-rows: 1
   :widths: 25 75
   :width: 100%

   * - Name
     - Description

   * - Local Developer Environment
     - Developer workstation or local CI runner.  Assumed trusted at invocation time.  Hosts the manifest (``dfetch.yaml``), vendor directory, dependency metadata (``.dfetch_data.yaml``), and patch files.

   * - Internet
     - All traffic crossing the local/remote boundary.  TLS enforcement is the responsibility of the OS and VCS clients; dfetch does not enforce HTTPS on manifest URLs.

   * - Remote VCS Infrastructure
     - Upstream Git and SVN servers (GitHub, GitLab, Gitea, self-hosted).  Not controlled by the dfetch project; content is untrusted until verified.

   * - Archive Content Space
     - Downloaded archive bytes before extraction and validation.  Decompression-bomb and path-traversal checks enforce this boundary during extraction.


Data Flow Diagram
-----------------

.. raw:: html

   <div class="tm-diagram" role="button" tabindex="0" title="Click to view fullscreen">

.. uml::

   @startdot
   digraph tm {
       graph [
           fontname = Arial;
           fontsize = 14;
       ]
       node [
           fontname = Arial;
           fontsize = 14;
           rankdir = lr;
       ]
       edge [
           shape = none;
           arrowtail = onormal;
           fontname = Arial;
           fontsize = 12;
       ]
       labelloc = "t";
       fontsize = 20;
       nodesep = 1;

       subgraph cluster_boundary_ArchiveContentSpace_7113ed0f48 {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>Archive Content\nSpace</i>>;
           ]

           process_AArchiveExtractiontarfilezipfile_b8773cb4e7 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "A-24: Archive\nExtraction\n(tarfile /\nzipfile)";
               margin = 0.02;
           ]

       }

       subgraph cluster_boundary_Internet_88f2d9c06f {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>Internet</i>>;
           ]


       }

       subgraph cluster_boundary_LocalDeveloperEnvironment_acf3059e70 {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>Local Developer\nEnvironment</i>>;
           ]

           actor_Developer_f2eb7a3ff7 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "Developer";
               margin = 0.02;
           ]

           externalentity_AConsumerBuildSystem_0291419f72 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-11: Consumer\nBuild System";
               margin = 0.02;
           ]

           process_AdfetchProcess_c76a0a7067 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "A-22: dfetch\nProcess";
               margin = 0.02;
           ]

           process_APatchApplicationpatchng_c6f87088c2 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "A-25: Patch\nApplication\n(patch-ng)";
               margin = 0.02;
           ]

           datastore_AdfetchManifest_9345ab4c19 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-12: dfetch\nManifest";
           ]

           datastore_AFetchedSourceCode_86e4604564 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-13: Fetched\nSource Code";
           ]

           datastore_ASBOMOutputCycloneDX_b2e5892d06 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-15: SBOM Output\n(CycloneDX)";
           ]

           datastore_ADependencyMetadata_990b886585 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-18: Dependency\nMetadata";
           ]

           datastore_APatchFiles_9df04f8dae [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-19: Patch Files";
           ]

           datastore_ALocalVCSCachetemp_da43120000 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-20: Local VCS\nCache (temp)";
           ]

           datastore_AAuditCheckReports_7eb89910ee [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-21: Audit /\nCheck Reports";
           ]

           process_AGitClonegitinitfetchcheckout_86c0e9a37a [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "A-27: Git Clone\n(git init / fetch\n/ checkout)";
               margin = 0.02;
           ]

           process_ASVNExportsvnexport_dd106a3558 [
               shape = circle;
               color = black;
               fontcolor = black;
               label = "A-26: SVN Export\n(svn export)";
               margin = 0.02;
           ]

       }

       subgraph cluster_boundary_RemoteVCSInfrastructure_579e9aae81 {
           graph [
               fontsize = 10;
               fontcolor = black;
               style = dashed;
               color = firebrick2;
               label = <<i>Remote VCS\nInfrastructure</i>>;
           ]

           externalentity_ARemoteVCSServer_d2006ce1bb [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-09: Remote VCS\nServer";
               margin = 0.02;
           ]

           externalentity_AArchiveHTTPServer_f8af758679 [
               shape = square;
               color = black;
               fontcolor = black;
               label = "A-10: Archive HTTP\nServer";
               margin = 0.02;
           ]

           datastore_AUpstreamSourceAttestationVSA_2c440ebe53 [
               shape = cylinder;
               color = black;
               fontcolor = black;
               label = "A-23: Upstream\nSource Attestation\n(VSA)";
           ]

       }

       actor_Developer_f2eb7a3ff7 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-01: Invoke\ndfetch command";
       ]

       datastore_AdfetchManifest_9345ab4c19 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-02: Read\nmanifest";
       ]

       process_AdfetchProcess_c76a0a7067 -> externalentity_ARemoteVCSServer_d2006ce1bb [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-03a: Fetch VCS\ncontent -\nHTTPS/SSH";
       ]

       process_AdfetchProcess_c76a0a7067 -> externalentity_ARemoteVCSServer_d2006ce1bb [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-03b: Fetch VCS\ncontent - svn:// /\nhttp://";
       ]

       externalentity_ARemoteVCSServer_d2006ce1bb -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-04a: VCS\ncontent inbound -\nHTTPS/SSH";
       ]

       externalentity_ARemoteVCSServer_d2006ce1bb -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-04b: VCS\ncontent inbound -\nsvn:// / http://";
       ]

       process_AdfetchProcess_c76a0a7067 -> externalentity_AArchiveHTTPServer_f8af758679 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-05a: Archive\ndownload request -\nHTTPS";
       ]

       process_AdfetchProcess_c76a0a7067 -> externalentity_AArchiveHTTPServer_f8af758679 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-05b: Archive\ndownload request -\nHTTP";
       ]

       externalentity_AArchiveHTTPServer_f8af758679 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-06a: Archive\nbytes - HTTPS";
       ]

       externalentity_AArchiveHTTPServer_f8af758679 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-06b: Archive\nbytes - HTTP\n(plaintext risk)";
       ]

       process_AdfetchProcess_c76a0a7067 -> datastore_AFetchedSourceCode_86e4604564 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-07: Write\nvendored files";
       ]

       process_AdfetchProcess_c76a0a7067 -> datastore_ADependencyMetadata_990b886585 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-08: Write\ndependency\nmetadata";
       ]

       process_AdfetchProcess_c76a0a7067 -> datastore_ASBOMOutputCycloneDX_b2e5892d06 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-09: Write SBOM";
       ]

       datastore_ADependencyMetadata_990b886585 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-16: Read\ndependency\nmetadata";
       ]

       datastore_APatchFiles_9df04f8dae -> process_APatchApplicationpatchng_c6f87088c2 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-10: Read patch\nfor application";
       ]

       process_APatchApplicationpatchng_c6f87088c2 -> datastore_AFetchedSourceCode_86e4604564 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-10b: Write\npatched files to\nvendor directory";
       ]

       datastore_AFetchedSourceCode_86e4604564 -> externalentity_AConsumerBuildSystem_0291419f72 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-15: Vendored\nsource to build";
       ]

       process_AdfetchProcess_c76a0a7067 -> process_AArchiveExtractiontarfilezipfile_b8773cb4e7 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-11: Dispatch\narchive bytes to\nextraction";
       ]

       process_AArchiveExtractiontarfilezipfile_b8773cb4e7 -> datastore_ALocalVCSCachetemp_da43120000 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-12: Write\nextracted archive\nto temp dir";
       ]

       process_AdfetchProcess_c76a0a7067 -> process_ASVNExportsvnexport_dd106a3558 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-13: Dispatch\nSVN export\nsubprocess";
       ]

       process_ASVNExportsvnexport_dd106a3558 -> datastore_ALocalVCSCachetemp_da43120000 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-14: Write SVN\nexport to temp dir";
       ]

       process_AdfetchProcess_c76a0a7067 -> process_AGitClonegitinitfetchcheckout_86c0e9a37a [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-23: Dispatch\ngit clone\nsubprocess";
       ]

       process_AGitClonegitinitfetchcheckout_86c0e9a37a -> datastore_ALocalVCSCachetemp_da43120000 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-24: Write git\ncheckout to temp\ndir";
       ]

       process_AdfetchProcess_c76a0a7067 -> datastore_AAuditCheckReports_7eb89910ee [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-17: Write audit\n/ check reports";
       ]

       datastore_ALocalVCSCachetemp_da43120000 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-22: Read\nvalidated content\nfrom local VCS\ncache";
       ]

       datastore_AdfetchManifest_9345ab4c19 -> process_AdfetchProcess_c76a0a7067 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-18: Read\nintegrity hash for\narchive\nverification";
       ]

       process_AdfetchProcess_c76a0a7067 -> datastore_AdfetchManifest_9345ab4c19 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-18b: Write\ncomputed hash to\nmanifest (dfetch\nfreeze)";
       ]

       actor_Developer_f2eb7a3ff7 -> datastore_AdfetchManifest_9345ab4c19 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-20: Author /\nmaintain\ndfetch.yaml";
       ]

       externalentity_ARemoteVCSServer_d2006ce1bb -> datastore_AUpstreamSourceAttestationVSA_2c440ebe53 [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-19: VCS server\npublishes source\nattestation (not\nconsumed by\ndfetch)";
       ]

       actor_Developer_f2eb7a3ff7 -> datastore_APatchFiles_9df04f8dae [
           color = black;
           fontcolor = black;
           dir = forward;
           label = "DF-21: Create /\nmaintain patch\nfiles";
       ]

   }
   @enddot

.. raw:: html

   </div>
   <style>
   .tm-diagram{cursor:zoom-in;}
   .tm-diagram:fullscreen,
   .tm-diagram:-webkit-full-screen{
     background:#fff;display:flex;
     align-items:center;justify-content:center;
   }
   .tm-diagram:fullscreen img,
   .tm-diagram:-webkit-full-screen img{
     max-width:100vw;max-height:100vh;
     width:auto;height:auto;cursor:zoom-out;
   }
   </style>
   <script>
   (function(){
     function toggleFs(el){
       if(!document.fullscreenElement){
         (el.requestFullscreen||el.webkitRequestFullscreen).call(el);
       }else{
         (document.exitFullscreen||document.webkitExitFullscreen).call(document);
       }
     }
     document.querySelectorAll('.tm-diagram:not([data-fs])').forEach(function(d){
       d.dataset.fs='1';
       d.addEventListener('click',function(){toggleFs(d);});
       d.addEventListener('keydown',function(e){
         if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleFs(d);}
       });
     });
   })();
   </script>


Sequence Diagram
----------------

.. raw:: html

   <div class="tm-diagram" role="button" tabindex="0" title="Click to view fullscreen">

.. uml::

   @startuml
   skinparam defaultFontSize 16
   actor actor_Developer_f2eb7a3ff7 as "Developer"
   entity externalentity_ARemoteVCSServer_d2006ce1bb as "A-09: Remote\nVCS Server"
   entity externalentity_AArchiveHTTPServer_f8af758679 as "A-10:\nArchive HTTP\nServer"
   database datastore_AUpstreamSourceAttestationVSA_2c440ebe53 as "A-23:\nUpstream\nSource\nAttestation\n(VSA)"
   entity externalentity_AConsumerBuildSystem_0291419f72 as "A-11:\nConsumer\nBuild System"
   entity process_AdfetchProcess_c76a0a7067 as "A-22: dfetch\nProcess"
   entity process_APatchApplicationpatchng_c6f87088c2 as "A-25: Patch\nApplication\n(patch-ng)"
   database datastore_AdfetchManifest_9345ab4c19 as "A-12: dfetch\nManifest"
   database datastore_AFetchedSourceCode_86e4604564 as "A-13:\nFetched\nSource Code"
   database datastore_ASBOMOutputCycloneDX_b2e5892d06 as "A-15: SBOM\nOutput\n(CycloneDX)"
   database datastore_ADependencyMetadata_990b886585 as "A-18:\nDependency\nMetadata"
   database datastore_APatchFiles_9df04f8dae as "A-19: Patch\nFiles"
   entity process_AArchiveExtractiontarfilezipfile_b8773cb4e7 as "A-24:\nArchive\nExtraction\n(tarfile /\nzipfile)"
   database datastore_ALocalVCSCachetemp_da43120000 as "A-20: Local\nVCS Cache\n(temp)"
   database datastore_AAuditCheckReports_7eb89910ee as "A-21: Audit\n/ Check\nReports"
   entity process_AGitClonegitinitfetchcheckout_86c0e9a37a as "A-27: Git\nClone (git\ninit / fetch\n/ checkout)"
   entity process_ASVNExportsvnexport_dd106a3558 as "A-26: SVN\nExport (svn\nexport)"

   actor_Developer_f2eb7a3ff7 -> process_AdfetchProcess_c76a0a7067: DF-01: Invoke dfetch command
   datastore_AdfetchManifest_9345ab4c19 -> process_AdfetchProcess_c76a0a7067: DF-02: Read manifest
   process_AdfetchProcess_c76a0a7067 -> externalentity_ARemoteVCSServer_d2006ce1bb: DF-03a: Fetch VCS content - HTTPS/SSH
   process_AdfetchProcess_c76a0a7067 -> externalentity_ARemoteVCSServer_d2006ce1bb: DF-03b: Fetch VCS content - svn:// / http://
   externalentity_ARemoteVCSServer_d2006ce1bb -> process_AdfetchProcess_c76a0a7067: DF-04a: VCS content inbound - HTTPS/SSH
   externalentity_ARemoteVCSServer_d2006ce1bb -> process_AdfetchProcess_c76a0a7067: DF-04b: VCS content inbound - svn:// / http://
   process_AdfetchProcess_c76a0a7067 -> externalentity_AArchiveHTTPServer_f8af758679: DF-05a: Archive download request - HTTPS
   process_AdfetchProcess_c76a0a7067 -> externalentity_AArchiveHTTPServer_f8af758679: DF-05b: Archive download request - HTTP
   externalentity_AArchiveHTTPServer_f8af758679 -> process_AdfetchProcess_c76a0a7067: DF-06a: Archive bytes - HTTPS
   externalentity_AArchiveHTTPServer_f8af758679 -> process_AdfetchProcess_c76a0a7067: DF-06b: Archive bytes - HTTP (plaintext risk)
   process_AdfetchProcess_c76a0a7067 -> datastore_AFetchedSourceCode_86e4604564: DF-07: Write vendored files
   process_AdfetchProcess_c76a0a7067 -> datastore_ADependencyMetadata_990b886585: DF-08: Write dependency metadata
   process_AdfetchProcess_c76a0a7067 -> datastore_ASBOMOutputCycloneDX_b2e5892d06: DF-09: Write SBOM
   datastore_ADependencyMetadata_990b886585 -> process_AdfetchProcess_c76a0a7067: DF-16: Read dependency metadata
   datastore_APatchFiles_9df04f8dae -> process_APatchApplicationpatchng_c6f87088c2: DF-10: Read patch for application
   process_APatchApplicationpatchng_c6f87088c2 -> datastore_AFetchedSourceCode_86e4604564: DF-10b: Write patched files to vendor directory
   datastore_AFetchedSourceCode_86e4604564 -> externalentity_AConsumerBuildSystem_0291419f72: DF-15: Vendored source to build
   process_AdfetchProcess_c76a0a7067 -> process_AArchiveExtractiontarfilezipfile_b8773cb4e7: DF-11: Dispatch archive bytes to extraction
   process_AArchiveExtractiontarfilezipfile_b8773cb4e7 -> datastore_ALocalVCSCachetemp_da43120000: DF-12: Write extracted archive to temp dir
   process_AdfetchProcess_c76a0a7067 -> process_ASVNExportsvnexport_dd106a3558: DF-13: Dispatch SVN export subprocess
   process_ASVNExportsvnexport_dd106a3558 -> datastore_ALocalVCSCachetemp_da43120000: DF-14: Write SVN export to temp dir
   process_AdfetchProcess_c76a0a7067 -> process_AGitClonegitinitfetchcheckout_86c0e9a37a: DF-23: Dispatch git clone subprocess
   process_AGitClonegitinitfetchcheckout_86c0e9a37a -> datastore_ALocalVCSCachetemp_da43120000: DF-24: Write git checkout to temp dir
   process_AdfetchProcess_c76a0a7067 -> datastore_AAuditCheckReports_7eb89910ee: DF-17: Write audit / check reports
   datastore_ALocalVCSCachetemp_da43120000 -> process_AdfetchProcess_c76a0a7067: DF-22: Read validated content from local VCS cache
   datastore_AdfetchManifest_9345ab4c19 -> process_AdfetchProcess_c76a0a7067: DF-18: Read integrity hash for archive verification
   process_AdfetchProcess_c76a0a7067 -> datastore_AdfetchManifest_9345ab4c19: DF-18b: Write computed hash to manifest (dfetch freeze)
   actor_Developer_f2eb7a3ff7 -> datastore_AdfetchManifest_9345ab4c19: DF-20: Author / maintain dfetch.yaml
   externalentity_ARemoteVCSServer_d2006ce1bb -> datastore_AUpstreamSourceAttestationVSA_2c440ebe53: DF-19: VCS server publishes source attestation (not consumed by dfetch)
   actor_Developer_f2eb7a3ff7 -> datastore_APatchFiles_9df04f8dae: DF-21: Create / maintain patch files
   @enduml

.. raw:: html

   </div>
   <style>
   .tm-diagram{cursor:zoom-in;}
   .tm-diagram:fullscreen,
   .tm-diagram:-webkit-full-screen{
     background:#fff;display:flex;
     align-items:center;justify-content:center;
   }
   .tm-diagram:fullscreen img,
   .tm-diagram:-webkit-full-screen img{
     max-width:100vw;max-height:100vh;
     width:auto;height:auto;cursor:zoom-out;
   }
   </style>
   <script>
   (function(){
     function toggleFs(el){
       if(!document.fullscreenElement){
         (el.requestFullscreen||el.webkitRequestFullscreen).call(el);
       }else{
         (document.exitFullscreen||document.webkitExitFullscreen).call(document);
       }
     }
     document.querySelectorAll('.tm-diagram:not([data-fs])').forEach(function(d){
       d.dataset.fs='1';
       d.addEventListener('click',function(){toggleFs(d);});
       d.addEventListener('keydown',function(e){
         if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleFs(d);}
       });
     });
   })();
   </script>


Asset Identification
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 40 13 17
   :width: 100%

   * - Name
     - Description
     - Type
     - C / I / A
   * - A-09: Remote VCS Server
     - Upstream Git or SVN host: GitHub, GitLab, Gitea, self-hosted Git/SVN.  Not controlled by the dfetch project; content is untrusted until verified.  The SLSA source level of any upstream is unknown and unverified - dfetch does not check whether the upstream enforces branch protection, mandatory review, or ancestry enforcement, and no VSA is fetched alongside repository content (A-23).  Threat postures: a compromised upstream maintainer account (phishing, credential stuffing, or MFA bypass) delivers attacker-controlled commits over an authenticated channel where transport security gives no protection — mitigated only by commit-SHA pinning and review before accepting any update.  A network-adjacent attacker (BGP hijack, compromised DNS resolver) can intercept unencrypted traffic (svn://, http://) and inject redirects, but cannot break correctly implemented TLS or SSH.
     - ExternalEntity
     - High / High / High
   * - A-10: Archive HTTP Server
     - HTTP/HTTPS server serving ``.tar.gz``, ``.tgz``, ``.tar.bz2``, ``.tar.xz``, or ``.zip`` files.  CRITICAL: ``http://`` (non-TLS) URLs are accepted without enforcement of integrity hashes - the ``integrity.hash`` field is optional.  Threat postures: a network-adjacent attacker (BGP hijack, compromised DNS resolver, or corporate proxy) can intercept ``http://`` traffic and serve a malicious archive transparently — ``integrity.hash`` is the only defence for plain-HTTP URLs.  A compromised CDN node or registry can serve malicious content under a valid TLS certificate; transport integrity gives no protection — only a verified content hash or signed attestation detects server-side substitution.
     - ExternalEntity
     - — / — / —
   * - A-11: Consumer Build System
     - Build system that compiles fetched source code (A-13).  Not controlled by dfetch - it receives untrusted third-party source.
     - ExternalEntity
     - — / — / —
   * - A-12: dfetch Manifest
     - ``dfetch.yaml`` - declares all upstream sources (URL/VCS type), version pins (branch / tag / revision / SHA), dst paths, patch references, and optional integrity hashes.  Tampering redirects fetches to attacker-controlled sources.  RISK: ``integrity.hash`` is Optional in schema - archive deps can be declared without any content-authenticity guarantee.  Threat postures: a malicious manifest contributor introduces a ``dfetch.yaml`` change that redirects a dep to an attacker-controlled URL, points ``dst:`` at a sensitive path, or embeds a credential-bearing URL — dfetch is not the control point; code review at the PR boundary is the intended mitigating control.  A local-filesystem attacker with write access to the working tree (gained via a compromised dev dependency, malicious post-install hook, or lateral movement) can tamper with ``.dfetch_data.yaml``, patch files, and vendored source after dfetch writes them to disk.
     - Datastore
     - Critical / Critical / —
   * - A-13: Fetched Source Code
     - Third-party source code written to the ``dst:`` path after extraction / checkout.  Becomes a direct build input for the consuming project.  A compromised upstream or MITM can inject malicious code that executes in the consumer's build system, test runner, or production binary.
     - Datastore
     - Critical / Critical / High
   * - A-15: SBOM Output (CycloneDX)
     - CycloneDX JSON/XML produced by ``dfetch report -t sbom``.  Enumerates vendored components with PURL, license, and hash.  Falsification hides actual dependencies from downstream CVE scanners.  NOTE: this SBOM covers vendored deps only - dfetch itself has a separate machine-readable SBOM published on PyPI (see A-04 in tm_supply_chain.py).
     - Datastore
     - High / High / —
   * - A-16: VCS Credentials
     - SSH private keys, HTTPS Personal Access Tokens, SVN passwords.  Used to authenticate to private upstream repositories.  dfetch never persists these - managed by OS keychain, SSH agent, or CI secret store.
     - Data
     - High / High / High
   * - A-17: Embedded Credential in Remote URL
     - A VCS or archive URL that encodes a credential in the userinfo component (e.g. ``https://user:TOKEN@github.com/org/repo.git``).  dfetch writes ``remote_url`` verbatim to ``.dfetch_data.yaml`` after each successful fetch.  If the URL contains a Personal Access Token or password, that credential is persisted in plaintext and typically committed to VCS, where it becomes readable from every clone and CI checkout indefinitely.
     - Data
     - — / — / —
   * - A-18: Dependency Metadata
     - ``.dfetch_data.yaml`` files written after each successful fetch.  Contains: remote_url, revision/branch/tag, hash, last-fetch timestamp.  Read by ``dfetch check`` to detect outdated deps.  Tampering can suppress update notifications - an attacker who controls the local filesystem can silently mask a compromised vendored dep.
     - Datastore
     - High / High / —
   * - A-19: Patch Files
     - Unified-diff ``.patch`` files referenced by ``patch:`` in ``dfetch.yaml``.  Applied by ``patch-ng`` after fetch.  dfetch validates that each patch file path resides within the project directory (``subproject.py``), but does not check where the patch contents will write — a malicious patch can still write to arbitrary destination paths within reach of ``patch-ng``.  Patch files are not integrity-verified (no hash in manifest schema).
     - Datastore
     - High / High / —
   * - A-20: Local VCS Cache (temp)
     - Temporary directory used during git-clone / svn-checkout / archive extraction.  Deleted after content is copied to dst.  Path-traversal attacks targeting this space are mitigated by ``check_no_path_traversal()`` and post-extraction symlink walks.
     - Datastore
     - High / High / High
   * - A-21: Audit / Check Reports
     - SARIF, Jenkins warnings-ng, Code Climate JSON produced by ``dfetch check``.  Falsification hides vulnerabilities from downstream security dashboards.
     - Datastore
     - High / High / —
   * - A-22: dfetch Process
     - Python CLI entry point dispatching to: update, check, diff, add, remove, update-patch, format-patch, freeze, import, init, report, validate, environment.  Invokes Git and SVN as subprocesses (``shell=False``, list args).  Extracts archives with decompression-bomb limits and path-traversal checks.
     - Process
     - High / High / High
   * - A-23: Upstream Source Attestation (VSA)
     - SLSA Source Provenance Attestation or Verification Summary Attestation (VSA) that an upstream VCS host can publish for a specific revision, attesting that the source-level controls required by a given SLSA source level - branch protection, mandatory review, and ancestry enforcement - were applied.  CRITICAL: dfetch has no mechanism to request or verify source-level attestations and the manifest schema has no field to declare an expected SLSA source level.  In the absence of a VSA the consumer cannot cryptographically distinguish a well-governed upstream from one with no controls at all.
     - Datastore
     - High / High / —
   * - A-24: Archive Extraction (tarfile / zipfile)
     - Decompresses and extracts TAR (.tar.gz/.tgz/.tar.bz2/.tar.xz) and ZIP archives to a temporary directory.  Pre-extraction checks validate decompression-bomb limits, path traversal, symlinks, hardlinks, device files, and FIFOs.  On Python ≥ 3.11.4: ``filter='tar'`` strips setuid/setgid bits during extraction.  On Python < 3.11.4: ``extractall()`` is called without a filter - setuid, setgid, and sticky bits from TAR member headers are preserved on the extracted files, allowing a malicious archive to introduce setuid-root binaries into the vendor directory.
     - Process
     - High / High / High
   * - A-25: Patch Application (patch-ng)
     - Invokes ``patch-ng`` to apply unified-diff files from ``patch:`` references in the manifest.  dfetch validates that each patch file resides within the project directory (``subproject.py``), but does not independently sanitise the destination paths *inside* the patch file before handing off to the library.  Path safety for patch application targets is delegated to ``patch-ng``'s internal implementation.
     - Process
     - High / High / High
   * - A-26: SVN Export (svn export)
     - Runs ``svn export --non-interactive --force`` to check out SVN dependencies.  The ``--ignore-externals`` flag is NOT passed.  SVN repositories with ``svn:externals`` properties will trigger additional fetches from third-party SVN servers not declared in ``dfetch.yaml``.  After export, ``SvnSubProject._fetch_externals()`` queries the externals list and records each one as a ``Dependency`` with ``source_type='svn-external'`` — mirroring the metadata tracking that git submodules receive.  These fetches bypass dfetch's manifest controls: no integrity hash and no code review of the external URL (the URL comes from the upstream repository, not from ``dfetch.yaml``).
     - Process
     - High / High / High
   * - A-27: Git Clone (git init / fetch / checkout)
     - Sequence of ``git init``, ``git remote add origin``, ``git fetch``, and ``git reset --hard FETCH_HEAD`` (or ``git checkout``) invoked as list-arg subprocesses to check out Git dependencies.  Sparse-checkout (``core.sparsecheckout``) is applied when a ``src:`` path is specified.  ``GIT_TERMINAL_PROMPT=0`` and ``BatchMode=yes`` suppress interactive credential prompts.  No commit-signature or tag-signature verification is performed; authenticity relies entirely on transport security (TLS / SSH).
     - Process
     - High / High / High





Dataflows
---------

.. list-table::
   :header-rows: 1
   :widths: 35 20 20 25
   :width: 100%

   * - Name
     - From
     - To
     - Protocol

   * - DF-01: Invoke dfetch command
     - Developer
     - A-22: dfetch Process
     -

   * - DF-02: Read manifest
     - A-12: dfetch Manifest
     - A-22: dfetch Process
     -

   * - DF-03a: Fetch VCS content - HTTPS/SSH
     - A-22: dfetch Process
     - A-09: Remote VCS Server
     - HTTPS / SSH

   * - DF-03b: Fetch VCS content - svn:// / http://
     - A-22: dfetch Process
     - A-09: Remote VCS Server
     - HTTP / SVN

   * - DF-04a: VCS content inbound - HTTPS/SSH
     - A-09: Remote VCS Server
     - A-22: dfetch Process
     - HTTPS / SSH

   * - DF-04b: VCS content inbound - svn:// / http://
     - A-09: Remote VCS Server
     - A-22: dfetch Process
     - HTTP / SVN

   * - DF-05a: Archive download request - HTTPS
     - A-22: dfetch Process
     - A-10: Archive HTTP Server
     - HTTPS

   * - DF-05b: Archive download request - HTTP
     - A-22: dfetch Process
     - A-10: Archive HTTP Server
     - HTTP

   * - DF-06a: Archive bytes - HTTPS
     - A-10: Archive HTTP Server
     - A-22: dfetch Process
     - HTTPS

   * - DF-06b: Archive bytes - HTTP (plaintext risk)
     - A-10: Archive HTTP Server
     - A-22: dfetch Process
     - HTTP

   * - DF-07: Write vendored files
     - A-22: dfetch Process
     - A-13: Fetched Source Code
     -

   * - DF-08: Write dependency metadata
     - A-22: dfetch Process
     - A-18: Dependency Metadata
     -

   * - DF-09: Write SBOM
     - A-22: dfetch Process
     - A-15: SBOM Output (CycloneDX)
     -

   * - DF-16: Read dependency metadata
     - A-18: Dependency Metadata
     - A-22: dfetch Process
     -

   * - DF-10: Read patch for application
     - A-19: Patch Files
     - A-25: Patch Application (patch-ng)
     -

   * - DF-10b: Write patched files to vendor directory
     - A-25: Patch Application (patch-ng)
     - A-13: Fetched Source Code
     -

   * - DF-15: Vendored source to build
     - A-13: Fetched Source Code
     - A-11: Consumer Build System
     -

   * - DF-11: Dispatch archive bytes to extraction
     - A-22: dfetch Process
     - A-24: Archive Extraction (tarfile / zipfile)
     -

   * - DF-12: Write extracted archive to temp dir
     - A-24: Archive Extraction (tarfile / zipfile)
     - A-20: Local VCS Cache (temp)
     -

   * - DF-13: Dispatch SVN export subprocess
     - A-22: dfetch Process
     - A-26: SVN Export (svn export)
     -

   * - DF-14: Write SVN export to temp dir
     - A-26: SVN Export (svn export)
     - A-20: Local VCS Cache (temp)
     -

   * - DF-23: Dispatch git clone subprocess
     - A-22: dfetch Process
     - A-27: Git Clone (git init / fetch / checkout)
     -

   * - DF-24: Write git checkout to temp dir
     - A-27: Git Clone (git init / fetch / checkout)
     - A-20: Local VCS Cache (temp)
     -

   * - DF-17: Write audit / check reports
     - A-22: dfetch Process
     - A-21: Audit / Check Reports
     -

   * - DF-22: Read validated content from local VCS cache
     - A-20: Local VCS Cache (temp)
     - A-22: dfetch Process
     -

   * - DF-18: Read integrity hash for archive verification
     - A-12: dfetch Manifest
     - A-22: dfetch Process
     -

   * - DF-18b: Write computed hash to manifest (dfetch freeze)
     - A-22: dfetch Process
     - A-12: dfetch Manifest
     -

   * - DF-20: Author / maintain dfetch.yaml
     - Developer
     - A-12: dfetch Manifest
     -

   * - DF-19: VCS server publishes source attestation (not consumed by dfetch)
     - A-09: Remote VCS Server
     - A-23: Upstream Source Attestation (VSA)
     -

   * - DF-21: Create / maintain patch files
     - Developer
     - A-19: Patch Files
     -


Threats
-------

.. list-table::
   :header-rows: 1
   :widths: 10 22 18 15 34
   :width: 100%

   * - ID
     - Description
     - Target
     - Analysis
     - Controls / Notes
   * - DFT-01
     - Unencrypted transport interception (MITM)
     - DF-06b: Archive bytes - HTTP (plaintext risk)
     - | **Sev:** 🟠H
       | **Risk:** 🔴C
       | **STRIDE:** T S
       | **Status:** Mitigate
     - C-005 mitigates only when ``integrity.hash`` is present; plain HTTP without a hash has no transport or content protection.
   * - DFT-02
     - Supply-chain content substitution via server-side compromise
     - DF-04a: VCS content inbound - HTTPS/SSH
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T S
       | **Status:** Mitigate
     - Archives: C-005 mitigates when hash is present. Git/SVN refs have no equivalent integrity mechanism; pinning to a commit SHA is the strongest available mitigation.
   * - DFT-03
     - Path traversal in archive or patch extraction
     - A-25: Patch Application (patch-ng)
     - | **Sev:** 🔴VH
       | **Risk:** 🟠H
       | **STRIDE:** T E
       | **Status:** Mitigate
     - Archive and VCS extraction mitigated by C-001, C-003, C-004. Patch files carry no integrity hash and are not independently verified.
   * - DFT-04
     - Sensitive datastore write without content integrity verification
     - A-13: Fetched Source Code
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T
       | **Status:** Mitigate
     - C-008
   * - DFT-05
     - Mutable VCS reference enables silent content substitution
     - DF-04a: VCS content inbound - HTTPS/SSH
     - | **Sev:** 🟡M
       | **Risk:** 🟠H
       | **STRIDE:** T S
       | **Status:** Mitigate
     - C-005 mitigates archive deps when hash present. Git/SVN: no integrity mechanism; pinning to an immutable commit SHA is recommended but not enforced by dfetch.
   * - DFT-07
     - CI/CD secret exfiltration via supply-chain attack on build environment
     - A-25: Patch Application (patch-ng)
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** I
       | **Status:** Accept
     - dfetch uses ``shell=False`` throughout (C-007); residual supply-chain compromise of dfetch itself is the supply-chain model's scope.  Accepted based on the **dfetch scope boundary** assumption: dfetch is responsible only for its own security posture; a compromised dfetch installation is addressed by the supply-chain threat model, not the runtime-usage model.
   * - DFT-08
     - Tampered secondary artifact suppresses or bypasses security checks
     - A-18: Dependency Metadata
     - | **Sev:** 🟡M
       | **Risk:** 🟠H
       | **STRIDE:** T
       | **Status:** Mitigate
     - Manifest schema (C-008) validates all string fields; patch files carry no integrity hash and are not verified before application.
   * - DFT-09
     - Archive decompression bomb causes resource exhaustion
     - A-24: Archive Extraction (tarfile / zipfile)
     - | **Sev:** 🟡M
       | **Risk:** 🟡M
       | **STRIDE:** D
       | **Status:** Mitigate
     - C-002
   * - DFT-10
     - Build or development dependency substitution via compromised registry
     - A-22: dfetch Process
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T
       | **Status:** Accept
     - dfetch's runtime dependency supply-chain is the supply-chain model's scope; use a verified dfetch installation.  Accepted based on the **dfetch scope boundary** assumption: dfetch is responsible only for its own security posture; the integrity of dfetch's own runtime dependencies is out of scope for this usage model and is addressed by the supply-chain threat model.
   * - DFT-12
     - SSRF via unvalidated HTTP redirect chain
     - DF-05a: Archive download request - HTTPS
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** I
       | **Status:** Accept
     - Archive downloads follow up to 10 HTTP redirects without validating the destination against RFC-1918, loopback, or link-local ranges; SSRF to internal metadata endpoints is possible.  Accepted based on the **No HTTPS enforcement** assumption: HTTPS enforcement and safe URL selection are the manifest author's responsibility; the manifest is under code review, and URLs that could expose internal services should be rejected at the review boundary.
   * - DFT-13
     - Credential embedded in source URL persisted to unencrypted metadata
     - A-18: Dependency Metadata
     - | **Sev:** 🟠H
       | **Risk:** 🟡M
       | **STRIDE:** I
       | **Status:** Accept
     - dfetch persists the configured URL to ``.dfetch_data.yaml``; credentials embedded in URLs appear in that file in plaintext.  Accepted based on the **No persisted secrets** assumption: no runtime secrets are persisted to disk by dfetch itself — VCS credentials are expected to be managed by the OS keychain, SSH agent, or CI secret store rather than embedded in source URLs.
   * - DFT-14
     - Dangerous file permission bits preserved during archive extraction
     - A-24: Archive Extraction (tarfile / zipfile)
     - | **Sev:** 🟠H
       | **Risk:** 🟡M
       | **STRIDE:** T
       | **Status:** Accept
     - dfetch does not strip executable or setuid/setgid bits from extracted archive members; on Python < 3.11.4, TAR extraction preserves such bits.  dfetch supports Python ≥ 3.10 (``requires-python = '>=3.10'`` in ``pyproject.toml``), so this is a live concern for users on Python 3.10.x or Python 3.11.0–3.11.3.  Mitigation: pin dfetch to archives from trusted, reviewed sources only, or run on Python ≥ 3.11.4 where the TAR extraction filter strips these bits.  Accepted based on the **Trusted workstation** assumption: developer workstations are trusted at dfetch invocation time; setuid bits on extracted files in the vendor directory are a local concern within that trusted environment, and a compromised workstation is outside the scope of this model.
   * - DFT-15
     - VCS externals / submodules trigger undeclared third-party fetches
     - A-27: Git Clone (git init / fetch / checkout)
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T
       | **Status:** Accept
     - Git submodules are followed: ``git submodule update --init --recursive`` is called unconditionally during every Git fetch (``dfetch/vcs/git.py``), and each submodule is recorded as a ``Dependency`` with ``source_type='git-submodule'`` (``gitsubproject.py``).  SVN ``export`` is invoked without ``--ignore-externals``; each ``svn:externals`` entry triggers an additional fetch, and ``SvnSubProject._fetch_externals()`` records it as a ``Dependency`` with ``source_type='svn-external'`` (``svnsubproject.py``).  Both behaviours are intentional — dfetch vendors submodule and external trees and surfaces them in metadata — but the fetched URLs come from the upstream repository (``.gitmodules`` / ``svn:externals``), not from ``dfetch.yaml``, and therefore bypass manifest code review and carry no integrity hash.  Suppressing these fetches (e.g. passing ``--no-recurse-submodules`` or ``--ignore-externals``) would be a design change that removes intentional vendoring behaviour.  Accepted based on the **Manifest under code review** assumption: the choice to vendor an upstream that contains submodules or svn:externals is declared in ``dfetch.yaml`` and subject to code review; the decision to trust those nested URLs is made at the manifest-review boundary.
   * - DFT-16
     - Configured destination path allows writes to security-sensitive project directories
     - A-22: dfetch Process
     - | **Sev:** 🔴VH
       | **Risk:** 🟠H
       | **STRIDE:** T E
       | **Status:** Accept
     - C-001 prevents writes outside the project root; no denylist blocks writes to sensitive within-root paths such as ``.github/workflows/``.  Defense-in-depth: CI pipelines should run ``dfetch update`` in a step that does not have write access to ``.github/workflows/`` (e.g. by restricting permissions or running in a directory sandbox).  Accepted based on the **Manifest under code review** assumption: the ``dst:`` path for every dependency is declared in ``dfetch.yaml`` and subject to code review; any change pointing a destination at a sensitive directory would be rejected at the review boundary.
   * - DFT-17
     - Typosquatting or unverified source identity on an unauthenticated channel
     - DF-06a: Archive bytes - HTTPS
     - | **Sev:** 🟠H
       | **Risk:** 🟡M
       | **STRIDE:** S
       | **Status:** Accept
     - Manifest author responsibility; the manifest is under code review.  Accepted based on the **Manifest under code review** assumption: ``dfetch.yaml`` is under version control and subject to code review; an adversary who introduces a typosquatted or unverified URL must do so through a manifest change that passes the review boundary.
   * - DFT-18
     - Dependency confusion - public registry package shadows private internal package
     - A-12: dfetch Manifest
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T S
       | **Status:** Accept
     - Not applicable to dfetch's fetch-by-explicit-URL model; relevant only if using package-registry shorthand.  Accepted based on the **dfetch scope boundary** assumption: dfetch fetches by explicit URL declared in the manifest rather than by package name resolved against a registry; dependency confusion via registry namespace shadowing cannot occur within dfetch's fetch model.
   * - DFT-19
     - Malicious upstream update or intentional maintainer sabotage (protestware)
     - A-13: Fetched Source Code
     - | **Sev:** 🔴VH
       | **Risk:** 🟠H
       | **STRIDE:** T
       | **Status:** Accept
     - Upstream maintainer trust; pinning to an immutable commit SHA is the strongest available mitigation but is not enforced by dfetch.  Accepted based on the **dfetch scope boundary** assumption: the security of fetched third-party source code is the responsibility of the manifest author who selects and pins each dependency; intentional maintainer sabotage of an upstream is outside dfetch's control.
   * - DFT-20
     - Abandoned package namespace reclaimed by malicious actor
     - A-12: dfetch Manifest
     - | **Sev:** 🟠H
       | **Risk:** 🟡M
       | **STRIDE:** S T
       | **Status:** Accept
     - Not applicable to direct-URL fetches; relevant only if using Git-hosting shorthand with inferred registry lookup.  Accepted based on the **dfetch scope boundary** assumption: dfetch fetches by explicit URL declared in the manifest rather than resolving package names against a registry; abandoned-namespace reclaim attacks require a registry lookup step that does not exist in dfetch's fetch model.
   * - DFT-21
     - Unsigned or forged VCS tag accepted as a trusted version pin
     - DF-04a: VCS content inbound - HTTPS/SSH
     - | **Sev:** 🟠H
       | **Risk:** 🟡M
       | **STRIDE:** S T
       | **Status:** Accept
     - dfetch does not verify VCS tag signatures; pinning to an immutable commit SHA is recommended.  Accepted based on the **Mutable VCS references** assumption: branch- and tag-pinned Git dependencies are mutable references; upstream force-pushes can silently change the commit a tag resolves to without triggering a manifest diff, and tag-signature verification is not enforced by dfetch.
   * - DFT-22
     - Vendored content contains submodule or nested external reference triggering undeclared fetch
     - A-13: Fetched Source Code
     - | **Sev:** 🟡M
       | **Risk:** 🟡M
       | **STRIDE:** T
       | **Status:** Accept
     - dfetch does not parse or execute embedded build manifests (CMakeLists.txt, package.json, etc.); undeclared fetches via build-system externals cannot occur.  However, Git dependencies with submodules and SVN dependencies with ``svn:externals`` do trigger undeclared fetches — see DFT-15 for details and mitigations.  Accepted based on the **dfetch scope boundary** assumption: the security of fetched third-party source code and any nested dependencies it carries is the responsibility of the manifest author who selects and pins each dependency.
   * - DFT-23
     - Replay or freeze attack delivers stale content to suppress security updates
     - DF-06a: Archive bytes - HTTPS
     - | **Sev:** 🟡M
       | **Risk:** 🟡M
       | **STRIDE:** T
       | **Status:** Accept
     - No freshness check; ``dfetch check`` detects version drift but does not enforce a minimum version or reject stale content.  Accepted based on the **Mutable VCS references** assumption: branch- and tag-pinned dependencies are mutable references whose content can be changed by upstream force-pushes; stale-content delivery is an acknowledged consequence of using mutable pins without a freshness enforcement mechanism.
   * - DFT-24
     - Local dependency cache or metadata store poisoned to suppress integrity alerts
     - A-18: Dependency Metadata
     - | **Sev:** 🟠H
       | **Risk:** 🟡M
       | **STRIDE:** T
       | **Status:** Accept
     - ``.dfetch_data.yaml`` metadata is not integrity-protected; tampering could suppress update notifications from ``dfetch check``.  Accepted based on the **Trusted workstation** assumption: developer workstations are trusted at dfetch invocation time; local filesystem write access sufficient to tamper with ``.dfetch_data.yaml`` implies a compromised workstation, which is outside the scope of this model.
   * - DFT-25
     - Forged or unverifiable provenance attestation conceals malicious build output
     - A-15: SBOM Output (CycloneDX)
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** S T R
       | **Status:** Accept
     - dfetch does not verify upstream SLSA provenance of fetched sources; provenance verification is the consumer's responsibility.  Accepted based on the **dfetch scope boundary** assumption: the security of fetched third-party source code is the responsibility of the manifest author who selects and pins each dependency; upstream provenance attestation is outside dfetch's own security posture.
   * - DFT-26
     - Protocol or transport downgrade forces connection over insecure channel
     - A-27: Git Clone (git init / fetch / checkout)
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T I
       | **Status:** Mitigate
     - C-009 emits a visible warning immediately before the VCS command when a plaintext scheme (``http://``, ``git://``, ``svn://``) is detected, with credentials redacted and ``https://`` / ``svn+ssh://`` recommended.  Detection only — dfetch does not reject or upgrade plaintext URLs; scheme selection remains the manifest author's responsibility.
   * - DFT-28
     - CI/CD build cache poisoned to silently substitute a malicious compiled artifact
     - A-20: Local VCS Cache (temp)
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T
       | **Status:** Accept
     - Build-cache poisoning (SLSA E6) is a CI/CD supply-chain concern that applies to the dfetch build pipeline, not to runtime usage.  dfetch does not maintain a persistent compiled artifact cache; fetched source files are written directly to the vendor directory.  See the supply-chain threat model for the mitigating control (C-033).  Accepted based on the **dfetch scope boundary** assumption: dfetch is responsible only for its own security posture; the CI/CD build pipeline for dfetch itself is outside the scope of the runtime-usage model.
   * - DFT-30
     - Weak or deprecated hash algorithm allows collision-based integrity bypass
     - A-22: dfetch Process
     - | **Sev:** 🟠H
       | **Risk:** 🟠H
       | **STRIDE:** T S
       | **Status:** Mitigate
     - C-005, C-034
   * - DFT-31
     - Upstream source publishes no SLSA Source provenance attestation — consumer cannot verify upstream security controls
     - DF-04a: VCS content inbound - HTTPS/SSH
     - | **Sev:** 🟡M
       | **Risk:** 🟢L
       | **STRIDE:** R
       | **Status:** Accept
     - Upstream repositories are outside dfetch's control; no mechanism exists to require or verify upstream SLSA source level.  Accepted based on the **dfetch scope boundary** assumption: the security of fetched third-party source code is the responsibility of the manifest author who selects and pins each dependency; verifying upstream governance controls is outside dfetch's own security posture.
   * - DFT-32
     - Upstream source enforces no mandatory two-party review — single contributor can introduce changes without independent verification
     - A-13: Fetched Source Code
     - | **Sev:** 🟡M
       | **Risk:** 🟢L
       | **STRIDE:** T
       | **Status:** Accept
     - Upstream repositories are outside dfetch's control; no mechanism exists to require mandatory two-party review on upstream changes.  Accepted based on the **dfetch scope boundary** assumption: the security of fetched third-party source code is the responsibility of the manifest author who selects and pins each dependency; requiring upstream review policies is outside dfetch's own security posture.
   * - DFT-33
     - Upstream default-branch history rewritten — ancestry broken, pinned SHA orphaned or made unreachable
     - DF-04a: VCS content inbound - HTTPS/SSH
     - | **Sev:** 🟡M
       | **Risk:** 🟢L
       | **STRIDE:** T
       | **Status:** Accept
     - Upstream repositories are outside dfetch's control; dfetch cannot prevent or detect upstream force-pushes.  Accepted based on the **Mutable VCS references** assumption: branch- and tag-pinned Git dependencies are mutable references; upstream force-pushes silently change what is fetched without triggering a manifest diff, and dfetch has no mechanism to verify that a pinned SHA remains reachable after a history rewrite.


Controls
--------

.. list-table::
   :header-rows: 1
   :widths: 8 25 15 52
   :width: 100%

   * - ID
     - Name
     - Threats
     - Description
   * - C-001
     - Path-traversal prevention
     - DFT-03
     - ``check_no_path_traversal()`` resolves both the candidate path and the destination root via ``os.path.realpath`` (symlink-aware), then rejects any path whose resolved prefix does not start with the resolved root.  Applied to every file copy and post-extraction symlink.  ``dfetch/util/util.py``
   * - C-002
     - Decompression-bomb protection
     - DFT-09
     - Archives are rejected if the uncompressed size exceeds 500 MB or the member count exceeds 10 000.  ``dfetch/vcs/archive.py``
   * - C-003
     - Archive symlink validation
     - DFT-03
     - Absolute and escaping (``..``) symlink targets are rejected for both TAR and ZIP.  A post-extraction walk validates all symlinks against the manifest root.  ``dfetch/vcs/archive.py``
   * - C-004
     - Archive member type checks
     - DFT-03
     - TAR and ZIP members of type device file or FIFO are rejected outright.  ``dfetch/vcs/archive.py``
   * - C-005
     - Integrity hash verification
     - DFT-01, DFT-02, DFT-05, DFT-30
     - SHA-256, SHA-384, and SHA-512 verified via ``hmac.compare_digest`` (constant-time comparison, resistant to timing attacks).  Primary defence against content substitution for archive dependencies.  Effectiveness is conditional on the hash field being present.  ``dfetch/vcs/integrity_hash.py``
   * - C-006
     - Non-interactive VCS
     - DFT-06
     - ``GIT_TERMINAL_PROMPT=0``, ``BatchMode=yes`` for Git; ``--non-interactive`` for SVN.  Credential prompts are suppressed to prevent interactive hijacking in CI.  ``dfetch/vcs/git.py, dfetch/vcs/svn.py``
   * - C-007
     - Subprocess safety
     - DFT-06
     - All external commands invoked with ``shell=False`` and list-form arguments - no shell-injection vector.  ``dfetch/util/cmdline.py``
   * - C-008
     - Manifest input validation
     - DFT-04, DFT-08
     - StrictYAML schema with ``SAFE_STR = Regex(r"^[^\x00-\x1F\x7F-\x9F]*$")`` rejects control characters in all string fields.  ``dfetch/manifest/schema.py``
   * - C-009
     - Plaintext transport detection
     - DFT-26
     - ``plaintext_warning()`` (``dfetch/manifest/project.py``) inspects the resolved remote URL immediately before each VCS command is issued (inside the ``check_for_update`` and ``update`` spinners in ``subproject.py``).  If the scheme is ``http://``, ``git://``, or ``svn://``, a visible warning is emitted naming the redacted URL (credentials stripped from the userinfo component) and recommending ``https://`` or ``svn+ssh://``.  Detection only — dfetch still proceeds with the plaintext connection; the control raises user awareness but does not enforce scheme selection.  ``dfetch/manifest/project.py, dfetch/project/subproject.py``
   * - C-034
     - Hash algorithm allowlist (SHA-256/384/512 only)
     - DFT-30
     - ``integrity_hash.py`` accepts only ``sha256:``, ``sha384:``, and ``sha512:`` prefixes; any other algorithm prefix is rejected at parse time.  MD5 and SHA-1 are not accepted.  This directly mitigates DFT-30 (SLSA M2: exploit cryptographic hash collisions) by ensuring that integrity hashes, when present, use algorithms with no known practical collision attacks.  ``dfetch/vcs/integrity_hash.py``
