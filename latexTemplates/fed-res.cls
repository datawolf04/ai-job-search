%% Start of file `fed-res.cls'.
% Federal Resume Class File

%-------------------------------------------------------------------------------
%                Identification
%-------------------------------------------------------------------------------
\ProvidesClass{fed-res}
\NeedsTeXFormat{LaTeX2e}

%-------------------------------------------------------------------------------
%                Class options
%-------------------------------------------------------------------------------
% Options for draft or final
\DeclareOption{draft}{\setlength\overfullrule{5pt}}
\DeclareOption{final}{\setlength\overfullrule{0pt}}

% Inherit options of article
\DeclareOption*{%
  \PassOptionsToClass{\CurrentOption}{article}
}
\ProcessOptions\relax
\LoadClass{article}

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------------------------------------------------------------
%                3rd party packages
%-------------------------------------------------------------------------------
\RequirePackage{latexsym}
\RequirePackage[empty]{fullpage}
\RequirePackage{titlesec}
\RequirePackage{marvosym}
\RequirePackage[usenames,dvipsnames]{color}
\RequirePackage{verbatim}
\RequirePackage{enumitem} % Handles list environments
\RequirePackage[hidelinks]{hyperref} % Settings for hyperlinks
\RequirePackage{fancyhdr} % Create header and footer
\RequirePackage[english]{babel}
\RequirePackage{csquotes}
\RequirePackage{tabularx} % Allows tables with automatically varying column widths
\RequirePackage[export]{adjustbox} % Allows for easy resizing of tables or figures to fit page width
\RequirePackage{indentfirst} % Allows first paragraph in new section to have indentation

\input{glyphtounicode}

% To use bib file for publication information
% Sorting=ydnt gives reverse year then name then title
% Maxbibnames and minbibnames define number of authors before et al.
% Uniquelist requires additional authors to be added such that each publication has a unique list of authors
\usepackage[backend=biber,style=authoryear,sorting=ydnt, maxbibnames=1,
minbibnames=1,uniquelist=false]{biblatex}
\addbibresource{citations.bib} % Read in citations from citations.bib - uncomment if using biblatex to generate publications list
\setlength\bibitemsep{1em} % Set separation between multiple citations

%-------------------------------------------------------------------------------
%                Configuration for document layout and style
%-------------------------------------------------------------------------------
\pagestyle{fancy}
\fancyhf{} % Clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\setlength{\footskip}{4.4pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}

\urlstyle{same}

\raggedbottom
\raggedright
\newlength{\oldtabcolsep} % Define variable for original table column separation
\setlength{\oldtabcolsep}{\tabcolsep} % Save original table column separation for later use
\setlength{\tabcolsep}{0pt} % Change table column separation to 0pt

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

%-------------------------------------------------------------------------------
%                Configuration for resume entry elements
%-------------------------------------------------------------------------------

% For a single bulleted item, useful for narrative descriptions of experience
\newcommand{\resumeItem}[1]{
  \item{
    {#1 \vspace{-2pt}}
  }
}

% For a volunteer experience or education item (includes location but no supervisor info or hours worked)
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{#3} & \textit{ #4} \\
    \end{tabular*}\vspace{-7pt}
}

% For a volunteer experience or job related training item without a location
\newcommand{\resumeSubheadingShort}[2]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
    \end{tabular*}\vspace{-7pt}
}

% For a work experience item including supervisor info and hours worked
\newcommand{\resumeSubheadingWork}[6]{
  \vspace{-2pt}\item
    \begin{tabularx}{0.97\textwidth}[t]{l >{\raggedleft\arraybackslash}X} % X means the right column takes up any leftover space from the left up to the defined table width - see tabularx docs for more info
      \textbf{#1} & #2 \\
      \textit{#3} & \textit{ #4} \\
    \end{tabularx}
    \begin{tabularx}{0.97\textwidth}[t]{l >{\raggedleft\arraybackslash}X}
      #5 & #6 \\
    \end{tabularx}\vspace{-7pt}
}

% Optional style for multiple work positions
\newcommand{\resumeSubSubheading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{#1} & #2 \\
    \end{tabular*}\vspace{-7pt}
}

% Optional style for projects
\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      #1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

% Define list environments start and end
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

% A quick style for publications/citations without using biblatex
% Just put all the text you want the citation to have for [1] and the hanging indent will automatically be applied
% Usage: \cvpub{<citation>}
\newcommand*{\cvpub}[1]{%
	\leftskip 1.1cm
    \parindent -0.7cm
    {#1}\vspace{3pt}
}
