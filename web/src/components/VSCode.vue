<template>
    <div class="home linux x64">
  
  <div id="main">
    <div class="navbar-fixed-container">
      <div class="navbar navbar-inverse navbar-fixed-top affix-top" data-spy="affix" data-offset-top="1">
        <div id="cookie-banner"></div>		<nav role="navigation" aria-label="Top Level">
          <div class="container">
            <div class="nav navbar-header">
              <a class="navbar-brand" href="/"><span>Visual Studio Code</span></a>
              <div class="tabloopElement" tabindex="0" style="display: none;"></div><button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse" aria-label="Expand and Collapse Menu">
                          <span class="icon-bar"></span>
                          <span class="icon-bar"></span>
                          <span class="icon-bar"></span>
                </button>
                  </div>
                  <div class="navbar-collapse collapse" style="max-height: min(60vh, 400px);">
              <ul class="nav navbar-nav navbar-left">
                <li><a id="nav-docs" href="/docs">Docs</a></li>
                <li><a id="nav-updates" href="/updates">Updates</a></li>
                <li><a id="nav-blogs" href="/blogs">Blog</a></li>
                <li><a id="nav-extend" href="/api">API</a></li>
                <li><a href="https://marketplace.visualstudio.com/VSCode" target="_blank" rel="noopener" id="nav-extensions">Extensions</a></li>
                <li><a id="nav-faqs" href="/docs/supporting/faq">FAQ</a></li>
                <li class="search visible-xs visible-sm"><a href="/Search">Search</a></li>
                <li><a id="nav-copilot" href="/docs/copilot/overview">GitHub Copilot</a></li>
              </ul>
                      
    
              <ul class="nav navbar-nav navbar-right" role="presentation">
                <li>
                  <button type="button" class="theme-switch" id="theme-toggle">
                    <img class="theme-icon-light" src="/assets/icons/theme-light.svg" alt="Switch to the dark theme">
                    <img class="theme-icon-dark" src="/assets/icons/theme-dark.svg" alt="Switch to the light theme">
                  </button>
                </li>
                <li>
                  <a href="/Search" title="Search" class="btn search-btn" id="nav-search">
                    <img class="search-icon-light" src="/assets/icons/search.svg" width="16px" height="16px" alt="Search">
                    <img class="search-icon-dark" src="/assets/icons/search-dark.svg" width="16px" height="16px" alt="Search">
                  </a>
                </li>
                <li class="search" role="presentation">
                  <form class="nav-search search-form" role="search" aria-label="Search">
                    <div class="input-group" role="presentation">
                      <input type="text" name="q" class="search-box form-control" placeholder="Search Docs" aria-label="Search text">
                      <span class="input-group-btn">
                        <button tabindex="0" class="btn" type="submit" aria-label="Search">
                          <img class="search-icon-dark" src="/assets/icons/search-dark.svg" alt="Search">
                          <img class="search-icon-light" src="/assets/icons/search.svg" alt="Search">
                        </button>
                      </span>
                    </div>
                  </form>						</li>
                <!-- this was hiden in the home and download page, keeping it for now -->
                <li><a class="link-button" href="/Download" id="nav-download">
                <span>Download</span></a><div class="tabloopElement" tabindex="0" style="display: none;"></div></li>
              </ul>
            </div>
          </div>
        </nav>
      </div>
    </div>		<div class="updates-banner home ">
      <div class="container">
            <p class="message">Try <a class="copilot-deep-link" href="vscode://GitHub.Copilot-Chat/chat?mode=agent&amp;referrer=vscode-agentbanner" id="banner-link-updates" rel="noopener">agent mode</a> in VS Code!</p>
      </div>
      <div tabindex="0" role="button" title="Dismiss this update" class="dismiss-btn" id="banner-dismiss-btn"><span class="sr-only">Dismiss this update</span><span aria-hidden="true" class="glyph-icon"></span></div>
    </div>		<!-- This div wraps around the entire site -->
    <!-- The body itself should already have a main tag -->
    <div id="main-content">
      <div class="container home">
    <section class="hero-content col-sm-12">
        <div class="hero-text">
            <h1>Your code editor. Redefined with AI.</h1>
            <div class="download-content-wrapper">
                <div id="download-buttons" class="download-hero alt-downloads linux x64">
                    <!-- Download for user's current OS -->
                    <div class="primary-buttons">
                        <button type="button" class="link-button dlink" data-os="osx" id="download-buttons-osx">Download for macOS</button>
                        <button type="button" class="link-button dlink" data-os="win" id="download-buttons-win">Download for Windows</button>
                        <div class="linux">
                            <button type="button" class="link-button dlink deb-btn" data-os="linux64_deb" id="download-linux64_deb"><img src="/assets/icons/download.svg" width="18px" height="18px" alt="Download VS Code">.deb<small>Debian, Ubuntu...</small></button>
                            <button type="button" class="link-button dlink rpm-btn" data-os="linux64_rpm_repo" id="download-linux64_rpm_repo"><img src="/assets/icons/download.svg" width="18px" height="18px" alt="Download VS Code">.rpm<small>Red Hat, Fedora...</small></button>
                            <div class="collapse" id="linux32-downloads-insiders">
                                <ul class="list-unstyled text-center">
                                    <li><a class="dlink" data-os="linux32_deb" id="download-buttons-linux32_deb"><strong>.deb</strong> (x86)</a></li>
                                    <li><a class="dlink" data-os="linux32_rpm" id="download-buttons-linux32_rpm"><strong>.rpm</strong> (x86)</a></li>
                                    <li><a class="dlink" data-os="linux32" id="download-buttons-linux32"><strong>.tar.gz</strong> (x86)</a></li>
                                </ul>
                            </div>
                        </div>
                        <button type="button" class="link-button dlink other-os" href="/Download">Download<small class="build-type">Stable Build</small></button>
                        <a class="link-button secondary copilot-deep-link" href="vscode://GitHub.Copilot-Chat/chat?mode=agent&amp;referrer=vscode-agentcta" rel="noopener">Try agent mode</a>
                    </div>
                </div>
                <p id="download-matrix-label" class="hero-alt-download-links"><a href="https://vscode.dev/" target="_blank" rel="noopener" title="For quick code edits locally or remotely on GitHub and Azure Repos." id="download-buttons-web">Web</a>, <a href="/insiders" id="download-buttons-insiders">Insiders edition</a>, or <a href="/Download">other platforms</a></p>
                <p class="terms">By using VS Code, you agree to its <span class="wrap-together"><a href="https://code.visualstudio.com/license" target="_blank" rel="noopener" title="View the Visual Studio Code license.">license</a> and <a href="https://go.microsoft.com/fwlink/?LinkId=521839" target="_blank" rel="noopener" title="View the Microsoft privacy statement.">privacy statement</a>.</span></p>
            </div>        </div>
        <div class="hero-video-container" role="img" aria-label="A demonstration animation of VS Code using Copilot Chat, Copilot Edits, Inline Chat, and AI-assisted commit message generation to create and refine a Wordle clone web app built with React and Vite.">
            <video width="1008" height="639" id="hero-video-dark" class="hero-video dark" poster="/assets/home/hero-poster-dark.webp" playsinline="" autoplay="" muted="">
                <source src="/assets/home/hero-dark-sm.webm" type="video/webm" media="(max-width: 991px)">
                <source src="/assets/home/hero-dark-sm.mp4" type="video/mp4" media="(max-width: 991px)">
                <source src="/assets/home/hero-dark-lg.webm" type="video/webm">
                <source src="/assets/home/hero-dark-lg.mp4" type="video/mp4">
            </video>
            <video width="1008" height="639" id="hero-video-light" class="hero-video light" poster="/assets/home/hero-poster-light.webp" playsinline="" autoplay="" muted="">
                <source src="/assets/home/hero-light-sm.webm" type="video/webm" media="(max-width: 991px)">
                <source src="/assets/home/hero-light-sm.mp4" type="video/mp4" media="(max-width: 991px)">
                <source src="/assets/home/hero-light-lg.webm" type="video/webm">
                <source src="/assets/home/hero-light-lg.mp4" type="video/mp4">
            </video>
            <img width="1240" height="831" role="presentation" src="/assets/home/hero-background.webp" alt="">
        </div>
        <div class="video-control">
            <button id="hero-video-button" aria-pressed="false" aria-label="Hero animation is currently playing. Click to pause.">
                Pause
            </button>
        </div>
    </section>
</div>

<div class="container">
    <section class="swimlane row three-col-features">
        <div class="three-col-content">
            <div class="col-sm-4 col-lg-4">
                <div class="three-col-card">
                    <h2>Any model for any team</h2>
                    <p>Use AI models like Claude Sonnet out of the box, or bring your own key to access models from
                        Azure,
                        Anthropic, Google, Ollama, OpenAI, and OpenRouter.</p>
                    <div>
                        <img src="/assets/home/choose-model-dark.webp" class="swimlane-image dark" loading="lazy" alt="Dropdown menu in GitHub Copilot Chat displaying AI model options: 'Claude 3.7 Sonnet' selected, with other options like 'Claude 3.5 Sonnet', 'GPT 4.5', 'GPT 4o', and 'Manage Models...'">
                        <img src="/assets/home/choose-model-light.webp" class="swimlane-image light" loading="lazy" alt="Dropdown menu in GitHub Copilot Chat displaying AI model options: 'Claude 3.7 Sonnet' selected, with other options like 'Claude 3.5 Sonnet', 'GPT 4.5', 'GPT 4o', and 'Manage Models...'">
                    </div>
                </div>
            </div>

            <div class="col-sm-4 col-lg-4">
                <div class="three-col-card">
                    <h2>An expert on your codebase</h2>
                    <p>Your codebase is indexed locally and remotely (on GitHub) to understand what's relevant, enabling
                        fast, context-aware interactions.</p>
                    <div>
                        <img src="/assets/home/an-expert-on-your-codebase-dark.webp" class="swimlane-image dark" loading="lazy" alt="A VS Code chat prompt. The prompt includes codebase and file context by writing #codebase and #file:HistoryView.swift in the message.">
                        <img src="/assets/home/an-expert-on-your-codebase-light.webp" class="swimlane-image light" loading="lazy" alt="A VS Code chat prompt. The prompt includes codebase and file context by writing #codebase and #file:HistoryView.swift in the message.">
                    </div>
                </div>
            </div>
            <div class="col-sm-4 col-lg-4">
                <div class="three-col-card">
                    <h2>AI that works the way your team does</h2>
                    <p>Personalize interactions using custom instructions and reusable prompt files tailored to your
                        workflows, tools, and projects.</p>
                    <div>
                        <img src="/assets/home/instructions-dark.webp" class="swimlane-image dark" loading="lazy" alt="Settings JSON for copilot instructions, the first set to `use React functional components', then including another file for extra instructions 'code-style.md'.">
                        <img src="/assets/home/instructions-light.webp" class="swimlane-image light" loading="lazy" alt="Settings JSON for copilot instructions, the first set to `use React functional components', then including another file for extra instructions 'code-style.md'.">
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section class="swimlane row">
        <div class="copilot-free-banner">
            <div class="col-sm-6 col-lg-6">
                <h2>Use AI features in VS Code for free</h2>
            </div>
            <div class="col-sm-6 col-lg-6">
                <p>No trial. No credit card required. Just your GitHub account.</p>
                <a class="link-button secondary copilot-deep-link" href="vscode://GitHub.Copilot-Chat/chat?mode=agent&amp;referrer=vscode-agentmainbanner" rel="noopener">Try free</a>
            </div>
        </div>
    </section>

    <section class="swimlane row">
        <div class="swimlane-content">
            <div class="col-sm-6 col-lg-4">
                <div class="secondary-value-prop">
                    <h2>Agent mode</h2>
                    <p>Tackle complex, multi-step tasks. Agent mode reads your codebase, suggests edits across files,
                        runs terminal commands, and responds to compile or test failures — all in a loop until the job
                        is done. Further refine agent mode to fit your team's workflows with VS Code extensions and
                        Model Context Protocol (MCP) servers.</p>
                    <a href="https://code.visualstudio.com/docs/copilot/chat/chat-agent-mode" rel="noopener">Build with
                        agent mode</a>
                </div>
            </div>
            <div class="col-sm-6 col-lg-8">
                <img src="/assets/home/swimlane-chat-dark.webp" class="swimlane-image dark" loading="lazy" alt="VS Code window showing a code editor with projects.tsx open, alongside a chat panel in Agent mode. The chat discusses an open issue from GitHub.">
                <img src="/assets/home/swimlane-chat-light.webp" class="swimlane-image light" loading="lazy" alt="VS Code window showing a code editor with projects.tsx open, alongside a chat panel in Agent mode. The chat discusses an open issue from GitHub.">
            </div>
        </div>
    </section>

    <section class="swimlane row">
        <div class="swimlane-content">
            <div class="col-sm-6 col-lg-4">
                <div class="value-prop-intro">
                    <h2>Next Edit Suggestions</h2>
                    <p>VS Code predicts your next move as you code. Use the Tab key to accept AI-powered
                        suggestions right in your editor. It intelligently recommends what to change — and where — based
                        on the edits you're already making.</p>
                    <a href="https://code.visualstudio.com/docs/copilot/ai-powered-suggestions#_next-edit-suggestions" rel="noopener">Code with AI-powered suggestions</a>
                </div>
            </div>
            <div class="col-sm-6 col-lg-8">
                <img src="/assets/home/swimlane-nes-dark.webp" class="swimlane-image dark" loading="lazy" alt="Code editor showing a JavaScript file post.js. It defines a render method that renders a social media post by calling an external API. Next Edit Suggestions is suggesting how to complete the implementation.">
                <img src="/assets/home/swimlane-nes-light.webp" class="swimlane-image light" loading="lazy" alt="Code editor showing a JavaScript file post.js. It defines a render method that renders a social media post by calling an external API. Next Edit Suggestions is suggesting how to complete the implementation.">
            </div>
        </div>
    </section>

    <section class="extensions-container row">
        <div class="extensions-container-content row">
            <div class="col-sm-6 col-lg-4">
                <h2>Code with extensions</h2>
                <p>Customize VS Code with AI-powered functionality from extensions and Model Context Protocol servers to
                    use in Chat. Or, <a href="https://code.visualstudio.com/docs/copilot/copilot-extensibility-overview">build your own
                        extension</a> to power your team's unique scenarios.
                </p>
            </div>
            <div class="col-sm-6 col-lg-8">
                <div class="extensions-grid-container">
                    <div class="extensions-grid">
                        <a href="https://marketplace.visualstudio.com/items?itemName=ms-python.python" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/python-extension.png" loading="lazy" alt="Python extension icon">
                            <div class="extension-tile-details">
                                <h3>Python</h3>
                                <p>Adds rich language support for Python</p>
                            </div>
                        </a>
                        <a href="https://marketplace.visualstudio.com/items?itemName=Stripe.vscode-stripe" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/stripe-extension.png" loading="lazy" alt="Stripe extension icon">
                            <div class="extension-tile-details">
                                <h3>Stripe</h3>
                                <p>Build, test, and use Stripe inside your editor</p>
                            </div>
                        </a>
                        <a href="https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/c-extension.png" loading="lazy" alt="C/C extension icon">
                            <div class="extension-tile-details">
                                <h3>C/C++</h3>
                                <p>Adds rich language support for C/C++</p>
                            </div>
                        </a>
                    </div>
                    <div class="extensions-grid">
                        <a href="https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/jupyter-extension.png" loading="lazy" alt="Jupyter extension icon">
                            <div class="extension-tile-details">
                                <h3>Jupyter</h3>
                                <p>Language support for Jupyter Notebooks</p>
                            </div>
                        </a>
                        <a href="https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/gitlens-extension.png" loading="lazy" alt="GitLens extension icon">
                            <div class="extension-tile-details">
                                <h3>GitLens</h3>
                                <p>Supercharge your Git experience</p>
                            </div>
                        </a>
                        <a href="https://marketplace.visualstudio.com/items?itemName=ms-dotnettools.csdevkit" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/cs-dev-kit-extension.png" loading="lazy" alt="C# Dev Kit extension icon">
                            <div class="extension-tile-details">
                                <h3>C# Dev Kit</h3>
                                <p>Powerful tools for your C# environment</p>
                            </div>
                        </a>
                    </div>
                    <div class="extensions-grid">
                        <a href="https://marketplace.visualstudio.com/items?itemName=mongodb.mongodb-vscode" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/mongodb-extension.png" loading="lazy" alt="MongoDB extension icon">
                            <div class="extension-tile-details">
                                <h3>MongoDB</h3>
                                <p>Extension for the @MongoDB agent</p>
                            </div>
                        </a>
                        <a href="https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azure-github-copilot" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/azure.png" loading="lazy" alt="GitHub Copilot for Azure extension icon">
                            <div class="extension-tile-details">
                                <h3>GitHub Copilot for Azure</h3>
                                <p>Streamline the process of developing for Azure</p>
                            </div>
                        </a>
                        <a href="https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack" target="_blank" rel="noopener" class="extension-tile">
                            <img src="/assets/images/remote-extension.png" loading="lazy" alt="Remote Development extension icon">
                            <div class="extension-tile-details">
                                <h3>Remote Development</h3>
                                <p>Open folders in a container on a remote machine</p>
                            </div>
                        </a>
                    </div>
                </div>
                <div class="extensions-grid-caption">
                    <p>View 60k+ extensions in the <a href="https://marketplace.visualstudio.com/vscode" rel="noopener" target="_blank">Extension Marketplace</a></p>
                </div>
            </div>
        </div>
    </section>

    <section class="swimlane row">
        <div class="swimlane-content">
            <div class="col-sm-6 col-lg-4">
                <div class="value-prop-intro">
                    <h2>Code in any language</h2>
                    <p>VS Code supports almost every major programming language. Several ship in the box, like
                        JavaScript,
                        TypeScript, CSS, and HTML, but extensions for others can be found in the VS Code Marketplace.
                    </p>
                </div>
            </div>
            <div class="languages col-sm-6 col-lg-8">
                <div><img src="/assets/home/language-js.png" alt="JavaScript icon"><code>JavaScript</code></div>
                <div><img src="/assets/home/language-ts.png" alt="TypeScript icon"><code>TypeScript</code></div>
                <div><img src="/assets/home/language-python.png" alt="Python icon"><code>Python</code></div>
                <div><img src="/assets/home/language-cs.png" alt="C# icon"><code>C#</code></div>
                <div><img src="/assets/home/language-cpp.png" alt="C++ icon"><code>C++</code></div>
                <div><img src="/assets/home/language-html.png" alt="HTML icon"><code>HTML</code></div>
                <div><img src="/assets/home/language-java.png" alt="Java icon"><code>Java</code></div>
                <div><img src="/assets/home/language-json.png" alt="JSON icon"><code>JSON</code></div>
                <div><img src="/assets/home/language-php.png" alt="PHP icon"><code>PHP</code></div>
                <div><img src="/assets/home/language-markdown.png" alt="Markdown icon"><code>Markdown</code></div>
                <div><img src="/assets/home/language-powershell.png" alt="Powershell icon"><code>Powershell</code></div>
                <div><img src="/assets/home/language-yaml.png" alt="YAML icon"><code>YAML</code></div>
            </div>
        </div>
    </section>

    <section class="swimlane row fully-customizable-swimlane">
        <div class="swimlane-content">
            <div class="col-sm-6 col-lg-4">
                <div class="value-prop-intro">
                    <h2>Fully customizable</h2>
                    <p>Customize your VS Code UI and layout so that it fits your coding style.</p>
                </div>
                <div class="secondary-value-prop">
                    <p><a href="https://code.visualstudio.com/docs/configure/themes" rel="noopener">Color themes</a>
                        let you modify the colors in VS Code's user interface to suit your preferences and work
                        environment.</p>
                </div>
                <div class="secondary-value-prop">
                    <p><a href="https://code.visualstudio.com/docs/configure/settings#_settings-sync" rel="noopener" class="value-prop-bold">Settings Sync</a> enables you to share your user settings across
                        your VS Code instances with the Settings Sync feature.</p>
                </div>
                <div class="secondary-value-prop">
                    <p><a href="https://code.visualstudio.com/docs/configure/profiles" rel="noopener" class="value-prop-bold">Profiles</a> let you create sets of customizations and quickly
                        switch between them or share them with others.</p>
                </div>
            </div>
            <div class="col-sm-6 col-lg-8">
                <img src="/assets/home/swimlane-customized.png" class="swimlane-image dark" loading="lazy" alt="Selecting the GitHub Dark theme with a quick pick">
                <img src="/assets/home/swimlane-customized-light.png" class="swimlane-image light" loading="lazy" alt="Selecting the GitHub Dark theme with a quick pick">
            </div>
        </div>
    </section>

    <section class="swimlane row code-anywhere-swimlane">
        <div class="swimlane-content">
            <div class="col-sm-6 col-lg-4">
                <div class="value-prop-intro">
                    <h2>Code anywhere</h2>
                    <p>Code wherever you're most productive, whether you're connected to the cloud, a remote repository,
                        or in the browser with VS Code for the Web (vscode.dev).</p>
                </div>
                <div class="secondary-value-prop">
                    <p><a href="https://code.visualstudio.com/docs/sourcecontrol/overview" rel="noopener">Built-in
                            Source Control</a> empowers you with Git support out-of-the-box. Many other source control
                        providers are available through extensions.</p>
                </div>
                <div class="secondary-value-prop">
                    <p><a href="https://code.visualstudio.com/docs/remote/codespaces" rel="noopener" class="value-prop-bold">GitHub Codespaces</a> provides cloud-powered development
                        environments for any activity - whether it's a long-term project, or a short-term task like
                        reviewing a pull request.</p>
                </div>
            </div>
            <div class="col-sm-6 col-lg-8">
                <img src="/assets/home/swimlane-anywhere.png" class="swimlane-image dark" loading="lazy" alt="vscode.dev in an Edge browser tab">
                <img src="/assets/home/swimlane-anywhere-light.png" class="swimlane-image light" loading="lazy" alt="vscode.dev in an Edge browser tab">
            </div>
        </div>
    </section>

    <section class="rich-features row">
        <div class="secondary-tagline col-sm-12">
            <h2>Code with rich features</h2>
            <p>There's a lot more to an editor. Whether it's using built-in features or rich extensions, there's
                something for everyone.</p>
        </div>
        <div class="feature-grid col-sm-12">
            <a href="https://code.visualstudio.com/docs/terminal/basics" class="feature-card">
                <img src="/assets/icons/codicon-terminal.svg" alt="terminal icon">
                <h3 class="feature-card-title">Integrated terminal</h3>
                <p>Use your favorite shell whether it's zsh, pwsh, or git bash, all inside the editor.
                </p>
            </a>
            <a href="https://code.visualstudio.com/docs/debugtest/debugging" class="feature-card">
                <img src="/assets/icons/codicon-debug.svg" alt="debug icon">
                <h3 class="feature-card-title">Run code</h3>
                <p>Run and debug your code without leaving your editor.</p>
            </a>
            <a href="https://code.visualstudio.com/docs/sourcecontrol/overview" class="feature-card">
                <img src="/assets/icons/codicon-version-control.svg" alt="branching icon">
                <h3 class="feature-card-title">Version control</h3>
                <p>Built-in support for git and many other source control providers.</p>
            </a>
            <a href="https://code.visualstudio.com/docs/debugtest/tasks" class="feature-card">
                <img src="/assets/icons/codicon-build-tasks.svg" alt="tools icon">
                <h3 class="feature-card-title">Build tasks</h3>
                <p>Run tools and analyze their results from within VS Code.</p>
            </a>
            <a href="https://code.visualstudio.com/updates/v1_66#_local-history" class="feature-card">
                <img src="/assets/icons/codicon-local-history.svg" alt="history icon">
                <h3 class="feature-card-title">Local history</h3>
                <p>Never lose your changes with automatically tracked local history.</p>
            </a>
            <a href="https://code.visualstudio.com/docs/configure/themes" class="feature-card">
                <img src="/assets/icons/codicon-themes.svg" alt="palette icon">
                <h3 class="feature-card-title">Themes</h3>
                <p>Your theme is an extension of your personality. Add some flair to your editor and add your touch.</p>
            </a>
            <a href="https://code.visualstudio.com/docs/configure/accessibility/accessibility" class="feature-card">
                <img src="/assets/icons/codicon-accessibility.svg" alt="keyboard icon">
                <h3 class="feature-card-title">Accessibility</h3>
                <p>Optimized experience for screen readers, high contrast themes, and keyboard-only navigation.</p>
            </a>
            <a href="https://code.visualstudio.com/docs/setup/vscode-web" class="feature-card">
                <img src="/assets/icons/codicon-web.svg" alt="globe icon">
                <h3 class="feature-card-title">Web support</h3>
                <p>Whether you are on your phone, tablet, or desktop, you can access your code from anywhere.</p>
            </a>
        </div>
    </section>
</div>


</div>
    </div>
  

  <footer role="contentinfo" class="container">
    <div class="footer-container">
      <div class="footer-row">
        <div class="footer-social">
          <ul class="links">
            <li>
              <a href="https://go.microsoft.com/fwlink/?LinkID=533687"><img src="/assets/icons/x-icon.svg" class="x-icon" alt="Follow us on X"></a>
            </li>
            <li>
              <a href="https://github.com/microsoft/vscode"><img src="/assets/icons/github-icon.svg" alt="VS Code on Github"></a>
            </li>
            <li>
              <a href="https://www.youtube.com/@code"><img src="/assets/icons/youtube-icon.svg" alt="VS Code on YouTube"></a>
            </li>
          </ul>
          <a id="footer-microsoft-link" class="microsoft-logo" href="https://www.microsoft.com">
            <img src="/assets/icons/microsoft.svg" alt="Microsoft homepage">
          </a>
        </div>
      </div>
      <div class="footer-row">
        <ul class="links">
          <li><a id="footer-support-link" href="https://support.serviceshub.microsoft.com/supportforbusiness/create?sapId=d66407ed-3967-b000-4cfb-2c318cad363d" target="_blank" rel="noopener">Support</a></li>
          <li><a id="footer-privacy-link" href="https://go.microsoft.com/fwlink/?LinkId=521839" target="_blank" rel="noopener">Privacy</a></li>
          <li style=""><a id="footer-cookie-link" style="cursor: pointer;" onclick="manageConsent()" target="_blank" rel="noopener">Manage Cookies</a></li>
          <li><a id="footer-terms-link" href="https://www.microsoft.com/legal/terms-of-use" target="_blank" rel="noopener">Terms of Use</a></li>
          <li><a id="footer-license-link" href="/License" target="_blank" rel="noopener">License</a></li>
        </ul>
      </div>
    </div>
  </footer>


</div>

  </template>